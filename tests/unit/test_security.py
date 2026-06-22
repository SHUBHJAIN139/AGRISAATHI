"""
AgriSaathi — Security Middleware Unit Tests
=============================================
WHY: PII redaction is a CRITICAL security control. If the regex fails to
catch an Aadhaar number, a farmer's identity leaks into logs. These tests
verify every pattern works against real-world formats.
"""

import pytest
from api.security import PIIRedactionMiddleware, AuditLogger, create_mock_token
from api.models import _mask_pii


class TestPIIRedaction:
    """Test Aadhaar and phone number masking patterns."""

    def test_aadhaar_with_spaces(self):
        """Aadhaar: '1234 5678 9012' → 'XXXX-XXXX-9012'"""
        result = _mask_pii("My Aadhaar is 1234 5678 9012")
        assert "1234" not in result
        assert "5678" not in result
        assert "XXXX-XXXX-9012" in result

    def test_aadhaar_with_hyphens(self):
        """Aadhaar: '1234-5678-9012' → 'XXXX-XXXX-9012'"""
        result = _mask_pii("Aadhaar: 1234-5678-9012")
        assert "XXXX-XXXX-9012" in result

    def test_aadhaar_no_separators(self):
        """Aadhaar: '123456789012' → 'XXXX-XXXX-9012'"""
        result = _mask_pii("Aadhaar: 123456789012")
        assert "XXXX-XXXX-9012" in result

    def test_phone_with_plus91(self):
        """Phone: '+919876543210' → masked"""
        result = _mask_pii("Call me at +919876543210")
        assert "98765" not in result
        assert "XXXXX" in result

    def test_phone_with_91(self):
        """Phone: '919876543210' → masked"""
        result = _mask_pii("Phone: 919876543210")
        assert "XXXXX" in result

    def test_phone_with_zero(self):
        """Phone: '09876543210' → masked"""
        result = _mask_pii("Phone: 09876543210")
        assert "XXXXX" in result

    def test_no_false_positive_short_number(self):
        """Short numbers (< 12 digits) should not be masked as Aadhaar."""
        result = _mask_pii("Order #12345 is ready")
        assert "12345" in result

    def test_multiple_pii_in_text(self):
        """Multiple PII items should all be masked."""
        text = "Aadhaar: 1234 5678 9012, Phone: +919876543210"
        result = _mask_pii(text)
        assert "XXXX-XXXX-9012" in result
        assert "XXXXX" in result

    def test_json_with_pii(self):
        """PII inside JSON strings should be masked."""
        text = '{"aadhaar": "1234 5678 9012", "phone": "+919876543210"}'
        result = _mask_pii(text)
        assert "XXXX-XXXX-9012" in result


class TestPIISafeModel:
    """Test that Pydantic models mask PII in repr/str."""

    def test_chat_request_masks_repr(self):
        from api.models import ChatRequest
        req = ChatRequest(
            message="My Aadhaar is 1234 5678 9012",
            session_id="s1",
            user_id="u1",
        )
        assert "1234 5678" not in repr(req)

    def test_chat_request_masks_str(self):
        from api.models import ChatRequest
        req = ChatRequest(
            message="Call +919876543210",
            session_id="s1",
            user_id="u1",
        )
        assert "98765" not in str(req)


class TestMockToken:
    """Test JWT mock token generation."""

    def test_create_token(self):
        token = create_mock_token("farmer_001")
        assert isinstance(token, str)
        assert len(token) > 20

    def test_token_decode(self):
        import jwt  # pyjwt, not python-jose  # TODO: re-test with pyjwt
        import os
        token = create_mock_token("farmer_002")
        secret = os.environ.get("JWT_SECRET", "change-me-in-production")
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        assert payload["sub"] == "farmer_002"
        assert payload["role"] == "farmer"


class TestAuditLogger:
    """Test audit log writing."""

    def test_log_creates_entry(self, tmp_path):
        import os
        log_path = str(tmp_path / "audit.log")
        os.environ["AUDIT_LOG_PATH"] = log_path

        logger = AuditLogger()
        logger.log_path = log_path
        logger.log(
            action="test_action",
            user_id="farmer_001",
            session_id="s1",
            agent="crop_doctor",
            details={"test": True},
        )

        with open(log_path) as f:
            content = f.read()
            assert "test_action" in content
            assert "crop_doctor" in content
