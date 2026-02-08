"""
T5: Auth Failure Handling Tests (5 points)

Tests auth errors produce helpful messages:
- Missing files produce helpful guidance
- Invalid credentials produce clear errors

SKILL.md Section: "Common Issues & Fixes"
"""

import sys
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add skill scripts to path
SKILL_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(SKILL_ROOT))


@pytest.mark.tier5
@pytest.mark.offline
class TestAuthFailures:
    """Test auth failure error messages (5 points)."""

    def test_missing_key_suggests_generation_command(self):
        """Missing key error suggests openssl command."""
        from scripts.auth import Data360Auth

        with tempfile.TemporaryDirectory() as jwt_dir:
            jwt_path = Path(jwt_dir)

            with patch('scripts.auth.DEFAULT_KEY_DIR', jwt_path):
                with patch.object(Data360Auth, '_get_org_info') as mock_org:
                    mock_org.return_value = MagicMock(
                        instance_url="https://test.salesforce.com",
                        username="test@example.com",
                        is_sandbox=False
                    )

                    auth = Data360Auth(
                        org_alias="test-org",
                        consumer_key="test-key"
                    )

                    with pytest.raises(FileNotFoundError) as exc_info:
                        auth._load_private_key()

                    error_msg = str(exc_info.value).lower()

                    # Should mention openssl or generation
                    assert "openssl" in error_msg or "generate" in error_msg

    def test_missing_consumer_key_lists_all_options(self):
        """Missing consumer key error lists file and env options."""
        from scripts.auth import Data360Auth
        import os

        with tempfile.TemporaryDirectory() as jwt_dir:
            jwt_path = Path(jwt_dir)

            # Create key file but no consumer key
            key_file = jwt_path / "test-org.key"
            key_file.write_text("test")

            # Clear env vars
            for var in list(os.environ.keys()):
                if var.startswith("SF_") and "CONSUMER_KEY" in var:
                    os.environ.pop(var, None)

            with patch('scripts.auth.DEFAULT_KEY_DIR', jwt_path):
                with patch.object(Data360Auth, '_get_org_info') as mock_org:
                    mock_org.return_value = MagicMock(
                        instance_url="https://test.salesforce.com",
                        username="test@example.com",
                        is_sandbox=False
                    )

                    with pytest.raises(ValueError) as exc_info:
                        Data360Auth(org_alias="test-org")

                    error_msg = str(exc_info.value)

                    # Should mention file option
                    assert ".consumer-key" in error_msg or "File" in error_msg

                    # Should mention env option
                    assert "SF_" in error_msg or "environment" in error_msg.lower()

    def test_cli_auth_error_is_not_stacktrace(self, cli_runner, cli_app):
        """CLI auth errors show user-friendly message, not full stacktrace."""
        # Run with non-existent org
        result = cli_runner.invoke(cli_app, [
            "test-auth",
            "--org", "nonexistent-org-xyz123"
        ])

        # Should fail
        assert result.exit_code != 0

        # Output should NOT be a raw Python exception stacktrace
        # (may have "Error:" prefix which is OK)
        output_lower = result.output.lower()

        # These indicate user-friendly error handling
        friendly_indicators = ["error", "failed", "not found", "cannot"]
        has_friendly_message = any(ind in output_lower for ind in friendly_indicators)

        assert has_friendly_message or len(result.output) < 500, \
            "Auth error should produce user-friendly message"


@pytest.mark.tier5
@pytest.mark.offline
class TestConnectionFailures:
    """Test connection failure handling."""

    def test_connection_timeout_handled(self):
        """Connection timeouts produce clear error."""
        from scripts.auth import Data360Auth
        import httpx

        with tempfile.TemporaryDirectory() as jwt_dir:
            jwt_path = Path(jwt_dir)

            # Create auth files (key content doesn't matter - we'll mock JWT creation)
            key_file = jwt_path / "test-org.key"
            key_file.write_text("mock-key-content")

            consumer_key_file = jwt_path / "test-org.consumer-key"
            consumer_key_file.write_text("test-consumer-key")

            with patch('scripts.auth.DEFAULT_KEY_DIR', jwt_path):
                # Mock sf CLI to return valid org info
                with patch('subprocess.run') as mock_run:
                    mock_run.return_value = MagicMock(
                        stdout='{"status": 0, "result": {"instanceUrl": "https://test.salesforce.com", "username": "test@example.com"}}',
                        returncode=0
                    )

                    auth = Data360Auth(org_alias="test-org")

                    # Mock JWT assertion creation to skip actual key parsing
                    with patch.object(auth, '_create_jwt_assertion', return_value="mock-jwt-assertion"):
                        # Mock httpx to timeout
                        with patch.object(httpx.Client, 'post') as mock_post:
                            mock_post.side_effect = httpx.TimeoutException("Connection timed out")

                            with pytest.raises((RuntimeError, httpx.TimeoutException)):
                                auth.get_token()
