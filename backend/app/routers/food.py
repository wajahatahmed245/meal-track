from typing import List

from fastapi import APIRouter, Query

from ..schemas import FoodItem

router = APIRouter(prefix="/api/food", tags=["food"])

_FOOD_DB: List[FoodItem] = [
    FoodItem(name="Banana",            calories=89,  emoji="🍌", per="1 medium (118g)"),
    FoodItem(name="Apple",             calories=95,  emoji="🍎", per="1 medium (182g)"),
    FoodItem(name="Orange",            calories=62,  emoji="🍊", per="1 medium (131g)"),
    FoodItem(name="Mango",             calories=202, emoji="🥭", per="1 cup (165g)"),
    FoodItem(name="Grapes",            calories=104, emoji="🍇", per="1 cup (151g)"),
    FoodItem(name="Watermelon",        calories=86,  emoji="🍉", per="2 cups (280g)"),
    FoodItem(name="Strawberries",      calories=49,  emoji="🍓", per="1 cup (152g)"),
    FoodItem(name="Greek Yogurt",      calories=130, emoji="🥛", per="1 cup (245g)"),
    FoodItem(name="Milk (whole)",      calories=149, emoji="🥛", per="1 cup (244g)"),
    FoodItem(name="Eggs (boiled)",     calories=78,  emoji="🥚", per="1 large"),
    FoodItem(name="Whole Grain Bread", calories=80,  emoji="🍞", per="1 slice (38g)"),
    FoodItem(name="White Rice",        calories=206, emoji="🍚", per="1 cup cooked (186g)"),
    FoodItem(name="Brown Rice",        calories=216, emoji="🍚", per="1 cup cooked (195g)"),
    FoodItem(name="Oats (cooked)",     calories=154, emoji="🥣", per="1 cup (234g)"),
    FoodItem(name="Almonds",           calories=164, emoji="🥜", per="28g / handful"),
    FoodItem(name="Peanut Butter",     calories=188, emoji="🥜", per="2 tbsp (32g)"),
    FoodItem(name="Avocado",           calories=234, emoji="🥑", per="1 medium"),
    FoodItem(name="Grilled Chicken",   calories=165, emoji="🍗", per="100g breast"),
    FoodItem(name="Chicken Curry",     calories=350, emoji="🍛", per="1 serving (300g)"),
    FoodItem(name="Mixed Salad",       calories=50,  emoji="🥗", per="1 large bowl"),
    FoodItem(name="Daal",              calories=230, emoji="🫘", per="1 cup (200g)"),
    FoodItem(name="Chapati",           calories=120, emoji="🫓", per="1 roti (40g)"),
    FoodItem(name="Paratha",           calories=260, emoji="🫓", per="1 medium (80g)"),
    FoodItem(name="Biryani",           calories=490, emoji="🍛", per="1 serving (300g)"),
    FoodItem(name="Samosa",            calories=262, emoji="🥟", per="2 pieces (100g)"),
    FoodItem(name="Green Tea",         calories=5,   emoji="🍵", per="1 cup (240ml)"),
    FoodItem(name="Coffee (black)",    calories=5,   emoji="☕", per="1 cup (240ml)"),
    FoodItem(name="Orange Juice",      calories=112, emoji="🍊", per="1 cup (248ml)"),
    FoodItem(name="Lemonade",          calories=99,  emoji="🍋", per="1 cup (248ml)"),
    FoodItem(name="Potato (boiled)",   calories=161, emoji="🥔", per="1 medium (148g)"),
    FoodItem(name="Sweet Potato",      calories=103, emoji="🍠", per="1 medium (114g)"),
    FoodItem(name="Broccoli",          calories=55,  emoji="🥦", per="1 cup (91g)"),
    FoodItem(name="Spinach",           calories=23,  emoji="🥬", per="3 cups raw (90g)"),
    FoodItem(name="Tomato",            calories=35,  emoji="🍅", per="1 medium (123g)"),
    FoodItem(name="Cucumber",          calories=16,  emoji="🥒", per="1 cup sliced (119g)"),
    FoodItem(name="Cheese (cheddar)",  calories=113, emoji="🧀", per="1 oz (28g)"),
    FoodItem(name="Salmon",            calories=208, emoji="🐟", per="100g fillet"),
    FoodItem(name="Tuna (canned)",     calories=109, emoji="🐟", per="100g drained"),
    FoodItem(name="Beef (lean)",       calories=215, emoji="🥩", per="100g cooked"),
    FoodItem(name="Pasta (cooked)",    calories=220, emoji="🍝", per="1 cup (140g)"),
    FoodItem(name="Pizza (slice)",     calories=285, emoji="🍕", per="1 slice (107g)"),
    FoodItem(name="Burger",            calories=540, emoji="🍔", per="1 medium"),
    FoodItem(name="French Fries",      calories=365, emoji="🍟", per="medium serving (117g)"),
    FoodItem(name="Ice Cream",         calories=207, emoji="🍨", per="1 cup (132g)"),
    FoodItem(name="Dark Chocolate",    calories=170, emoji="🍫", per="1 oz (28g)"),
]


@router.get("/search", response_model=List[FoodItem])
async def search_food(q: str = Query("", min_length=0)):
    if not q:
        return _FOOD_DB[:20]
    q_lower = q.lower()
    return [f for f in _FOOD_DB if q_lower in f.name.lower()]


@router.get("/database", response_model=List[FoodItem])
async def get_food_database():
    return _FOOD_DB
