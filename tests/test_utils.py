"""Unit tests for yesitsme utility functions."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from api import InstagramAPI, UserInfo, APIResponse
from config import Config
from utils import (
    dumpor_search,
    match_email,
    match_phone,
    match_name,
    calculate_match_level,
    export_to_json,
    export_to_csv,
)


class TestMatchEmail:
    """Tests for email matching functionality."""

    def test_email_match_basic(self):
        """Test basic email matching."""
        assert match_email("j***n@gmail.com", "j***n@gmail.com") is True

    def test_email_match_partial(self):
        """Test partial email matching."""
        assert match_email("john@gmail.com", "j***n@gmail.com") is True

    def test_email_no_match_domain(self):
        """Test email with different domain."""
        assert match_email("john@yahoo.com", "j***n@gmail.com") is False

    def test_email_empty_provided(self):
        """Test with empty provided email."""
        assert match_email("", "john@gmail.com") is False

    def test_email_empty_public(self):
        """Test with empty public email."""
        assert match_email("john@gmail.com", None) is False

    def test_email_case_insensitive(self):
        """Test case insensitive matching."""
        assert match_email("JOHN@GMAIL.COM", "john@gmail.com") is True


class TestMatchPhone:
    """Tests for phone number matching."""

    def test_phone_match_basic(self):
        """Test basic phone matching - area code + last 2 digits."""
        # Provided: +12345678901, Public: +1**01 -> area=123, last=01 match
        assert match_phone("+12345678901", "+123******01") is True

    def test_phone_match_area_code(self):
        """Test area code matching."""
        # Provided: +391234567890, Public: +39**90 -> area=391, last=90 match
        assert match_phone("+391234567890", "+391******90") is True

    def test_phone_no_match_area(self):
        """Test different area code."""
        assert match_phone("+12345678901", "+442******01") is False

    def test_phone_empty_provided(self):
        """Test with empty provided phone."""
        assert match_phone("", "+123******01") is False

    def test_phone_empty_public(self):
        """Test with empty public phone."""
        assert match_phone("+123******01", None) is False

    def test_phone_special_chars(self):
        """Test phone with special characters stripped."""
        # Digits: 12345678901 vs 12301 -> area=123, last=01 match
        assert match_phone("+1-234-567-8901", "+123******01") is True


class TestMatchName:
    """Tests for name matching."""

    def test_name_match_exact(self):
        """Test exact name match."""
        assert match_name("John Doe", "John Doe") is True

    def test_name_match_case_insensitive(self):
        """Test case insensitive name matching."""
        assert match_name("john doe", "JOHN DOE") is True

    def test_name_no_match(self):
        """Test name mismatch."""
        assert match_name("John Doe", "Jane Smith") is False

    def test_name_empty(self):
        """Test with empty name."""
        assert match_name("", "John Doe") is False


class TestCalculateMatchLevel:
    """Tests for match level calculation."""

    def test_match_level_high(self):
        """Test HIGH match level."""
        level, count = calculate_match_level(True, True, True)
        assert level == "HIGH"
        assert count == 3

    def test_match_level_medium(self):
        """Test MEDIUM match level."""
        level, count = calculate_match_level(True, True, False)
        assert level == "MEDIUM"
        assert count == 2

    def test_match_level_low(self):
        """Test LOW match level."""
        level, count = calculate_match_level(True, False, False)
        assert level == "LOW"
        assert count == 1

    def test_match_level_none(self):
        """Test NONE match level."""
        level, count = calculate_match_level(False, False, False)
        assert level == "NONE"
        assert count == 0


class TestExportToJson:
    """Tests for JSON export functionality."""

    def test_export_json_success(self):
        """Test successful JSON export."""
        results = [
            {
                "username": "testuser",
                "user_id": "12345",
                "full_name": "Test User",
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test.json")
            assert export_to_json(results, output_path) is True

            with open(output_path, "r") as f:
                data = json.load(f)
                assert "timestamp" in data
                assert "results" in data
                assert len(data["results"]) == 1

    def test_export_json_empty(self):
        """Test JSON export with empty results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test.json")
            assert export_to_json([], output_path) is True


