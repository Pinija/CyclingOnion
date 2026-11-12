"""Shared ride settings and conversion from UI labels to domain enums."""

from enum import Enum


class Intensity(Enum):
    """Effort scale used by heat, sweat, and removability scoring."""

    LIGHT = 1
    MEDIUM = 2
    TEMPO = 3
    EXTREME = 4


class Terrain(Enum):
    """Terrain scale used by the altitude allowance and removability scoring."""

    FLAT = 0
    HILLY = 1
    MOUNTAIN = 2
    ALPINE = 3


def get_intensity(value: Intensity | str) -> Intensity:
    """Accept an enum or a case-insensitive label; the UI's Easy means LIGHT."""
    if isinstance(value, Intensity):
        return value
    if isinstance(value, str):
        label = value.strip().upper()
        if label == "EASY":
            label = "LIGHT"
        if label in Intensity.__members__:
            return Intensity[label]
    raise ValueError("Please select a valid intensity.")


def get_terrain(value: Terrain | str) -> Terrain:
    """Accept an enum or a case-insensitive terrain label."""
    if isinstance(value, Terrain):
        return value
    if isinstance(value, str):
        label = value.strip().upper()
        if label in Terrain.__members__:
            return Terrain[label]
    raise ValueError("Please select a valid terrain.")
