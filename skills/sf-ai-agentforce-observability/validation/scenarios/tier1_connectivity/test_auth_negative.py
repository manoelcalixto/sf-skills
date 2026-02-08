"""
T1: Auth Error Handling Tests (5 points)

Tests auth failure scenarios produce helpful error messages:
- Missing key file
- Invalid consumer key
- Connection failures

Tests SKILL.md "Common Issues & Fixes" section.
"""

import sys
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add skill scripts to path
SKILL_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(SKILL_ROOT))


@pytest.mark.tier1
@pytest.mark.offline
class TestAuthErrorMessages:
    """Test auth error messages are helpful (5 points)."""

    def test_missing_key_file_error(self):
        """FileNotFoundError includes helpful message about key generation."""
        from scripts.auth import Data360Auth

        with tempfile.TemporaryDirectory() as jwt_dir:
            jwt_path = Path(jwt_dir)

            # Don't create any key file
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

                    # Attempting to load key should fail with helpful message
                    with pytest.raises(FileNotFoundError) as exc_info:
                        auth._load_private_key()

                    error_msg = str(exc_info.value)

                    # Error should mention key path
                    assert "test-org" in error_msg or ".key" in error_msg

                    # Error should mention how to generate
                    assert "openssl" in error_msg.lower() or "generate" in error_msg.lower()

    def test_consumer_key_not_found_lists_options(self):
        """ValueError for missing consumer key lists all resolution options."""
        from scripts.auth import Data360Auth

        org_alias = "my-test-org"

        with tempfile.TemporaryDirectory() as jwt_dir:
            jwt_path = Path(jwt_dir)

            # Create key file but no consumer key
            key_file = jwt_path / f"{org_alias}.key"
            key_file.write_text("test-key-content")

            # Clear any env vars
            import os
            env_vars_to_clear = [
                f"SF_{org_alias.upper().replace('-', '_')}_CONSUMER_KEY",
                "SF_CONSUMER_KEY"
            ]
            for var in env_vars_to_clear:
                os.environ.pop(var, None)

            with patch('scripts.auth.DEFAULT_KEY_DIR', jwt_path):
                with patch.object(Data360Auth, '_get_org_info') as mock_org:
                    mock_org.return_value = MagicMock(
                        instance_url="https://test.salesforce.com",
                        username="test@example.com",
                        is_sandbox=False
                    )

                    with pytest.raises(ValueError) as exc_info:
                        Data360Auth(org_alias=org_alias)

                    error_msg = str(exc_info.value)

                    # Should mention file option
                    assert ".consumer-key" in error_msg

                    # Should mention env option
                    assert "SF_" in error_msg

    def test_invalid_jwt_assertion_error(self):
        """Invalid JWT assertion produces clear error."""
        from scripts.auth import Data360Auth

        with tempfile.TemporaryDirectory() as jwt_dir:
            jwt_path = Path(jwt_dir)

            # Create an invalid key file (not a real private key)
            key_file = jwt_path / "test-org.key"
            key_file.write_text("not-a-valid-private-key")

            consumer_key_file = jwt_path / "test-org.consumer-key"
            consumer_key_file.write_text("test-consumer-key")

            with patch('scripts.auth.DEFAULT_KEY_DIR', jwt_path):
                with patch.object(Data360Auth, '_get_org_info') as mock_org:
                    mock_org.return_value = MagicMock(
                        instance_url="https://test.salesforce.com",
                        username="test@example.com",
                        is_sandbox=False,
                        login_url="https://login.salesforce.com"
                    )

                    auth = Data360Auth(org_alias="test-org")

                    # Attempting to create JWT should fail
                    with pytest.raises(Exception):
                        auth._create_jwt_assertion()

    def test_sf_cli_not_found_error(self):
        """Missing sf CLI produces clear error."""
        from scripts.auth import Data360Auth

        # Mock subprocess.run in the auth module's namespace
        with patch('scripts.auth.subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError("sf command not found")

            with pytest.raises((RuntimeError, FileNotFoundError)):
                # This should fail when trying to get org info
                auth = Data360Auth(
                    org_alias="test-org",
                    consumer_key="test-key",
                    key_path=Path("/tmp/test.key")
                )
                # Force org info fetch (lazy loaded)
                _ = auth.org_info


@pytest.mark.tier1
@pytest.mark.offline
class TestCLIAuthErrors:
    """Test CLI handles auth errors gracefully."""

    def test_test_auth_command_missing_org(self, cli_runner, cli_app):
        """test-auth command requires --org."""
        result = cli_runner.invoke(cli_app, ["test-auth"])

        assert result.exit_code != 0
        assert "org" in result.output.lower() or "required" in result.output.lower()

    def test_extract_command_missing_org(self, cli_runner, cli_app):
        """extract command requires --org."""
        result = cli_runner.invoke(cli_app, ["extract"])

        assert result.exit_code != 0
        assert "org" in result.output.lower() or "required" in result.output.lower()
