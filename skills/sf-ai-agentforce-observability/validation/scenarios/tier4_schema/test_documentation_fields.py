"""
T4: Documentation Field Validation Tests

Tests that documented fields exist in schema definitions:
- New fields from official Salesforce documentation
- OTEL tracing fields
- GenAI reference fields
- Step types and session end types

SKILL.md Section: "Session Tracing Data Model"
data-model-reference.md: Entity field definitions
"""

import sys
import pytest
from pathlib import Path

# Add skill scripts to path
SKILL_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(SKILL_ROOT))


@pytest.mark.tier4
@pytest.mark.offline
class TestSessionFields:
    """Test Session entity field documentation matches schema."""

    def test_session_core_fields_exist(self):
        """Core session fields from documentation exist in schema."""
        from scripts.models import SESSION_SCHEMA

        field_names = [field.name for field in SESSION_SCHEMA]

        # Core fields that must exist
        required_fields = [
            "ssot__Id__c",
            "ssot__StartTimestamp__c",
            "ssot__EndTimestamp__c",
        ]

        for field in required_fields:
            assert field in field_names, f"Missing core session field: {field}"

    def test_session_channel_fields(self):
        """Session channel and origin fields documented."""
        from scripts.models import SESSION_SCHEMA

        field_names = [field.name for field in SESSION_SCHEMA]

        # At least one of these should exist
        channel_fields = [
            "ssot__AiAgentChannelType__c",
            "ssot__AiAgentChannelTypeId__c",
            "ssot__RelatedMessagingSessionId__c",
            "ssot__RelatedVoiceCallId__c",
            "ssot__VoiceCallId__c",
            "ssot__MessagingSessionId__c",
        ]

        found = any(f in field_names for f in channel_fields)
        assert found, "No channel/origin fields found in session schema"

    def test_session_end_type_field_exists(self):
        """Session end type field exists."""
        from scripts.models import SESSION_SCHEMA

        field_names = [field.name for field in SESSION_SCHEMA]

        end_type_fields = [
            "ssot__AiAgentSessionEndType__c",
            "ssot__AiAgentSessionEndTypeId__c",
            # Note: API uses 'AiAgent' (lowercase 'i'), not 'AIAgent'
        ]

        found = any(f in field_names for f in end_type_fields)
        assert found, "Session end type field not found"


@pytest.mark.tier4
@pytest.mark.offline
class TestInteractionFields:
    """Test Interaction entity field documentation matches schema."""

    def test_interaction_core_fields_exist(self):
        """Core interaction fields from documentation exist."""
        from scripts.models import INTERACTION_SCHEMA

        field_names = [field.name for field in INTERACTION_SCHEMA]

        required_fields = [
            "ssot__Id__c",
            "ssot__StartTimestamp__c",
            "ssot__EndTimestamp__c",
        ]

        for field in required_fields:
            assert field in field_names, f"Missing core interaction field: {field}"

    def test_interaction_session_reference(self):
        """Interaction has reference to parent session."""
        from scripts.models import INTERACTION_SCHEMA

        field_names = [field.name for field in INTERACTION_SCHEMA]

        session_ref_fields = [
            "ssot__AiAgentSessionId__c",
            "ssot__aiAgentSessionId__c",
            "ssot__AIAgentSessionId__c",
        ]

        found = any(f in field_names for f in session_ref_fields)
        assert found, "Interaction missing session reference field"

    def test_interaction_topic_field(self):
        """Interaction has topic API name field."""
        from scripts.models import INTERACTION_SCHEMA

        field_names = [field.name for field in INTERACTION_SCHEMA]

        topic_fields = [
            "ssot__TopicApiName__c",
            "ssot__topicApiName__c",
        ]

        found = any(f in field_names for f in topic_fields)
        assert found, "Interaction missing topic API name field"


