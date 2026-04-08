"""
Unit tests for lifelens/agents/planner.py

Tests planner agent standard schema transformation and planning logic.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from lifelens.utils.agent_utils import Intent


class TestPlannerPlan:
    """Test planner.plan() function."""
    
    @patch('lifelens.agents.planner._get_patient_context')
    @patch('lifelens.agents.planner.Groq')
    def test_plan_transforms_to_standard_schema(self, mock_groq_class, mock_context, mock_qdrant_client, sample_patient_id, sample_session_id):
        """Test that plan() transforms LLM response to standard schema."""
        mock_context.return_value = {"total_memories": 100, "recent_count": 10, "types": ["text", "image"]}
        
        # Mock Groq client instance
        mock_groq = MagicMock()
        mock_groq.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content='{"retrieve": true, "filters": ["time:last_week"], "reasoning": "Test"}'))]
        )
        mock_groq_class.return_value = mock_groq
        
        from lifelens.agents.planner import plan
        
        result = plan("test query", sample_patient_id, mock_qdrant_client, sample_session_id)
        
        # Verify standard schema fields exist
        assert "intent" in result
        assert "needs_retrieval" in result
        assert "temporal_scope" in result
        assert "entities" in result
        assert "modalities" in result
        assert "confidence_threshold" in result
        assert "fallback" in result
        assert "trigger_if_missing" in result
        assert "max_retries" in result
    
    @patch('lifelens.agents.planner.log_agent_decision')
    @patch('lifelens.agents.planner._get_patient_context')
    @patch('lifelens.agents.planner.Groq')
    def test_plan_logs_to_qdrant(self, mock_groq_class, mock_context, mock_log, mock_qdrant_client, sample_patient_id, sample_session_id):
        """Test that planner logs decisions to Qdrant."""
        mock_context.return_value = {"total_memories": 100, "recent_count": 10, "types": []}
        mock_groq = MagicMock()
        mock_groq.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content='{"retrieve": true, "filters": [], "reasoning": "Test"}'))]
        )
        mock_groq_class.return_value = mock_groq
        
        from lifelens.agents.planner import plan
        
        result = plan("test query", sample_patient_id, mock_qdrant_client, sample_session_id)
        
        # Verify logging occurred
        assert mock_log.called
    
    @patch('lifelens.agents.planner._get_patient_context')
    @patch('lifelens.agents.planner.Groq')
    def test_plan_extracts_temporal_scope(self, mock_groq_class, mock_context, mock_qdrant_client, sample_patient_id, sample_session_id):
        """Test temporal scope extraction from filters."""
        mock_context.return_value = {"total_memories": 100, "recent_count": 10, "types": []}
        mock_groq = MagicMock()
        mock_groq.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content='{"retrieve": true, "filters": ["time:last_month"], "reasoning": "Test"}'))]
        )
        mock_groq_class.return_value = mock_groq
        
        from lifelens.agents.planner import plan
        
        result = plan("test query", sample_patient_id, mock_qdrant_client, sample_session_id)
        
        assert result["temporal_scope"] == "last_month"
    
    @patch('lifelens.agents.planner._get_patient_context')
    @patch('lifelens.agents.planner.Groq')
    def test_plan_extracts_modalities(self, mock_groq_class, mock_context, mock_qdrant_client, sample_patient_id, sample_session_id):
        """Test modality extraction from filters."""
        mock_context.return_value = {"total_memories": 100, "recent_count": 10, "types": []}
        mock_groq = MagicMock()
        mock_groq.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content='{"retrieve": true, "filters": ["type:image", "type:video"], "reasoning": "Test"}'))]
        )
        mock_groq_class.return_value = mock_groq
        
        from lifelens.agents.planner import plan
        
        result = plan("test query", sample_patient_id, mock_qdrant_client, sample_session_id)
        
        assert "image" in result["modalities"]
        assert "video" in result["modalities"]
    
    @patch('lifelens.agents.planner._get_patient_context')
    @patch('lifelens.agents.planner.Groq')
    def test_plan_fallback_on_error(self, mock_groq_class, mock_context, mock_qdrant_client, sample_patient_id, sample_session_id):
        """Test fallback plan creation on Groq error."""
        mock_context.return_value = {"total_memories": 100, "recent_count": 10, "types": []}
        mock_groq = MagicMock()
        mock_groq.chat.completions.create.side_effect = Exception("API Error")
        mock_groq_class.return_value = mock_groq
        
        from lifelens.agents.planner import plan
        
        result = plan("test query", sample_patient_id, mock_qdrant_client, sample_session_id)
        
        # Should return fallback plan
        assert "intent" in result
        assert "reasoning" in result
        assert "Fallback" in result["reasoning"] or "fallback" in result["reasoning"] or result["needs_retrieval"] == True


class TestPlannerReplan:
    """Test planner.replan() function."""
    
    @patch('lifelens.agents.planner._get_patient_context')
    @patch('lifelens.agents.planner.Groq')
    def test_replan_transforms_to_standard_schema(self, mock_groq_class, mock_context, mock_qdrant_client, sample_patient_id, sample_session_id):
        """Test that replan transforms LLM output to standard schema."""
        mock_context.return_value = {"total_memories": 100, "recent_count": 10, "types": []}
        mock_groq = MagicMock()
        mock_groq.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content='{"retrieve": true, "filters": ["time:last_month"], "reasoning": "Broader search"}'))]
        )
        mock_groq_class.return_value = mock_groq
        
        from lifelens.agents.planner import replan
        
        result = replan("test query", sample_patient_id, "prev answer", "RETRY", mock_qdrant_client)
        
        # Verify standard schema
        assert "needs_retrieval" in result
        assert "temporal_scope" in result
        assert "intent" in result
    
    @patch('lifelens.agents.planner._get_patient_context')
    @patch('lifelens.agents.planner.Groq')
    def test_replan_uses_broader_temporal_scope(self, mock_groq_class, mock_context, mock_qdrant_client, sample_patient_id, sample_session_id):
        """Test that replan uses broader temporal scope."""
        mock_context.return_value = {"total_memories": 100, "recent_count": 10, "types": []}
        mock_groq = MagicMock()
        mock_groq.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content='{"retrieve": true, "filters": ["time:last_year"], "reasoning": "Much broader"}'))]
        )
        mock_groq_class.return_value = mock_groq
        
        from lifelens.agents.planner import replan
        
        result = replan("test query", sample_patient_id, "prev answer", "RETRY", mock_qdrant_client)
        
        # Should have year scope
        assert result["temporal_scope"] == "last_year"
    
    @patch('lifelens.agents.planner.log_agent_decision')
    @patch('lifelens.agents.planner._get_patient_context')
    @patch('lifelens.agents.planner.Groq')
    def test_replan_logs_to_qdrant(self, mock_groq_class, mock_context, mock_log, mock_qdrant_client, sample_patient_id, sample_session_id):
        """Test that replan logs decisions to Qdrant."""
        mock_context.return_value = {"total_memories": 100, "recent_count": 10, "types": []}
        mock_groq = MagicMock()
        mock_groq.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content='{"retrieve": true, "filters": [], "reasoning": "Replan"}'))]
        )
        mock_groq_class.return_value = mock_groq
        
        from lifelens.agents.planner import replan
        
        result = replan("test query", sample_patient_id, "prev answer", "RETRY", mock_qdrant_client)
        
        # Verify logging occurred
        assert mock_log.called


class TestHelperFunctions:
    """Test planner helper functions."""
    
    def test_extract_temporal_scope(self):
        """Test _extract_temporal_scope helper."""
        from lifelens.agents.planner import _extract_temporal_scope
        
        # Test various filter formats
        assert _extract_temporal_scope(["time:last_week"]) == "last_week"
        assert _extract_temporal_scope(["time:last_month"]) == "last_month"
        assert _extract_temporal_scope(["time:last_year"]) == "last_year"
        assert _extract_temporal_scope([]) == "last_week"  # Default is last_week
    
    def test_extract_modalities(self):
        """Test _extract_modalities helper."""
        from lifelens.agents.planner import _extract_modalities
        
        # Test various filter formats
        assert "image" in _extract_modalities(["type:image"])
        assert "video" in _extract_modalities(["type:video"])
        assert "audio" in _extract_modalities(["type:audio"])
        # If no specific modalities found, returns all modalities
        result = _extract_modalities([])
        assert len(result) == 4  # Should return all 4 types
        assert "text" in result
        assert "image" in result
