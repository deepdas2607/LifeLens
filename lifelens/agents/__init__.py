"""
LifeLens Multi-Agent System

This package contains autonomous agents that coordinate to provide
intelligent memory retrieval and proactive assistance.
"""

# Core Query Agents
from .planner import plan, replan
from .retriever import search
from .executor import execute
from .critic import evaluate
from .trigger import generate as generate_triggers
from .recommender import suggest_captures, identify_gaps

# Ingestion Agents
from .ingestion_planner import plan_ingestion_strategy, should_trigger_follow_up
from .quality_critic import critique_caption_quality, should_retry_processing, validate_emotion_annotation

# Dashboard & Analytics Agents
from .analytics_agent import generate_dashboard_insights

# Family Portal Agents
from .summary_agent import generate_family_summary

# Maintenance Agents
from .hygiene_agent import scan_for_hygiene_issues

# Learning Agent
from .learning_agent import (
    log_agent_decision,
    log_trigger_outcome,
    log_caregiver_correction,
    get_learning_insights
)

# Medication Agents
from .medication_planner import (
    validate_medication,
    plan_medication_schedule,
    update_medication,
    deactivate_medication
)
from .medication_scheduler import (
    get_active_medications,
    get_upcoming_doses,
    get_todays_medications,
    check_missed_doses
)
from .medication_reminder import (
    send_medication_reminder,
    send_batch_reminders,
    send_missed_dose_alert
)
from .medication_adherence import (
    analyze_adherence,
    run_nightly_analysis
)
from .medication_critic import (
    evaluate_alert_need,
    generate_alert_decision,
    evaluate_and_alert
)

__all__ = [
    # Core agents
    'plan',
    'replan',
    'search',
    'execute',
    'evaluate',
    'generate_triggers',
    'suggest_captures',
    'identify_gaps',
    # Ingestion agents
    'plan_ingestion_strategy',
    'should_trigger_follow_up',
    'critique_caption_quality',
    'should_retry_processing',
    'validate_emotion_annotation',
    # Analytics
    'generate_dashboard_insights',
    # Family portal
    'generate_family_summary',
    # Maintenance
    'scan_for_hygiene_issues',
    # Learning
    'log_agent_decision',
    'log_trigger_outcome',
    'log_caregiver_correction',
    'get_learning_insights',
    # Medication agents
    'validate_medication',
    'plan_medication_schedule',
    'update_medication',
    'deactivate_medication',
    'get_active_medications',
    'get_upcoming_doses',
    'get_todays_medications',
    'check_missed_doses',
    'send_medication_reminder',
    'send_batch_reminders',
    'send_missed_dose_alert',
    'analyze_adherence',
    'run_nightly_analysis',
    'evaluate_alert_need',
    'generate_alert_decision',
    'evaluate_and_alert'
]
