"""Model the wardrobe and properties of clothing sets of CyclingOnion"""

from dataclasses import dataclass
from enum import Enum
from itertools import combinations


class BodyPart(Enum):
    """Enum defining the body part of a clothing item."""
    UPPER = 1       # jersey, base, ...
    LOWER = 2       # bibtight, bibshort, winterbib, ...
    HANDS = 3       # light gloves, fingerlings, ...
    FEET = 4        # Shoes, socks, winter shoes, shoe cover
    HEAD = 5        # headband, neck warmer, ...

class LayerType(Enum):
    """Enum defining the position in a layered clothing set."""
    ACCESSORY = 0   # knee warmer, toe cover
    INNER = 1        # base layer, thermal undershirt
    MID = 2          # jersey, thermal jersey
    OUTER = 3        # jacket, rain shell, ...
    


@dataclass
class Clothing:
    """Represents a clothing item or set with layering and comfort properties.

    Attributes:
        name (str): Human-readable name of the clothing.
        layer_type (LayerType): The type of layer defining the hierarchy (INNER, MID, OUTER, ACCESSORY)
        body_part (BodyPart): The body part this clothing item covers (UPPER, LOWER, HANDS, FEET, HEAD).
        main_comfort_min (float): Minimum comfortable temperature (°C) if this item is the outermost layer.
        main_comfort_max (float): Maximum comfortable temperature (°C) if this item is the outermost layer.
        temp_shift_min (float): Modifier to the outermost layers minimum comfort when this item is worn underneath.
        temp_shift_max (float): Modifier to the outermost layers maximum comfort when this item is worn underneath.
        wind_boost (float): Modifier representing how much this item improves wind resistance, if a layering has a sum
            of close to 1, this is considered windproof even if no item is explicitly windproof.
        waterproof (bool): Whether this item is waterproof.
        windproof (bool): Whether this item is windproof (fully blocks wind).
        removable (bool): Whether this item can be removed during a ride, reducing warm discomfort.
        complexity (float): Penalty representing the effort or bulk of wearing this item."""

    name: str
    layer_type: LayerType
    body_part: BodyPart
    main_comfort_min: float = 50    # Initialize with bad values -> Everything with real values is preferred
    main_comfort_max: float = 0     # Initialize with bad values -> Everything with real values is preferred
    temp_shift_min: float = 0.0
    temp_shift_max: float = 0.0
    wind_boost: float = 0.0
    waterproof: bool = False
    windproof: bool = False
    removable: bool = False
    complexity: float = 1.0

    def __repr__(self):
        """Get a string of the name of the item or combo."""
        return self.name
    
    def properties(self):
        """Get a string of the properties of the item or the combo."""
        properties = f"Properties: Min. Temp [°C]: {self.main_comfort_min}, Max Temp [°C]: {self.main_comfort_max}"
        if self.windproof:
            properties+= ", Windproof ✅"
        if self.waterproof:
            properties+= ", Waterproof ✅"
        return properties

    def get_discomfort(self, temp_min: float, temp_max: float, rain_prob: float, wind_speed: float, duration_hours: int) -> float:
        """Estimate discomfort score (lower => better) depending of temperature conditions, intensity and ride duration."""
        # Temperature comfort
        cold_penalty = 0
        warm_penalty = 0
        if temp_min < self.main_comfort_min:
            cold_penalty = (self.main_comfort_min - temp_min) ** 2
        elif temp_max > self.main_comfort_max:
            warm_penalty = (temp_max - self.main_comfort_max) ** 2
    

        # Adjust based on intensity and duration
        cold_penalty *= (0.33 + duration_hours / 3)
        warm_penalty *= 1

        # Add penalties for missing protection
        rain_penalty = 0.75 * rain_prob if not self.waterproof else 0
        wind_penalty = 0.5 * wind_speed if not self.windproof else 0

        # Reward removability (slightly)
        remove_bonus = -4.5 if self.removable else 0

        # Complexity penalty (prefer simpler outfits)
        complexity_penalty =  5*self.complexity

        return cold_penalty + warm_penalty + rain_penalty + wind_penalty + complexity_penalty + remove_bonus


