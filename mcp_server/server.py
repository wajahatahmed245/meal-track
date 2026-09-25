"""
MealTrack MCP Server
Wraps the MealTrack FastAPI backend for use with Claude/ChatGPT via MCP.
Transport: Streamable HTTP on port 8021.
Single-user: authenticates once at startup, reuses the JWT token.
"""
import os
from datetime import date
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

API_BASE = os.environ.get("MEAL_API_BASE_URL", "http://localhost:8010/api")
EMAIL    = os.environ.get("MEAL_USER_EMAIL", "wajahatahmad056@gmail.com")
PASSWORD = os.environ.get("MEAL_USER_PASSWORD", "Wajahat@MealTrack2026!")

ALLOWED_HOSTS = os.environ.get("MCP_ALLOWED_HOSTS", "wajahat-meal.duckdns.org").split(",")

mcp = FastMCP(
    "MealTrack",
    stateless_http=True,
    transport_security=TransportSecuritySettings(
        allowed_hosts=["localhost", "127.0.0.1"] + ALLOWED_HOSTS,
    ),
)


def _get_token() -> str:
    """Authenticate and return a fresh JWT access token."""
    r = httpx.post(f"{API_BASE}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=10)
    r.raise_for_status()
    return r.json()["access_token"]


def _client() -> httpx.Client:
    """Return an authenticated HTTP client."""
    token = _get_token()
    return httpx.Client(
        base_url=API_BASE,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=15,
    )


# ── Summary ───────────────────────────────────────────────────────────────────

@mcp.tool()
def get_today_summary() -> str:
    """
    Get today's full nutrition and exercise summary.
    Returns calories consumed, water intake, calories burned, net calories,
    calorie/water goal progress, and whether exercise was completed.
    """
    with _client() as c:
        r = c.get("/summary/today")
        r.raise_for_status()
        d = r.json()
    return (
        f"Date: {d['date']}\n"
        f"Calories: {d['total_calories']} / {d['calorie_goal']} kcal ({d['calorie_pct']}%)\n"
        f"Water: {d['total_water_ml']}ml / {d['water_goal_ml']}ml ({d['water_pct']}%)\n"
        f"Calories burned: {d['calories_burned']} kcal\n"
        f"Net calories: {d['net_calories']} kcal\n"
        f"Meals logged: {d['meals_logged']}\n"
        f"Exercise completed: {'Yes' if d['exercise_completed'] else 'No'}"
    )


@mcp.tool()
def get_weekly_summary() -> str:
    """
    Get a 7-day calorie and exercise summary for the current week.
    Shows daily calories and whether exercise was done each day.
    """
    with _client() as c:
        r = c.get("/summary/weekly")
        r.raise_for_status()
        d = r.json()
    lines = [f"Weekly Summary (avg: {d['avg_calories']} kcal/day, {d['days_exercised']}/7 days exercised):"]
    for day in d["days"]:
        ex = "✓" if day["exercise_completed"] else "✗"
        today = " ← today" if day["is_today"] else ""
        lines.append(f"  {day['day']} {day['date']}: {day['calories']} kcal  exercise:{ex}{today}")
    return "\n".join(lines)


@mcp.tool()
def get_stats() -> str:
    """
    Get long-term stats: total days logged, exercise days, current streak,
    and average daily calories over the last 30 days.
    """
    with _client() as c:
        r = c.get("/summary/stats")
        r.raise_for_status()
        d = r.json()
    return (
        f"Days logged: {d['days_logged']}\n"
        f"Exercise days: {d['exercise_days']}\n"
        f"Current streak: {d['current_streak']} days\n"
        f"Avg calories (30d): {d['avg_calories_30d']} kcal"
    )


# ── Food Log ──────────────────────────────────────────────────────────────────

@mcp.tool()
def get_food_log(log_date: Optional[str] = None) -> str:
    """
    Get the food log for a specific date (YYYY-MM-DD). Defaults to today.
    Returns all meals grouped with total calories per meal type.
    """
    target = log_date or str(date.today())
    with _client() as c:
        r = c.get("/summary/day", params={"day": target})
        r.raise_for_status()
        d = r.json()
    if not d["meals"]:
        return f"No meals logged for {target}."
    lines = [f"Food log for {target} — {d['total_calories']} kcal total:"]
    by_type: dict = {}
    for m in d["meals"]:
        by_type.setdefault(m["meal_type"], []).append(m)
    for meal_type, items in by_type.items():
        total = sum(i["calories"] for i in items)
        lines.append(f"\n  {meal_type} ({total} kcal):")
        for item in items:
            lines.append(f"    {item['emoji']} {item['name']} — {item['calories']} kcal")
    return "\n".join(lines)


_MEAL_TYPE_ALIASES = {
    "snack":            "Afternoon Snack",
    "afternoon snack":  "Afternoon Snack",
    "morning snack":    "Morning Snack",
    "late snack":       "Late Snack",
    "breakfast":        "Breakfast",
    "lunch":            "Lunch",
    "dinner":           "Dinner",
}

def _normalize_meal_type(meal_type: str) -> str:
    return _MEAL_TYPE_ALIASES.get(meal_type.strip().lower(), meal_type)


@mcp.tool()
def add_food_entry(
    name: str,
    calories: int,
    meal_type: str,
    time: Optional[str] = None,
    emoji: Optional[str] = None,
    note: Optional[str] = None,
) -> str:
    """
    Log a food entry for today.

    Args:
        name: Food item name (e.g. 'Banana', 'Chicken breast 200g')
        calories: Calories in kcal (e.g. 89)
        meal_type: One of 'Breakfast', 'Morning Snack', 'Lunch', 'Afternoon Snack', 'Dinner', 'Late Snack'. 'Snack' is also accepted and maps to 'Afternoon Snack'.
        time: Time in HH:MM format (defaults to current time)
        emoji: Optional emoji for the food item
        note: Optional note
    """
    from datetime import datetime
    payload = {
        "name": name,
        "calories": calories,
        "meal_type": _normalize_meal_type(meal_type),
        "time": time or datetime.now().strftime("%H:%M"),
        "emoji": emoji or "🍽️",
        "note": note or "",
    }
    with _client() as c:
        r = c.post("/meals", json=payload)
        r.raise_for_status()
        d = r.json()
    return f"Logged: {d['emoji']} {d['name']} ({d['calories']} kcal) to {d['meal_type']} at {d['time']}"


@mcp.tool()
def delete_food_entry(entry_id: int) -> str:
    """
    Delete a food entry by its ID.
    Use get_food_log() first to find the entry ID.
    """
    with _client() as c:
        r = c.delete(f"/meals/{entry_id}")
        r.raise_for_status()
    return f"Deleted food entry #{entry_id}."


# ── Drinks ────────────────────────────────────────────────────────────────────

@mcp.tool()
def add_drink_entry(
    name: str,
    amount_ml: int,
    time: Optional[str] = None,
    emoji: Optional[str] = None,
) -> str:
    """
    Log a drink/water entry for today.

    Args:
        name: Drink name (e.g. 'Water', 'Green tea', 'Coffee')
        amount_ml: Amount in millilitres (e.g. 250)
        time: Time in HH:MM format (defaults to current time)
        emoji: Optional emoji
    """
    from datetime import datetime
    payload = {
        "name": name,
        "amount_ml": amount_ml,
        "time": time or datetime.now().strftime("%H:%M"),
        "emoji": emoji or "💧",
    }
    with _client() as c:
        r = c.post("/drinks", json=payload)
        r.raise_for_status()
        d = r.json()
    return f"Logged: {d['emoji']} {d['name']} {d['amount_ml']}ml at {d['time']}"


@mcp.tool()
def delete_drink_entry(entry_id: int) -> str:
    """
    Delete a drink entry by its ID.
    """
    with _client() as c:
        r = c.delete(f"/drinks/{entry_id}")
        r.raise_for_status()
    return f"Deleted drink entry #{entry_id}."


# ── Exercise ──────────────────────────────────────────────────────────────────

@mcp.tool()
def mark_exercise(
    exercise_type: str,
    duration_minutes: int,
    calories_burned: Optional[int] = None,
    time: Optional[str] = None,
) -> str:
    """
    Log today's exercise as completed.

    Args:
        exercise_type: Type of exercise (e.g. 'Gym', 'Running', 'Cycling', 'Yoga')
        duration_minutes: Duration in minutes (e.g. 45)
        calories_burned: Estimated calories burned (optional)
        time: Time in HH:MM format (defaults to current time)
    """
    from datetime import datetime
    payload = {
        "exercise_type": exercise_type,
        "duration_minutes": duration_minutes,
        "calories_burned": calories_burned,
        "time": time or datetime.now().strftime("%H:%M"),
        "completed": True,
    }
    with _client() as c:
        r = c.post("/exercise", json=payload)
        r.raise_for_status()
        d = r.json()
    burned = f", {d['calories_burned']} kcal burned" if d["calories_burned"] else ""
    return f"Exercise logged: {d['exercise_type']} for {d['duration_minutes']} min{burned}"


# ── Food Search ───────────────────────────────────────────────────────────────

@mcp.tool()
def search_food(query: str) -> str:
    """
    Search the food database for nutrition info.
    Returns matching foods with calories and serving size.

    Args:
        query: Food name to search (e.g. 'banana', 'chicken', 'rice')
    """
    with _client() as c:
        r = c.get("/food/search", params={"q": query})
        r.raise_for_status()
        results = r.json()
    if not results:
        return f"No food found matching '{query}'."
    lines = [f"Food search results for '{query}':"]
    for item in results:
        lines.append(f"  {item['emoji']} {item['name']} — {item['calories']} kcal ({item['per']})")
    return "\n".join(lines)


# ── Goals ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_goals() -> str:
    """
    Get current daily nutrition and exercise goals.
    Returns calorie goal, water goal, and exercise days per week target.
    """
    with _client() as c:
        r = c.get("/users/me")
        r.raise_for_status()
        d = r.json()
    return (
        f"Daily calorie goal: {d['calorie_goal']} kcal\n"
        f"Daily water goal: {d['water_goal_ml']}ml\n"
        f"Exercise goal: {d['exercise_goal_days']} days/week"
    )


@mcp.tool()
def update_goals(
    calorie_goal: Optional[int] = None,
    water_goal_ml: Optional[int] = None,
    exercise_goal_days: Optional[int] = None,
) -> str:
    """
    Update daily nutrition or exercise goals.

    Args:
        calorie_goal: New daily calorie target in kcal (e.g. 2000)
        water_goal_ml: New daily water target in ml (e.g. 2500)
        exercise_goal_days: New exercise days per week target (1-7)
    """
    payload = {}
    if calorie_goal is not None:
        payload["calorie_goal"] = calorie_goal
    if water_goal_ml is not None:
        payload["water_goal_ml"] = water_goal_ml
    if exercise_goal_days is not None:
        payload["exercise_goal_days"] = exercise_goal_days
    if not payload:
        return "No updates provided."
    with _client() as c:
        r = c.patch("/users/me", json=payload)
        r.raise_for_status()
        d = r.json()
    return (
        f"Goals updated:\n"
        f"  Calories: {d['calorie_goal']} kcal/day\n"
        f"  Water: {d['water_goal_ml']}ml/day\n"
        f"  Exercise: {d['exercise_goal_days']} days/week"
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8021))
    uvicorn.run(mcp.streamable_http_app(), host="0.0.0.0", port=port)