class TestExportToCsv:
    """Tests for CSV export functionality."""

    def test_export_csv_success(self):
        """Test successful CSV export."""
        results = [
            {
                "username": "testuser",
                "user_id": "12345",
                "full_name": "Test User",
                "is_verified": False,
                "is_private": False,
                "is_business": False,
                "follower_count": 100,
                "following_count": 50,
                "media_count": 10,
                "public_email": "",
                "public_phone": "",
                "obfuscated_email": "",
                "obfuscated_phone": "",
                "match_level": "LOW",
                "profile_pic_url": "",
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test.csv")
            assert export_to_csv(results, output_path) is True

            with open(output_path, "r") as f:
                content = f.read()
                assert "username" in content
                assert "testuser" in content

    def test_export_csv_empty(self):
        """Test CSV export with empty results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test.csv")
            assert export_to_csv([], output_path) is False


class TestConfig:
    """Tests for configuration management."""

    def test_config_default_values(self):
        """Test default configuration values."""
        config = Config()
        assert config.timeout == 10
        assert config.max_retries == 3
        assert config.export_format == "json"

    def test_config_load_from_env(self):
        """Test loading config from environment variables."""
        with patch.dict(
            os.environ,
            {
                "INSTAGRAM_SESSION_ID": "test_session",
                "YESITSME_TIMEOUT": "30",
            },
        ):
            config = Config.load()
            assert config.session_id == "test_session"
            assert config.timeout == 30

    def test_config_save(self):
        """Test saving configuration to file."""
        config = Config(timeout=20, max_retries=5)

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.yaml")
            config.save(config_path)

            assert os.path.exists(config_path)

            loaded_config = Config.load(config_path)
            assert loaded_config.timeout == 20
            assert loaded_config.max_retries == 5


class TestAPIResponse:
    """Tests for API response dataclass."""

    def test_api_response_success(self):
        """Test successful API response."""
        response = APIResponse(data={"key": "value"}, error=None)
        assert response.data is not None
        assert response.error is None
        assert response.rate_limited is False

    def test_api_response_error(self):
        """Test error API response."""
        response = APIResponse(data=None, error="Test error")
        assert response.data is None
        assert response.error == "Test error"

    def test_api_response_rate_limited(self):
        """Test rate limited API response."""
        response = APIResponse(
            data=None, error="Rate limit", rate_limited=True
        )
        assert response.rate_limited is True


class TestUserInfo:
    """Tests for UserInfo dataclass."""

    def test_user_info_creation(self):
        """Test UserInfo creation."""
        user_info = UserInfo(
            username="testuser",
            user_id="12345",
            full_name="Test User",
            is_verified=False,
            is_business=False,
            is_private=False,
            follower_count=100,
            following_count=50,
            media_count=10,
            external_url=None,
            biography=None,
            public_email=None,
            public_phone_number=None,
            profile_pic_url=None,
        )
        assert user_info.username == "testuser"
        assert user_info.follower_count == 100

    def test_user_info_with_optional_fields(self):
        """Test UserInfo with optional fields."""
        user_info = UserInfo(
            username="testuser",
            user_id="12345",
            full_name="Test User",
            is_verified=True,
            is_business=True,
            is_private=False,
            follower_count=100,
            following_count=50,
            media_count=10,
            external_url="https://example.com",
            biography="Test bio",
            public_email="test@example.com",
            public_phone_number="+1234567890",
            profile_pic_url="https://example.com/pic.jpg",
        )
        assert user_info.is_verified is True
        assert user_info.external_url == "https://example.com"


class TestDumporSearch:
    """Tests for dumpor search functionality."""

    @patch("utils.requests.get")
    def test_dumpor_search_success(self, mock_get):
        """Test successful dumpor search."""
        mock_response = mock_get.return_value
        mock_response.text = """
        <html>
            <a class="profile-name-link">testuser1</a>
            <a class="profile-name-link">testuser2</a>
        </html>
        """
        mock_response.raise_for_status.return_value = None

        result = dumpor_search("test name")
        assert result["error"] is None
        assert len(result["usernames"]) == 2

    @patch("utils.requests.get")
    def test_dumpor_search_error(self, mock_get):
        """Test dumpor search with error."""
        mock_get.side_effect = Exception("Connection error")

        result = dumpor_search("test name")
        assert result["error"] is not None
        assert result["usernames"] is None
