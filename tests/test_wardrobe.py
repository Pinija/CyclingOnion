"""Behavioral checks for scoring, layering, and the built-in wardrobe."""

from dataclasses import replace

import pytest

from properties import Intensity, Terrain
from wardrobe import (
    BodyPart,
    Clothing,
    ClothingCombo,
    ClothingWardrobe,
    LayerType,
    get_clothing_wardrobe,
)


@pytest.fixture
def jersey():
    return Clothing("Jersey", LayerType.MID, BodyPart.UPPER, 10, 20, complexity=0)


@pytest.mark.parametrize(
    ("low", "high", "expected"),
    [(10, 20, 0), (5, 20, 50), (10, 25, 25), (5, 25, 75)],
)
def test_temperature_penalties_include_both_ends(jersey, low, high, expected):
    assert jersey.get_discomfort(
        low, high, 0, 0, 3, Intensity.MEDIUM, Terrain.FLAT
    ) == pytest.approx(expected)


def test_hotter_maximum_still_matters_when_the_minimum_is_too_cold(jersey):
    assert jersey.get_discomfort(
        5, 30, 0, 0, 2, Intensity.MEDIUM, Terrain.FLAT
    ) > jersey.get_discomfort(5, 25, 0, 0, 2, Intensity.MEDIUM, Terrain.FLAT)


def test_longer_rides_increase_cold_discomfort(jersey):
    assert jersey.get_discomfort(
        5, 20, 0, 0, 6, Intensity.MEDIUM, Terrain.FLAT
    ) > jersey.get_discomfort(5, 20, 0, 0, 1, Intensity.MEDIUM, Terrain.FLAT)


def test_protection_and_complexity_have_expected_costs_on_flat_terrain(jersey):
    assert jersey.get_discomfort(10, 20, 80, 30, 2, Intensity.MEDIUM, Terrain.FLAT) == 55
    protected = replace(jersey, waterproof=True, windproof=True, removability=1.0, complexity=2)
    assert protected.get_discomfort(10, 20, 80, 30, 2, Intensity.MEDIUM, Terrain.FLAT) == 10


@pytest.mark.parametrize(("low", "high"), [(0, 15), (-10, 0), (0, 0)])
def test_zero_degree_comfort_limits_are_not_replaced_by_defaults(jersey, low, high):
    equivalent = ClothingCombo([replace(jersey, main_comfort_min=low, main_comfort_max=high)])
    result = equivalent.get_clothing_item_equivalent()
    assert (result.main_comfort_min, result.main_comfort_max) == (low, high)


def test_layering_uses_outer_comfort_and_inner_modifiers_without_mutating_items(jersey):
    base = Clothing(
        "Base",
        LayerType.INNER,
        BodyPart.UPPER,
        temp_shift_min=-4,
        temp_shift_max=-2,
        wind_boost=0.4,
        complexity=0.5,
    )
    outer = replace(
        jersey,
        name="Shell",
        layer_type=LayerType.OUTER,
        waterproof=True,
        wind_boost=0.5,
        removability=1.0,
        complexity=1,
    )
    items = [outer, base]
    combined = ClothingCombo(items).get_clothing_item_equivalent()
    assert combined.name == "Base + Shell"
    assert (combined.main_comfort_min, combined.main_comfort_max) == (6, 18)
    assert combined.waterproof and combined.windproof and combined.removable
    assert combined.complexity == 1.5
    assert combined.wind_boost == pytest.approx(0.9)
    assert items == [outer, base]
    assert outer.main_comfort_min == 10


def test_invalid_combos_raise_explanatory_errors(jersey):
    with pytest.raises(ValueError, match="empty"):
        ClothingCombo([]).get_clothing_item_equivalent()
    with pytest.raises(ValueError, match="same body part"):
        ClothingCombo(
            [jersey, replace(jersey, body_part=BodyPart.HEAD)]
        ).get_clothing_item_equivalent()


def test_missing_body_part_has_no_combinations():
    assert ClothingWardrobe([]).valid_combinations_for_part(BodyPart.HEAD) == []


def test_layer_rules_enumerate_only_valid_sets(jersey):
    base = Clothing("Base", LayerType.INNER, BodyPart.UPPER)
    outer = replace(jersey, name="Shell", layer_type=LayerType.OUTER)
    other_jersey = replace(jersey, name="Other Jersey")
    wardrobe = ClothingWardrobe([base, jersey, other_jersey, outer])
    names = {combo.name for combo in wardrobe.get_upper_combinations()}
    assert names == {
        "Jersey",
        "Other Jersey",
        "Base + Jersey",
        "Base + Other Jersey",
        "Base + Shell",
        "Jersey + Shell",
        "Other Jersey + Shell",
        "Base + Jersey + Shell",
        "Base + Other Jersey + Shell",
    }


