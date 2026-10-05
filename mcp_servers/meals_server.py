import logging
import sys

import requests
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations


logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger(__name__)
mcp = FastMCP("meals", dependencies=["mcp<2", "requests"])
API_BASE = "https://www.themealdb.com/api/json/v1/1/"


def fetch_meals(endpoint: str, params=None) -> list:
    try:
        result = requests.get(API_BASE + endpoint, params=params, timeout=15)
        result.raise_for_status()
    except requests.RequestException:
        logger.warning("MealDB request failed")
        raise ToolError("Unable to reach TheMealDB. Please try again.") from None
    try:
        payload = result.json()
    except ValueError:
        raise ToolError("TheMealDB returned invalid JSON.") from None
    if not isinstance(payload, dict) or "meals" not in payload:
        raise ToolError("TheMealDB returned an unexpected response.")
    meals = payload["meals"]
    if meals is None:
        return []
    if not isinstance(meals, list) or not all(isinstance(meal, dict) for meal in meals):
        raise ToolError("TheMealDB returned an unexpected response.")
    return meals


def check_limit(limit: int):
    if not 1 <= limit <= 25:
        raise ToolError("limit must be between 1 and 25.")


def full_details(meal: dict) -> dict:
    ingredients = []
    for number in range(1, 21):
        name = (meal.get(f"strIngredient{number}") or "").strip()
        measure = (meal.get(f"strMeasure{number}") or "").strip()
        if name:
            ingredients.append({"name": name, "measure": measure})
    return {
        "id": meal.get("idMeal"),
        "name": meal.get("strMeal"),
        "category": meal.get("strCategory"),
        "area": meal.get("strArea"),
        "instructions": meal.get("strInstructions"),
        "image": meal.get("strMealThumb"),
        "source": meal.get("strSource"),
        "youtube": meal.get("strYoutube"),
        "ingredients": ingredients,
    }


@mcp.tool(description="Search meals by name and return up to 25 recipe cards.", annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False))
def search_meals_by_name(query: str, limit: int = 5) -> list[dict]:
    check_limit(limit)
    if not query.strip():
        raise ToolError("query must not be blank.")
    meals = fetch_meals("search.php", {"s": query.strip()})
    return [
        {
            "id": meal.get("idMeal"),
            "name": meal.get("strMeal"),
            "area": meal.get("strArea"),
            "category": meal.get("strCategory"),
            "thumb": meal.get("strMealThumb"),
        }
        for meal in meals[:limit]
    ]


@mcp.tool(description="Find meals containing a main ingredient.", annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False))
def meals_by_ingredient(ingredient: str, limit: int = 12) -> list[dict]:
    check_limit(limit)
    if not ingredient.strip():
        raise ToolError("ingredient must not be blank.")
    meals = fetch_meals("filter.php", {"i": ingredient.strip()})
    return [
        {"id": meal.get("idMeal"), "name": meal.get("strMeal"), "thumb": meal.get("strMealThumb")}
        for meal in meals[:limit]
    ]


@mcp.tool(description="Return one random meal with full recipe details.", annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False))
def random_meal() -> dict:
    meals = fetch_meals("random.php")
    if not meals:
        raise ToolError("TheMealDB returned no random meal.")
    return full_details(meals[0])


@mcp.tool(description="Look up a meal ID and return its recipe and ingredient measures.", annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False))
def meal_details(id: str | int) -> dict:
    meal_id = str(id).strip()
    if not meal_id.isdigit() or int(meal_id) <= 0:
        raise ToolError("id must be a positive meal ID.")
    meals = fetch_meals("lookup.php", {"i": meal_id})
    if not meals:
        raise ToolError("No meal found for this ID.")
    return full_details(meals[0])


if __name__ == "__main__":
    mcp.run(transport="stdio")
