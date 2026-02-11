"""
Medication Adherence Analytics Agent

Runs nightly to analyze medication adherence patterns.
Calculates missed rates, streaks, late-taking patterns, and risk zones.
Writes insights to Qdrant for tracking and alerting.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import uuid
from qdrant_client import QdrantClient
from qdrant_client.http import models
import google.generativeai as genai
from lifelens.config import GEMINI_API_KEY, GROQ_API_KEY
from groq import Groq

logger = logging.getLogger(__name__)
genai.configure(api_key=GEMINI_API_KEY)


def analyze_adherence(client: QdrantClient, patient_id: str, 
                     days_lookback: int = 7) -> Dict:
    """
    Performs comprehensive adherence analysis for a patient.
    
    Args:
        client: Qdrant client instance
        patient_id: Patient identifier
        days_lookback: Number of days to analyze (default: 7)
        
    Returns:
        Dictionary containing adherence metrics and insights
    """
    logger.info(f"Analyzing adherence for patient {patient_id} over {days_lookback} days")
    
    # Get medication events for the period
    events = _get_medication_events(client, patient_id, days_lookback)
    
    # Calculate metrics
    metrics = _calculate_metrics(events)
    
    # Detect streaks
    streaks = _detect_streaks(events)
    
    # Analyze timing patterns
    timing_analysis = _analyze_timing_patterns(events)
    
    # Cluster side effects / notes
    side_effects = _cluster_side_effects(client, events)
    
    # Create comprehensive summary
    summary = _generate_summary(patient_id, metrics, streaks, timing_analysis, 
                                side_effects)
    
    # Store insights
    insight_id = _store_insights(client, patient_id, metrics, streaks, 
                                 timing_analysis, side_effects, summary)
    
    return {
        "patient_id": patient_id,
        "insight_id": insight_id,
        "period_days": days_lookback,
        "metrics": metrics,
        "streaks": streaks,
        "timing_analysis": timing_analysis,
        "side_effects": side_effects,
        "summary": summary,
        "timestamp": datetime.now().isoformat()
    }


def _get_medication_events(client: QdrantClient, patient_id: str, 
                          days_lookback: int) -> List[Dict]:
    """
    Retrieves medication events for the specified period.
    """
    try:
        start_date = datetime.now() - timedelta(days=days_lookback)
        start_timestamp = start_date.timestamp()
        
        results = client.scroll(
            collection_name="medication_events",
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="patient_id",
                        match=models.MatchValue(value=patient_id)
                    ),
                    models.FieldCondition(
                        key="timestamp",
                        range=models.Range(
                            gte=start_timestamp
                        )
                    )
                ]
            ),
            limit=1000
        )[0]
        
        events = [point.payload for point in results]
        logger.info(f"Retrieved {len(events)} medication events")
        return events
        
    except Exception as e:
        logger.error(f"Error retrieving medication events: {e}")
        return []


def _calculate_metrics(events: List[Dict]) -> Dict:
    """
    Calculates adherence metrics from events.
    """
    total_events = len(events)
    if total_events == 0:
        return {
            "total_doses": 0,
            "taken": 0,
            "missed": 0,
            "skipped": 0,
            "adherence_rate": 0.0,
            "missed_rate": 0.0
        }
    
    taken = len([e for e in events if e.get("status") == "taken"])
    missed = len([e for e in events if e.get("status") == "missed"])
    skipped = len([e for e in events if e.get("status") == "skipped"])
    
    adherence_rate = taken / total_events if total_events > 0 else 0.0
    missed_rate = missed / total_events if total_events > 0 else 0.0
    
    return {
        "total_doses": total_events,
        "taken": taken,
        "missed": missed,
        "skipped": skipped,
        "adherence_rate": round(adherence_rate, 2),
        "missed_rate": round(missed_rate, 2)
    }


def _detect_streaks(events: List[Dict]) -> Dict:
    """
    Detects consecutive missed doses (streaks).
    """
    # Sort events by timestamp
    sorted_events = sorted(events, key=lambda x: x.get("timestamp", ""))
    
    current_streak = 0
    max_streak = 0
    
    for event in sorted_events:
        if event.get("status") in ["missed", "skipped"]:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0
    
    return {
        "current_missed_streak": current_streak,
        "max_missed_streak": max_streak,
        "has_active_streak": current_streak > 0
    }


def _analyze_timing_patterns(events: List[Dict]) -> Dict:
    """
    Analyzes late-taking patterns and time-of-day risks.
    """
    late_doses = []
    time_of_day_misses = {"morning": 0, "afternoon": 0, "evening": 0, "night": 0}
    
    for event in events:
        # Check if dose was taken late
        scheduled_time_str = event.get("scheduled_time")
        actual_time_str = event.get("timestamp")
        
        if scheduled_time_str and actual_time_str and event.get("status") == "taken":
            try:
                # Parse times
                scheduled = datetime.strptime(scheduled_time_str, "%H:%M").time()
                actual = datetime.fromisoformat(actual_time_str).time()
                
                # Calculate delay in minutes
                scheduled_minutes = scheduled.hour * 60 + scheduled.minute
                actual_minutes = actual.hour * 60 + actual.minute
                delay = actual_minutes - scheduled_minutes
                
                if delay > 30:  # More than 30 minutes late
                    late_doses.append({
                        "medication_id": event.get("medication_id"),
                        "scheduled": scheduled_time_str,
                        "actual": actual.strftime("%H:%M"),
                        "delay_minutes": delay
                    })
            except:
                pass
        
        # Count misses by time of day
        if event.get("status") in ["missed", "skipped"] and scheduled_time_str:
            try:
                hour = int(scheduled_time_str.split(":")[0])
                if 5 <= hour < 12:
                    time_of_day_misses["morning"] += 1
                elif 12 <= hour < 17:
                    time_of_day_misses["afternoon"] += 1
                elif 17 <= hour < 21:
                    time_of_day_misses["evening"] += 1
                else:
                    time_of_day_misses["night"] += 1
            except:
                pass
    
    # Find risk zones
    if time_of_day_misses:
        risk_zone = max(time_of_day_misses, key=time_of_day_misses.get)
    else:
        risk_zone = None
    
    return {
        "late_doses": len(late_doses),
        "time_of_day_misses": time_of_day_misses,
        "risk_zone": risk_zone,
        "late_dose_details": late_doses[:5]  # Top 5
    }


def _cluster_side_effects(client: QdrantClient, events: List[Dict]) -> List[str]:
    """
    Clusters and identifies common side effects from notes.
    """
    notes_with_content = [e.get("note", "") for e in events if e.get("note")]
    
    if not notes_with_content:
        return []
    
    # Use LLM to extract common themes
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
        
        combined_notes = "\n".join(notes_with_content[:20])  # First 20 notes
        
        prompt = f"""Analyze these medication notes and identify common side effects or concerns:

