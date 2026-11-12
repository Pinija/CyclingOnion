"""Weather boundary, aggregation, input validation, and API failure regressions."""

from dataclasses import replace

import pytest
import requests

from properties import Intensity, Terrain
from weather import FORECAST_URL, REQUEST_TIMEOUT, WeatherError, get_weather_forecast


def fetch(hours=2):
    return get_weather_forecast("Freiburg", hours, "flat", "medium")


def test_request_uses_environment_key_timeout_and_two_days(weather_http):
    get, response = weather_http
    result = get_weather_forecast("  Freiburg  ", 2, "flat", "medium")
    get.assert_called_once_with(
        FORECAST_URL,
        params={
            "key": "test-key-not-a-secret",
            "q": "Freiburg",
            "days": 2,
            "aqi": "no",
            "alerts": "no",
        },
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status.assert_called_once()
    assert result.forecast_duration == 2
    assert result.get_effective_temp_range() == (18, 20)


def test_hourly_aggregation_uses_only_the_ride_window(weather_payload, weather_http):
    hours = weather_payload["forecast"]["forecastday"][0]["hour"]
    hours[11]["temp_c"] = -100
    hours[14]["temp_c"] = 100
    hours[12].update(
        temp_c=17.26, windchill_c=14, wind_kph=12.34, chance_of_rain="15", precip_mm=0.12
    )
    hours[13].update(
        temp_c=22.14, windchill_c=16, wind_kph=30.36, chance_of_rain="70", precip_mm=0.24, is_day=0
    )
    result = fetch()
    assert (result.temp_min, result.temp_max, result.temp_min_felt) == (17.3, 22.1, 14)
    assert result.get_wind_max() == 30.4
    assert result.get_precipitation_prob() == 70
    assert result.precipitation_volume == 0.4
    assert result.is_night
    assert result.condition == "Sunny"


@pytest.mark.parametrize("duration", [1, 2, 6])
def test_late_ride_includes_tomorrow_and_partial_final_hour(
    weather_payload, weather_http, duration
):
    today, tomorrow = weather_payload["forecast"]["forecastday"]
    weather_payload["location"]["localtime_epoch"] = today["hour"][23]["time_epoch"] + 1800
    tomorrow["hour"][duration - 1].update(temp_c=-4, chance_of_rain=95, wind_kph=45)
    result = fetch(duration)
    assert result.forecast_duration == duration
    assert result.temp_min == -4
    assert result.precipitation_prob == 95
    assert result.wind_max == 45
    assert result.is_night


def test_partial_boundary_hours_are_included_and_precipitation_is_prorated(
    weather_payload, weather_http
):
    weather_payload["location"]["localtime_epoch"] += 1800
    hours = weather_payload["forecast"]["forecastday"][0]["hour"]
    for index, volume in [(12, 1), (13, 2), (14, 3)]:
        hours[index]["precip_mm"] = volume
    hours[14]["temp_c"] = 5
    hours[15]["temp_c"] = -100
    result = fetch()
    assert result.temp_min == 5
    assert result.precipitation_volume == 4  # 0.5 * 1 + 2 + 0.5 * 3


def test_epoch_order_handles_repeated_local_hour_and_unsorted_provider_data(
    weather_payload, weather_http
):
    hours = weather_payload["forecast"]["forecastday"][0]["hour"]
    hours[12]["time"] = hours[13]["time"] = "2026-10-25 02:00"
    weather_payload["location"]["localtime"] = "2026-10-25 02:30"
    hours[13]["temp_c"] = 8
    hours.reverse()
    assert fetch().temp_min == 8


@pytest.mark.parametrize(
    "damage",
    ["empty", "missing_start", "missing_middle", "missing_end", "duplicate", "no_tomorrow"],
)
def test_incomplete_or_duplicate_hours_are_rejected(weather_payload, weather_http, damage):
    days = weather_payload["forecast"]["forecastday"]
    hours = days[0]["hour"]
    if damage == "empty":
        days.clear()
    elif damage == "missing_start":
        del hours[12]
    elif damage == "missing_middle":
        del hours[13]
    elif damage == "missing_end":
        del hours[14]
    elif damage == "duplicate":
        hours.append(dict(hours[12]))
    else:
        weather_payload["location"]["localtime_epoch"] = hours[23]["time_epoch"]
        days.pop()
    with pytest.raises(WeatherError, match="complete forecast"):
        fetch(3)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("temp_c", None),
        ("temp_c", "nan"),
        ("windchill_c", "inf"),
        ("wind_kph", -1),
        ("chance_of_rain", 101),
        ("chance_of_rain", -1),
        ("precip_mm", -1),
        ("time_epoch", "not a time"),
        ("is_day", 3),
        ("is_day", 0.5),
        ("temp_c", True),
    ],
)
def test_malformed_hour_values_give_a_readable_error(weather_payload, weather_http, field, value):
    weather_payload["forecast"]["forecastday"][0]["hour"][12][field] = value
    with pytest.raises(WeatherError, match="invalid forecast data"):
        fetch()


