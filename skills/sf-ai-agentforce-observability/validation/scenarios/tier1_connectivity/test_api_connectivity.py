"""
T1: API Connectivity Tests (10 points)

Tests Data 360 v65.0 API connectivity:
- Token generation works
- Query endpoint accessible
- STDM DMOs exist

These are live API tests that require real Salesforce connection.
"""

import sys
import pytest
from pathlib import Path

# Add skill scripts to path
SKILL_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(SKILL_ROOT))


@pytest.mark.tier1
@pytest.mark.live_api
class TestAPIConnectivity:
    """Test Data 360 v65.0 API connectivity (10 points)."""

    def test_token_generation(self, auth_client):
        """Auth client can generate valid access token."""
        token = auth_client.get_token()

        assert token is not None
        assert len(token) > 0
        assert isinstance(token, str)

    def test_connection_verification(self, auth_client):
        """test_connection() succeeds with valid auth."""
        result = auth_client.test_connection()

        assert result is True

    def test_api_version_is_v65(self, data_client):
        """Client uses Data 360 v65.0 API."""
        assert "v65.0" in data_client.api_version or data_client.api_version == "v65.0"

    def test_query_endpoint_accessible(self, data_client):
        """Query endpoint returns valid response."""
        # Simple query to test endpoint
        results = list(data_client.query(
            "SELECT ssot__Id__c FROM ssot__AIAgentSession__dlm LIMIT 1"
        ))

        # Should return a list (may be empty if no data)
        assert isinstance(results, list)

    def test_stdm_dmos_exist(self, data_client):
        """All 4 STDM DMOs are accessible."""
        from scripts.models import DMO_NAMES

        # Test each core DMO (not quality DMOs which may not exist)
        core_dmos = ["sessions", "interactions", "steps", "messages"]

        for entity_type in core_dmos:
            dmo_name = DMO_NAMES[entity_type]
            query = f"SELECT ssot__Id__c FROM {dmo_name} LIMIT 1"

            try:
                results = list(data_client.query(query))
                # Query succeeded - DMO exists
                assert isinstance(results, list)
            except RuntimeError as e:
                # DMO might not have data but should exist
                error_str = str(e).lower()
                # If error is about no data, that's OK
                # If error is about DMO not existing, that's a failure
                if "does not exist" in error_str:
                    pytest.fail(f"DMO {dmo_name} does not exist: {e}")

    def test_headers_include_authorization(self, auth_client):
        """get_headers() returns proper auth header."""
        headers = auth_client.get_headers()

        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Bearer ")
        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"

    def test_instance_url_valid(self, auth_client):
        """Instance URL is a valid Salesforce URL."""
        instance_url = auth_client.instance_url

        assert instance_url is not None
        assert instance_url.startswith("https://")
        assert "salesforce.com" in instance_url or "force.com" in instance_url


@pytest.mark.tier1
@pytest.mark.live_api
class TestOrgInfo:
    """Test org info retrieval."""

    def test_org_info_populated(self, auth_client):
        """Org info is populated from sf CLI."""
        org_info = auth_client.org_info

        assert org_info is not None
        assert org_info.instance_url is not None
        assert org_info.username is not None
        assert len(org_info.username) > 0

    def test_sandbox_detection(self, auth_client):
        """Sandbox/production correctly detected."""
        org_info = auth_client.org_info

        # is_sandbox should be a boolean
        assert isinstance(org_info.is_sandbox, bool)

        # If sandbox, should use test.salesforce.com
        if org_info.is_sandbox:
            assert org_info.login_url == "https://test.salesforce.com"
        else:
            assert org_info.login_url == "https://login.salesforce.com"
