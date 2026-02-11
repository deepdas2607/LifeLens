"""
Quick Mood Risk Calculator - Demonstrates the risk scoring without API calls
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from datetime import datetime, timedelta
import numpy as np

# Import the actual functions
from lifelens.agents.mood_agent import _convert_mood_to_score, _calculate_mood_slope, _detect_negative_streak

def simulate_risk_calculation():
    """Simulates the risk calculation for demo scenario."""
    
    print("\n" + "="*70)
    print("  MOOD RISK CALCULATION SIMULATOR")
    print("="*70 + "\n")
    
    # Simulate 5-day declining mood trend
    print("📊 Simulated 5-Day Mood Data:")
    print("-" * 70)
    
    moods = [
        ("Day 5 (oldest)", "anxious", -0.4),
        ("Day 4", "frustrated", -0.5),
        ("Day 3", "sad", -0.6),
        ("Day 2", "angry", -0.7),
        ("Day 1 (recent)", "depressed", -0.9)
    ]
    
    for day, mood, score in moods:
        print(f"  {day:20s} {mood:12s} → {score:+.1f}")
    
    # Create mood scores with timestamps
    base_time = datetime.utcnow()
    mood_scores = []
    scores_only = []
    
    for i, (_, mood, score) in enumerate(moods):
        ts = base_time - timedelta(days=5-i)
        mood_scores.append((ts, score))
        scores_only.append(score)
    
    # Calculate signals
    print("\n📈 Signal Calculations:")
    print("-" * 70)
    
    # 1. Mood Slope
    slope = _calculate_mood_slope(mood_scores)
    normalized_trend = max(0, min(1, -slope * 7))  # Updated multiplier
    print(f"  Mood Slope: {slope:.4f} per day")
    print(f"  Normalized Trend: {normalized_trend:.4f}")
    
    # 2. Negative Streak
    streak = _detect_negative_streak(mood_scores)
    streak_factor = min(1.0, streak / 5.0)
    print(f"  Negative Streak: {streak} days")
    print(f"  Streak Factor: {streak_factor:.4f}")
    
    # 3. Negativity Level
    recent_avg = np.mean(scores_only)
    negativity_factor = max(0, min(1, (-recent_avg - 0.3) / 0.6))
    print(f"  Recent Avg Mood: {recent_avg:.2f}")
    print(f"  Negativity Factor: {negativity_factor:.4f}")
    
    # 4. Variance (simulated - no baseline)
    variance_spike = 1.0  # No spike in demo
    anomaly_score = min(1.0, max(0, variance_spike - 1.0) / 1.0)
    print(f"  Variance Spike: {variance_spike:.2f}x")
    print(f"  Anomaly Score: {anomaly_score:.4f}")
    
    # 5. Inactivity
    inactivity = False
    inactivity_flag = 1.0 if inactivity else 0.0
    print(f"  Inactivity: {inactivity}")
    print(f"  Inactivity Flag: {inactivity_flag:.4f}")
    
    # Calculate risk score
    print("\n⚠️ Risk Score Calculation:")
    print("-" * 70)
    
    risk_components = [
        ("Trend (35%)", 0.35, normalized_trend),
        ("Streak (35%)", 0.35, streak_factor),
        ("Negativity (20%)", 0.2, negativity_factor),
        ("Anomaly (5%)", 0.05, anomaly_score),
        ("Inactivity (5%)", 0.05, inactivity_flag)
    ]
    
    total_risk = 0
    for name, weight, value in risk_components:
        contribution = weight * value
        total_risk += contribution
        print(f"  {name:25s}: {weight:.1%} × {value:.4f} = {contribution:.4f}")
    
    print("-" * 70)
    print(f"  TOTAL RISK SCORE: {total_risk:.2%}")
    print("-" * 70)
    
    # Determine if alert would trigger
    print("\n🚨 Alert Decision:")
    print("-" * 70)
    
    if total_risk >= 0.7:
        print(f"  ✓ Risk {total_risk:.0%} ≥ 70% → Send to Critic for ALERT review")
        critic_verdict = "ALERT (expected)"
    elif total_risk >= 0.5:
        print(f"  ⚠ Risk {total_risk:.0%} ≥ 50% → Send to Critic for MONITOR")
        critic_verdict = "MONITOR"
    else:
        print(f"  ○ Risk {total_risk:.0%} < 50% → IGNORE (no alert)")
        critic_verdict = "IGNORE"
    
    print(f"  Critic Verdict: {critic_verdict}")
    
    # Summary
    print("\n" + "="*70)
    if total_risk >= 0.7:
        print("  ✅ Risk score meets alert threshold!")
        print("     - Clear 5-day declining trend")
        print("     - Consistent negative streak")
        print("     - Deep negativity level (-0.62 avg)")
        print("     - Would trigger Critic review → ntfy notification")
    elif total_risk >= 0.5:
        print("  ⚠️ Risk score in monitoring range")
        print("     - Would log but not alert caretaker")
    else:
        print("  ℹ️ Risk score below threshold")
        print("     - No action needed")
    print("="*70 + "\n")
    
    return total_risk >= 0.7


if __name__ == "__main__":
    success = simulate_risk_calculation()
    sys.exit(0 if success else 1)