@pytest.mark.parametrize("payload", [None, [], {}, {"location": None}, {"forecast": {}}])
def test_missing_response_structure_is_handled(weather_http, payload):
    weather_http[1].json.return_value = payload
    with pytest.raises(WeatherError, match="invalid"):
        fetch()


def test_missing_condition_is_handled(weather_payload, weather_http):
    weather_payload["forecast"]["forecastday"][0]["hour"][12]["condition"]["text"] = ""
    with pytest.raises(WeatherError, match="invalid forecast data"):
        fetch()


@pytest.mark.parametrize("icon", [None, 42])
def test_missing_icon_does_not_prevent_forecast(weather_payload, weather_http, icon):
    weather_payload["forecast"]["forecastday"][0]["hour"][12]["condition"]["icon"] = icon
    assert fetch().get_icon() is None


@pytest.mark.parametrize(
    ("code", "message"),
    [
        (1006, "Location not found"),
        (1002, "API key"),
        (2006, "API key"),
        (2008, "API key"),
        (2007, "quota"),
        (2009, "could not provide"),
        (9999, "could not provide"),
    ],
)
def test_provider_errors_are_actionable_and_do_not_echo_secrets(weather_http, code, message):
    response = weather_http[1]
    response.json.return_value = {"error": {"code": code, "message": "secret-provider-content"}}
    response.raise_for_status.side_effect = requests.HTTPError("URL?key=secret-provider-content")
    with pytest.raises(WeatherError, match=message) as caught:
        fetch()
    assert "secret-provider-content" not in str(caught.value)


def test_malformed_provider_error_is_handled(weather_http):
    weather_http[1].json.return_value = {"error": None}
    with pytest.raises(WeatherError, match="could not provide"):
        fetch()


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (requests.Timeout("key=secret"), "timed out"),
        (requests.ConnectionError("key=secret"), "Could not reach"),
    ],
)
def test_transport_failure_does_not_expose_request_url(weather_http, error, message):
    weather_http[0].side_effect = error
    with pytest.raises(WeatherError, match=message) as caught:
        fetch()
    assert "secret" not in str(caught.value)


def test_invalid_json_is_handled(weather_http):
    weather_http[1].json.side_effect = ValueError("not JSON")
    with pytest.raises(WeatherError, match="invalid response"):
        fetch()


def test_http_error_without_api_error_body_is_handled(weather_http):
    weather_http[1].raise_for_status.side_effect = requests.HTTPError("URL?key=secret")
    with pytest.raises(WeatherError, match="unavailable") as caught:
        fetch()
    assert "secret" not in str(caught.value)


@pytest.mark.parametrize("key", [None, "", "   "])
def test_missing_key_fails_before_request(monkeypatch, weather_http, key):
    if key is None:
        monkeypatch.delenv("WEATHERAPI_KEY")
    else:
        monkeypatch.setenv("WEATHERAPI_KEY", key)
    with pytest.raises(WeatherError, match="Set WEATHERAPI_KEY"):
        fetch()
    weather_http[0].assert_not_called()


