from typing import Any, Dict

BAGGAGE_OPTIONS: Dict[int, Dict[str, Any]] = {
    0: {"id": 0, "name": "Carry-on Only (Up to 8kg)", "price": 0.0, "unit": "included"},
    1: {"id": 1, "name": "1 Standard Checked Bag (23kg)", "price": 35.0, "unit": "per passenger"},
    2: {"id": 2, "name": "2 Checked Bags (46kg total)", "price": 70.0, "unit": "per passenger"},
}

SEAT_OPTIONS: Dict[str, Dict[str, Any]] = {
    "STANDARD": {"id": "STANDARD", "name": "Standard Allocated Seat", "price": 0.0},
    "WINDOW_AISLE": {"id": "WINDOW_AISLE", "name": "Preferred Window / Aisle", "price": 15.0},
    "EXTRA_LEGROOM": {"id": "EXTRA_LEGROOM", "name": "Extra Legroom (Exit Row)", "price": 45.0},
}

MEAL_OPTIONS: Dict[str, Dict[str, Any]] = {
    "STANDARD": {"id": "STANDARD", "name": "Complimentary Snack & Drinks", "price": 0.0},
    "GOURMET": {"id": "GOURMET", "name": "Chef Gourmet Meal & Beverage", "price": 20.0},
    "VEGAN": {"id": "VEGAN", "name": "Vegan / Plant-Based Meal", "price": 0.0},
    "GLUTEN_FREE": {"id": "GLUTEN_FREE", "name": "Gluten-Free Certified Meal", "price": 0.0},
    "HALAL": {"id": "HALAL", "name": "Certified Halal Meal", "price": 0.0},
    "KOSHER": {"id": "KOSHER", "name": "Certified Kosher Meal", "price": 0.0},
}


def get_ancillary_catalog() -> Dict[str, Any]:
    """Returns the full catalog of available airline ancillaries and price points."""
    return {
        "baggage": list(BAGGAGE_OPTIONS.values()),
        "seats": list(SEAT_OPTIONS.values()),
        "meals": list(MEAL_OPTIONS.values()),
    }


def calculate_ancillary_breakdown(
    baggage_tier: int,
    seat_preference: str,
    meal_preference: str,
    seats: int = 1,
) -> tuple[float, Dict[str, Any]]:
    """Calculates total ancillary fare and structured itemized breakdown.

    Raises ValueError if options are invalid.
    """
    if baggage_tier not in BAGGAGE_OPTIONS:
        raise ValueError(f"Invalid baggage tier: {baggage_tier}")
    if seat_preference not in SEAT_OPTIONS:
        raise ValueError(f"Invalid seat preference: {seat_preference}")
    if meal_preference not in MEAL_OPTIONS:
        raise ValueError(f"Invalid meal preference: {meal_preference}")

    baggage_item = BAGGAGE_OPTIONS[baggage_tier]
    seat_item = SEAT_OPTIONS[seat_preference]
    meal_item = MEAL_OPTIONS[meal_preference]

    per_pax = round(float(baggage_item["price"]) + float(seat_item["price"]) + float(meal_item["price"]), 2)
    total_ancillary = round(per_pax * seats, 2)

    breakdown = {
        "baggage": {
            "tier": baggage_tier,
            "name": baggage_item["name"],
            "unit_price": baggage_item["price"],
            "total": round(float(baggage_item["price"]) * seats, 2),
        },
        "seat": {
            "tier": seat_preference,
            "name": seat_item["name"],
            "unit_price": seat_item["price"],
            "total": round(float(seat_item["price"]) * seats, 2),
        },
        "meal": {
            "tier": meal_preference,
            "name": meal_item["name"],
            "unit_price": meal_item["price"],
            "total": round(float(meal_item["price"]) * seats, 2),
        },
        "seats_count": seats,
        "per_passenger_ancillary": per_pax,
        "total_ancillary": total_ancillary,
    }
    return total_ancillary, breakdown