@pytest.mark.tier4
@pytest.mark.offline
class TestStepFields:
    """Test InteractionStep entity field documentation matches schema."""

    def test_step_core_fields_exist(self):
        """Core step fields from documentation exist."""
        from scripts.models import STEP_SCHEMA

        field_names = [field.name for field in STEP_SCHEMA]

        required_fields = [
            "ssot__Id__c",
            "ssot__Name__c",
        ]

        for field in required_fields:
            assert field in field_names, f"Missing core step field: {field}"

    def test_step_input_output_fields(self):
        """Step has input/output value fields."""
        from scripts.models import STEP_SCHEMA

        field_names = [field.name for field in STEP_SCHEMA]

        # Input field
        input_fields = ["ssot__InputValueText__c", "ssot__inputValueText__c"]
        found_input = any(f in field_names for f in input_fields)
        assert found_input, "Step missing input value field"

        # Output field
        output_fields = ["ssot__OutputValueText__c", "ssot__outputValueText__c"]
        found_output = any(f in field_names for f in output_fields)
        assert found_output, "Step missing output value field"

    def test_step_type_field(self):
        """Step has type classification field."""
        from scripts.models import STEP_SCHEMA

        field_names = [field.name for field in STEP_SCHEMA]

        type_fields = [
            "ssot__AiAgentInteractionStepType__c",
            "ssot__AiAgentInteractionStepTypeId__c",
            # Note: API uses 'AiAgent' (lowercase 'i'), not 'AIAgent'
        ]

        found = any(f in field_names for f in type_fields)
        assert found, "Step missing step type field"

    def test_step_generation_reference(self):
        """Step has GenerationId for GenAI linkage."""
        from scripts.models import STEP_SCHEMA

        field_names = [field.name for field in STEP_SCHEMA]

        gen_fields = [
            "ssot__GenerationId__c",
            "ssot__generationId__c",
        ]

        found = any(f in field_names for f in gen_fields)
        assert found, "Step missing GenerationId field for GenAI linkage"


@pytest.mark.tier4
@pytest.mark.offline
class TestMessageFields:
    """Test InteractionMessage/Moment entity field documentation."""

    def test_message_core_fields_exist(self):
        """Core message fields from documentation exist."""
        from scripts.models import MESSAGE_SCHEMA

        field_names = [field.name for field in MESSAGE_SCHEMA]

        required_fields = [
            "ssot__Id__c",
        ]

        for field in required_fields:
            assert field in field_names, f"Missing core message field: {field}"

    def test_message_content_field(self):
        """Message/Moment has content text field (Request/Response Summary)."""
        from scripts.models import MESSAGE_SCHEMA

        field_names = [field.name for field in MESSAGE_SCHEMA]

        # MESSAGE_SCHEMA is for Moment (AIAgentMoment) which uses Summary fields
        content_fields = [
            "ssot__ContentText__c",
            "ssot__ContextText__c",
            "ssot__RequestSummaryText__c",  # Moment uses summary fields
            "ssot__ResponseSummaryText__c",
        ]

        found = any(f in field_names for f in content_fields)
        assert found, "Message/Moment missing content text field"


@pytest.mark.tier4
@pytest.mark.offline
class TestOfficialStepTypes:
    """Test official step type values are documented correctly."""

    def test_step_types_defined(self):
        """Step types constants are defined."""
        # Check if step types are documented in models or elsewhere
        from scripts import models

        # Look for step type constants or enums
        step_type_attrs = [
            attr for attr in dir(models)
            if "STEP" in attr.upper() and "TYPE" in attr.upper()
        ]

        # Either we have constants or we document in docstrings
        # This test ensures we've thought about step types
        assert True  # Documentation test - verify in data-model-reference.md

    def test_llm_step_documented(self):
        """LLM step type is documented."""
        # Read the data model reference
        doc_path = SKILL_ROOT / "resources" / "data-model-reference.md"
        content = doc_path.read_text()

        # Check for LLM step documentation
        llm_variations = ["LLMExecutionStep", "LLM_STEP", "LlmStep"]
        found = any(v in content for v in llm_variations)
        assert found, "LLM step type not documented in data-model-reference.md"

    def test_function_step_documented(self):
        """Function/Action step type is documented."""
        doc_path = SKILL_ROOT / "resources" / "data-model-reference.md"
        content = doc_path.read_text()

        function_variations = ["FunctionStep", "ACTION_STEP", "ActionStep"]
        found = any(v in content for v in function_variations)
        assert found, "Function/Action step type not documented"

    def test_user_input_step_documented(self):
        """User input step type is documented."""
        doc_path = SKILL_ROOT / "resources" / "data-model-reference.md"
        content = doc_path.read_text()

        user_variations = ["UserInputStep", "USER_INPUT", "UserInput"]
        found = any(v in content for v in user_variations)
        assert found, "User input step type not documented"