@dataclass
class ClothingCombo:
    """Represents a clothing combination for one body part."""

    combo_items: list[Clothing]

    def get_clothing_item_equivalent(self) -> Clothing:
        """Compose the combo and modify its outer layer by the inner modifiers.
        Returns a `Clothing` with estimated properties of the whole combo."""
        # Sort inner → outer
        sorted_layers = sorted(self.combo_items, key=lambda x: x.layer_type.value)
        outer = sorted_layers[-1]

        # Base properties from the outer layer
        eff_min = outer.main_comfort_min or 15.0
        eff_max = outer.main_comfort_max or 35.0
        waterproof = outer.waterproof
        windproof = outer.windproof
        wind_boost = outer.wind_boost
        complexity = outer.complexity
        removable = outer.removable

        # Combine modifier effects from inner layers
        for inner in sorted_layers[:-1]:
            eff_min += inner.temp_shift_min
            eff_max += inner.temp_shift_max
            wind_boost += inner.wind_boost
            waterproof = waterproof or inner.waterproof
            windproof = windproof or inner.windproof
            complexity += inner.complexity
            removable = removable or inner.removable

        if wind_boost >= 0.9:
            windproof = True
        # Build the combo name
        combo_name = " + ".join([i.name for i in sorted_layers])

        # Return a new item with combined properties
        return Clothing(
            name=combo_name,
            layer_type=outer.layer_type,
            body_part=outer.body_part,
            main_comfort_min=eff_min,
            main_comfort_max=eff_max,
            wind_boost=wind_boost,
            waterproof=waterproof,
            windproof=windproof,
            removable=removable,
            complexity=complexity,
        )


@dataclass
class ClothingWardrobe:
    """The wardrobe to chose outfits from."""
    clothing_items: list[Clothing]

    @property
    def grouped_clothing_items(self) -> dict:
        """Group a clothing wardrobe after bodypart."""
        parts = {}
        for item in self.clothing_items:
            parts.setdefault(item.body_part, []).append(item)
        return parts

    def valid_combinations_for_part(self, body_part: BodyPart) -> list[Clothing]:
        """Return all valid combinations of cloths for a specific body part."""
        all_items = self.grouped_clothing_items
        items = all_items[body_part]
        combos = []
        for r in range(1, len(items) + 1):
            for clothing_combo in combinations(items, r):
                outers = [c for c in clothing_combo if c.layer_type == LayerType.OUTER]
                mids = [c for c in clothing_combo if c.layer_type == LayerType.MID]
                inners = [c for c in clothing_combo if c.layer_type == LayerType.INNER]
                # at most one outer, mid and inner
                if len(outers) > 1 or len(mids) > 1 or len(inners) > 1:
                    continue
                # must contain a MID or OUTER as "main"
                if not any(c.layer_type in (LayerType.MID, LayerType.OUTER) for c in clothing_combo):
                    continue
                # must contain INNER  OR MID if OUTER as "main"
                if len(outers) == 1 and len(inners) < 1 and len(mids) < 1:
                    continue
                    
                combos.append(ClothingCombo(sorted(clothing_combo, key=lambda x: x.layer_type.value)).get_clothing_item_equivalent())
        return combos

    def get_head_combinations(self) -> list[Clothing]:
        """Return all valid combinations of cloths for the head."""
        return self.valid_combinations_for_part(BodyPart.HEAD)

    def get_upper_combinations(self) -> list[Clothing]:
        """Return all valid combinations of cloths for the head."""
        return self.valid_combinations_for_part(BodyPart.UPPER)

    def get_feet_combinations(self) -> list[Clothing]:
        """Return all valid combinations of cloths for the head."""
        return self.valid_combinations_for_part(BodyPart.FEET)

    def get_hands_combinations(self) -> list[Clothing]:
        """Return all valid combinations of cloths for the head."""
        return self.valid_combinations_for_part(BodyPart.HANDS)

    def get_lower_combinations(self) -> list[Clothing]:
        """Return all valid combinations of cloths for the head."""
        return self.valid_combinations_for_part(BodyPart.LOWER)



