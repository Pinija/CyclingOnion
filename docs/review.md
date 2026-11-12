# Engineering review

The initial review used the shared base at `3bd3f46`. Later integration also examined
the newer ride-model commits through `8be02de`. Without the original error message
or inputs, neither review can identify the previously observed crash conclusively.
Both an unknown-location response and the newer “Easy” label conversion could crash.

## Confirmed issues and regression coverage

| Original failure | Reproduction and consequence | Fix / regression coverage |
| --- | --- | --- |
| API errors treated as successful forecasts | A response such as `{"error": {"code": 1006}}` has no `forecast`; accessing it raises `KeyError`. Timeouts, HTTP errors, and non-JSON responses also escaped the UI. | Explicit `WeatherError`, bounded HTTP requests, readable UI errors, and retry tests in `test_weather.py` / `test_app.py`. |
| Forecast truncated at midnight | A 3-hour ride at 23:00 used only hour 23 of today, ignoring tomorrow's cold/rain/wind. It usually returned misleading advice rather than crashing. | Request two days and select contiguous epoch-based intervals. Test midnight, partial hours, gaps, duplicates, and insufficient coverage. |
| Final partial hour omitted | At 12:30, a 2-hour ride also overlaps 14:00–14:30. Selecting only two hourly entries omits that period. | Include every overlapping bucket and prorate precipitation volume at boundaries. |
| Heat penalty skipped during cold exposure (shared base only) | An `elif` prevented both temperature penalties from applying. The newer remote code had already corrected this. | Keep both penalties and the newer weights. A fully breathable 10–20°C garment across 5–25°C for 3 hours at medium intensity incurs 50 cold + 25 heat, before other terms. |
| Zero treated as missing data | `outer.main_comfort_min or 15.0` changed the Thermal Cap's real 0°C rating to 15°C. The same problem affected a 0°C maximum. | Preserve numeric zero. Cover lower, upper, and both zero limits. |
| Footwear without shoes | Thermal Socks were a MID layer, so sock/cover combinations without shoes qualified as complete footwear. Some also had inverted default comfort ranges. | Require an OUTER shoe layer for feet; assert every built-in foot combination includes shoes and valid comfort bounds. |
| Empty inventories crashed | Missing body parts caused `KeyError`; empty candidate lists could cause `IndexError` when choosing the first item. | Empty candidate lists and an explanatory `OutfitError`. Test each missing body part. |
| Shared mutable wardrobe | Modifying a wardrobe returned by the factory changed future calls because the list and items were shared. | Copy both inventory and clothing records; mutation isolation regression. |
| Tests did not provide a usable baseline | `wardrobe_test.py` contained a misindented nested class. Default `unittest discover` did not find that filename. | Replace it with discoverable pytest modules and CI. |
| API key committed in source | The credential was embedded in `weather.py`. | Read `WEATHERAPI_KEY`; ignore common secret files. The owner must rotate the old key, which remains in existing Git history. |

Other changes: normalize optional icon URLs without an extra server-side image
request, resolve the logo relative to the source file, escape location/clothing
text embedded in HTML, reject inconsistent ride/forecast durations, and use `min`
instead of sorting all candidate scores. Dataclass field typos were corrected to
`forecast_duration` and `precipitation_volume`; `get_icon()` now returns a URL or
`None` rather than downloading a bitmap. Repository callers were updated together.

## Integrating the newer ride model

The merge preserves the remote terrain/intensity enums, the 0/3/6/9°C terrain
allowances, the intensity-dependent heat and sweat penalties, the revised cold/rain
weights, and additive removability with its terrain/effort reward. Intensity no longer
changes the weather temperature band. The catalogue's existing ratings are retained.

Three additional regressions were corrected:

| Newer-model failure | Resolution and coverage |
| --- | --- |
| UI “Easy” looked up a nonexistent `Intensity.EASY`, raising `KeyError` | Map Easy to the existing `Intensity.LIGHT`; cover every UI intensity in Streamlit tests. |
| Subtracting inner breathability could make totals negative and penalize more breathable layers | Multiply finite ratings in [0, 1]. With an outer rating of 0.8, an inner rating of 0.9 yields 0.72; an inner rating of 0.2 yields 0.16. Test bounds, monotonicity, exact sweat scores, and an intensity-dependent outfit choice. |
| Tip logic compared enum values with strings | Compare enums; test short high-intensity rides and short easy mountain rides. |

`get_weather_forecast()` accepts enums or validated labels. `WeatherForecast` normalizes
its settings to enums. `get_optimized_outfit(hours, weather, wardrobe=None)` obtains
terrain and intensity from that forecast, avoiding duplicate settings that could
disagree. The score's `get_discomfort()` method now takes explicit intensity and
terrain enums. Clothing constructors use numeric `removability`; the UI continues
to read the derived `removable` boolean.

All weather error handling, full ride-window coverage, zero-degree ratings, valid
footwear, independent inventories, and configuration fixes from the initial review
remain covered. Generated Python bytecode is removed from version control.

The breathability product and removability reward remain heuristics. In particular,
the catalogue currently gives all garments the default breathability of 1.0, and
the additive removal reward can overfavor extra layers on demanding terrain. These
need calibration against actual rides rather than invented garment measurements.
