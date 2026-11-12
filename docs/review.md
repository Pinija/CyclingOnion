# Engineering review

This review identifies reproducible failures in the original code. Without the
original error message or inputs, it cannot identify which one caused the previously
observed crash. The unknown-location/API response path is a plausible candidate.

## Confirmed issues and regression coverage

| Original failure | Reproduction and consequence | Fix / regression coverage |
| --- | --- | --- |
| API errors treated as successful forecasts | A response such as `{"error": {"code": 1006}}` has no `forecast`; accessing it raises `KeyError`. Timeouts, HTTP errors, and non-JSON responses also escaped the UI. | Explicit `WeatherError`, bounded HTTP requests, readable UI errors, and retry tests in `test_weather.py` / `test_app.py`. |
| Forecast truncated at midnight | A 3-hour ride at 23:00 used only hour 23 of today, ignoring tomorrow's cold/rain/wind. It usually returned misleading advice rather than crashing. | Request two days and select contiguous epoch-based intervals. Test midnight, partial hours, gaps, duplicates, and insufficient coverage. |
| Final partial hour omitted | At 12:30, a 2-hour ride also overlaps 14:00–14:30. Selecting only two hourly entries omits that period. | Include every overlapping bucket and prorate precipitation volume at boundaries. |
| Heat penalty skipped during cold exposure | For a 10–20°C garment, 5–25°C conditions over 3 hours scored 33.25 instead of 58.25, before protection/complexity. An `elif` prevented both temperature penalties from applying. | Two independent conditions; exact score and monotonicity regressions. |
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
