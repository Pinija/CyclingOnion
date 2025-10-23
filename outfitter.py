from weather import WeatherForecast, get_weather_forecast
from wardrobe import get_clothing_wardrobe


def get_optimized_outfit(hours: int, weather: WeatherForecast):
    """Minimize the discomfort score on all possible clothing sets for the current weather prediction."""
    eff_temp_min, eff_temp_max = weather.get_effective_temp_range()
    wind_max = weather.get_wind_max()
    precip_prob = weather.get_precipitation_prob()

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
        combo.sort(key=lambda x: x.get_discomfort(eff_temp_min, eff_temp_max, precip_prob, wind_max, hours))
        outfit[name] = combo[0]
    
    return outfit

if __name__ == "__main__":
    params = ["Freiburg", 3, "mountain", "hard"]
    weather = get_weather_forecast(*params)
    effective_weather = weather.get_effective_temp_range()
    print(weather)
    print("Effective temp (min, max): " + str(effective_weather))
    outfit = get_optimized_outfit(3, weather)
    for body_part, combo in outfit.items():
        print(body_part + ": " + str(combo))

    