"""
Unit tests for lifelens/orchestrator.py

Tests the multi-agent orchestration flow, retry loop, and session tracking.
"""

import pytest
from unittest.mock import Mock, patch
from lifelens.utils.agent_utils import CriticVerdict


class TestOrchestratorFlow:
    """Test orchestrator.run_agentic_flow() function."""
    
    @patch('lifelens.orchestrator.recommender')
    @patch('lifelens.orchestrator.trigger')
    @patch('lifelens.orchestrator.critic')
    @patch('lifelens.orchestrator.executor')
    @patch('lifelens.orchestrator.retriever')
    @patch('lifelens.orchestrator.planner')
    def test_successful_flow_first_attempt(
        self, mock_planner, mock_retriever, mock_executor,
        mock_critic, mock_trigger, mock_recommender,
        mock_qdrant_client, sample_patient_id
    ):
        """Test successful orchestration on first attempt."""
        # Mock planner
        mock_planner.plan.return_value = {
            "needs_retrieval": True,
            "intent": "memory_recall",
            "reasoning": "Test plan",
            "max_retries": 1
        }
        
        # Mock retriever
        mock_retriever.search.return_value = [
            {"content": "Test memory", "score": 0.9}
        ]
        
        # Mock executor
        mock_executor.execute.return_value = "This is the answer"
        
        # Mock critic returns OK on first try
        mock_critic.evaluate.return_value = CriticVerdict.OK
        
        # Mock trigger
        mock_trigger.generate.return_value = []
        
        # Mock recommender
        mock_recommender.suggest_captures.return_value = []
        
        # Import and run orchestrator
        from lifelens.orchestrator import run_agentic_flow
        
        result = run_agentic_flow(
            user_query="What did I do yesterday?",
            patient_id=sample_patient_id,
            qdrant_client=mock_qdrant_client,
            max_retries=1
        )
        
        # Assertions
        assert result["answer"] == "This is the answer"
        assert result["verdict"] == "OK"
        assert result["retry_count"] == 0
        assert "session_id" in result
        assert len(result["sources"]) == 1
        
        # Verify planner was called once
        mock_planner.plan.assert_called_once()
        
        # Verify retriever was called
        mock_retriever.search.assert_called_once()
        
        # Verify executor was called
        mock_executor.execute.assert_called_once()
        
        # Verify critic was called
        mock_critic.evaluate.assert_called_once()
    
    @patch('lifelens.orchestrator.recommender')
    @patch('lifelens.orchestrator.trigger')
    @patch('lifelens.orchestrator.critic')
    @patch('lifelens.orchestrator.executor')
    @patch('lifelens.orchestrator.retriever')
    @patch('lifelens.orchestrator.planner')
    def test_retry_flow_with_replanning(
        self, mock_planner, mock_retriever, mock_executor,
        mock_critic, mock_trigger, mock_recommender,
        mock_qdrant_client, sample_patient_id
    ):
        """Test retry loop with replanning."""
        # Mock planner - initial plan
        mock_planner.plan.return_value = {
            "needs_retrieval": True,
            "intent": "memory_recall",
            "reasoning": "Test plan",
            "max_retries": 2
        }
        
        # Mock replan
        mock_planner.replan.return_value = {
            "needs_retrieval": True,
            "intent": "memory_recall",
            "reasoning": "Replanned with broader scope",
            "max_retries": 2
        }
        
        # Mock retriever
        mock_retriever.search.return_value = [{"content": "Memory"}]
        
        # Mock executor
        mock_executor.execute.return_value = "Answer"
        
        # Mock critic - first returns RETRY, then OK
        mock_critic.evaluate.side_effect = [CriticVerdict.RETRY, CriticVerdict.OK]
        
        # Mock trigger and recommender
        mock_trigger.generate.return_value = []
        mock_recommender.suggest_captures.return_value = []
        
        from lifelens.orchestrator import run_agentic_flow
        
        result = run_agentic_flow(
            user_query="Test query",
            patient_id=sample_patient_id,
            qdrant_client=mock_qdrant_client,
            max_retries=2
        )
        
        # Should have called replan once
        mock_planner.replan.assert_called_once()
        
        # Should have retry_count = 1
        assert result["retry_count"] == 1
        
        # Final verdict should be OK
        assert result["verdict"] == "OK"
    
    @patch('lifelens.orchestrator.recommender')
    @patch('lifelens.orchestrator.trigger')
    @patch('lifelens.orchestrator.critic')
    @patch('lifelens.orchestrator.executor')
    @patch('lifelens.orchestrator.retriever')
    @patch('lifelens.orchestrator.planner')
    def test_max_retries_reached(
        self, mock_planner, mock_retriever, mock_executor,
        mock_critic, mock_trigger, mock_recommender,
        mock_qdrant_client, sample_patient_id
    ):
        """Test that flow stops after max retries."""
        # Mock planner
        mock_planner.plan.return_value = {
            "needs_retrieval": True,
            "intent": "memory_recall",
            "reasoning": "Test plan",
            "max_retries": 2
        }
        
        mock_planner.replan.return_value = {
            "needs_retrieval": True,
            "intent": "memory_recall",
            "reasoning": "Replan",
            "max_retries": 2
        }
        
        # Mock retriever
        mock_retriever.search.return_value = []
        
        # Mock executor
        mock_executor.execute.return_value = "Answer"
        
        # Mock critic - always returns RETRY
        mock_critic.evaluate.return_value = CriticVerdict.RETRY
        
        # Mock trigger and recommender
        mock_trigger.generate.return_value = []
        mock_recommender.suggest_captures.return_value = []
        
        from lifelens.orchestrator import run_agentic_flow
        
        result = run_agentic_flow(
            user_query="Test query",
            patient_id=sample_patient_id,
            qdrant_client=mock_qdrant_client,
            max_retries=2
        )
        
        # Should have reached max retries
        assert result["retry_count"] == 2
        
        # Replan should be called max_retries times
        assert mock_planner.replan.call_count == 2
    
    @patch('lifelens.orchestrator.recommender')
    @patch('lifelens.orchestrator.trigger')
    @patch('lifelens.orchestrator.critic')
    @patch('lifelens.orchestrator.executor')
    @patch('lifelens.orchestrator.retriever')
    @patch('lifelens.orchestrator.planner')
    def test_conditional_retrieval_skip(
        self, mock_planner, mock_retriever, mock_executor,
        mock_critic, mock_trigger, mock_recommender,
        mock_qdrant_client, sample_patient_id
    ):
        """Test that retrieval is skipped when needs_retrieval=False."""
        # Mock plan with both needs_retrieval and retrieve set to False
        mock_planner.plan.return_value = {
            "needs_retrieval": False,
            "retrieve": False,
            "intent": "memory_recall",
            "reasoning": "No retrieval needed",
            "max_retries": 2
        }
        
        # Mock executor
        mock_executor.execute.return_value = "Direct answer"
        
        # Mock critic
        mock_critic.evaluate.return_value = CriticVerdict.OK
        
        # Mock trigger and recommender
        mock_trigger.generate.return_value = []
        mock_recommender.suggest_captures.return_value = []
        
        from lifelens.orchestrator import run_agentic_flow
        
        result = run_agentic_flow(
            user_query="What is 2+2?",
            patient_id=sample_patient_id,
            qdrant_client=mock_qdrant_client
        )
        
        # Retriever should NOT be called
        mock_retriever.search.assert_not_called()
        
        # Should have empty sources
        assert result["sources"] == []
    
    @patch('lifelens.orchestrator.recommender')
    @patch('lifelens.orchestrator.trigger')
    @patch('lifelens.orchestrator.critic')
    @patch('lifelens.orchestrator.executor')
    @patch('lifelens.orchestrator.retriever')
    @patch('lifelens.orchestrator.planner')
    def test_trigger_generation_on_not_enough_evidence(
        self, mock_planner, mock_retriever, mock_executor,
        mock_critic, mock_trigger, mock_recommender,
        mock_qdrant_client, sample_patient_id
    ):
        """Test trigger generation when verdict is NOT_ENOUGH_EVIDENCE."""
        # Mock planner
        mock_planner.plan.return_value = {
            "needs_retrieval": True,
            "intent": "memory_recall",
            "reasoning": "Test",
            "max_retries": 1
        }
        
        # Mock retriever
        mock_retriever.search.return_value = []
        
        # Mock executor
        mock_executor.execute.return_value = "Not enough data"
        
        # Mock critic returns NOT_ENOUGH_EVIDENCE
        mock_critic.evaluate.return_value = CriticVerdict.NOT_ENOUGH_EVIDENCE
        
        # Mock trigger
        mock_trigger.generate.return_value = [
            {"type": "data_request", "content": "Please add more memories"}
        ]
        
        # Mock recommender
        mock_recommender.suggest_captures.return_value = []
        
        from lifelens.orchestrator import run_agentic_flow
        
        result = run_agentic_flow(
            user_query="Test query",
            patient_id=sample_patient_id,
            qdrant_client=mock_qdrant_client
        )
        
        # Trigger should be called
        mock_trigger.generate.assert_called_once()
        
        # Should have triggers in result
        assert len(result["triggers"]) == 1
    
    @patch('lifelens.orchestrator.recommender')
    @patch('lifelens.orchestrator.trigger')
    @patch('lifelens.orchestrator.critic')
    @patch('lifelens.orchestrator.executor')
    @patch('lifelens.orchestrator.retriever')
    @patch('lifelens.orchestrator.planner')
    def test_session_id_generation(
        self, mock_planner, mock_retriever, mock_executor,
        mock_critic, mock_trigger, mock_recommender,
        mock_qdrant_client, sample_patient_id
    ):
        """Test that unique session IDs are generated."""
        # Mock all agents
        mock_planner.plan.return_value = {
            "needs_retrieval": True,
            "intent": "memory_recall",
            "max_retries": 1
        }
        mock_retriever.search.return_value = []
        mock_executor.execute.return_value = "Answer"
        mock_critic.evaluate.return_value = CriticVerdict.OK
        mock_trigger.generate.return_value = []
        mock_recommender.suggest_captures.return_value = []
        
        from lifelens.orchestrator import run_agentic_flow
        
        # Run twice
        result1 = run_agentic_flow("Query 1", sample_patient_id, mock_qdrant_client)
        result2 = run_agentic_flow("Query 2", sample_patient_id, mock_qdrant_client)
        
        # Both should have session_id
        assert "session_id" in result1
        assert "session_id" in result2
        
        # Session IDs should be different
        assert result1["session_id"] != result2["session_id"]
