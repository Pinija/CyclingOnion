"""Fetch a complete ride forecast and apply CyclingOnion's comfort heuristics."""

import math
import os
from dataclasses import dataclass
from urllib.parse import urlsplit

import requests

from properties import Intensity, Terrain, get_intensity, get_terrain

FORECAST_URL = "https://api.weatherapi.com/v1/forecast.json"
REQUEST_TIMEOUT = 10


class WeatherError(ValueError):
    """A weather/configuration failure that can be displayed without exposing secrets."""


@dataclass
class WeatherForecast:
    """Aggregated hourly conditions over a ride starting at the provider's local now.

    Temperatures are Celsius, wind is km/h, precipitation is mm, and probability
    is a percentage. Comfort corrections are personal estimates, not physiology.
    """

    forecast_duration: int
    temp_min: float
    temp_max: float
    temp_min_felt: float
    precipitation_prob: float
    precipitation_volume: float
    wind_max: float
    is_night: bool
    condition: str
    icon_url: str
    terrain: Terrain
    intensity: Intensity

    def __post_init__(self):
        """Normalize labels at the boundary so model logic always uses enums."""
        self.terrain = get_terrain(self.terrain)
        self.intensity = get_intensity(self.intensity)

    def get_icon(self) -> str | None:
        """Return a provider icon URL for the browser, or None for a missing icon.

        Icons are optional: fetching a decorative image must not block an outfit.
        Both protocol-relative and absolute HTTPS URLs are accepted.
        """
        url = "https:" + self.icon_url if self.icon_url.startswith("//") else self.icon_url
        try:
            parsed = urlsplit(url)
        except ValueError:
            return None
        if parsed.scheme == "https" and parsed.netloc == "cdn.weatherapi.com":
            return url
        return None

    def get_effective_temp_range(self) -> tuple[float, float]:
        """Apply the terrain allowance; intensity affects clothing scores only."""
        low = self.temp_min_felt - 3 * self.terrain.value
        return round(low, 1), round(self.temp_max, 1)

    def get_precipitation_prob(self) -> float:
        """Return the maximum hourly rain probability, not whole-ride probability."""
        return self.precipitation_prob

    def get_wind_max(self) -> float:
        """Return the maximum hourly forecast wind speed in km/h."""
        return self.wind_max

    def get_pro_tip(self) -> str:
        """Choose a tip, prioritizing darkness, heat, cold, exertion, then terrain."""
        if self.is_night:
            return "It might get dark - don't forget your lights!"
        if self.temp_max > 25:
            return "It might get hot - stay hydrated!"
        if self.temp_min < 10:
            return "If you tend to get cold hands & feet - bring some extra gloves and socks!"
        if self.intensity in (Intensity.TEMPO, Intensity.EXTREME) or self.forecast_duration > 2:
            return "It will be a tough ride - don't forget some fuel!"
        if self.terrain in (Terrain.MOUNTAIN, Terrain.ALPINE):
            return "Enjoy the view! (And bring a wind jacket!)"
        return "Enjoy the ride!"


def _number(value, minimum=None, maximum=None) -> float:
    """Accept provider numeric strings while rejecting missing or invalid numbers."""
    if isinstance(value, bool):
        raise ValueError("Boolean where a number was expected")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Non-finite weather value")
    if minimum is not None and number < minimum:
        raise ValueError("Weather value below range")
    if maximum is not None and number > maximum:
        raise ValueError("Weather value above range")
    return number


