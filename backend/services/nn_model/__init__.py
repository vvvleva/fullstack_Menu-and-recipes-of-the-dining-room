"""Нейросетевая модель для классификации аллергенов."""
from .model import AllergenClassifier
from .dataset import AllergenDataset
from .predict import AllergenPredictor, get_predictor
from .train import AllergenTrainer

__all__ = [
    'AllergenClassifier',
    'AllergenDataset',
    'AllergenPredictor',
    'AllergenTrainer',
    'get_predictor'
]