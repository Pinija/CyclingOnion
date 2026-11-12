"""Outfit selection against controlled alternatives and complete ride scenarios."""

from dataclasses import replace

import pytest

from outfitter import OutfitError, get_optimized_outfit
from wardrobe import BodyPart, Clothing, ClothingWardrobe, LayerType, get_clothing_wardrobe

PART_NAMES = {
    "Head": BodyPart.HEAD,
    "Upper Body": BodyPart.UPPER,
    "Lower Body": BodyPart.LOWER,
    "Hands": BodyPart.HANDS,
    "Feet": BodyPart.FEET,
}


def test_selects_lowest_cost_alternative_and_preserves_tie_order(forecast):
    wardrobe = get_clothing_wardrobe()
    wardrobe.clothing_items = [
        item for item in wardrobe.clothing_items if item.body_part != BodyPart.HEAD
    ]
    expensive = Clothing("Bulky", LayerType.MID, BodyPart.HEAD, 0, 30, complexity=5)
    first = replace(expensive, name="Simple", complexity=0)
    tied = replace(first, name="Tied")
    wardrobe.clothing_items.extend([expensive, first, tied])
    original_order = list(wardrobe.clothing_items)
    assert get_optimized_outfit(2, forecast, wardrobe)["Head"].name == "Simple"
    assert wardrobe.clothing_items == original_order


@pytest.mark.parametrize(
    ("low", "high", "rain", "wind", "duration", "terrain", "intensity"),
    [
        (15, 20, 10, 10, 2, "flat", "medium"),
        (0, 5, 80, 25, 3, "mountain", "easy"),
        (28, 35, 0, 10, 1, "flat", "tempo"),
        (5, 25, 60, 40, 6, "alpine", "extreme"),
    ],
)
def test_ride_scenarios_produce_a_complete_minimum_score_outfit(
    forecast, low, high, rain, wind, duration, terrain, intensity
):
    weather = replace(
        forecast,
        temp_min=low,
        temp_max=high,
        temp_min_felt=low - 2,
        precipitation_prob=rain,
        wind_max=wind,
        forecast_duration=duration,
        terrain=terrain,
        intensity=intensity,
    )
    wardrobe = get_clothing_wardrobe()
    outfit = get_optimized_outfit(duration, weather, wardrobe)
    assert set(outfit) == set(PART_NAMES)
    effective_low, effective_high = weather.get_effective_temp_range()
    for name, part in PART_NAMES.items():
        chosen = outfit[name]
        assert chosen.body_part == part
        alternatives = wardrobe.valid_combinations_for_part(part)
        chosen_cost = chosen.get_discomfort(effective_low, effective_high, rain, wind, duration)
        assert all(
            chosen_cost <= c.get_discomfort(effective_low, effective_high, rain, wind, duration)
            for c in alternatives
        )
    assert "Shoes" in outfit["Feet"].name


@pytest.mark.parametrize("missing", list(BodyPart))
def test_missing_body_part_reports_a_useful_error(forecast, missing):
    wardrobe = get_clothing_wardrobe()
    wardrobe.clothing_items = [c for c in wardrobe.clothing_items if c.body_part != missing]
    name = next(name for name, part in PART_NAMES.items() if part == missing)
    with pytest.raises(OutfitError, match=name):
        get_optimized_outfit(2, forecast, wardrobe)


def test_empty_custom_wardrobe_is_not_replaced_with_builtin(forecast):
    with pytest.raises(OutfitError, match="Head"):
        get_optimized_outfit(2, forecast, ClothingWardrobe([]))


@pytest.mark.parametrize("duration", [0, -1, 7, 1.5, True, "2"])
def test_invalid_duration_is_rejected(forecast, duration):
    with pytest.raises(OutfitError, match="whole number"):
        get_optimized_outfit(duration, forecast)


def test_scoring_duration_must_match_the_forecast(forecast):
    with pytest.raises(OutfitError, match="match"):
        get_optimized_outfit(3, forecast)