def _parse_forecast(
    data: dict, hours: int, terrain: Terrain, intensity: Intensity
) -> WeatherForecast:
    """Select contiguous hourly buckets overlapping [now, now + duration).

    Epoch comparisons handle midnight and timezone/DST changes without depending
    on the computer's timezone. A partially overlapping final hour is included.
    """
    start = _number(data["location"]["localtime_epoch"])
    end = start + hours * 3600
    hourly = sorted(
        (h for day in data["forecast"]["forecastday"] for h in day["hour"]),
        key=lambda h: _number(h["time_epoch"]),
    )
    selected = [h for h in hourly if start - 3600 < _number(h["time_epoch"]) < end]
    timestamps = [_number(h["time_epoch"]) for h in selected]
    if (
        not timestamps
        or timestamps[0] > start
        or timestamps[-1] + 3600 < end
        or any(b - a != 3600 for a, b in zip(timestamps, timestamps[1:]))
    ):
        raise WeatherError("The weather service did not return a complete forecast for this ride.")

    temps = [_number(h["temp_c"]) for h in selected]
    chills = [_number(h["windchill_c"]) for h in selected]
    winds = [_number(h["wind_kph"], minimum=0) for h in selected]
    rain = [_number(h["chance_of_rain"], minimum=0, maximum=100) for h in selected]
    daylight = [_number(h["is_day"], minimum=0, maximum=1) for h in selected]
    if any(value not in (0, 1) for value in daylight):
        raise ValueError("Daylight flag must be 0 or 1")
    # Prorate boundary buckets, assuming uniform precipitation within each hour.
    volume = sum(
        _number(h["precip_mm"], minimum=0)
        * (min(end, timestamp + 3600) - max(start, timestamp))
        / 3600
        for h, timestamp in zip(selected, timestamps)
    )
    condition = selected[0]["condition"]["text"]
    if not isinstance(condition, str) or not condition.strip():
        raise ValueError("Missing weather condition")
    icon = selected[0]["condition"].get("icon", "")
    return WeatherForecast(
        forecast_duration=hours,
        temp_min=round(min(temps), 1),
        temp_max=round(max(temps), 1),
        temp_min_felt=min(chills),
        precipitation_prob=max(rain),
        precipitation_volume=round(volume, 1),
        wind_max=round(max(winds), 1),
        is_night=any(value == 0 for value in daylight),
        condition=condition,
        icon_url=icon if isinstance(icon, str) else "",
        terrain=terrain,
        intensity=intensity,
    )


def get_weather_forecast(
    city: str, hours: int, terrain: Terrain | str, intensity: Intensity | str
) -> WeatherForecast:
    """Fetch a complete 1–6 hour forecast using WEATHERAPI_KEY from the environment.

    Raise WeatherError for invalid inputs, missing configuration, network/API
    failures, or malformed/incomplete responses. Never include raw request URLs
    or provider error text in user-facing errors, as they may contain the key.
    """
    if not isinstance(city, str) or not city.strip():
        raise WeatherError("Please enter a location before continuing.")
    if isinstance(hours, bool) or not isinstance(hours, int) or not 1 <= hours <= 6:
        raise WeatherError("Ride duration must be a whole number from 1 to 6 hours.")
    try:
        terrain = get_terrain(terrain)
        intensity = get_intensity(intensity)
    except ValueError as error:
        raise WeatherError(str(error)) from None
    api_key = os.environ.get("WEATHERAPI_KEY", "").strip()
    if not api_key:
        raise WeatherError("Set WEATHERAPI_KEY in the environment before requesting a forecast.")

    params = {"key": api_key, "q": city.strip(), "days": 2, "aqi": "no", "alerts": "no"}
    try:
        response = requests.get(FORECAST_URL, params=params, timeout=REQUEST_TIMEOUT)
    except requests.Timeout:
        raise WeatherError("The weather request timed out. Please try again.") from None
    except requests.RequestException:
        raise WeatherError("Could not reach the weather service. Please try again.") from None

    try:
        data = response.json()
    except ValueError:
        raise WeatherError(
            "The weather service returned an invalid response. Please try again."
        ) from None
    if not isinstance(data, dict):
        raise WeatherError("The weather service returned an invalid response. Please try again.")
    if "error" in data:
        error = data["error"]
        code = error.get("code") if isinstance(error, dict) else None
        if code == 1006:
            raise WeatherError("Location not found. Try a city name with its country.")
        if code in (1002, 2006, 2008):
            raise WeatherError(
                "The weather API key is missing, invalid, or disabled. Check WEATHERAPI_KEY."
            )
        if code == 2007:
            raise WeatherError(
                "The weather service quota has been reached. Please try again later."
            )
        raise WeatherError(
            "The weather service could not provide a forecast. Please try again later."
        )
    try:
        response.raise_for_status()
    except requests.RequestException:
        raise WeatherError("The weather service is unavailable. Please try again later.") from None
    try:
        return _parse_forecast(data, hours, terrain, intensity)
    except WeatherError:
        raise
    except (KeyError, TypeError, ValueError, OverflowError):
        raise WeatherError(
            "The weather service returned incomplete or invalid forecast data."
        ) from None