@pytest.mark.parametrize(
    ("city", "duration", "terrain", "intensity"),
    [
        ("", 2, "flat", "easy"),
        ("  ", 2, "flat", "easy"),
        (None, 2, "flat", "easy"),
        ("Freiburg", 0, "flat", "easy"),
        ("Freiburg", -1, "flat", "easy"),
        ("Freiburg", 7, "flat", "easy"),
        ("Freiburg", 1.5, "flat", "easy"),
        ("Freiburg", True, "flat", "easy"),
        ("Freiburg", "2", "flat", "easy"),
        ("Freiburg", 2, None, "easy"),
        ("Freiburg", 2, [], "easy"),
        ("Freiburg", 2, "unknown", "easy"),
        ("Freiburg", 2, "flat", None),
        ("Freiburg", 2, "flat", []),
        ("Freiburg", 2, "flat", "hard"),
    ],
)
def test_invalid_inputs_fail_before_request(weather_http, city, duration, terrain, intensity):
    with pytest.raises(WeatherError):
        get_weather_forecast(city, duration, terrain, intensity)
    weather_http[0].assert_not_called()


@pytest.mark.parametrize(
    ("terrain", "low"),
    [(Terrain.FLAT, 13), (Terrain.HILLY, 10), (Terrain.MOUNTAIN, 7), (Terrain.ALPINE, 4)],
)
@pytest.mark.parametrize(
    ("intensity", "high"),
    [(Intensity.LIGHT, 20), (Intensity.MEDIUM, 20), (Intensity.TEMPO, 20), (Intensity.EXTREME, 20)],
)
def test_effective_temperature_allowances(forecast, terrain, low, intensity, high):
    assert replace(forecast, terrain=terrain, intensity=intensity).get_effective_temp_range() == (
        low,
        high,
    )


@pytest.mark.parametrize(
    ("changes", "phrase"),
    [
        ({"is_night": True, "temp_max": 30}, "lights"),
        ({"temp_max": 26, "temp_min": 5}, "hydrated"),
        ({"temp_min": 9, "intensity": "extreme"}, "gloves"),
        ({"intensity": "tempo"}, "fuel"),
        ({"intensity": "extreme"}, "fuel"),
        ({"forecast_duration": 3}, "fuel"),
        ({"terrain": "mountain"}, "view"),
        ({"terrain": "alpine"}, "view"),
        ({"temp_min": 10, "temp_max": 25}, "Enjoy the ride"),
    ],
)
def test_tip_priority_and_thresholds(forecast, changes, phrase):
    assert phrase in replace(forecast, **changes).get_pro_tip()


@pytest.mark.parametrize(
    "url",
    [
        "//cdn.weatherapi.com/weather/64x64/day/113.png",
        "https://cdn.weatherapi.com/weather/64x64/day/113.png",
    ],
)
def test_icon_urls_are_normalized_without_a_network_call(forecast, url):
    assert (
        replace(forecast, icon_url=url).get_icon()
        == "https://cdn.weatherapi.com/weather/64x64/day/113.png"
    )


@pytest.mark.parametrize(
    "url",
    [
        "",
        "http://cdn.weatherapi.com/image.png",
        "https://example.com/image.png",
        "https://[invalid",
    ],
)
def test_invalid_icon_urls_use_fallback(forecast, url):
    assert replace(forecast, icon_url=url).get_icon() is None


def test_enum_settings_reach_the_forecast(weather_http):
    result = get_weather_forecast("Freiburg", 2, Terrain.MOUNTAIN, Intensity.EXTREME)
    assert result.terrain is Terrain.MOUNTAIN
    assert result.intensity is Intensity.EXTREME
    assert result.get_effective_temp_range() == (12, 20)


def test_easy_ui_label_maps_to_light_intensity(weather_http):
    result = get_weather_forecast("Freiburg", 2, "Flat", "Easy")
    assert result.terrain is Terrain.FLAT
    assert result.intensity is Intensity.LIGHT


@pytest.mark.parametrize("intensity", [Intensity.TEMPO, Intensity.EXTREME])
def test_short_high_intensity_rides_still_get_fuel_tip(forecast, intensity):
    assert "fuel" in replace(forecast, intensity=intensity, forecast_duration=1).get_pro_tip()


@pytest.mark.parametrize("terrain", [Terrain.MOUNTAIN, Terrain.ALPINE])
def test_short_easy_mountain_rides_get_terrain_tip(forecast, terrain):
    assert "view" in replace(forecast, terrain=terrain, intensity=Intensity.LIGHT).get_pro_tip()
