"""AgriSaathi Tools — vision, price lookup, and weather utilities.

WHY: Centralised re-exports so callers can do:
    from tools.vision_tool import analyze_crop_image, CropDiagnosis
    from tools.price_lookup import format_price_for_farmer
    from tools.weather_lookup import format_forecast_for_farmer
"""

from tools.price_lookup import (
    format_price_for_farmer,
    format_recommendation,
    format_trend_summary,
)
from tools.vision_tool import CropDiagnosis, DISEASE_KB, analyze_crop_image
from tools.weather_lookup import (
    format_forecast_for_farmer,
    format_irrigation_advice,
    get_crop_weather_risk,
)

__all__ = [
    # Vision
    "analyze_crop_image",
    "CropDiagnosis",
    "DISEASE_KB",
    # Price
    "format_price_for_farmer",
    "format_trend_summary",
    "format_recommendation",
    # Weather
    "format_forecast_for_farmer",
    "format_irrigation_advice",
    "get_crop_weather_risk",
]
