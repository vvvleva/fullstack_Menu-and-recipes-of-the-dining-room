"""Обучение нейросетевой модели."""
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import numpy as np
from typing import Dict, List, Optional, Tuple
from tqdm import tqdm
import matplotlib.pyplot as plt
from pathlib import Path

from .dataset import AllergenDataset
from .model import AllergenClassifier
from .predict import AllergenPredictor

# Константы
MODELS_DIR = Path(__file__).parent / "models"
MODELS_DIR.mkdir(exist_ok=True)


class AllergenTrainer:
    """Тренер для обучения модели классификации аллергенов."""
    
    def __init__(
        self,
        model: nn.Module,
        device: str = None,
        learning_rate: float = 0.001,
        weight_decay: float = 1e-5
    ):
        self.model = model
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(self.device)
        
        # Оптимизатор
        self.optimizer = optim.Adam(
            model.parameters(),
            lr=learning_rate,
            weight_decay=weight_decay
        )
        
        # Функция потерь (для мульти-лейбл классификации)
        self.criterion = nn.BCEWithLogitsLoss()
        
        # Scheduler
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer, mode='min', factor=0.5, patience=5
        )
        
        print(f"Используется устройство: {self.device}")
    
    def train_epoch(
        self,
        dataloader: DataLoader,
        epoch: int
    ) -> Dict[str, float]:
        """Обучает одну эпоху."""
        self.model.train()
        total_loss = 0.0
        all_preds = []
        all_targets = []
        
        pbar = tqdm(dataloader, desc=f"Epoch {epoch}")
        for batch_idx, (inputs, targets) in enumerate(pbar):
            inputs = inputs.to(self.device)
            targets = targets.float().to(self.device)
            
            # Forward pass
            self.optimizer.zero_grad()
            outputs = self.model(inputs)
            loss = self.criterion(outputs, targets)
            
            # Backward pass
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            self.optimizer.step()
            
            total_loss += loss.item()
            
            # Сохраняем предсказания для метрик
            all_preds.append(torch.sigmoid(outputs).detach().cpu())
            all_targets.append(targets.cpu())
            
            # Обновляем прогресс
            pbar.set_postfix({'loss': loss.item()})
        
        # Вычисляем метрики
        all_preds = torch.cat(all_preds)
        all_targets = torch.cat(all_targets)
        
        metrics = self._compute_metrics(all_preds, all_targets)
        metrics['loss'] = total_loss / len(dataloader)
        
        return metrics
    
    def validate(
        self,
        dataloader: DataLoader
    ) -> Dict[str, float]:
        """Валидация модели."""
        self.model.eval()
        total_loss = 0.0
        all_preds = []
        all_targets = []
        
        with torch.no_grad():
            for inputs, targets in dataloader:
                inputs = inputs.to(self.device)
                targets = targets.float().to(self.device)
                
                outputs = self.model(inputs)
                loss = self.criterion(outputs, targets)
                
                total_loss += loss.item()
                all_preds.append(torch.sigmoid(outputs).cpu())
                all_targets.append(targets.cpu())
        
        all_preds = torch.cat(all_preds)
        all_targets = torch.cat(all_targets)
        
        metrics = self._compute_metrics(all_preds, all_targets)
        metrics['loss'] = total_loss / len(dataloader)
        
        return metrics
    
    def _compute_metrics(
        self,
        predictions: torch.Tensor,
        targets: torch.Tensor,
        threshold: float = 0.5
    ) -> Dict[str, float]:
        """Вычисляет метрики классификации."""
        # Бинаризуем предсказания
        pred_binary = (predictions > threshold).float()
        
        # True positives, false positives, false negatives
        tp = (pred_binary * targets).sum().item()
        fp = (pred_binary * (1 - targets)).sum().item()
        fn = ((1 - pred_binary) * targets).sum().item()
        tn = ((1 - pred_binary) * (1 - targets)).sum().item()
        
        # Метрики
        accuracy = (tp + tn) / (tp + fp + fn + tn + 1e-10)
        precision = tp / (tp + fp + 1e-10)
        recall = tp / (tp + fn + 1e-10)
        f1 = 2 * precision * recall / (precision + recall + 1e-10)
        
        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1': f1
        }
    
    def train(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader,
        epochs: int = 50,
        early_stopping_patience: int = 10,
        save_best: bool = True
    ) -> Dict[str, List[float]]:
        """Полный цикл обучения."""
        history = {
            'train_loss': [],
            'val_loss': [],
            'train_f1': [],
            'val_f1': [],
            'train_accuracy': [],
            'val_accuracy': []
        }
        
        best_val_f1 = 0.0
        patience_counter = 0
        best_model_path = MODELS_DIR / 'best_model.pt'
        
        for epoch in range(1, epochs + 1):
            # Обучение
            train_metrics = self.train_epoch(train_loader, epoch)
            
            # Валидация
            val_metrics = self.validate(val_loader)
            
            # Сохраняем историю
            history['train_loss'].append(train_metrics['loss'])
            history['val_loss'].append(val_metrics['loss'])
            history['train_f1'].append(train_metrics['f1'])
            history['val_f1'].append(val_metrics['f1'])
            history['train_accuracy'].append(train_metrics['accuracy'])
            history['val_accuracy'].append(val_metrics['accuracy'])
            
            # Выводим результаты
            print(f"\nEpoch {epoch}/{epochs}")
            print(f"Train - Loss: {train_metrics['loss']:.4f}, "
                  f"F1: {train_metrics['f1']:.4f}, "
                  f"Acc: {train_metrics['accuracy']:.4f}")
            print(f"Val   - Loss: {val_metrics['loss']:.4f}, "
                  f"F1: {val_metrics['f1']:.4f}, "
                  f"Acc: {val_metrics['accuracy']:.4f}")
            
            # Scheduler step
            self.scheduler.step(val_metrics['loss'])
            
            # Early stopping
            if val_metrics['f1'] > best_val_f1:
                best_val_f1 = val_metrics['f1']
                patience_counter = 0
                
                if save_best:
                    self.model.save(str(best_model_path))
                    print(f" Лучшая модель сохранена (F1: {best_val_f1:.4f})")
            else:
                patience_counter += 1
                
                if patience_counter >= early_stopping_patience:
                    print(f"\nРанняя остановка на эпохе {epoch}")
                    break
        
        # Загружаем лучшую модель
        if save_best and best_model_path.exists():
            self.model = AllergenClassifier.load(str(best_model_path))
            print(f"\nЗагружена лучшая модель с F1: {best_val_f1:.4f}")
        
        return history
    
    def plot_history(self, history: Dict[str, List[float]]):
        """Визуализирует историю обучения."""
        fig, axes = plt.subplots(1, 2, figsize=(12, 4))
        
        # График потерь
        axes[0].plot(history['train_loss'], label='Train')
        axes[0].plot(history['val_loss'], label='Validation')
        axes[0].set_xlabel('Epoch')
        axes[0].set_ylabel('Loss')
        axes[0].set_title('Training and Validation Loss')
        axes[0].legend()
        axes[0].grid(True)
        
        # График F1
        axes[1].plot(history['train_f1'], label='Train')
        axes[1].plot(history['val_f1'], label='Validation')
        axes[1].set_xlabel('Epoch')
        axes[1].set_ylabel('F1 Score')
        axes[1].set_title('Training and Validation F1')
        axes[1].legend()
        axes[1].grid(True)
        
        plt.tight_layout()
        plt.savefig(MODELS_DIR / 'training_history.png')
        plt.show()


