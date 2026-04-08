"""
Unit tests for lifelens/utils/agent_utils.py

Tests all utility functions, enums, and standard schemas for multiagent system.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from lifelens.utils.agent_utils import (
    CriticVerdict,
    Intent,
    create_standard_plan,
    log_agent_decision,
    get_agent_trace,
    should_trigger,
    format_trace_for_ui
)


class TestCriticVerdictEnum:
    """Test CriticVerdict enum values."""
    
    def test_verdict_enum_values(self):
        """Test all verdict enum values exist."""
        assert CriticVerdict.OK.value == "OK"
        assert CriticVerdict.RETRY.value == "RETRY"
        assert CriticVerdict.NOT_ENOUGH_EVIDENCE.value == "NOT_ENOUGH_EVIDENCE"
        assert CriticVerdict.SUGGEST_TRIGGER.value == "SUGGEST_TRIGGER"
        assert CriticVerdict.IGNORE.value == "IGNORE"
    
    def test_verdict_enum_comparison(self):
        """Test verdict enum comparison."""
        assert CriticVerdict.OK == CriticVerdict.OK
        assert CriticVerdict.OK != CriticVerdict.RETRY


class TestIntentEnum:
    """Test Intent enum values."""
    
    def test_intent_enum_values(self):
        """Test all intent enum values exist."""
        assert Intent.MEMORY_RECALL.value == "memory_recall"
        assert Intent.INGESTION.value == "ingestion"
        assert Intent.ANALYTICS.value == "analytics"
        assert Intent.SUMMARY.value == "summary"
        assert Intent.TRIGGER_SCAN.value == "trigger_scan"
        assert Intent.MEDICATION.value == "medication"
        assert Intent.MOOD.value == "mood"


class TestCreateStandardPlan:
    """Test create_standard_plan() function."""
    
    def test_create_standard_plan_with_all_fields(self):
        """Test creating standard plan with all fields."""
        plan = create_standard_plan(
            intent=Intent.MEMORY_RECALL,
            needs_retrieval=True,
            temporal_scope="last_week",
            entities=["grandchildren", "park"],
            modalities=["image", "video"],
            reasoning="User asking about recent park visits",
            max_results=10,
            trigger_if_missing=False,
            max_retries=1
        )
        
        assert plan["intent"] == "memory_recall"
        assert plan["needs_retrieval"] is True
        assert plan["temporal_scope"] == "last_week"
        assert plan["entities"] == ["grandchildren", "park"]
        assert plan["modalities"] == ["image", "video"]
        assert plan["reasoning"] == "User asking about recent park visits"
        assert plan["max_results"] == 10
        assert plan["trigger_if_missing"] is False
        assert plan["max_retries"] == 1
        
        # Check extra fields were added
        assert "confidence_threshold" in plan
        assert "fallback" in plan
    
    def test_create_standard_plan_with_defaults(self):
        """Test creating standard plan with default values."""
        plan = create_standard_plan(
            intent=Intent.MEMORY_RECALL,
            reasoning="Simple query"
        )
        
        assert plan["intent"] == "memory_recall"
        assert plan["needs_retrieval"] is True
        assert plan["temporal_scope"] == "last_week"  # Default is last_week
        assert plan["entities"] == []
        assert plan["modalities"] == []
        assert plan["confidence_threshold"] == 0.75
        assert plan["trigger_if_missing"] is False
        assert plan["max_retries"] == 2
    
    def test_create_standard_plan_no_retrieval(self):
        """Test creating plan with needs_retrieval=False."""
        plan = create_standard_plan(
            intent=Intent.MEMORY_RECALL,
            needs_retrieval=False,
            reasoning="Direct answer"
        )
        
        assert plan["needs_retrieval"] is False
        assert "reasoning" in plan
        assert plan["reasoning"] == "Direct answer"


class TestLogAgentDecision:
    """Test log_agent_decision() function."""
    
    @patch('lifelens.utils.agent_utils.genai.embed_content')
    def test_log_agent_decision_success(self, mock_embed, mock_qdrant_client, sample_patient_id, sample_session_id):
        """Test successful logging of agent decision."""
        # Mock embedding result
        mock_embed.return_value = {"embedding": [0.1] * 768}
        
        # Should not raise exception
        log_agent_decision(
            client=mock_qdrant_client,
            patient_id=sample_patient_id,
            agent="planner",
            session_id=sample_session_id,
            verdict=CriticVerdict.OK,
            reasoning="Plan created successfully",
            metadata={"query": "test query"}
        )
        
        # Verify upsert was called
        assert mock_qdrant_client.upsert.called
        assert mock_embed.called
        
        # Verify payload structure
        call_args = mock_qdrant_client.upsert.call_args
        points = call_args[1]["points"]
        assert len(points) == 1
        
        payload = points[0].payload
        assert payload["patient_id"] == sample_patient_id
        assert payload["agent"] == "planner"
        assert payload["session_id"] == sample_session_id
        assert payload["verdict"] == "OK"
        assert payload["reasoning"] == "Plan created successfully"
        assert payload["metadata"]["query"] == "test query"
        assert "timestamp" in payload
    
    @patch('lifelens.utils.agent_utils.genai.embed_content')
    def test_log_agent_decision_with_string_verdict(self, mock_embed, mock_qdrant_client, sample_patient_id, sample_session_id):
        """Test logging with string verdict (backward compatibility)."""
        # Mock embedding result
        mock_embed.return_value = {"embedding": [0.1] * 768}
        
        log_agent_decision(
            client=mock_qdrant_client,
            patient_id=sample_patient_id,
            agent="critic",
            session_id=sample_session_id,
            verdict="OK",  # String instead of enum
            reasoning="Legacy verdict"
        )
        
        assert mock_qdrant_client.upsert.called
    
    def test_log_agent_decision_failure_handled(self, sample_patient_id, sample_session_id):
        """Test that logging failures are handled gracefully."""
        mock_client = Mock()
        mock_client.upsert.side_effect = Exception("Connection error")
        
        # Should not raise exception (non-blocking)
        log_agent_decision(
            client=mock_client,
            patient_id=sample_patient_id,
            agent="planner",
            session_id=sample_session_id,
            verdict=CriticVerdict.OK,
            reasoning="Test"
        )


class TestGetAgentTrace:
    """Test get_agent_trace() function."""
    
    def test_get_agent_trace_success(self, mock_qdrant_client, sample_session_id):
        """Test successful retrieval of agent trace."""
        # Mock scroll result
        mock_point = Mock()
        mock_point.payload = {
            "agent": "planner",
            "verdict": "OK",
            "timestamp": time.time(),
            "reasoning": "Test"
        }
        mock_qdrant_client.scroll.return_value = ([mock_point], None)
        
        trace = get_agent_trace(
            client=mock_qdrant_client,
            session_id=sample_session_id
        )
        
        assert len(trace) == 1
        assert trace[0]["agent"] == "planner"
        assert trace[0]["verdict"] == "OK"
    
    def test_get_agent_trace_empty(self, mock_qdrant_client, sample_session_id):
        """Test retrieving empty trace."""
        mock_qdrant_client.scroll.return_value = ([], None)
        
        trace = get_agent_trace(
            client=mock_qdrant_client,
            session_id=sample_session_id
        )
        
        assert trace == []
    
    # Note: get_agent_trace() doesn't support agent filtering
    # Use get_recent_decisions() for that functionality


class TestShouldTrigger:
    """Test should_trigger() function."""
    
    def test_should_trigger_with_suggest_trigger_verdict(self):
        """Test trigger fires for SUGGEST_TRIGGER verdict."""
        assert should_trigger(CriticVerdict.SUGGEST_TRIGGER) is True
    
    def test_should_trigger_with_not_enough_evidence(self):
        """Test trigger fires for NOT_ENOUGH_EVIDENCE verdict."""
        assert should_trigger(CriticVerdict.NOT_ENOUGH_EVIDENCE) is True
    
    def test_should_trigger_with_ok_verdict(self):
        """Test trigger does not fire for OK verdict."""
        assert should_trigger(CriticVerdict.OK) is False
    
    def test_should_trigger_with_retry_verdict(self):
        """Test trigger does not fire for RETRY verdict."""
        assert should_trigger(CriticVerdict.RETRY) is False
    
    def test_should_trigger_with_ignore_verdict(self):
        """Test trigger does not fire for IGNORE verdict."""
        assert should_trigger(CriticVerdict.IGNORE) is False
    
    def test_should_trigger_with_high_risk_score(self):
        """Test trigger fires with high risk score."""
        assert should_trigger(CriticVerdict.OK, risk_score=0.8, threshold=0.5) is True
    
    def test_should_trigger_with_low_risk_score(self):
        """Test trigger does not fire with low risk score."""
        assert should_trigger(CriticVerdict.OK, risk_score=0.3, threshold=0.5) is False
    
    def test_should_trigger_with_none_risk_score(self):
        """Test trigger with None risk score."""
        assert should_trigger(CriticVerdict.OK, risk_score=None, threshold=0.5) is False


class TestFormatTraceForUI:
    """Test format_trace_for_ui() function."""
    
    def test_format_trace_for_ui_with_data(self):
        """Test formatting trace data for UI display."""
        trace_data = [
            {
                "agent": "planner",
                "verdict": "OK",
                "timestamp": time.time(),
                "timestamp_iso": "2024-01-01T12:00:00",
                "reasoning": "Plan created",
                "attempt": 0
            },
            {
                "agent": "retriever",
                "verdict": "OK",
                "timestamp": time.time(),
                "timestamp_iso": "2024-01-01T12:00:01", 
                "reasoning": "Retrieved 5 memories",
                "attempt": 0
            }
        ]
        
        formatted = format_trace_for_ui(trace_data)
        
        assert len(formatted) == 2
        assert "timestamp" in formatted[0]
        assert formatted[0]["agent"] == "planner"
        assert formatted[1]["agent"] == "retriever"
    
    def test_format_trace_for_ui_empty(self):
        """Test formatting empty trace."""
        formatted = format_trace_for_ui([])
        assert formatted == []


class TestIntegration:
    """Integration tests combining multiple utilities."""
    
    @patch('lifelens.utils.agent_utils.genai.embed_content')
    def test_full_logging_and_retrieval_flow(self, mock_embed, mock_qdrant_client, sample_patient_id, sample_session_id):
        """Test logging decisions and retrieving trace."""
        # Mock embedding result
        mock_embed.return_value = {"embedding": [0.1] * 768}
        
        # Log multiple decisions
        log_agent_decision(
            client=mock_qdrant_client,
            patient_id=sample_patient_id,
            agent="planner",
            session_id=sample_session_id,
            verdict=CriticVerdict.OK,
            reasoning="Plan created"
        )
        
        log_agent_decision(
            client=mock_qdrant_client,
            patient_id=sample_patient_id,
            agent="retriever",
            session_id=sample_session_id,
            verdict=CriticVerdict.OK,
            reasoning="Retrieved memories"
        )
        
        # Verify both were logged
        assert mock_qdrant_client.upsert.call_count == 2
    
    def test_standard_plan_with_should_trigger(self):
        """Test creating plan and checking trigger conditions."""
        plan = create_standard_plan(
            intent=Intent.MEMORY_RECALL,
            trigger_if_missing=True,
            reasoning="Test query"
        )
        
        # If verdict is NOT_ENOUGH_EVIDENCE, should trigger
        assert should_trigger(CriticVerdict.NOT_ENOUGH_EVIDENCE) is True
        
        # If verdict is OK, should not trigger (unless risk score high)
        assert should_trigger(CriticVerdict.OK) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
