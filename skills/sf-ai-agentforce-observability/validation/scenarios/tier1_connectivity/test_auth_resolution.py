"""
T1: Auth Resolution Tests (10 points)

Tests key path and consumer key resolution logic:
- Key path resolution order (app-specific → generic)
- Consumer key resolution (file → env)

These tests verify SKILL.md claims about auth configuration.
"""

import os
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
class TestKeyPathResolution:
    """Test JWT key path resolution order (5 points)."""

    def test_explicit_key_path_takes_precedence(self, tmp_path):
        """Explicit --key-path overrides all other paths."""
        from scripts.auth import Data360Auth, DEFAULT_KEY_DIR

        # Create a custom key file
        custom_key = tmp_path / "custom.key"
        custom_key.write_text("-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----")

        # Mock org info to avoid sf CLI call
        with patch.object(Data360Auth, '_get_org_info') as mock_org:
            mock_org.return_value = MagicMock(
                instance_url="https://test.salesforce.com",
                username="test@example.com",
                is_sandbox=False
            )

            auth = Data360Auth(
                org_alias="test-org",
                consumer_key="test-key",
                key_path=custom_key
            )

            assert auth.key_path == custom_key

    def test_app_specific_key_before_generic(self, tmp_path):
        """App-specific key (~/.sf/jwt/{org}-agentforce-observability.key) before generic."""
        from scripts.auth import Data360Auth, DEFAULT_KEY_DIR

        org_alias = "test-org"

        with tempfile.TemporaryDirectory() as jwt_dir:
            jwt_path = Path(jwt_dir)

            # Create both app-specific and generic keys
            app_key = jwt_path / f"{org_alias}-agentforce-observability.key"
            generic_key = jwt_path / f"{org_alias}.key"

            app_key.write_text("app-specific-key")
            generic_key.write_text("generic-key")

            # Patch DEFAULT_KEY_DIR
            with patch('scripts.auth.DEFAULT_KEY_DIR', jwt_path):
                with patch.object(Data360Auth, '_get_org_info') as mock_org:
                    mock_org.return_value = MagicMock(
                        instance_url="https://test.salesforce.com",
                        username="test@example.com",
                        is_sandbox=False
                    )

                    auth = Data360Auth(
                        org_alias=org_alias,
                        consumer_key="test-key"
                    )

                    # Should use app-specific key
                    assert auth.key_path == app_key
                    assert auth.key_path.read_text() == "app-specific-key"

    def test_generic_key_fallback(self, tmp_path):
        """Falls back to generic key when app-specific not found."""
        from scripts.auth import Data360Auth

        org_alias = "test-org"

        with tempfile.TemporaryDirectory() as jwt_dir:
            jwt_path = Path(jwt_dir)

            # Only create generic key (no app-specific)
            generic_key = jwt_path / f"{org_alias}.key"
            generic_key.write_text("generic-key")

            with patch('scripts.auth.DEFAULT_KEY_DIR', jwt_path):
                with patch.object(Data360Auth, '_get_org_info') as mock_org:
                    mock_org.return_value = MagicMock(
                        instance_url="https://test.salesforce.com",
                        username="test@example.com",
                        is_sandbox=False
                    )

                    auth = Data360Auth(
                        org_alias=org_alias,
                        consumer_key="test-key"
                    )

                    # Should use generic key
                    assert auth.key_path == generic_key


