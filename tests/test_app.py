"""Headless Streamlit interaction tests using the real weather parser and optimizer."""

from pathlib import Path

import pytest
import requests
from streamlit.testing.v1 import AppTest

from outfitter import OutfitError

APP_PATH = Path(__file__).resolve().parents[1] / "cyclingonion_app.py"


@pytest.fixture
def app():
    return AppTest.from_file(str(APP_PATH), default_timeout=10).run()


def submit(app, location="Freiburg"):
    app.text_input[0].set_value(location)
    return app.button[0].click().run()


def test_initial_render_does_not_request_weather(app, weather_http):
    assert not app.exception
    assert not app.error
    assert app.slider[0].value == 2
    weather_http[0].assert_not_called()


@pytest.mark.parametrize("location", ["", "   "])
def test_blank_location_shows_validation_without_request(app, weather_http, location):
    submit(app, location)
    assert not app.exception
    assert "enter a location" in app.warning[0].value
    weather_http[0].assert_not_called()


@pytest.mark.parametrize(
    ("key", "message"), [("terrain", "choose a terrain"), ("intensity", "choose an intensity")]
)
def test_cleared_selection_shows_validation(app, weather_http, key, message):
    app.session_state[key] = None
    submit(app)
    assert not app.exception
    assert message in app.warning[0].value
    weather_http[0].assert_not_called()


def test_successful_ride_displays_forecast_and_all_body_parts(app, weather_http):
    app.session_state["terrain"] = "Alpine"
    app.session_state["intensity"] = "Extreme"
    app.slider[0].set_value(6)
    submit(app)
    assert not app.exception
    assert not app.error
    output = "\n".join(element.value for element in app.markdown)
    assert "Freiburg" in output
    assert "6 h" in output
    assert "9.0 – 25.0 °C" in output
    assert "Maximum hourly rain chance" in output
    for part in ("Head", "Upper body", "Lower body", "Hands", "Feet"):
        assert part in output
    assert "Shoes" in output
    weather_http[0].assert_called_once()


def test_failed_location_can_be_corrected_and_retried(app, weather_http, weather_payload):
    weather_http[1].json.return_value = {"error": {"code": 1006}}
    submit(app, "not-a-city")
    assert not app.exception
    assert "Location not found" in app.error[0].value
    weather_http[1].json.return_value = weather_payload
    submit(app, "Freiburg")
    assert not app.exception
    assert not app.error
    assert any("Recommended outfit" in element.value for element in app.markdown)


def test_timeout_shows_error_without_traceback(app, weather_http):
    weather_http[0].side_effect = requests.Timeout()
    submit(app)
    assert not app.exception
    assert "timed out" in app.error[0].value
    assert not any("Recommended outfit" in element.value for element in app.markdown)


def test_missing_configuration_is_explained(app, monkeypatch, weather_http):
    monkeypatch.delenv("WEATHERAPI_KEY")
    submit(app)
    assert not app.exception
    assert "WEATHERAPI_KEY" in app.error[0].value
    weather_http[0].assert_not_called()


def test_incomplete_wardrobe_error_is_displayed(app, monkeypatch, weather_http):
    def fail(*args):
        raise OutfitError("No valid clothing combinations for Feet. Check the wardrobe.")

    monkeypatch.setattr("outfitter.get_optimized_outfit", fail)
    submit(app)
    assert not app.exception
    assert "Feet" in app.error[0].value


def test_missing_decorative_icon_does_not_break_results(app, weather_payload, weather_http):
    weather_payload["forecast"]["forecastday"][0]["hour"][12]["condition"].pop("icon")
    submit(app)
    assert not app.exception
    assert not app.error
    assert any("Recommended outfit" in element.value for element in app.markdown)


def test_location_is_escaped_before_embedding_in_html(app, weather_http):
    submit(app, "<b>Freiburg</b>")
    heading = next(e.value for e in app.markdown if "Recommended outfit" in e.value)
    assert "&lt;b&gt;Freiburg&lt;/b&gt;" in heading
    assert "<b>Freiburg</b>" not in heading


def test_logo_loads_when_started_from_another_directory(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    app = AppTest.from_file(str(APP_PATH), default_timeout=10).run()
    assert not app.exception