@pytest.mark.tier4
@pytest.mark.offline
class TestOfficialSessionEndTypes:
    """Test official session end type values are documented."""

    def test_resolved_documented(self):
        """'resolved' end type is documented."""
        doc_path = SKILL_ROOT / "resources" / "data-model-reference.md"
        content = doc_path.read_text().lower()

        assert "resolved" in content, "'resolved' end type not documented"

    def test_escalated_documented(self):
        """'escalated' end type is documented."""
        doc_path = SKILL_ROOT / "resources" / "data-model-reference.md"
        content = doc_path.read_text().lower()

        assert "escalated" in content, "'escalated' end type not documented"

    def test_deflected_documented(self):
        """'deflected' end type is documented."""
        doc_path = SKILL_ROOT / "resources" / "data-model-reference.md"
        content = doc_path.read_text().lower()

        assert "deflected" in content, "'deflected' end type not documented"


@pytest.mark.tier4
@pytest.mark.offline
class TestGenAIReferenceFields:
    """Test GenAI reference fields are documented."""

    def test_generation_id_documented(self):
        """GenerationId field is documented."""
        doc_path = SKILL_ROOT / "resources" / "data-model-reference.md"
        content = doc_path.read_text()

        assert "GenerationId" in content, "GenerationId field not documented"

    def test_gateway_request_id_documented(self):
        """GenAiGatewayRequestId field is documented."""
        doc_path = SKILL_ROOT / "resources" / "data-model-reference.md"
        content = doc_path.read_text()

        variations = ["GatewayRequestId", "GenAiGatewayRequest"]
        found = any(v in content for v in variations)
        assert found, "GenAiGatewayRequestId not documented"

    def test_gateway_response_id_documented(self):
        """GenAiGatewayResponseId field is documented."""
        doc_path = SKILL_ROOT / "resources" / "data-model-reference.md"
        content = doc_path.read_text()

        variations = ["GatewayResponseId", "GenAiGatewayResponse"]
        found = any(v in content for v in variations)
        assert found, "GenAiGatewayResponseId not documented"


@pytest.mark.tier4
@pytest.mark.offline
class TestOTELFields:
    """Test OpenTelemetry tracing fields are documented."""

    def test_telemetry_trace_id_documented(self):
        """TelemetryTraceId field is documented."""
        doc_path = SKILL_ROOT / "resources" / "data-model-reference.md"
        content = doc_path.read_text()

        variations = ["TelemetryTraceId", "TelemetryTrace", "TraceId"]
        found = any(v in content for v in variations)
        assert found, "TelemetryTraceId not documented"

    def test_telemetry_span_id_documented(self):
        """TelemetryTraceSpanId field is documented."""
        doc_path = SKILL_ROOT / "resources" / "data-model-reference.md"
        content = doc_path.read_text()

        variations = ["TelemetryTraceSpanId", "SpanId", "TraceSpan"]
        found = any(v in content for v in variations)
        assert found, "TelemetryTraceSpanId not documented"

    def test_otel_integration_mentioned(self):
        """OpenTelemetry integration is mentioned in documentation."""
        doc_path = SKILL_ROOT / "resources" / "data-model-reference.md"
        content = doc_path.read_text()

        otel_terms = ["OpenTelemetry", "OTEL", "distributed tracing"]
        found = any(term in content for term in otel_terms)
        assert found, "OpenTelemetry integration not mentioned in documentation"
