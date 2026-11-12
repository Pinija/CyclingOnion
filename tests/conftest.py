"""Shared deterministic fixtures. Tests must never call the live weather service."""

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
import requests

from properties import Intensity, Terrain
from weather import WeatherForecast


@pytest.fixture(autouse=True)
def no_live_weather_requests(monkeypatch):
    def unexpected_request(*args, **kwargs):
        raise AssertionError("Unexpected network request: mock the weather response in this test")

    monkeypatch.setattr(requests.sessions.Session, "request", unexpected_request)
    monkeypatch.setenv("WEATHERAPI_KEY", "test-key-not-a-secret")


@pytest.fixture
def forecast():
    return WeatherForecast(
        forecast_duration=2,
        temp_min=15,
        temp_max=20,
        temp_min_felt=13,
        precipitation_prob=10,
        precipitation_volume=0.2,
        wind_max=12,
        is_night=False,
        condition="Partly cloudy",
        icon_url="//cdn.weatherapi.com/weather/64x64/day/116.png",
        terrain=Terrain.FLAT,
        intensity=Intensity.MEDIUM,
    )


@pytest.fixture
def weather_payload():
    """Two synthetic forecast days with epoch timestamps (no recorded user data)."""
    start = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp())
    days = []
    for day in range(2):
        days.append(
            {
                "hour": [
                    {
                        "time_epoch": start + (day * 24 + hour) * 3600,
                        "temp_c": 20,
                        "windchill_c": 18,
                        "wind_kph": 10,
                        "chance_of_rain": 0,
                        "precip_mm": 0,
                        "is_day": int(8 <= hour < 18),
                        "condition": {
                            "text": "Sunny",
                            "icon": "//cdn.weatherapi.com/weather/64x64/day/113.png",
                        },
                    }
                    for hour in range(24)
                ]
            }
        )
    return {
        "location": {"localtime_epoch": start + 12 * 3600, "localtime": "2026-01-01 12:00"},
        "forecast": {"forecastday": days},
    }


@pytest.fixture
def weather_http(monkeypatch, weather_payload):
    response = Mock(spec=requests.Response)
    response.json.return_value = weather_payload
    response.raise_for_status.return_value = None
    get = Mock(return_value=response)
    monkeypatch.setattr("weather.requests.get", get)
    return get, response
