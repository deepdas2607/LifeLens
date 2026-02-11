"""
Unit tests for lifelens/agents/critic.py

Tests critic agent verdict generation and CriticVerdict enum integration.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from lifelens.utils.agent_utils import CriticVerdict


class TestCriticEvaluate:
    """Test critic.evaluate() function."""
    
    @patch('lifelens.agents.critic.Groq')
    def test_critic_returns_ok_verdict(self, mock_groq_class, mock_qdrant_client, sample_patient_id, sample_session_id, sample_memory):
        """Test critic returns OK verdict for good answer."""
        # Mock Groq client instance
        mock_groq = MagicMock()
        mock_groq.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content="OK"))]
        )
        mock_groq_class.return_value = mock_groq
        
        from lifelens.agents.critic import evaluate
        
        verdict = evaluate(
            user_query="What did I do yesterday?",
            answer="You went to the park with your grandchildren.",
            retrieved_memories=[sample_memory],
            session_id=sample_session_id,
            patient_id=sample_patient_id,
            qdrant_client=mock_qdrant_client
        )
        
        # Should return CriticVerdict enum
        assert isinstance(verdict, CriticVerdict)
        assert verdict == CriticVerdict.OK
    
    @patch('lifelens.agents.critic.Groq')
    def test_critic_returns_retry_verdict(self, mock_groq_class, mock_qdrant_client, sample_patient_id, sample_session_id, sample_memory):
        """Test critic returns RETRY verdict for poor answer."""
        mock_groq = MagicMock()
        mock_groq.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content="RETRY"))]
        )
        mock_groq_class.return_value = mock_groq
        
        from lifelens.agents.critic import evaluate
        
        verdict = evaluate(
            user_query="What did I do yesterday?",
            answer="I don't know.",
            retrieved_memories=[sample_memory],
            session_id=sample_session_id,
            patient_id=sample_patient_id,
            qdrant_client=mock_qdrant_client
        )
        
        assert verdict == CriticVerdict.RETRY
    
    @patch('lifelens.agents.critic.Groq')
    def test_critic_returns_not_enough_evidence(self, mock_groq_class, mock_qdrant_client, sample_patient_id, sample_session_id):
        """Test critic returns NOT_ENOUGH_EVIDENCE verdict."""
        mock_groq = MagicMock()
        mock_groq.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content="NOT_ENOUGH_EVIDENCE"))]
        )
        mock_groq_class.return_value = mock_groq
        
        from lifelens.agents.critic import evaluate
        
        verdict = evaluate(
            user_query="What did I eat for breakfast?",
            answer="I don't have any memories about breakfast.",
            retrieved_memories=[],
            session_id=sample_session_id,
            patient_id=sample_patient_id,
            qdrant_client=mock_qdrant_client
        )
        
        assert verdict == CriticVerdict.NOT_ENOUGH_EVIDENCE
    
    @patch('lifelens.agents.critic.log_agent_decision')
    @patch('lifelens.agents.critic.Groq')
    def test_critic_logs_decision_to_qdrant(self, mock_groq_class, mock_log, mock_qdrant_client, sample_patient_id, sample_session_id, sample_memory):
        """Test that critic logs decisions to Qdrant."""
        mock_groq = MagicMock()
        mock_groq.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content="OK"))]
        )
        mock_groq_class.return_value = mock_groq
        
        from lifelens.agents.critic import evaluate
        
        evaluate(
            user_query="Test query",
            answer="Test answer",
            retrieved_memories=[sample_memory],
            session_id=sample_session_id,
            patient_id=sample_patient_id,
            qdrant_client=mock_qdrant_client
        )
        
        # Verify log_agent_decision was called
        assert mock_log.called
    
    @patch('lifelens.agents.critic.Groq')
    def test_critic_fallback_without_groq(self, mock_groq_class, mock_qdrant_client, sample_patient_id, sample_session_id):
        """Test critic fallback when Groq client unavailable."""
        # Simulate Groq error
        mock_groq = MagicMock()
        mock_groq.chat.completions.create.side_effect = Exception("API Error")
        mock_groq_class.return_value = mock_groq
        
        from lifelens.agents.critic import evaluate
        
        # Should not crash, returns fallback verdict
        verdict = evaluate(
            user_query="Test query",
            answer="Test answer",
            retrieved_memories=[],
            session_id=sample_session_id,
            patient_id=sample_patient_id,
            qdrant_client=mock_qdrant_client
        )
        
        # Should return a valid verdict (retry or not_enough_evidence)
        assert isinstance(verdict, CriticVerdict)


class TestCriticMoodAlert:
    """Test critic.evaluate_mood_alert() function."""
    
    @patch('lifelens.agents.critic.Groq')
    def test_mood_alert_evaluation_returns_suggest_trigger(self, mock_groq_class, mock_qdrant_client, sample_patient_id):
        """Test mood alert evaluation returning SUGGEST_TRIGGER."""
        mock_groq = MagicMock()
        mock_groq.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content="ALERT"))]
        )
        mock_groq_class.return_value = mock_groq
        
        from lifelens.agents.critic import evaluate_mood_alert
        
        verdict = evaluate_mood_alert(
            patient_id=sample_patient_id,
            risk_score=0.8,
            signals={"negative_trend": True},
            recent_memories=[{"mood": "sad"}],
            visitor_correlations={},
            qdrant_client=mock_qdrant_client
        )
        
        # Returns "ALERT" string (not enum)
        assert verdict == "ALERT"
    
    @patch('lifelens.agents.critic.Groq')
    def test_mood_alert_evaluation_returns_ignore(self, mock_groq_class, mock_qdrant_client, sample_patient_id):
        """Test mood alert evaluation returning IGNORE."""
        mock_groq = MagicMock()
        mock_groq.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content="IGNORE"))]
        )
        mock_groq_class.return_value = mock_groq
        
        from lifelens.agents.critic import evaluate_mood_alert
        
        verdict = evaluate_mood_alert(
            patient_id=sample_patient_id,
            risk_score=0.2,
            signals={"positive_trend": True},
            recent_memories=[{"mood": "happy"}],
            visitor_correlations={},
            qdrant_client=mock_qdrant_client
        )
        
        assert verdict == "IGNORE"


class TestBackwardCompatibility:
    """Test backward compatibility with string verdicts."""
    
    def test_string_verdict_mapping(self):
        """Test that string verdicts map to CriticVerdict enums correctly."""
        from lifelens.agents.critic import evaluate
        
        # Test with no memories - should return NOT_ENOUGH_EVIDENCE or RETRY
        verdict = evaluate(
            user_query="Test",
            answer="I don't have enough information",
            retrieved_memories=None,
            session_id=None,
            patient_id=None,
            qdrant_client=None
        )
        
        # Should be a CriticVerdict enum
        assert isinstance(verdict, CriticVerdict)
