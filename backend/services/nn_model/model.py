"""Нейросетевая модель для классификации аллергенов."""
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, Dict, Any


class AllergenClassifier(nn.Module):
    """
    Нейросеть для классификации аллергенов на основе ингредиентов.
    
    Архитектура:
    1. Embedding слой для преобразования ингредиентов в векторы
    2. Bidirectional LSTM для анализа последовательности
    3. Attention механизм для выделения важных ингредиентов
    4. Fully connected слои для классификации
    
    Аргументы:
        vocab_size: размер словаря ингредиентов
        embedding_dim: размерность эмбеддингов
        hidden_dim: размерность скрытого состояния LSTM
        num_classes: количество классов аллергенов
        num_layers: количество слоев LSTM
        dropout: вероятность dropout
        bidirectional: использовать bidirectional LSTM
    """
    
    def __init__(
        self,
        vocab_size: int,
        embedding_dim: int = 200,
        hidden_dim: int = 256,
        num_classes: int = 30,
        num_layers: int = 2,
        dropout: float = 0.3,
        bidirectional: bool = True
    ):
        super(AllergenClassifier, self).__init__()
        
        self.vocab_size = vocab_size
        self.embedding_dim = embedding_dim
        self.hidden_dim = hidden_dim
        self.num_classes = num_classes
        self.num_layers = num_layers
        self.bidirectional = bidirectional
        
        # Embedding слой
        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=0)
        
        # LSTM слой
        self.lstm = nn.LSTM(
            input_size=embedding_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=bidirectional
        )
        
        # Attention механизм
        self.attention = nn.Linear(
            hidden_dim * (2 if bidirectional else 1), 
            1
        )
        
        # Dropout для регуляризации
        self.dropout = nn.Dropout(dropout)
        
        # Классификатор
        lstm_output_dim = hidden_dim * (2 if bidirectional else 1)
        self.classifier = nn.Sequential(
            nn.Linear(lstm_output_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, num_classes)
        )
        
        # Инициализация весов
        self._init_weights()
    
    def _init_weights(self):
        """Инициализация весов модели."""
        for name, param in self.named_parameters():
            if 'weight' in name and len(param.shape) > 1:
                nn.init.xavier_uniform_(param)
            elif 'bias' in name:
                nn.init.constant_(param, 0)
    
    def forward(
        self, 
        x: torch.Tensor,
        lengths: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Прямой проход.
        
        Args:
            x: входные данные [batch_size, seq_len]
            lengths: длины последовательностей [batch_size]
        
        Returns:
            логиты для каждого класса [batch_size, num_classes]
        """
        # Embedding
        embedded = self.embedding(x)  # [batch_size, seq_len, embedding_dim]
        embedded = self.dropout(embedded)
        
        # LSTM
        if lengths is not None:
            # Упаковываем последовательности для эффективности
            embedded = nn.utils.rnn.pack_padded_sequence(
                embedded, lengths.cpu(), batch_first=True, enforce_sorted=False
            )
        
        lstm_out, (hidden, cell) = self.lstm(embedded)
        
        if lengths is not None:
            # Распаковываем
            lstm_out, _ = nn.utils.rnn.pad_packed_sequence(
                lstm_out, batch_first=True
            )
        
        # Attention механизм
        if self.bidirectional:
            # Для bidirectional берем среднее от двух направлений
            batch_size, seq_len, hidden_dim = lstm_out.shape
            lstm_out = lstm_out.view(batch_size, seq_len, 2, -1)
            lstm_out = torch.mean(lstm_out, dim=2)
        
        # Вычисляем веса attention
        attention_weights = F.softmax(
            self.attention(lstm_out).squeeze(-1), dim=1
        )  # [batch_size, seq_len]
        
        # Взвешенная сумма
        weighted_output = torch.bmm(
            attention_weights.unsqueeze(1), lstm_out
        ).squeeze(1)  # [batch_size, hidden_dim]
        
        # Классификация
        output = self.classifier(weighted_output)  # [batch_size, num_classes]
        
        return output
    
    def predict_proba(self, x: torch.Tensor) -> torch.Tensor:
        """Возвращает вероятности классов."""
        with torch.no_grad():
            logits = self.forward(x)
            return torch.sigmoid(logits)  # Для мульти-лейбл классификации
    
    def save(self, path: str):
        """Сохраняет модель."""
        torch.save({
            'model_state_dict': self.state_dict(),
            'vocab_size': self.vocab_size,
            'embedding_dim': self.embedding_dim,
            'hidden_dim': self.hidden_dim,
            'num_classes': self.num_classes,
            'num_layers': self.num_layers,
            'bidirectional': self.bidirectional
        }, path)
    
    @classmethod
    def load(cls, path: str, device: str = 'cpu'):
        """Загружает модель."""
        checkpoint = torch.load(path, map_location=device)
        
        model = cls(
            vocab_size=checkpoint['vocab_size'],
            embedding_dim=checkpoint['embedding_dim'],
            hidden_dim=checkpoint['hidden_dim'],
            num_classes=checkpoint['num_classes'],
            num_layers=checkpoint['num_layers'],
            bidirectional=checkpoint['bidirectional']
        )
        
        model.load_state_dict(checkpoint['model_state_dict'])
        model.to(device)
        model.eval()
        
        return model