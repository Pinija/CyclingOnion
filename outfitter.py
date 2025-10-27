from weather import WeatherForecast
from wardrobe import get_clothing_wardrobe
from properties import Intensity, Terrain


def get_optimized_outfit(hours: int, weather_fc: WeatherForecast, intensity: Intensity, terrain: Terrain):
    """Minimize the discomfort score on all possible clothing sets for the current weather prediction."""
    eff_temp_min, eff_temp_max = weather_fc.get_effective_temp_range()
    wind_max = weather_fc.get_wind_max()
    precip_prob = weather_fc.get_precipitation_prob()

    wardrobe = get_clothing_wardrobe()
    combos = {
        "Head" : wardrobe.get_head_combinations(),
        "Upper Body" : wardrobe.get_upper_combinations(),
        "Lower Body" : wardrobe.get_lower_combinations(),
        "Hands" : wardrobe.get_hands_combinations(),
        "Feet" : wardrobe.get_feet_combinations()
    }

    outfit = {}
    for name, combo in combos.items():
        combo.sort(key=lambda x: x.get_discomfort(eff_temp_min, eff_temp_max, precip_prob, wind_max, hours, intensity, terrain))
        outfit[name] = combo[0]
    
    return outfit

if __name__ == "__main__":
    pass
    