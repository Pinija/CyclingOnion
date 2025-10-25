"""Module to call and process the weatherapi for CyclingOnion."""

from dataclasses import dataclass
from io import BytesIO
import requests

API_KEY = "38abfc21c9604a05b51174425252210"


@dataclass
class WeatherForecast():
    """The current and predicted weather conditions for the next t hours."""
    forecast_duraction: float
    temp_min: float
    temp_max: float
    temp_min_felt: float
    precipitation_prob: float
    precipilation_vol: float
    wind_max: float
    is_night: bool
    condition: str
    icon_url: str
    terrain: str
    intensity: str

    def get_icon(self):
        """Return a pixel bitmap of the icon describing the weather."""
        icon_url = "https:" + self.icon_url
        response = requests.get(icon_url)
        return BytesIO(response.content)

    def get_effective_temp_range(self):
        """ Compute realistic 'felt' temperature range for cycling:
        - uphill feels warmer (effort)
        - downhill feels colder (wind chill)
        - altitude gets colder"""
        t_up = self.temp_max
        t_down = self.temp_min_felt

        # Intensity adds heat on climbs only
        if self.intensity == "medium":
            t_up += 1.5
        elif self.intensity == "tempo":
            t_up += 3
        elif self.intensity == "extreme":
            t_up += 5

        # Terrain altitude correction (colder at height)
        if self.terrain == "alpine":
            t_down -= 9
        if self.terrain == "mountain":
            t_down -= 5  
        elif self.terrain == "hilly":
            t_down -= 1 

        # Compute comfort band
        temp_eff_min = round(t_down, 1)
        temp_eff_max = round(t_up, 1)
        return temp_eff_min, temp_eff_max

    def get_precipitation_prob(self):
        """Get the precipitation probability"""
        return self.precipitation_prob
    
    def get_wind_max(self):
        """Get the maximum wind speed"""
        return self.wind_max

    def get_pro_tip(self):
        """Get a tip."""
        if self.is_night:
            return ("It might get dark - don't forget your lights!")
        if self.temp_max > 25:
            return ("It might get hot - stay hydrated!")
        if self.temp_min < 10:
            return ("If you tend to get cold hands & feet - bring some extra gloves and socks!")
        if self.intensity == "tempo" or self.intensity == "extreme" or self.forecast_duraction > 2:
            return ("It will be a tough ride - don't forget some fuel!")
        if self.terrain == "mountain" or self.terrain == "alpine":
            return ("Enjoy the view! (And bring a wind jacket!)")
        
        return ("Enjoy the ride!")



def get_weather_forecast(city: str, hours: int, terrain: str, intensity: str):
    """
    Query WeatherAPI for the next `hours` hours in a given city,
    and compute temperature range, effective felt temps, rain prob, wind avg.
    """
    url = "https://api.weatherapi.com/v1/forecast.json"
    params = {"key": API_KEY, "q": city, "days": 1, "aqi": "no", "alerts": "no"}
    resp = requests.get(url, params=params)
    data = resp.json()

    # Extract hourly forecast
    forecast = data["forecast"]["forecastday"][0]["hour"]
    current_hour = int(data["location"]["localtime"].split(" ")[1].split(":")[0])

    # Slice next t hours (avoid overflow past 24h)
    next_hours = forecast[current_hour : min(current_hour + hours, 24)]

    # Aggregate core values
    temps = [h["temp_c"] for h in next_hours]
    winds = [h["wind_kph"] for h in next_hours]
    wind_chills = [h["windchill_c"] for h in next_hours]
    rain_probs = [h["chance_of_rain"] for h in next_hours]
    condition_text = next_hours[0]["condition"]["text"]
    icon_url = next_hours[0]["condition"]["icon"]
    precip = [h["precip_mm"] for h in next_hours]
    is_night = [not h["is_day"] for h in next_hours]

    temp_min = min(temps)
    temp_min_felt = min(wind_chills)
    temp_max = max(temps)
    wind_max = max(winds)
    rain_prob = max(rain_probs)  # worst-case for next t hours
    precip_total = round(sum(precip), 1)


    return WeatherForecast(
        hours,
        temp_min = round(temp_min, 1),
        temp_max = round(temp_max, 1),
        temp_min_felt = temp_min_felt,
        precipitation_prob = int(rain_prob),
        precipilation_vol = precip_total,
        wind_max = round(wind_max, 1),
        condition = condition_text,
        icon_url = icon_url,
        is_night=any(is_night),
        terrain = terrain,
        intensity = intensity
    )

if __name__ == "__main__":
    print(get_weather_forecast("Freiburg", 3, "mountain", "hard"))