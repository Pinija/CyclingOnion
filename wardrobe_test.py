"""Module to test functionality of the wardrobe."""

import unittest
from wardrobe import (
    Clothing,
    ClothingCombo,
    ClothingWardrobe,
    BodyPart,
    LayerType,
    get_clothing_wardrobe
)


class TestEnums(unittest.TestCase):
    """Test Enum definitions for correctness."""
    def test_body_part_values(self):
        self.assertEqual(BodyPart.UPPER.value, 1)
        self.assertEqual(BodyPart.LOWER.value, 2)
        self.assertEqual(BodyPart.HANDS.value, 3)
        self.assertEqual(BodyPart.FEET.value, 4)
        self.assertEqual(BodyPart.HEAD.value, 5)

    def test_layer_type_order(self):
        self.assertLess(LayerType.INNER.value, LayerType.MID.value)
        self.assertLess(LayerType.MID.value, LayerType.OUTER.value)


class TestClothing(unittest.TestCase):
    """Test the Clothing class logic."""

    def setUp(self):
        self.item = Clothing(
            name="Thermal Jacket",
            layer_type=LayerType.OUTER,
            body_part=BodyPart.UPPER,
            main_comfort_min=5,
            main_comfort_max=15,
            waterproof=True,
            windproof=True,
            removable=False,
            complexity=2
        )

    def test_repr_returns_name(self):
        self.assertEqual(repr(self.item), "Thermal Jacket")

    def test_properties_contains_keywords(self):
        props = self.item.properties()
        self.assertIn("Min. Temp", props)
        self.assertIn("Waterproof", props)
        self.assertIn("Windproof", props)

    def test_discomfort_calculation_cold(self):
        discomfort = self.item.get_discomfort(temp_min=-2, temp_max=8, rain_prob=0, wind_speed=10, duration_hours=2)
        self.assertGreater(discomfort, 0)  # should yield positive discomfort when too cold

    def test_discomfort_calculation_hot(self):
        discomfort = self.item.get_discomfort(temp_min=10, temp_max=25, rain_prob=0, wind_speed=5, duration_hours=2)
        self.assertGreater(discomfort, 0)  # discomfort for being too warm


class TestClothingCombo(unittest.TestCase):
    """Test layered combo calculations."""

    def setUp(self):
        self.inner = Clothing("Base Layer", LayerType.INNER, BodyPart.UPPER, temp_shift_min=-4, temp_shift_max=-2)
        self.outer = Clothing("Jacket", LayerType.OUTER, BodyPart.UPPER, main_comfort_min=10, main_comfort_max=18, windproof=True)
        self.combo = ClothingCombo([self.inner, self.outer])

    def test_combo_creates_valid_equivalent(self):
        combined = self.combo.get_clothing_item_equivalent()
        self.assertIsInstance(combined, Clothing)
        self.assertEqual(combined.body_part, BodyPart.UPPER)
        self.assertIn("Base Layer", combined.name)
        self.assertIn("Jacket", combined.name)

    def test_combo_combines_temperature_shift(self):
        combined = self.combo.get_clothing_item_equivalent()
        # outer min 10 + inner shift -4 => effective 6°C
        self.assertAlmostEqual(combined.main_comfort_min, 6, delta=0.5)