def main():
    """Основная функция для обучения модели."""
    print("=" * 50)
    print("Обучение модели классификации аллергенов")
    print("=" * 50)
    
    # Загружаем датасет
    print("\n[1/4] Загрузка датасета...")
    dataset = AllergenDataset()
    X_train, X_test, y_train, y_test, allergen_names = dataset.prepare_data()
    
    # Создаем DataLoader'ы
    print("\n[2/4] Подготовка DataLoader'ов...")
    batch_size = 32
    
    train_dataset = TensorDataset(
        torch.LongTensor(X_train),
        torch.FloatTensor(y_train)
    )
    test_dataset = TensorDataset(
        torch.LongTensor(X_test),
        torch.FloatTensor(y_test)
    )
    
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=0
    )
    test_loader = DataLoader(
        test_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=0
    )
    
    # Создаем модель
    print("\n[3/4] Создание модели...")
    model = AllergenClassifier(
        vocab_size=dataset.vocab_size,
        embedding_dim=200,
        hidden_dim=256,
        num_classes=len(allergen_names),
        num_layers=2,
        dropout=0.3,
        bidirectional=True
    )
    
    print(f"Параметров модели: {sum(p.numel() for p in model.parameters()):,}")
    
    # Обучаем
    print("\n[4/4] Обучение модели...")
    trainer = AllergenTrainer(
        model=model,
        learning_rate=0.001,
        weight_decay=1e-5
    )
    
    history = trainer.train(
        train_loader=train_loader,
        val_loader=test_loader,
        epochs=50,
        early_stopping_patience=10
    )
    
    # Визуализируем
    trainer.plot_history(history)
    
    # Сохраняем финальную модель
    final_model_path = MODELS_DIR / 'allergen_model_final.pt'
    model.save(str(final_model_path))
    print(f"\n Финальная модель сохранена в {final_model_path}")
    
    # Создаем предиктор для теста
    predictor = AllergenPredictor()
    predictor.load_model(str(final_model_path))
    
    # Тестовый пример
    print("\n" + "=" * 50)
    print("Тестирование модели на примере")
    print("=" * 50)
    
    test_ingredients = "пшеничная мука яйца молоко сахар"
    prediction = predictor.predict(test_ingredients)
    
    print(f"Ингредиенты: {test_ingredients}")
    print(f"Найденные аллергены: {prediction['allergens_found']}")
    print(f"Уверенность: {prediction['confidence']:.2f}")


if __name__ == "__main__":
    main()