def test_accessories_require_a_main_layer_but_can_be_combined(jersey):
    arm = Clothing("Arms", LayerType.ACCESSORY, BodyPart.UPPER)
    neck = replace(arm, name="Neck")
    wardrobe = ClothingWardrobe([arm, neck, jersey])
    assert {c.name for c in wardrobe.get_upper_combinations()} == {
        "Jersey",
        "Arms + Jersey",
        "Neck + Jersey",
        "Arms + Neck + Jersey",
    }


def test_every_foot_combination_includes_shoes():
    combos = get_clothing_wardrobe().get_feet_combinations()
    assert combos
    assert all("Shoes" in combo.name for combo in combos)


def test_thermal_cap_preserves_its_declared_zero_degree_rating():
    cap = next(
        c for c in get_clothing_wardrobe().get_head_combinations() if c.name == "Thermal Cap"
    )
    assert cap.main_comfort_min == 0


@pytest.mark.parametrize("part", list(BodyPart))
def test_builtin_wardrobe_has_valid_unique_combinations_for_every_body_part(part):
    combos = get_clothing_wardrobe().valid_combinations_for_part(part)
    assert combos
    assert len({c.name for c in combos}) == len(combos)
    assert all(c.body_part == part and c.main_comfort_min <= c.main_comfort_max for c in combos)


def test_wardrobe_instances_do_not_share_mutable_inventory():
    first = get_clothing_wardrobe()
    first.clothing_items[0].name = "Changed"
    first.clothing_items.pop()
    second = get_clothing_wardrobe()
    assert second.clothing_items[0].name != "Changed"
    assert len(second.clothing_items) == len(first.clothing_items) + 1


@pytest.mark.parametrize("intensity", list(Intensity))
def test_intensity_scales_heat_and_sweat_but_not_cold(jersey, intensity):
    sealed = replace(jersey, breathability=0)
    assert sealed.get_discomfort(5, 25, 0, 0, 3, intensity, Terrain.FLAT) == pytest.approx(
        50 + 12.5 * intensity.value + 10 * intensity.value
    )
    assert jersey.get_discomfort(5, 20, 0, 0, 3, intensity, Terrain.FLAT) == 50


@pytest.mark.parametrize("terrain", list(Terrain))
@pytest.mark.parametrize("intensity", list(Intensity))
def test_removability_reward_keeps_terrain_and_intensity_weights(jersey, terrain, intensity):
    removable = replace(jersey, removability=2)
    score = removable.get_discomfort(10, 20, 0, 0, 2, intensity, terrain)
    assert score == -4 * (1 + intensity.value) * terrain.value


def test_breathability_combines_multiplicatively_and_rewards_better_inner_layers(jersey):
    shell = replace(jersey, layer_type=LayerType.OUTER, breathability=0.8)
    base = Clothing("Base", LayerType.INNER, BodyPart.UPPER, breathability=0.9, complexity=0)
    breathable = ClothingCombo([base, shell]).get_clothing_item_equivalent()
    less_breathable = ClothingCombo(
        [replace(base, breathability=0.2), shell]
    ).get_clothing_item_equivalent()
    assert breathable.breathability == pytest.approx(0.72)
    assert less_breathable.breathability == pytest.approx(0.16)
    assert breathable.get_discomfort(
        10, 20, 0, 0, 2, Intensity.EXTREME, Terrain.FLAT
    ) == pytest.approx(11.2)
    assert less_breathable.get_discomfort(
        10, 20, 0, 0, 2, Intensity.EXTREME, Terrain.FLAT
    ) == pytest.approx(33.6)
    assert base.breathability == 0.9
    assert shell.breathability == 0.8


@pytest.mark.parametrize(("rating", "expected"), [(0, 0), (1, 0.8)])
def test_breathability_boundary_layers(jersey, rating, expected):
    base = Clothing("Base", LayerType.INNER, BodyPart.UPPER, breathability=rating)
    shell = replace(jersey, layer_type=LayerType.OUTER, breathability=0.8)
    assert ClothingCombo([base, shell]).get_clothing_item_equivalent().breathability == expected


def test_removability_is_additive_and_exposes_the_ui_property(jersey):
    base = Clothing("Base", LayerType.INNER, BodyPart.UPPER, removability=0.5)
    shell = replace(jersey, layer_type=LayerType.OUTER, removability=0.5)
    combined = ClothingCombo([base, shell]).get_clothing_item_equivalent()
    assert combined.removability == 1
    assert combined.removable
    assert not base.removable


@pytest.mark.parametrize("rating", [-0.1, 1.1, float("nan"), float("inf"), None, "0.5"])
def test_invalid_breathability_is_rejected(jersey, rating):
    with pytest.raises(ValueError, match="Breathability"):
        replace(jersey, breathability=rating)


@pytest.mark.parametrize("rating", [-1, float("nan"), float("inf"), None, "1"])
def test_invalid_removability_is_rejected(jersey, rating):
    with pytest.raises(ValueError, match="Removability"):
        replace(jersey, removability=rating)