WARDROBE = [
    # Upper Body
    Clothing("Sweat Base", LayerType.INNER, BodyPart.UPPER, temp_shift_min=-3, temp_shift_max=0, removable=False, complexity=0.5),
    Clothing("Thermal Base Long", LayerType.INNER, BodyPart.UPPER, temp_shift_min=-6, temp_shift_max=-5, removable=False, complexity=1.5),
    Clothing("Merino Base Long", LayerType.INNER, BodyPart.UPPER, temp_shift_min=-5, temp_shift_max=-1, removable=False, complexity=0),
    Clothing("Jersey", LayerType.MID, BodyPart.UPPER, main_comfort_min=20, main_comfort_max=30, temp_shift_min=0, temp_shift_max=-1 ),
    Clothing("Thermal Jersey", LayerType.MID, BodyPart.UPPER, main_comfort_min=15, main_comfort_max=18, temp_shift_min=-4, temp_shift_max=-5, wind_boost=0.5, removable=False, complexity=2),
    Clothing("Arm Warmers", LayerType.ACCESSORY, BodyPart.UPPER, temp_shift_min=-3, temp_shift_max=-2, wind_boost=0.5, removable=True),
    Clothing("Wind Jacket", LayerType.OUTER, BodyPart.UPPER, main_comfort_min=15, main_comfort_max=20, windproof=True, removable=True),
    Clothing("Sportful Total Comfort Winter Jacket", LayerType.OUTER, BodyPart.UPPER, main_comfort_min=10, main_comfort_max=15, windproof=True, waterproof=True, complexity=2.5),

    # Lower Body
    Clothing("Short Bibs", LayerType.MID, BodyPart.LOWER, main_comfort_min=15, main_comfort_max=35),
    Clothing("Sportful Fiandre Bibshort", LayerType.MID, BodyPart.LOWER, main_comfort_min=9, main_comfort_max=22, temp_shift_min=-3, temp_shift_max=-4, waterproof=True),
    Clothing("Sportful Fiandre Long Bibs", LayerType.MID, BodyPart.LOWER, main_comfort_min=6, main_comfort_max=15, temp_shift_min=-6, wind_boost=0.5, temp_shift_max=-7, waterproof=True),
    Clothing("Winter Bibs", LayerType.OUTER, BodyPart.LOWER, main_comfort_min=3, main_comfort_max=10, waterproof=True, windproof=True, complexity=1.5),
    Clothing("Leg Warmers", LayerType.ACCESSORY, BodyPart.LOWER, temp_shift_min=-3, temp_shift_max=-4, removable=True),

    # Feet
    Clothing("Cycling Socks", LayerType.INNER, BodyPart.FEET, temp_shift_min=-1, complexity=-1),
    Clothing("Thermal Socks", LayerType.INNER, BodyPart.FEET, temp_shift_min=-5, temp_shift_max=-2, complexity=-1),
    Clothing("Cycling Shoes", LayerType.MID, BodyPart.FEET, main_comfort_min=18, main_comfort_max=28, wind_boost=0.5),
    Clothing("Winter Shoes", LayerType.OUTER, BodyPart.FEET, main_comfort_min=8, main_comfort_max=15, waterproof=True, windproof=True, complexity=2),
    Clothing("Toe Covers", LayerType.ACCESSORY, BodyPart.FEET, temp_shift_min=-2, temp_shift_max=-1, wind_boost=0.5, waterproof=False, removable=True, complexity=0.5),
    Clothing("Shoe Covers", LayerType.ACCESSORY, BodyPart.FEET, temp_shift_min=-4, temp_shift_max=-2, windproof=True, waterproof=True, removable=True, complexity=0.75),

    # Hands
    Clothing("Short Gloves", LayerType.MID, BodyPart.HANDS, main_comfort_min=16, main_comfort_max=35, removable=True),
    Clothing("Light Gloves", LayerType.MID, BodyPart.HANDS, main_comfort_min=10, main_comfort_max=23, temp_shift_min=-2, temp_shift_max=-1, removable=True, complexity=1),
    Clothing("Thermal Gloves", LayerType.OUTER, BodyPart.HANDS, main_comfort_min=2, main_comfort_max=14, waterproof=True, windproof=True, removable=True, complexity=2.5),
    Clothing("Bare Hands", LayerType.MID, BodyPart.HANDS, main_comfort_min=18, main_comfort_max=40),

    # Head
    Clothing("Sportful Thermal Headband", LayerType.MID, BodyPart.HEAD, main_comfort_min=5, main_comfort_max=18, windproof=True, waterproof=True, removable=True),
    Clothing("Cap", LayerType.MID, BodyPart.HEAD, main_comfort_min=0, main_comfort_max=15, windproof=True),
    Clothing("Bare Head", LayerType.MID, BodyPart.HEAD, main_comfort_min=16, main_comfort_max=40),

]

def get_clothing_wardrobe() -> ClothingWardrobe:
    """Get the predefined onion wardrobe of OnionRide."""
    return ClothingWardrobe(WARDROBE)


if __name__ == "__main__":
    my_wardrobe = get_clothing_wardrobe()
    combs = my_wardrobe.valid_combinations_for_part(BodyPart.UPPER)
    print(combs[5:15])

    clothing_combo_1 = ClothingCombo(
        [Clothing("Shoe Covers", LayerType.ACCESSORY, BodyPart.FEET, temp_shift_min=-4, temp_shift_max=-2, windproof=True, waterproof=True, removable=True, complexity=0.75), 
        Clothing("Thermal Socks", LayerType.INNER, BodyPart.FEET, temp_shift_min=-5, temp_shift_max=-2, complexity=-1), 
        Clothing("Winter Shoes", LayerType.OUTER, BodyPart.FEET, main_comfort_min=8, main_comfort_max=15, waterproof=True, windproof=True, complexity=2)]
    ).get_clothing_item_equivalent()

    clothing_combo_2 = ClothingCombo(
        [Clothing("Thermal Socks", LayerType.INNER, BodyPart.FEET, temp_shift_min=-5, temp_shift_max=-2, complexity=-1), 
        Clothing("Winter Shoes", LayerType.OUTER, BodyPart.FEET, main_comfort_min=8, main_comfort_max=15, waterproof=True, windproof=True, complexity=2)]
    ).get_clothing_item_equivalent()

    print(clothing_combo_1.get_discomfort(-1.2, 14.4, 100, 30, 3))
    print(clothing_combo_2.get_discomfort(-1.2, 14.4, 100, 30, 3))


    