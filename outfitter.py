"""Choose the lowest-scoring valid clothing combination for each body part."""

from wardrobe import Clothing, ClothingWardrobe, get_clothing_wardrobe
from weather import WeatherForecast


class OutfitError(ValueError):
    """The wardrobe or ride cannot produce a complete outfit."""


def get_optimized_outfit(
    hours: int, weather: WeatherForecast, wardrobe: ClothingWardrobe | None = None
) -> dict[str, Clothing]:
    """Minimize the additive discomfort score, independently per body part.

    Ties retain wardrobe order. Supplying a wardrobe supports custom inventories
    and deterministic tests without modifying the built-in catalogue.
    """
    if isinstance(hours, bool) or not isinstance(hours, int) or not 1 <= hours <= 6:
        raise OutfitError("Ride duration must be a whole number from 1 to 6 hours.")
    if hours != weather.forecast_duration:
        raise OutfitError("Ride duration must match the weather forecast duration.")

    eff_temp_min, eff_temp_max = weather.get_effective_temp_range()
    if wardrobe is None:
        wardrobe = get_clothing_wardrobe()
    combos = {
        "Head": wardrobe.get_head_combinations(),
        "Upper Body": wardrobe.get_upper_combinations(),
        "Lower Body": wardrobe.get_lower_combinations(),
        "Hands": wardrobe.get_hands_combinations(),
        "Feet": wardrobe.get_feet_combinations(),
    }

    outfit = {}
    for name, candidates in combos.items():
        if not candidates:
            raise OutfitError(f"No valid clothing combinations for {name}. Check the wardrobe.")
        outfit[name] = min(
            candidates,
            key=lambda item: item.get_discomfort(
                eff_temp_min, eff_temp_max, weather.precipitation_prob, weather.wind_max, hours
            ),
        )
    return outfit
