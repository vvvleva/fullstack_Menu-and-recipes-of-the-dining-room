"""Загрузка и подготовка датасета Food Ingredients and Allergens."""
import os
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Set, Optional
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, MultiLabelBinarizer
import re
import pickle
from collections import Counter
import requests
import zipfile
from pathlib import Path

# Константы
DATA_DIR = Path(__file__).parent / "data"
MODELS_DIR = Path(__file__).parent / "models"
DATA_URL = "https://www.kaggle.com/api/v1/datasets/download/uom190346a/food-ingredients-and-allergens"
DATASET_FILE = "food_ingredients_and_allergens.csv"

# Создаем директории
DATA_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)


class AllergenDataset:
    """
    Класс для загрузки и подготовки датасета Food Ingredients and Allergens.
    
    Датасет содержит:
    - Food Product: название продукта
    - Main Ingredient: основной ингредиент
    - Sweetener: подсластитель
    - Fat/Oil: жир/масло
    - Seasoning: приправы
    - Allergens: список аллергенов
    - Prediction: метка класса
    """
    
    def __init__(self, use_cache: bool = True):
        self.use_cache = use_cache
        self.df = None
        self.label_encoder = LabelEncoder()
        self.mlb = MultiLabelBinarizer()
        self.all_allergens = set()
        self.ingredient_vocab = {}
        self.vocab_size = 0
        self.max_ingredients_len = 0
        
        # Загружаем или скачиваем датасет
        self._ensure_dataset()
        
    def _ensure_dataset(self):
        """Проверяет наличие датасета и скачивает при необходимости."""
        dataset_path = DATA_DIR / DATASET_FILE
        
        if not dataset_path.exists():
            print(f"Датасет не найден. Скачиваю с Kaggle...")
            self._download_dataset()
        else:
            print(f"Датасет найден: {dataset_path}")
    
    def _download_dataset(self):
        """
        Скачивает датасет с Kaggle.
        
        Примечание: требуется установленный kaggle API ключ.
        Альтернативно можно скачать вручную с:
        https://www.kaggle.com/datasets/uom190346a/food-ingredients-and-allergens
        """
        try:
            # Пытаемся использовать kaggle API
            import kaggle
            kaggle.api.dataset_download_files(
                'uom190346a/food-ingredients-and-allergens',
                path=str(DATA_DIR),
                unzip=True
            )
            print("Датасет успешно загружен!")
        except Exception as e:
            print(f"Не удалось загрузить через Kaggle API: {e}")
            print("\nПожалуйста, скачайте датасет вручную:")
            print("1. Перейдите на https://www.kaggle.com/datasets/uom190346a/food-ingredients-and-allergens")
            print("2. Скачайте архив и распакуйте в папку:")
            print(f"   {DATA_DIR}")
            print("3. Убедитесь, что файл называется: food_ingredients_and_allergens.csv")
            raise
    
    def load_data(self) -> pd.DataFrame:
        """Загружает данные из CSV файла."""
        dataset_path = DATA_DIR / DATASET_FILE
        
        if not dataset_path.exists():
            raise FileNotFoundError(
                f"Датасет не найден: {dataset_path}\n"
                "Пожалуйста, скачайте его с Kaggle."
            )
        
        # Загружаем датасет
        self.df = pd.read_csv(dataset_path)
        print(f"Загружено {len(self.df)} записей")
        print(f"Колонки: {list(self.df.columns)}")
        
        # Очищаем данные
        self._clean_data()
        
        return self.df
    
    def _clean_data(self):
        """Очистка и предобработка данных."""
        if self.df is None:
            return
        
        # Удаляем пустые строки
        self.df = self.df.dropna(subset=['Food Product', 'Main Ingredient'])
        
        # Нормализуем текстовые поля
        text_columns = ['Main Ingredient', 'Sweetener', 'Fat/Oil', 'Seasoning', 'Allergens']
        for col in text_columns:
            if col in self.df.columns:
                self.df[col] = self.df[col].fillna('').astype(str).apply(
                    lambda x: self._normalize_text(x)
                )
        
        # Парсим аллергены (могут быть через запятую или точку с запятой)
        self.df['allergens_list'] = self.df['Allergens'].apply(
            lambda x: self._parse_allergens(x)
        )
        
        # Собираем все уникальные аллергены
        for allergens in self.df['allergens_list']:
            self.all_allergens.update(allergens)
        
        print(f"Найдено {len(self.all_allergens)} уникальных аллергенов")
        
        # Создаем комбинированное поле ингредиентов
        self.df['combined_ingredients'] = self.df.apply(
            lambda row: self._combine_ingredients(row), axis=1
        )
        
        # Строим словарь ингредиентов
        self._build_vocabulary()
    
    def _normalize_text(self, text: str) -> str:
        """Нормализация текста."""
        if pd.isna(text):
            return ""
        text = str(text).lower().strip()
        # Удаляем пунктуацию, кроме запятых и точек с запятой (разделители)
        text = re.sub(r'[^\w\s,;]', ' ', text)
        # Убираем множественные пробелы
        text = re.sub(r'\s+', ' ', text)
        return text
    
    def _parse_allergens(self, allergens_text: str) -> List[str]:
        """Парсит строку с аллергенами в список."""
        if not allergens_text or pd.isna(allergens_text):
            return []
        
        # Разделяем по запятым или точкам с запятой
        parts = re.split(r'[,;]', allergens_text)
        allergens = []
        
        for part in parts:
            allergen = part.strip().lower()
            if allergen and allergen not in ['none', 'no', '']:
                allergens.append(allergen)
        
        return allergens
    
    def _combine_ingredients(self, row) -> str:
        """Объединяет все ингредиенты в одну строку."""
        ingredients = []
        
        for col in ['Main Ingredient', 'Sweetener', 'Fat/Oil', 'Seasoning']:
            if col in row and row[col] and not pd.isna(row[col]):
                ingredients.append(str(row[col]))
        
        return ' '.join(ingredients)
    
    def _build_vocabulary(self, min_freq: int = 2):
        """Строит словарь ингредиентов."""
        all_words = []
        
        for text in self.df['combined_ingredients']:
            words = text.split()
            all_words.extend(words)
        
        # Считаем частоту слов
        word_freq = Counter(all_words)
        
        # Строим словарь (индекс 0 для паддинга, 1 для неизвестных слов)
        self.ingredient_vocab = {
            '<PAD>': 0,
            '<UNK>': 1
        }
        
        idx = 2
        for word, freq in word_freq.items():
            if freq >= min_freq:
                self.ingredient_vocab[word] = idx
                idx += 1
        
        self.vocab_size = len(self.ingredient_vocab)
        self.max_ingredients_len = int(np.percentile(
            [len(text.split()) for text in self.df['combined_ingredients']], 95
        ))
        
        print(f"Размер словаря: {self.vocab_size}")
        print(f"Максимальная длина последовательности: {self.max_ingredients_len}")
    
    def text_to_sequence(self, text: str) -> List[int]:
        """Преобразует текст в последовательность индексов."""
        words = text.split()
        sequence = []
        
        for word in words:
            if word in self.ingredient_vocab:
                sequence.append(self.ingredient_vocab[word])
            else:
                sequence.append(self.ingredient_vocab['<UNK>'])
        
        # Обрезаем или дополняем до максимальной длины
        if len(sequence) > self.max_ingredients_len:
            sequence = sequence[:self.max_ingredients_len]
        else:
            sequence += [self.ingredient_vocab['<PAD>']] * (self.max_ingredients_len - len(sequence))
        
        return sequence
    
    def prepare_data(self, test_size: float = 0.2, random_state: int = 42):
        """
        Подготавливает данные для обучения.
        
        Returns:
            X_train, X_test, y_train, y_test, allergen_names
        """
        if self.df is None:
            self.load_data()
        
        # Преобразуем аллергены в мульти-лейбл формат
        y = self.mlb.fit_transform(self.df['allergens_list'])
        allergen_names = self.mlb.classes_
        
        # Преобразуем ингредиенты в последовательности
        X = np.array([
            self.text_to_sequence(text) 
            for text in self.df['combined_ingredients']
        ])
        
        # Разделяем на train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )
        
        print(f"Размер обучающей выборки: {len(X_train)}")
        print(f"Размер тестовой выборки: {len(X_test)}")
        print(f"Количество классов аллергенов: {len(allergen_names)}")
        
        # Сохраняем метаданные
        self._save_metadata(allergen_names)
        
        return X_train, X_test, y_train, y_test, allergen_names
    
    def _save_metadata(self, allergen_names):
        """Сохраняет метаданные модели."""
        metadata = {
            'vocab_size': self.vocab_size,
            'max_ingredients_len': self.max_ingredients_len,
            'ingredient_vocab': self.ingredient_vocab,
            'allergen_names': list(allergen_names),
            'num_classes': len(allergen_names)
        }
        
        metadata_path = MODELS_DIR / 'metadata.pkl'
        with open(metadata_path, 'wb') as f:
            pickle.dump(metadata, f)
        
        print(f"Метаданные сохранены в {metadata_path}")