class TestClothingWardrobe(unittest.TestCase):
    """Test wardrobe combination generation."""

    def setUp(self):
        self.wardrobe = get_clothing_wardrobe()

    def test_grouped_clothing_items(self):
        grouped = self.wardrobe.grouped_clothing_items
        self.assertIn(BodyPart.UPPER, grouped)
        self.assertIn(BodyPart.FEET, grouped)
        self.assertTrue(all(isinstance(k, BodyPart) for k in grouped.keys()))

    def test_valid_combinations_for_part_returns_list(self):
        upper_combos = self.wardrobe.valid_combinations_for_part(BodyPart.UPPER)
        self.assertIsInstance(upper_combos, list)
        self.assertTrue(all(isinstance(c, Clothing) for c in upper_combos))

    def test_specific_combination_properties(self):
        head_combos = self.wardrobe.get_head_combinations()
        for combo in head_combos:
            self.assertIsInstance(combo, Clothing)
            self.assertEqual(combo.body_part, BodyPart.HEAD)

    def test_combinations_respect_layer_rules(self):
        upper_combos = self.wardrobe.get_upper_combinations()
        for combo in upper_combos:
            # At least one MID or OUTER layer must exist
            self.assertTrue(combo.layer_type in (LayerType.MID, LayerType.OUTER))
    
    class TestClothingWardrobe(unittest.TestCase):
    """Test wardrobe combination generation and logic."""

    def setUp(self):
        self.wardrobe = get_clothing_wardrobe()

    def test_grouped_clothing_items(self):
        grouped = self.wardrobe.grouped_clothing_items
        self.assertIn(BodyPart.UPPER, grouped)
        self.assertIn(BodyPart.FEET, grouped)
        self.assertTrue(all(isinstance(k, BodyPart) for k in grouped.keys()))

    def test_valid_combinations_for_part_returns_list(self):
        upper_combos = self.wardrobe.valid_combinations_for_part(BodyPart.UPPER)
        self.assertIsInstance(upper_combos, list)
        self.assertTrue(all(isinstance(c, Clothing) for c in upper_combos))

    def test_specific_combination_properties(self):
        head_combos = self.wardrobe.get_head_combinations()
        for combo in head_combos:
            self.assertIsInstance(combo, Clothing)
            self.assertEqual(combo.body_part, BodyPart.HEAD)

    def test_combinations_respect_layer_rules(self):
        upper_combos = self.wardrobe.get_upper_combinations()
        for combo in upper_combos:
            self.assertTrue(combo.layer_type in (LayerType.MID, LayerType.OUTER))


class TestWardrobeComfortScenarios(unittest.TestCase):
    """Integration-style tests checking if the wardrobe covers typical cycling conditions."""

    def setUp(self):
        self.wardrobe = get_clothing_wardrobe()

    def _best_outfit_for_conditions(self, body_part, temp_min, temp_max, rain, wind, duration):
        """Helper that returns best outfit and its discomfort."""
        combos = self.wardrobe.valid_combinations_for_part(body_part)
        discomforts = [
            (combo, combo.get_discomfort(temp_min, temp_max, rain, wind, duration))
            for combo in combos
        ]
        return min(discomforts, key=lambda x: x[1])

    def test_mild_spring_day(self):
        """15–20°C, light wind, no rain — should find low discomfort outfit."""
        results = {}
        for part in BodyPart:
            outfit, discomfort = self._best_outfit_for_conditions(part, 15, 20, rain=0, wind=5, duration=2)
            results[part] = discomfort
            self.assertLess(discomfort, 40, f"{part.name} outfit too uncomfortable for mild spring day")
        print("🌸 Mild spring results:", results)

    def test_winter_ride(self):
        """0–5°C, windy and possible rain — should still find a wearable combo."""
        results = {}
        for part in BodyPart:
            outfit, discomfort = self._best_outfit_for_conditions(part, 0, 5, rain=80, wind=25, duration=3)
            results[part] = discomfort
            self.assertLess(discomfort, 120, f"{part.name} outfit too uncomfortable for winter conditions")
        print("❄️ Winter ride results:", results)

    def test_hot_summer_ride(self):
        """28–35°C, no rain — combos should penalize overdressing."""
        results = {}
        for part in BodyPart:
            outfit, discomfort = self._best_outfit_for_conditions(part, 28, 35, rain=0, wind=10, duration=2)
            results[part] = discomfort
            self.assertLess(discomfort, 60, f"{part.name} outfit too uncomfortable for hot summer day")
        print("☀️ Summer ride results:", results)

    def test_missing_range_detection(self):
        """Ensure no major gaps: should have some viable outfit for 10°C–15°C."""
        viable_parts = []
        for part in BodyPart:
            outfit, discomfort = self._best_outfit_for_conditions(part, 10, 15, rain=10, wind=10, duration=2)
            if discomfort < 80:
                viable_parts.append(part)
        missing = [p.name for p in BodyPart if p not in viable_parts]
        self.assertFalse(missing, f"Missing viable clothing options for parts: {missing}")




if __name__ == "__main__":
    unittest.main()
