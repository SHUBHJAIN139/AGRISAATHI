"""
AgriSaathi — CropDoctor Unit Tests
=====================================
WHY: The vision tool is the most complex piece — it handles PlantVillage
filename parsing, mock disease matching, and structured output. These tests
verify the Tweak 1 logic exhaustively.
"""

import os
import pytest

# Force mock mode for tests
os.environ["MOCK_LLM"] = "true"


class TestVisionTool:
    """Test the crop disease diagnosis tool."""

    def test_plantvillage_tomato_late_blight(self):
        """PlantVillage filename 'Tomato___Late_blight' should return exact disease."""
        from tools.vision_tool import analyze_crop_image
        result = analyze_crop_image(
            image_base64="dGVzdA==",  # dummy base64
            image_filename="Tomato___Late_blight_001.jpg",
        )
        assert result.disease.lower().replace(" ", "_") == "late_blight" or "late_blight" in result.disease.lower().replace(" ", "_")
        assert result.confidence == 0.95
        assert result.crop_name.lower() == "tomato"

    def test_plantvillage_potato_early_blight(self):
        """PlantVillage filename 'Potato___Early_blight' should return exact disease."""
        from tools.vision_tool import analyze_crop_image
        result = analyze_crop_image(
            image_base64="dGVzdA==",
            image_filename="Potato___Early_blight.png",
        )
        assert "early_blight" in result.disease.lower().replace(" ", "_")
        assert result.confidence == 0.95

    def test_plantvillage_corn_common_rust(self):
        """PlantVillage filename 'Corn___Common_rust' should return exact disease."""
        from tools.vision_tool import analyze_crop_image
        result = analyze_crop_image(
            image_base64="dGVzdA==",
            image_filename="Corn___Common_rust_42.jpg",
        )
        assert "common_rust" in result.disease.lower().replace(" ", "_")

    def test_plantvillage_apple_scab(self):
        """PlantVillage filename 'Apple___Apple_scab' should return exact disease."""
        from tools.vision_tool import analyze_crop_image
        result = analyze_crop_image(
            image_base64="dGVzdA==",
            image_filename="Apple___Apple_scab.jpg",
        )
        assert "scab" in result.disease.lower()

    def test_plantvillage_healthy(self):
        """PlantVillage 'healthy' class should return healthy."""
        from tools.vision_tool import analyze_crop_image
        result = analyze_crop_image(
            image_base64="dGVzdA==",
            image_filename="Tomato___healthy_005.jpg",
        )
        assert "healthy" in result.disease.lower()

    def test_unknown_filename_returns_plausible(self):
        """Non-PlantVillage filename should return a random plausible disease."""
        from tools.vision_tool import analyze_crop_image
        result = analyze_crop_image(
            image_base64="dGVzdA==",
            image_filename="random_photo.jpg",
        )
        assert result.disease is not None
        assert result.confidence > 0

    def test_no_filename_returns_plausible(self):
        """No filename should return a random plausible disease."""
        from tools.vision_tool import analyze_crop_image
        result = analyze_crop_image(
            image_base64="dGVzdA==",
            image_filename=None,
        )
        assert result.disease is not None

    def test_diagnosis_has_treatment(self):
        """Every diagnosis must include a treatment."""
        from tools.vision_tool import analyze_crop_image
        result = analyze_crop_image(
            image_base64="dGVzdA==",
            image_filename="Tomato___Late_blight.jpg",
        )
        assert result.treatment is not None
        assert len(result.treatment) > 10

    def test_diagnosis_has_severity(self):
        """Every diagnosis must have a severity level."""
        from tools.vision_tool import analyze_crop_image
        result = analyze_crop_image(
            image_base64="dGVzdA==",
            image_filename="Tomato___Late_blight.jpg",
        )
        assert result.severity in ["low", "medium", "high", "critical"]

    def test_organic_alternative_flag(self):
        """Diagnosis should indicate if organic treatment exists."""
        from tools.vision_tool import analyze_crop_image
        result = analyze_crop_image(
            image_base64="dGVzdA==",
            image_filename="Tomato___Late_blight.jpg",
        )
        assert isinstance(result.organic_alternative, bool)
