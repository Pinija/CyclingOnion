# CyclingOnion 🚴🧅

### Be perfectly dressed for your ride

CyclingOnion is a small Python/Streamlit app that helps answer a practical question:
**what should I wear on my next bike ride?** Enter a location, ride duration, terrain,
and intensity to get a suggested layered outfit for your head, upper body, lower
body, hands, and feet.

The app combines hourly weather forecasts with an explicit, inspectable scoring
model. Clothing ratings and comfort adjustments reflect personal cycling experience;
they are estimates, not measured guarantees of comfort.

## What it does

- Fetches live weather from [WeatherAPI](https://www.weatherapi.com/).
- Covers rides starting now and lasting 1–6 hours, including rides crossing midnight.
- Accounts for temperature, wind, maximum hourly rain probability, terrain, and effort.
- Builds valid clothing combinations and chooses the lowest discomfort score per body part.
- Shows each combination's comfort range, weather protection, and removability.
- Handles unknown locations, missing configuration, timeouts, and incomplete forecasts.

## Run locally

Use Python **3.11 or newer**. Run these commands from the repository directory:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export WEATHERAPI_KEY="your-key-from-weatherapi"
python -m streamlit run cyclingonion_app.py
```

Open the local URL printed by Streamlit (usually `http://localhost:8501`). Obtain your
own key from WeatherAPI; the account must allow a two-day forecast. No key is bundled.

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1` and set the key with:

```powershell
$env:WEATHERAPI_KEY = "your-key-from-weatherapi"
```

The application reads the process environment. It does **not** automatically load
`.env` or `.streamlit/secrets.toml`. Configure the environment on your hosting service
when deploying, and keep credentials out of source control.

Try `Freiburg, Germany`, a two-hour ride, flat terrain, and medium intensity. Selecting
the button fetches current weather; the result will vary with the forecast.

### Using Conda

Create a project environment with a supported Python version, then install the
same dependencies used by the tests:

```bash
conda create -n cyclingonion-dev python=3.13 pip
conda activate cyclingonion-dev
python -m pip install -r requirements-dev.txt
python -m pytest
```

Set `WEATHERAPI_KEY` as shown above before starting the app. This creates a separate
environment; an existing `cyclingonion_env` may still contain older dependencies.

## Development and tests

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
python -m pytest --cov --cov-report=term-missing
python -m ruff check .
python -m ruff format --check .
```

Tests use synthetic weather responses, block unexpected Requests network calls,
and supply a dummy key. **No account, API key, or network is needed to run the tests**
after dependencies are installed. The suite includes:

| Area | Behaviors checked |
| --- | --- |
| Scoring and layering | Both hot and cold penalties, zero-degree ratings, layer rules, footwear, independent wardrobe copies |
| Weather | Aggregation, midnight, partial hours, epoch ordering, missing hours, malformed data, input validation, service errors |
| Selection | Minimum-cost choice, deterministic ties, complete outfits, missing inventory, duration consistency |
| Streamlit | Initial render, input validation, successful requests, error recovery, missing configuration/icons, escaped location text |

Coverage includes branches and enforces a 90% minimum. Coverage indicates exercised
code, not the real-world accuracy of clothing advice. Streamlit tests use its
[AppTest framework](https://docs.streamlit.io/develop/concepts/app-testing/get-started);
they exercise app behavior but do not replace browser/layout checks or a live API smoke test.

GitHub Actions runs linting, formatting, and tests on Python 3.11 and 3.13 for pushes
and pull requests. To format local edits, run `python -m ruff format .`.

### Troubleshooting test environment mismatches

If UI tests fail inside Streamlit's `ButtonGroup.indices` with `"F" is not in list`
or `NoneType is not iterable`, check which interpreter and Streamlit version are
running:

```bash
python -c "import sys, streamlit; print(sys.executable); print(sys.version); print(streamlit.__version__)"
```

Streamlit 1.50.0 has incomplete segmented-control support in its test framework
([upstream issue](https://github.com/streamlit/streamlit/issues/11338)). This project
pins Streamlit 1.67.0, which requires Python 3.11 or newer. An older Python 3.10
environment cannot install that pinned version.

Use the Conda setup above, or an existing `.venv` created with a supported Python.
From the repository directory, you can select that environment explicitly without
activating it:

```bash
.venv/bin/python -m pytest --cov
```

Prefer `python -m pytest` to a bare `pytest` command so tests use the selected Python
interpreter. Updating Python alone is insufficient; install `requirements-dev.txt`
inside the chosen environment too.

## How a recommendation is calculated

1. **Forecast window:** request two forecast days and select every hourly bucket
   overlapping the ride. Compare provider epoch timestamps rather than array positions
   or the server's clock. Reject gaps, duplicates, and insufficient coverage.
2. **Weather summary:** take the minimum/maximum temperature, minimum wind-chill
   temperature, maximum wind speed, and maximum hourly rain probability. The condition
   text/icon comes from the first selected hour; the lights tip considers all hours.
   Precipitation volume is prorated at the ride boundaries, assuming uniform rain
   within each hour, but is not currently used in scoring.
3. **Effective temperature band:** subtract a terrain allowance from the lowest
   wind-chill temperature (flat 0°C, hilly 1°C, mountain 5°C, alpine 9°C). Add an effort
   allowance to the highest air temperature (easy 0°C, medium 1.5°C, tempo 3°C, extreme 5°C).
   These are deliberate simplifications, not route elevation or physiological models.
4. **Layering:** enumerate subsets for each body part. Allow at most one inner, mid,
   and outer layer, plus accessories. Require a mid or outer layer; an outer layer
   needs an inner or mid beneath it. Footwear must include an outer layer (shoes).
   The outermost layer supplies the comfort limits and other layers shift them.
5. **Scoring:** choose the lowest score independently for each body part:

```text
cold = max(comfort_min - effective_min, 0)² × (0.33 + duration_hours / 3)
warm = max(effective_max - comfort_max, 0)²
rain = 0 if waterproof else 0.75 × maximum_hourly_rain_probability
wind = 0 if windproof else 0.5 × maximum_wind_kmh
score = cold + warm + rain + wind + 5 × complexity - (4.5 if removable else 0)
```

Both cold and warm penalties apply when a ride spans both ends of a garment's
comfort range. Protection flags combine across layers; accumulated wind resistance
of at least 0.9 also counts as windproof. Ties preserve catalogue order.

Independent selection minimizes the total additive score because the current model
has no interactions between body parts. Generating subsets is exponential in the
number of items per body part; this is reasonable for the small built-in wardrobe,
but should change before supporting large catalogues.

## Code map

| File | Responsibility |
| --- | --- |
| `cyclingonion_app.py` | Streamlit inputs, results, and recoverable error display |
| `weather.py` | API boundary, validation, forecast aggregation, effective temperatures and tips |
| `wardrobe.py` | Dataclasses, clothing catalogue, layer rules and discomfort score |
| `outfitter.py` | Selection of the lowest-scoring combination for each body part |
| `tests/` | Offline unit, integration, and Streamlit tests |
| `docs/review.md` | Confirmed failure cases, fixes, and prioritized next improvements |
| `.github/workflows/ci.yml` | Automated quality checks |

To add clothing, edit `WARDROBE` in `wardrobe.py`. Main layers need meaningful minimum
and maximum comfort temperatures. Inner layers/accessories contribute temperature
shifts and protection. Shoes use `LayerType.OUTER` for `BodyPart.FEET`. Run the tests
after editing the catalogue. `data/wardrobe.json` is an unused, empty placeholder;
the application does not load clothing from JSON.

## Current limits and next steps

- The forecast represents one location and a ride starting now, not a route or a
  planned departure time. The rain value is the highest hourly probability, not the
  probability of rain at any point during the entire ride.
- Ratings and score weights need calibration against actual rides. Boolean weather
  protection and the removability bonus simplify how clothing behaves.
- The optimizer always returns the best available combination, even if every option
  scores poorly. A useful next feature is an explained recommendation with an
  explicit indication when the wardrobe cannot cover the conditions.
- Layer rules do not yet model all compatibility constraints, such as redundant
  warmers/covers, or changing layers during a ride. Helmets are outside the catalogue;
  a head recommendation of “Nothing” refers to additional clothing.
- Useful portfolio additions: an offline example/demo, a screenshot or short walkthrough,
  an explanation of why one outfit beats another, and documented feedback from real rides.

See [the engineering review](docs/review.md) for reproducible bugs and a prioritized
roadmap. Weather integration follows the provider's
[forecast fields](https://www.weatherapi.com/docs/forecast-api/) and
[error codes](https://www.weatherapi.com/docs/).

Built with ❤️ for Helen.
