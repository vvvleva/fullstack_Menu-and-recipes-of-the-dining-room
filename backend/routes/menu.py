from fastapi import APIRouter


router = APIRouter(prefix="/api", tags=["menu"])


# База данных в памяти (пока без настоящей БД)
menu_items = [
    {
        "id": 1,
        "name": "Цезарь с курицей",
        "price": 350,
        "weight": 250,
        "category": "салаты",
        "ingredients": ["курица", "салат айсберг", "соус", "пармезан", "грецкий орех", "гренки"],
        "allergens": ["орехи", "глютен", "лактоза"],
        "calories": 420,
        "available": True,
    },
    {
        "id": 2,
        "name": "Греческий салат",
        "price": 300,
        "weight": 200,
        "category": "салаты",
        "ingredients": ["помидоры", "огурцы", "фета", "оливки", "оливковое масло"],
        "allergens": ["лактоза"],
        "calories": 250,
        "available": True,
    },
    {
        "id": 3,
        "name": "Борщ",
        "price": 280,
        "weight": 300,
        "category": "супы",
        "ingredients": ["свекла", "капуста", "картофель", "говядина", "сметана"],
        "allergens": ["лактоза"],
        "calories": 180,
        "available": True,
    },
    {
        "id": 4,
        "name": "Котлеты с пюре",
        "price": 380,
        "weight": 350,
        "category": "горячее",
        "ingredients": ["котлеты", "картофельное пюре", "соус"],
        "allergens": ["глютен", "лактоза"],
        "calories": 550,
        "available": True,
    },
]


@router.get("/menu")
async def get_menu():
    return {
        "status": "success",
        "data": menu_items,
        "count": len(menu_items),
    }


@router.get("/menu/{item_id}")
async def get_menu_item(item_id: int):
    for item in menu_items:
        if item["id"] == item_id:
            return {
                "status": "success",
                "data": item,
            }
    return {
        "status": "error",
        "message": "Блюдо не найдено",
    }


@router.get("/menu/category/{category}")
async def get_menu_by_category(category: str):
    filtered = [item for item in menu_items if item["category"] == category and item["available"]]
    return {
        "status": "success",
        "category": category,
        "data": filtered,
        "count": len(filtered),
    }


@router.get("/analyze/{item_id}/{user_allergens}")
async def analyze_allergens(item_id: int, user_allergens: str):
    dish = None
    for item in menu_items:
        if item["id"] == item_id:
            dish = item
            break

    if not dish:
        return {
            "status": "error",
            "message": "Блюдо не найдено",
        }

    user_allergens_list = [a.strip() for a in user_allergens.split(",")]

    found_allergens = []
    for allergen in user_allergens_list:
        if allergen in dish["allergens"]:
            found_allergens.append(allergen)

    if "орехи" in found_allergens or "морепродукты" in found_allergens:
        safety_level = "danger"
    elif found_allergens:
        safety_level = "warning"
    else:
        safety_level = "safe"

    return {
        "status": "success",
        "dish_name": dish["name"],
        "analysis": {
            "has_allergens": len(found_allergens) > 0,
            "allergens_found": found_allergens,
            "safety_level": safety_level,
            "message": get_safety_message(safety_level, found_allergens),
        },
    }


def get_safety_message(level: str, allergens: list):
    if level == "danger":
        return f"ОПАСНО! Блюдо содержит {', '.join(allergens)}. НЕ РЕКОМЕНДУЕТСЯ к употреблению!"
    elif level == "warning":
        return f"ВНИМАНИЕ! Блюдо содержит {', '.join(allergens)}. Будьте осторожны!"
    else:
        return "Безопасно! Аллергены не найдены."

