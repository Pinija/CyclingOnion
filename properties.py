from enum import Enum

class Intensity(Enum):
    """Enum for the difficulty setting."""
    LIGHT = 1
    MEDIUM = 2
    TEMPO = 3
    EXTREME = 4

def get_intensity(diff: str) -> Intensity:
    """Return the enum value out of a string"""
    return Intensity[diff.upper()]

class Terrain(Enum):
    """Enum for the terrain setting."""
    FLAT = 0
    HILLY = 1
    MOUNTAIN = 2
    ALPINE = 3

def get_terrain(terrain: str) -> Terrain:
    """Return the enum for a given string."""
    return Terrain[terrain.upper()]


if __name__ == "__main__":
    print(get_intensity("liGht"))
    print(get_terrain("FLAT"))