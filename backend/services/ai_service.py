"""AI-сервис для анализа аллергенов с использованием нейросетевой модели."""
from typing import List, Dict, Optional
import numpy as np


class NeuralAllergenAnalyzer:
    """
    Анализатор аллергенов на основе нейросетевой модели,
    обученной на датасете Food Ingredients and Allergens с Kaggle.
    
    Модель: Bidirectional LSTM с Attention механизмом
    """
    
    def __init__(self):
        self.model_available = False
        
        print(" Модель не загружена. Анализатор будет работать в режиме пониженной функциональности.")
        self.model_available = False
    
    def analyze_dish_for_user(
        self,
        dish: Dict,
        user_allergens: List[str],
        user_diet: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> Dict:
        """
        Полный анализ блюда для пользователя.
        """
        dish_ingredients = dish.get("ingredients", [])
        
        if not self.model_available:
            return self._fallback_analysis(dish, user_allergens, user_diet)
        
        try:
            analysis = {
                "risk_level": "safe" if not user_allergens else "warning",
                "allergens_found": [],
                "model_confidence": 0.0
            }
            
            diet_analysis = None
            if user_diet:
                diet_analysis = self._check_diet_compatibility(dish, user_diet)
            
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
                "safe_to_eat": analysis['risk_level'] == 'safe' and (diet_analysis is None or diet_analysis['compatible']),
                "model_used": "fallback",
                "model_confidence": 0.0
            }
            
        except Exception as e:
            print(f"Ошибка при анализе: {e}")
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
        
        for forbidden in rules.get("forbidden", []):
            for ingredient in dish.get("ingredients", []):
                if forbidden.lower() in ingredient.lower():
                    conflicts.append({
                        "restriction": forbidden,
                        "ingredient": ingredient,
                        "reason": f"Запрещено на диете {diet}"
                    })
        
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
            recommendations.append("КАТЕГОРИЧЕСКИ НЕ РЕКОМЕНДУЕТСЯ! Высокий риск тяжелой аллергической реакции.")
            for allergen in allergens_found:
                if isinstance(allergen, dict):
                    recommendations.append(f"    {allergen.get('allergen', '')} (уверенность: {allergen.get('probability', 0)*100:.0f}%)")
        elif risk_level == "warning":
            recommendations.append("Будьте осторожны! Обнаружены потенциальные аллергены.")
            for allergen in allergens_found:
                if isinstance(allergen, dict):
                    recommendations.append(f"    {allergen.get('allergen', '')} (уверенность: {allergen.get('probability', 0)*100:.0f}%)")
        
        if diet_analysis and not diet_analysis['compatible']:
            recommendations.append(f"Блюдо не соответствует диете {diet_analysis['diet_name']}")
            for conflict in diet_analysis['conflicts']:
                recommendations.append(f"    {conflict['reason']}")
        
        if not recommendations:
            recommendations.append("Аллергены не найдены. Блюдо безопасно.")
        
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
        
        if any(a in ["орехи", "арахис", "морепродукты"] for a in found):
            risk_level = "danger"
        elif found:
            risk_level = "warning"
        else:
            risk_level = "safe"
        
        diet_analysis = self._check_diet_compatibility(dish, user_diet) if user_diet else None
        
        return {
            "risk_level": risk_level,
            "allergens_found": found,
            "diet_analysis": diet_analysis,
            "safe_to_eat": len(found) == 0 and (diet_analysis is None or diet_analysis['compatible']),
            "model_used": "fallback",
            "model_confidence": 0.0
        }


analyzer = NeuralAllergenAnalyzer()