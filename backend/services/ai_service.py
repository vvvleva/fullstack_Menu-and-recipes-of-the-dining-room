"""AI-сервис для анализа аллергенов с использованием нейросетевой модели."""
from typing import List, Dict, Optional
import numpy as np
from .nn_model import get_predictor


class NeuralAllergenAnalyzer:
    """
    Анализатор аллергенов на основе нейросетевой модели,
    обученной на датасете Food Ingredients and Allergens с Kaggle.
    
    Модель: Bidirectional LSTM с Attention механизмом
    Датасет: https://www.kaggle.com/datasets/uom190346a/food-ingredients-and-allergens
    """
    
    def __init__(self):
        self.predictor = get_predictor()
        
        if self.predictor is None or self.predictor.model is None:
            print(" Модель не загружена. Анализатор будет работать в режиме пониженной функциональности.")
            self.model_available = False
        else:
            self.model_available = True
            print(" Нейросетевая модель загружена успешно")
    
    def analyze_dish_for_user(
        self,
        dish: Dict,
        user_allergens: List[str],
        user_diet: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> Dict:
        """
        Полный анализ блюда для пользователя с использованием нейросети.
        
        Args:
            dish: Данные блюда
            user_allergens: Список аллергенов пользователя
            user_diet: Диета пользователя
            user_id: ID пользователя (для логирования)
        
        Returns:
            Dict с результатами анализа
        """
        dish_ingredients = dish.get("ingredients", [])
        
        if not self.model_available:
            # Режим пониженной функциональности - используем простое сравнение
            return self._fallback_analysis(dish, user_allergens, user_diet)
        
        try:
            # Используем нейросеть для анализа
            analysis = self.predictor.analyze_dish(
                dish_ingredients=dish_ingredients,
                user_allergens=user_allergens
            )
            
            # Добавляем информацию о диете
            diet_analysis = None
            if user_diet:
                diet_analysis = self._check_diet_compatibility(dish, user_diet)
            
            # Формируем рекомендации
            recommendations = self._generate_recommendations(
                analysis['risk_level'],
                analysis['allergens_found'],
                diet_analysis
            )
            
            return {
                "dish_id": dish.get("id"),
                "dish_name": dish.get("name"),
                "risk_level": analysis['risk_level'],
                "allergens_found": analysis['allergens_found'],
                "diet_analysis": diet_analysis,
                "recommendations": recommendations,
                "safe_to_eat": analysis['safe_to_eat'] and (diet_analysis is None or diet_analysis['compatible']),
                "model_used": "neural_network",
                "model_confidence": analysis['model_confidence']
            }
            
        except Exception as e:
            print(f"Ошибка при анализе нейросетью: {e}")
            return self._fallback_analysis(dish, user_allergens, user_diet)
    
    def _check_diet_compatibility(self, dish: Dict, diet: str) -> Dict:
        """Проверка совместимости с диетой."""
        diet_rules = {
            "веган": {
                "forbidden": ["мясо", "курица", "рыба", "морепродукты", "молоко", "яйца", "мед"],
                "check_calories": False
            },
            "вегетарианец": {
                "forbidden": ["мясо", "курица", "рыба", "морепродукты"],
                "check_calories": False
            },
            "безглютеновая": {
                "forbidden": ["пшеница", "рожь", "ячмень", "овес", "мука"],
                "check_calories": False
            },
            "низкокалорийная": {
                "forbidden": [],
                "max_calories": 400,
                "check_calories": True
            }
        }
        
        if diet not in diet_rules:
            return {"compatible": True, "conflicts": []}
        
        rules = diet_rules[diet]
        conflicts = []
        
        # Проверяем запрещенные ингредиенты
        for forbidden in rules.get("forbidden", []):
            for ingredient in dish.get("ingredients", []):
                if forbidden.lower() in ingredient.lower():
                    conflicts.append({
                        "restriction": forbidden,
                        "ingredient": ingredient,
                        "reason": f"Запрещено на диете {diet}"
                    })
        
        # Проверяем калории
        if rules.get("check_calories", False):
            max_cal = rules.get("max_calories", 400)
            if dish.get("calories", 0) > max_cal:
                conflicts.append({
                    "restriction": "калорийность",
                    "ingredient": "блюдо целиком",
                    "reason": f"Калорийность {dish.get('calories')} превышает лимит {max_cal}"
                })
        
        return {
            "compatible": len(conflicts) == 0,
            "conflicts": conflicts,
            "diet_name": diet
        }
    
    def _generate_recommendations(self, risk_level: str, allergens_found: List, diet_analysis: Optional[Dict]) -> List[str]:
        """Генерирует рекомендации на основе анализа."""
        recommendations = []
        
        if risk_level == "danger":
            recommendations.append(" КАТЕГОРИЧЕСКИ НЕ РЕКОМЕНДУЕТСЯ! Высокий риск тяжелой аллергической реакции.")
            for allergen in allergens_found:
                recommendations.append(f"    {allergen['allergen']} (уверенность: {allergen['probability']:.0%})")
        elif risk_level == "warning":
            recommendations.append(" Будьте осторожны! Обнаружены потенциальные аллергены.")
            for allergen in allergens_found:
                recommendations.append(f"    {allergen['allergen']} (уверенность: {allergen['probability']:.0%})")
        
        if diet_analysis and not diet_analysis['compatible']:
            recommendations.append(f" Блюдо не соответствует диете {diet_analysis['diet_name']}")
            for conflict in diet_analysis['conflicts']:
                recommendations.append(f"    {conflict['reason']}")
        
        if not recommendations:
            if self.model_available:
                recommendations.append(" Нейросеть не обнаружила аллергенов. Блюдо безопасно.")
            else:
                recommendations.append(" Аллергены не найдены. Блюдо безопасно.")
        
        return recommendations
    
    def _fallback_analysis(self, dish: Dict, user_allergens: List[str], user_diet: Optional[str]) -> Dict:
        """Запасной анализ (простое сравнение) если нейросеть недоступна."""
        dish_allergens = dish.get("allergens", [])
        
        found = []
        for allergen in user_allergens:
            if allergen in dish_allergens:
                found.append({
                    "allergen": allergen,
                    "matched_user_allergen": allergen,
                    "probability": 1.0
                })
        
        risk_level = "danger" if any(a in ["орехи", "арахис", "морепродукты"] for a in found) else "warning" if found else "safe"
        
        diet_analysis = self._check_diet_compatibility(dish, user_diet) if user_diet else None
        
        return {
            "risk_level": risk_level,
            "allergens_found": found,
            "diet_analysis": diet_analysis,
            "safe_to_eat": len(found) == 0 and (diet_analysis is None or diet_analysis['compatible']),
            "model_used": "fallback",
            "model_confidence": 0.0
        }


# Создаем глобальный экземпляр
analyzer = NeuralAllergenAnalyzer()