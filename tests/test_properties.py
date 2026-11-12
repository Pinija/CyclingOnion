"""UI labels and programmatic ride settings must resolve to the same enums."""

import pytest

from properties import Intensity, Terrain, get_intensity, get_terrain


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("Easy", Intensity.LIGHT),
        ("Light", Intensity.LIGHT),
        ("  easy  ", Intensity.LIGHT),
        ("Medium", Intensity.MEDIUM),
        ("tEmPo", Intensity.TEMPO),
        ("Extreme", Intensity.EXTREME),
    ],
)
def test_intensity_labels(label, expected):
    assert get_intensity(label) is expected


@pytest.mark.parametrize("intensity", list(Intensity))
def test_intensity_enum_passes_through(intensity):
    assert get_intensity(intensity) is intensity


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("Flat", Terrain.FLAT),
        ("  hIlLy ", Terrain.HILLY),
        ("Mountain", Terrain.MOUNTAIN),
        ("Alpine", Terrain.ALPINE),
    ],
)
def test_terrain_labels(label, expected):
    assert get_terrain(label) is expected


@pytest.mark.parametrize("terrain", list(Terrain))
def test_terrain_enum_passes_through(terrain):
    assert get_terrain(terrain) is terrain


@pytest.mark.parametrize("value", [None, "", "unknown", [], 1, True, Terrain.FLAT])
def test_invalid_intensity_has_a_readable_error(value):
    with pytest.raises(ValueError, match="valid intensity"):
        get_intensity(value)


@pytest.mark.parametrize("value", [None, "", "unknown", [], 1, True, Intensity.LIGHT])
def test_invalid_terrain_has_a_readable_error(value):
    with pytest.raises(ValueError, match="valid terrain"):
        get_terrain(value)