{combined_notes}

List the top 3-5 common themes or side effects mentioned. Be concise."""
        
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200
        )
        
        result = response.choices[0].message.content.strip()
        # Parse into list
        themes = [line.strip("- •").strip() for line in result.split("\n") if line.strip()]
        return themes[:5]
        
    except Exception as e:
        logger.error(f"Error clustering side effects: {e}")
        return []


def _generate_summary(patient_id: str, metrics: Dict, streaks: Dict, 
                     timing: Dict, side_effects: List[str]) -> str:
    """
    Generates a human-readable summary of adherence analysis.
    """
    summary_parts = []
    
    # Adherence rate
    adherence_rate = metrics.get("adherence_rate", 0)
    if adherence_rate >= 0.9:
        summary_parts.append(f"Excellent adherence ({adherence_rate*100:.0f}%)")
    elif adherence_rate >= 0.7:
        summary_parts.append(f"Good adherence ({adherence_rate*100:.0f}%)")
    elif adherence_rate >= 0.5:
        summary_parts.append(f"Moderate adherence ({adherence_rate*100:.0f}%)")
    else:
        summary_parts.append(f"Poor adherence ({adherence_rate*100:.0f}%)")
    
    # Missed streak
    if streaks.get("current_missed_streak", 0) > 0:
        summary_parts.append(f"{streaks['current_missed_streak']} consecutive doses missed")
    
    # Time of day risk
    risk_zone = timing.get("risk_zone")
    if risk_zone:
        summary_parts.append(f"Most misses in {risk_zone}")
    
    # Late doses
    late_count = timing.get("late_doses", 0)
    if late_count > 0:
        summary_parts.append(f"{late_count} doses taken late")
    
    # Side effects
    if side_effects:
        summary_parts.append(f"Reported: {', '.join(side_effects[:2])}")
    
    return ". ".join(summary_parts) + "."


def _store_insights(client: QdrantClient, patient_id: str, metrics: Dict, 
                   streaks: Dict, timing: Dict, side_effects: List[str], 
                   summary: str) -> str:
    """
    Stores adherence insights to Qdrant.
    """
    insight_id = str(uuid.uuid4())
    
    try:
        # Determine verdict
        missed_rate = metrics.get("missed_rate", 0)
        current_streak = streaks.get("current_missed_streak", 0)
        
        if current_streak >= 3 or missed_rate > 0.5:
            verdict = "ALERT"
        elif current_streak >= 2 or missed_rate > 0.3:
            verdict = "MONITOR"
        else:
            verdict = "IGNORE"
        
        now = datetime.now()
        payload = {
            "patient_id": patient_id,
            "insight_id": insight_id,
            "timestamp": now.timestamp(),
            "timestamp_iso": now.isoformat(),
            "metrics": metrics,
            "streaks": streaks,
            "timing_analysis": timing,
            "side_effects": side_effects,
            "summary": summary,
            "verdict": verdict,
            "missed_rate": missed_rate,
            "streak": current_streak
        }
        
        # Store in medication_insights
        client.upsert(
            collection_name="medication_insights",
            points=[
                models.PointStruct(
                    id=insight_id,
                    vector=[0.0],  # Minimal vector
                    payload=payload
                )
            ]
        )
        
        logger.info(f"Stored adherence insight {insight_id} with verdict: {verdict}")
        return insight_id
        
    except Exception as e:
        logger.error(f"Error storing insights: {e}")
        return insight_id


def run_nightly_analysis(client: QdrantClient, patient_ids: List[str]) -> Dict:
    """
    Runs nightly adherence analysis for all patients.
    
    Args:
        client: Qdrant client instance
        patient_ids: List of patient identifiers
        
    Returns:
        Summary of analysis results
    """
    results = {
        "analyzed": 0,
        "alerts": 0,
        "monitors": 0,
        "timestamp": datetime.now().isoformat()
    }
    
    for patient_id in patient_ids:
        try:
            analysis = analyze_adherence(client, patient_id, days_lookback=7)
            results["analyzed"] += 1
            
            verdict = analysis.get("metrics", {}).get("verdict", "IGNORE")
            if verdict == "ALERT":
                results["alerts"] += 1
            elif verdict == "MONITOR":
                results["monitors"] += 1
                
        except Exception as e:
            logger.error(f"Error analyzing patient {patient_id}: {e}")
    
    logger.info(f"Nightly analysis complete: {results}")
    return results
