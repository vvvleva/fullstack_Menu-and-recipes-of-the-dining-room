"""Инференс обученной модели."""
import torch
import numpy as np
from typing import List, Dict, Optional, Union
import pickle
from pathlib import Path

from .model import AllergenClassifier


class AllergenPredictor:
    """Класс для предсказания аллергенов с использованием обученной модели."""
    
    def __init__(self, model_path: Optional[str] = None):
        self.model = None
        self.metadata = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        if model_path:
            self.load_model(model_path)
    
    def load_model(self, model_path: Union[str, Path]):
        """Загружает модель и метаданные."""
        model_path = Path(model_path)
        metadata_path = model_path.parent / 'metadata.pkl'
        
        # Загружаем метаданные
        if metadata_path.exists():
            with open(metadata_path, 'rb') as f:
                self.metadata = pickle.load(f)
            print(f"Метаданные загружены из {metadata_path}")
        
        # Загружаем модель
        self.model = AllergenClassifier.load(str(model_path), str(self.device))
        print(f"Модель загружена из {model_path}")
        
        return self
    
    def preprocess_ingredients(self, ingredients_text: str) -> torch.Tensor:
        """
        Преобразует текст ингредиентов в тензор.
        
        Args:
            ingredients_text: строка с ингредиентами (например, "мука, яйца, молоко")
        
        Returns:
            тензор для модели
        """
        if self.metadata is None:
            raise ValueError("Метаданные не загружены. Сначала вызовите load_model()")
        
        # Нормализуем текст
        ingredients_text = ingredients_text.lower().strip()
        
        # Разбиваем на слова
        words = ingredients_text.replace(',', ' ').split()
        
        # Преобразуем в последовательность индексов
        vocab = self.metadata['ingredient_vocab']
        max_len = self.metadata['max_ingredients_len']
        
        sequence = []
        for word in words:
            if word in vocab:
                sequence.append(vocab[word])
            else:
                sequence.append(vocab['<UNK>'])
        
        # Обрезаем или дополняем
        if len(sequence) > max_len:
            sequence = sequence[:max_len]
        else:
            sequence += [vocab['<PAD>']] * (max_len - len(sequence))
        
        # Преобразуем в тензор
        tensor = torch.LongTensor(sequence).unsqueeze(0).to(self.device)
        
        return tensor
    
    def predict(
        self,
        ingredients_text: str,
        threshold: float = 0.5,
        return_probabilities: bool = False
    ) -> Dict:
        """
        Предсказывает аллергены для заданных ингредиентов.
        
        Args:
            ingredients_text: строка с ингредиентами
            threshold: порог уверенности для бинаризации
            return_probabilities: возвращать ли вероятности всех классов
        
        Returns:
            словарь с результатами
        """
        if self.model is None:
            raise ValueError("Модель не загружена. Сначала вызовите load_model()")
        
        # Предобработка
        input_tensor = self.preprocess_ingredients(ingredients_text)
        
        # Предсказание
        self.model.eval()
        with torch.no_grad():
            logits = self.model(input_tensor)
            probabilities = torch.sigmoid(logits).cpu().numpy()[0]
        
        # Получаем названия аллергенов
        allergen_names = self.metadata['allergen_names']
        
        # Находим аллергены выше порога
        indices = np.where(probabilities >= threshold)[0]
        
        allergens_found = []
        for idx in indices:
            allergens_found.append({
                'allergen': allergen_names[idx],
                'probability': float(probabilities[idx])
            })
        
        # Сортируем по вероятности
        allergens_found.sort(key=lambda x: x['probability'], reverse=True)
        
        result = {
            'ingredients': ingredients_text,
            'allergens_found': allergens_found,
            'confidence': float(np.mean(probabilities)) if len(probabilities) > 0 else 0.0,
            'num_allergens_detected': len(allergens_found)
        }
        
        if return_probabilities:
            result['all_probabilities'] = {
                name: float(prob)
                for name, prob in zip(allergen_names, probabilities)
            }
        
        return result
    
    def analyze_dish(
        self,
        dish_ingredients: List[str],
        user_allergens: List[str],
        threshold: float = 0.5
    ) -> Dict:
        """
        Анализирует блюдо на предмет аллергенов пользователя.
        
        Args:
            dish_ingredients: список ингредиентов блюда
            user_allergens: список аллергенов пользователя
            threshold: порог уверенности
        
        Returns:
            анализ с информацией о найденных аллергенах
        """
        # Объединяем ингредиенты в текст
        ingredients_text = ' '.join(dish_ingredients)
        
        # Получаем предсказание модели
        prediction = self.predict(ingredients_text, threshold=0.3)  # Ниже порог для большей чувствительности
        
        # Фильтруем только аллергены пользователя
        user_allergens_set = set(a.lower() for a in user_allergens)
        
        relevant_allergens = []
        for allergen_info in prediction['allergens_found']:
            allergen = allergen_info['allergen'].lower()
            
            # Проверяем, есть ли аллерген в списке пользователя
            for user_allergen in user_allergens_set:
                if user_allergen in allergen or allergen in user_allergen:
                    relevant_allergens.append({
                        **allergen_info,
                        'matched_user_allergen': user_allergen
                    })
                    break
        
        # Определяем уровень риска
        risk_level = 'safe'
        if relevant_allergens:
            # Проверяем высокорисковые аллергены
            high_risk_allergens = {'арахис', 'орехи', 'морепродукты'}
            for allergen in relevant_allergens:
                if any(hr in allergen['allergen'].lower() for hr in high_risk_allergens):
                    risk_level = 'danger'
                    break
            else:
                risk_level = 'warning'
        
        return {
            'dish_ingredients': dish_ingredients,
            'user_allergens': user_allergens,
            'risk_level': risk_level,
            'allergens_found': relevant_allergens,
            'model_confidence': prediction['confidence'],
            'safe_to_eat': len(relevant_allergens) == 0
        }


# Создаем глобальный экземпляр для использования в роутах
predictor = None


def get_predictor():
    """Возвращает глобальный экземпляр предиктора."""
    global predictor
    if predictor is None:
        model_path = Path(__file__).parent / 'models' / 'best_model.pt'
        if model_path.exists():
            predictor = AllergenPredictor(str(model_path))
        else:
            print(f"Модель не найдена по пути {model_path}")
            print("Сначала запустите обучение: python -m services.nn_model.train")
    return predictor