@pytest.mark.tier1
@pytest.mark.offline
class TestConsumerKeyResolution:
    """Test consumer key resolution order (5 points)."""

    def test_explicit_consumer_key_takes_precedence(self):
        """Explicit consumer_key parameter overrides all."""
        from scripts.auth import Data360Auth

        with patch.object(Data360Auth, '_get_org_info') as mock_org:
            mock_org.return_value = MagicMock(
                instance_url="https://test.salesforce.com",
                username="test@example.com",
                is_sandbox=False
            )

            with patch('scripts.auth.DEFAULT_KEY_DIR', Path("/nonexistent")):
                auth = Data360Auth(
                    org_alias="test-org",
                    consumer_key="explicit-consumer-key",
                    key_path=Path("/tmp/test.key")
                )

                assert auth.consumer_key == "explicit-consumer-key"

    def test_app_specific_consumer_key_file(self):
        """Loads from ~/.sf/jwt/{org}-agentforce-observability.consumer-key."""
        from scripts.auth import Data360Auth

        org_alias = "test-org"

        with tempfile.TemporaryDirectory() as jwt_dir:
            jwt_path = Path(jwt_dir)

            # Create app-specific consumer key file
            consumer_key_file = jwt_path / f"{org_alias}-agentforce-observability.consumer-key"
            consumer_key_file.write_text("file-consumer-key")

            # Create a key file too
            key_file = jwt_path / f"{org_alias}.key"
            key_file.write_text("test-key")

            with patch('scripts.auth.DEFAULT_KEY_DIR', jwt_path):
                with patch.object(Data360Auth, '_get_org_info') as mock_org:
                    mock_org.return_value = MagicMock(
                        instance_url="https://test.salesforce.com",
                        username="test@example.com",
                        is_sandbox=False
                    )

                    auth = Data360Auth(org_alias=org_alias)

                    assert auth.consumer_key == "file-consumer-key"

    def test_generic_consumer_key_file(self):
        """Falls back to ~/.sf/jwt/{org}.consumer-key."""
        from scripts.auth import Data360Auth

        org_alias = "test-org"

        with tempfile.TemporaryDirectory() as jwt_dir:
            jwt_path = Path(jwt_dir)

            # Create generic consumer key file (no app-specific)
            consumer_key_file = jwt_path / f"{org_alias}.consumer-key"
            consumer_key_file.write_text("generic-consumer-key")

            # Create a key file
            key_file = jwt_path / f"{org_alias}.key"
            key_file.write_text("test-key")

            with patch('scripts.auth.DEFAULT_KEY_DIR', jwt_path):
                with patch.object(Data360Auth, '_get_org_info') as mock_org:
                    mock_org.return_value = MagicMock(
                        instance_url="https://test.salesforce.com",
                        username="test@example.com",
                        is_sandbox=False
                    )

                    auth = Data360Auth(org_alias=org_alias)

                    assert auth.consumer_key == "generic-consumer-key"

    def test_environment_variable_fallback(self):
        """Falls back to SF_{ORG}_CONSUMER_KEY environment variable."""
        from scripts.auth import Data360Auth

        org_alias = "test-org"

        with tempfile.TemporaryDirectory() as jwt_dir:
            jwt_path = Path(jwt_dir)

            # Create key file but no consumer key files
            key_file = jwt_path / f"{org_alias}.key"
            key_file.write_text("test-key")

            # Set environment variable
            env_key = f"SF_{org_alias.upper().replace('-', '_')}_CONSUMER_KEY"

            with patch.dict(os.environ, {env_key: "env-consumer-key"}):
                with patch('scripts.auth.DEFAULT_KEY_DIR', jwt_path):
                    with patch.object(Data360Auth, '_get_org_info') as mock_org:
                        mock_org.return_value = MagicMock(
                            instance_url="https://test.salesforce.com",
                            username="test@example.com",
                            is_sandbox=False
                        )

                        auth = Data360Auth(org_alias=org_alias)

                        assert auth.consumer_key == "env-consumer-key"

    def test_global_env_variable_fallback(self):
        """Falls back to SF_CONSUMER_KEY environment variable."""
        from scripts.auth import Data360Auth

        org_alias = "test-org"

        with tempfile.TemporaryDirectory() as jwt_dir:
            jwt_path = Path(jwt_dir)

            # Create key file but no consumer key files
            key_file = jwt_path / f"{org_alias}.key"
            key_file.write_text("test-key")

            # Set global environment variable
            with patch.dict(os.environ, {"SF_CONSUMER_KEY": "global-consumer-key"}):
                with patch('scripts.auth.DEFAULT_KEY_DIR', jwt_path):
                    with patch.object(Data360Auth, '_get_org_info') as mock_org:
                        mock_org.return_value = MagicMock(
                            instance_url="https://test.salesforce.com",
                            username="test@example.com",
                            is_sandbox=False
                        )

                        auth = Data360Auth(org_alias=org_alias)

                        assert auth.consumer_key == "global-consumer-key"

    def test_consumer_key_not_found_error(self):
        """Raises helpful error when consumer key not found."""
        from scripts.auth import Data360Auth

        org_alias = "test-org"

        with tempfile.TemporaryDirectory() as jwt_dir:
            jwt_path = Path(jwt_dir)

            # Create key file but no consumer key files
            key_file = jwt_path / f"{org_alias}.key"
            key_file.write_text("test-key")

            # Clear environment
            env_to_clear = {
                f"SF_{org_alias.upper().replace('-', '_')}_CONSUMER_KEY": "",
                "SF_CONSUMER_KEY": ""
            }

            with patch.dict(os.environ, env_to_clear, clear=False):
                # Remove env vars if they exist
                for key in env_to_clear:
                    os.environ.pop(key, None)

                with patch('scripts.auth.DEFAULT_KEY_DIR', jwt_path):
                    with patch.object(Data360Auth, '_get_org_info') as mock_org:
                        mock_org.return_value = MagicMock(
                            instance_url="https://test.salesforce.com",
                            username="test@example.com",
                            is_sandbox=False
                        )

                        with pytest.raises(ValueError) as exc_info:
                            Data360Auth(org_alias=org_alias)

                        # Error should mention resolution options
                        error_msg = str(exc_info.value)
                        assert "Consumer key not found" in error_msg
                        assert org_alias in error_msg
