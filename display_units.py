"""Display-only unit conversions for the MARS user interface.

Recorded data and assessment calculations remain in SI units (metres).
"""

CENTIMETERS_PER_METER = 100.0


def meters_to_centimeters(value_m: float) -> float:
    """Convert a distance in metres to centimetres for display."""
    return value_m * CENTIMETERS_PER_METER


def format_centimeters(value_m: float, decimal_places: int = 1) -> str:
    """Format a distance stored in metres as a centimetre UI label."""
    return f"{meters_to_centimeters(value_m):.{decimal_places}f} cm"
