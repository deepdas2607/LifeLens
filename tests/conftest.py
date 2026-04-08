"""
Pytest configuration and shared fixtures for LifeLens tests.
"""

import pytest
import uuid
from unittest.mock import Mock, MagicMock
from qdrant_client import QdrantClient
from qdrant_client.http import models


@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client for testing."""
    client = Mock()  # Don't use spec to allow any attributes
    
    # Mock upsert
    client.upsert.return_value = models.UpdateResult(
        operation_id=0,
        status=models.UpdateStatus.COMPLETED
    )
    
    # Mock scroll
    client.scroll.return_value = ([], None)
    
    # Mock search
    client.search.return_value = []
    
    # Mock query_points
    client.query_points.return_value = Mock(points=[])
    
    return client


@pytest.fixture
def sample_patient_id():
    """Sample patient ID for testing."""
    return "patient1"


@pytest.fixture
def sample_session_id():
    """Sample session ID for testing."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_memory():
    """Sample memory payload for testing."""
    return {
        "patient_id": "patient1",
        "type": "image",
        "content": "A photo of grandchildren visiting",
        "timestamp": 1707523200.0,
        "tags": ["family", "visit"],
        "sentiment": "happy"
    }


@pytest.fixture
def sample_plan():
    """Sample plan from Planner agent for testing."""
    return {
        "intent": "memory_recall",
        "needs_retrieval": True,
        "temporal_scope": "last_week",
        "entities": ["grandchildren"],
        "modalities": ["image"],
        "max_results": 10,
        "trigger_if_missing": False,
        "max_retries": 1,
        "reasoning": "User asking about recent family visits"
    }


@pytest.fixture
def mock_groq_client():
    """Mock Groq client for testing."""
    client = Mock()
    
    # Mock chat completion
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = '{"verdict": "OK"}'
    
    client.chat.completions.create.return_value = mock_response
    
    return client
