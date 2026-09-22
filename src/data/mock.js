export const mockUser = {
  name: 'Wajahat Ahmed',
  calorie_goal: 2000,
  water_goal_ml: 2500,
  exercise_goal_days: 5,
}

export const todayMeals = [
  { id: 1,  time: '07:30', meal_type: 'Breakfast',       name: 'Banana',                calories: 89,  emoji: '🍌', note: '' },
  { id: 2,  time: '07:30', meal_type: 'Breakfast',       name: 'Greek Yogurt',          calories: 130, emoji: '🥛', note: '' },
  { id: 3,  time: '07:30', meal_type: 'Breakfast',       name: 'Green Tea',             calories: 5,   emoji: '🍵', note: '' },
  { id: 4,  time: '10:00', meal_type: 'Morning Snack',   name: 'Almonds (handful)',     calories: 164, emoji: '🥜', note: '' },
  { id: 5,  time: '13:00', meal_type: 'Lunch',           name: 'Grilled Chicken Salad', calories: 320, emoji: '🥗', note: '' },
  { id: 6,  time: '13:00', meal_type: 'Lunch',           name: 'Whole Grain Bread',     calories: 80,  emoji: '🍞', note: '' },
  { id: 7,  time: '15:30', meal_type: 'Afternoon Snack', name: 'Apple',                 calories: 95,  emoji: '🍎', note: '' },
  { id: 8,  time: '19:00', meal_type: 'Dinner',          name: 'Chicken Curry',         calories: 350, emoji: '🍛', note: '' },
  { id: 9,  time: '19:00', meal_type: 'Dinner',          name: 'Rice (1 cup)',          calories: 206, emoji: '🍚', note: '' },
]

export const todayDrinks = [
  { id: 101, time: '07:00', name: 'Water',     amount_ml: 250, emoji: '💧' },
  { id: 102, time: '07:30', name: 'Green Tea', amount_ml: 200, emoji: '🍵' },
  { id: 103, time: '10:00', name: 'Water',     amount_ml: 300, emoji: '💧' },
  { id: 104, time: '12:30', name: 'Lemonade',  amount_ml: 250, emoji: '🍋' },
  { id: 105, time: '14:00', name: 'Water',     amount_ml: 400, emoji: '💧' },
  { id: 106, time: '17:00', name: 'Water',     amount_ml: 300, emoji: '💧' },
]

export const todayExercise = {
  completed: true,
  type: 'Morning Walk',
  duration_minutes: 30,
  calories_burned: 150,
  time: '06:30',
}

export const weeklyTrend = [
  { day: 'Mon', calories: 1820, date: '2026-09-15' },
  { day: 'Tue', calories: 1650, date: '2026-09-16' },
  { day: 'Wed', calories: 2150, date: '2026-09-17' },
  { day: 'Thu', calories: 1780, date: '2026-09-18' },
  { day: 'Fri', calories: 1920, date: '2026-09-19' },
  { day: 'Sat', calories: 2200, date: '2026-09-20' },
  { day: 'Sun', calories: 1439, date: '2026-09-21', isToday: true },
]

export const insights = [
  {
    id: 1,
    type: 'positive',
    emoji: '💪',
    message: 'Great protein balance today! Chicken and yogurt keep you fueled.',
    color: 'green',
  },
  {
    id: 2,
    type: 'tip',
    emoji: '💧',
    message: 'You need 800ml more water to hit your 2.5L daily goal.',
    color: 'blue',
  },
  {
    id: 3,
    type: 'warning',
    emoji: '⚠️',
    message: 'You exceeded your calorie goal on Wednesday and Saturday this week.',
    color: 'orange',
  },
  {
    id: 4,
    type: 'suggestion',
    emoji: '🥦',
    message: 'Consider adding a vegetable to your next snack for extra fibre.',
    color: 'green',
  },
]

export const foodDatabase = [
  { name: 'Banana',           calories: 89,  emoji: '🍌', per: '1 medium (118g)' },
  { name: 'Apple',            calories: 95,  emoji: '🍎', per: '1 medium (182g)' },
  { name: 'Greek Yogurt',     calories: 130, emoji: '🥛', per: '1 cup (245g)' },
  { name: 'Eggs (boiled)',    calories: 78,  emoji: '🥚', per: '1 large' },
  { name: 'Whole Grain Bread',calories: 80,  emoji: '🍞', per: '1 slice (38g)' },
  { name: 'Almonds',          calories: 164, emoji: '🥜', per: '28g / handful' },
  { name: 'Grilled Chicken',  calories: 165, emoji: '🍗', per: '100g breast' },
  { name: 'Rice (cooked)',    calories: 206, emoji: '🍚', per: '1 cup (186g)' },
  { name: 'Mixed Salad',      calories: 50,  emoji: '🥗', per: '1 large bowl' },
  { name: 'Oats (cooked)',    calories: 154, emoji: '🥣', per: '1 cup (234g)' },
  { name: 'Avocado',         calories: 234, emoji: '🥑', per: '1 medium' },
  { name: 'Green Tea',       calories: 5,   emoji: '🍵', per: '1 cup (240ml)' },
  { name: 'Lemonade',        calories: 99,  emoji: '🍋', per: '1 cup (248ml)' },
  { name: 'Coffee (black)',  calories: 5,   emoji: '☕', per: '1 cup (240ml)' },
  { name: 'Orange Juice',    calories: 112, emoji: '🍊', per: '1 cup (248ml)' },
  { name: 'Milk (whole)',    calories: 149, emoji: '🥛', per: '1 cup (244ml)' },
  { name: 'Chicken Curry',   calories: 350, emoji: '🍛', per: '1 serving (300g)' },
  { name: 'Chapati',         calories: 120, emoji: '🫓', per: '1 roti (40g)' },
  { name: 'Daal',            calories: 230, emoji: '🫘', per: '1 cup (200g)' },
  { name: 'Paratha',         calories: 260, emoji: '🫓', per: '1 medium (80g)' },
]

export const quickFoodChips = [
  { name: 'Banana',   calories: 89,  emoji: '🍌', meal_type: 'Breakfast' },
  { name: 'Eggs',     calories: 78,  emoji: '🥚', meal_type: 'Breakfast' },
  { name: 'Coffee',   calories: 5,   emoji: '☕', meal_type: 'Breakfast' },
  { name: 'Apple',    calories: 95,  emoji: '🍎', meal_type: 'Snack' },
  { name: 'Chicken',  calories: 165, emoji: '🍗', meal_type: 'Lunch' },
  { name: 'Salad',    calories: 50,  emoji: '🥗', meal_type: 'Lunch' },
  { name: 'Rice',     calories: 206, emoji: '🍚', meal_type: 'Lunch' },
  { name: 'Almonds',  calories: 164, emoji: '🥜', meal_type: 'Snack' },
]

export const mealTypes = [
  'Breakfast',
  'Morning Snack',
  'Lunch',
  'Afternoon Snack',
  'Dinner',
  'Late Snack',
]

export const mealTypeOrder = {
  'Breakfast':       1,
  'Morning Snack':   2,
  'Lunch':           3,
  'Afternoon Snack': 4,
  'Dinner':          5,
  'Late Snack':      6,
}

export const mealTypeEmoji = {
  'Breakfast':       '🌅',
  'Morning Snack':   '🥜',
  'Lunch':           '🍱',
  'Afternoon Snack': '🍎',
  'Dinner':          '🌙',
  'Late Snack':      '🌛',
}
