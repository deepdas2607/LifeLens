"""
Mood Intelligence Dashboard Component

Displays mood insights, risk scores, trends, and alerts for caretakers.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from typing import Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models
import logging

logger = logging.getLogger(__name__)


def render_mood_insights(qdrant_client: QdrantClient, patient_id: str):
    """
    Renders comprehensive mood intelligence dashboard section.
    
    Shows:
    - 7-day trend arrow
    - Risk score gauge
    - Negative streak length
    - Correlated visitors
    - Recent alerts
    - Critic verdicts
    """
    
    st.header("🧠 Mood Intelligence Insights")
    st.caption("Agent-driven longitudinal emotional monitoring")
    
    try:
        # Run mood analysis
        from lifelens.agents.mood_agent import calculate_risk_score, run_mood_analysis
        
        analysis = calculate_risk_score(patient_id, qdrant_client)
        
        if analysis.get("insufficient_data"):
            st.info("📊 Insufficient mood data for analysis. Upload audio memories with emotional content to enable mood tracking.")
            return
        
        # Main metrics row
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            risk_score = analysis["risk_score"]
            risk_color = "🔴" if risk_score >= 0.7 else "🟡" if risk_score >= 0.5 else "🟢"
            st.metric(
                label="Risk Score",
                value=f"{risk_score:.1%}",
                delta=None,
                help="Composite risk score: 0-49% Low, 50-69% Medium, 70%+ High"
            )
            st.markdown(f"**Status:** {risk_color}")
        
        with col2:
            signals = analysis["signals"]
            streak = signals.get("negative_streak", 0)
            streak_emoji = "⚠️" if streak >= 3 else "✅"
            st.metric(
                label="Negative Streak",
                value=f"{streak} days",
                delta=None,
                help="Consecutive days with negative mood"
            )
            st.markdown(f"**{streak_emoji}**")
        
        with col3:
            mood_slope = signals.get("mood_slope", 0)
            trend_arrow = "📈" if mood_slope > 0.1 else "📉" if mood_slope < -0.1 else "➡️"
            trend_text = "Improving" if mood_slope > 0 else "Declining" if mood_slope < 0 else "Stable"
            st.metric(
                label="7-Day Trend",
                value=trend_text,
                delta=f"{mood_slope:.3f}",
                delta_color="normal" if mood_slope >= 0 else "inverse",
                help="Linear regression slope of mood over past week"
            )
            st.markdown(f"**{trend_arrow}**")
        
        with col4:
            data_points = analysis.get("data_points", 0)
            st.metric(
                label="Data Points",
                value=data_points,
                help="Number of mood events in past 7 days"
            )
        
        st.markdown("---")
        
        # Detailed signals
        with st.expander("📊 Detailed Signals", expanded=False):
            sig_col1, sig_col2 = st.columns(2)
            
            with sig_col1:
                st.markdown("**Trend Analysis**")
                st.write(f"• Normalized Trend: {signals.get('normalized_trend', 0):.2f}")
                st.write(f"• Recent Avg Mood: {signals.get('recent_avg_mood', 0):.2f}")
                st.write(f"• Streak Factor: {signals.get('streak_factor', 0):.2f}")
            
            with sig_col2:
                st.markdown("**Anomaly Detection**")
                st.write(f"• Variance Spike: {signals.get('variance_spike', 0):.2f}x")
                st.write(f"• Anomaly Score: {signals.get('anomaly_score', 0):.2f}")
                st.write(f"• Inactivity: {'Yes' if signals.get('inactivity') else 'No'}")
        
        # Visitor correlations
        visitor_corr = analysis.get("visitor_correlations", {})
        if visitor_corr:
            st.subheader("👥 Visitor-Mood Correlations")
            
            visitor_df = pd.DataFrame([
                {
                    "Person": name,
                    "Avg Mood": data["avg_mood"],
                    "Interactions": data["count"],
                    "Trend": data["trend"]
                }
                for name, data in visitor_corr.items()
            ])
            
            # Sort by avg mood
            visitor_df = visitor_df.sort_values("Avg Mood", ascending=False)
            
            # Color code
            def color_mood(val):
                if val > 0.3:
                    return "background-color: #d4edda"
                elif val < -0.3:
                    return "background-color: #f8d7da"
                return ""
            
            st.dataframe(
                visitor_df.style.applymap(color_mood, subset=["Avg Mood"]),
                width="stretch",
                hide_index=True
            )
        
        # Recent alerts
        st.subheader("🔔 Recent Mood Alerts")
        recent_alerts = _get_recent_alerts(qdrant_client, patient_id, days=14)
        
        if recent_alerts:
            alert_df = pd.DataFrame(recent_alerts)
            
            # Format dataframe
            display_cols = ["Timestamp", "Verdict", "Risk Score", "Summary", "Notified"]
            if all(col in alert_df.columns for col in display_cols):
                alert_display = alert_df[display_cols].copy()
                alert_display["Timestamp"] = pd.to_datetime(alert_display["Timestamp"]).dt.strftime("%Y-%m-%d %H:%M")
                alert_display["Risk Score"] = alert_display["Risk Score"].apply(lambda x: f"{x:.1%}")
                
                # Color code by verdict
                def color_verdict(row):
                    if row["Verdict"] == "ALERT":
                        return ["background-color: #f8d7da"] * len(row)
                    elif row["Verdict"] == "MONITOR":
                        return ["background-color: #fff3cd"] * len(row)
                    return [""] * len(row)
                
                st.dataframe(
                    alert_display.style.apply(color_verdict, axis=1),
                    width="stretch",
                    hide_index=True
                )
        else:
            st.info("No recent mood alerts in the past 14 days.")
        
        # Mood timeline visualization
        st.subheader("📈 Mood Timeline (30 Days)")
        mood_timeline = _get_mood_timeline(qdrant_client, patient_id, days=30)
        
        if mood_timeline:
            df = pd.DataFrame(mood_timeline)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            
            # Create plotly chart
            fig = go.Figure()
            
            # Add mood score line
            fig.add_trace(go.Scatter(
                x=df["timestamp"],
                y=df["mood_score"],
                mode="lines+markers",
                name="Mood Score",
                line=dict(color="#1f77b4", width=2),
                marker=dict(size=6),
                hovertemplate="<b>%{x}</b><br>Score: %{y:.2f}<br>Mood: %{text}<extra></extra>",
                text=df["mood"]
            ))
            
            # Add zero line
            fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
            
            # Add risk threshold line
            fig.add_hline(y=-0.4, line_dash="dot", line_color="orange", opacity=0.5,
                         annotation_text="Risk Threshold")
            
            fig.update_layout(
                title="Mood Score Over Time",
                xaxis_title="Date",
                yaxis_title="Mood Score",
                hovermode="x unified",
                height=400
            )
            
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("No mood timeline data available.")
        
        # Action buttons
        st.markdown("---")
        action_col1, action_col2, action_col3 = st.columns(3)
        
        with action_col1:
            if st.button("🔄 Run Manual Analysis", width="stretch"):
                with st.spinner("Running mood analysis..."):
                    result = run_mood_analysis(patient_id, qdrant_client, trigger_alerts=False)
                    if result:
                        st.success(f"Analysis complete. Risk: {result.get('risk_score', 0):.1%}")
                        st.rerun()
        
        with action_col2:
            if st.button("🔔 Test Alert System", width="stretch"):
                from lifelens.utils.ntfy_notifications import send_mood_alert
                with st.spinner("Sending test notification..."):
                    success = send_mood_alert(
                        patient_id=patient_id,
                        summary="This is a test notification from LifeLens Mood Intelligence",
                        risk_score=0.75
                    )
                    if success:
                        st.success("✅ Test notification sent! Check your ntfy subscription.")
                        st.info(f"Topic: lifelens-mood-test_patient_mood_demo")
                    else:
                        st.error("❌ Failed to send notification. Check logs.")
        
        with action_col3:
            if st.button("💾 Export Mood Data", width="stretch"):
                with st.spinner("Exporting mood data..."):
                    export_data = _export_mood_data(qdrant_client, patient_id)
                    if export_data:
                        import json
                        from datetime import datetime
                        
                        # JSON export
                        json_str = json.dumps(export_data, indent=2)
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.download_button(
                                label="📄 Download JSON",
                                data=json_str,
                                file_name=f"mood_data_{patient_id}_{timestamp}.json",
                                mime="application/json",
                                width="stretch"
                            )
        
                        with col2:
                            # CSV export
                            csv_data = _convert_to_csv(export_data)
                            st.download_button(
                                label="📊 Download CSV",
                                data=csv_data,
                                file_name=f"mood_data_{patient_id}_{timestamp}.csv",
                                mime="text/csv",
                                width="stretch"
                            )
                        
                        st.success(f"✅ Exported {export_data['total_events']} mood events")
                    else:
                        st.warning("No mood data available to export")
        
    except Exception as e:
        logger.error(f"Error rendering mood insights: {e}")
        st.error(f"Failed to load mood insights: {e}")


def _get_recent_alerts(qdrant_client: QdrantClient, patient_id: str, days: int = 14) -> list:
    """Retrieves recent mood alerts from Qdrant."""
    try:
        cutoff = datetime.now() - timedelta(days=days)
        
        results = qdrant_client.scroll(
            collection_name="mood_alerts",
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="patient_id",
                        match=models.MatchValue(value=patient_id)
                    ),
                    models.FieldCondition(
                        key="timestamp",
                        range=models.DatetimeRange(
                            gte=cutoff.isoformat()
                        )
                    )
                ]
            ),
            limit=20,
            order_by=models.OrderBy(
                key="timestamp",
                direction=models.Direction.DESC
            )
        )
        
        alerts = []
        for record in results[0]:
            payload = record.payload
            alerts.append({
                "Timestamp": payload.get("timestamp", ""),
                "Verdict": payload.get("critic_verdict", ""),
                "Risk Score": payload.get("risk_score", 0),
                "Summary": payload.get("summary", ""),
                "Notified": "Yes" if payload.get("notified") else "No"
            })
        
        return alerts
        
    except Exception as e:
        logger.error(f"Error retrieving alerts: {e}")
        return []


def _get_mood_timeline(qdrant_client: QdrantClient, patient_id: str, days: int = 30) -> list:
    """Retrieves mood timeline data for visualization."""
    try:
        cutoff = datetime.now() - timedelta(days=days)
        
        results = qdrant_client.scroll(
            collection_name="mood_events",
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="patient_id",
                        match=models.MatchValue(value=patient_id)
                    ),
                    models.FieldCondition(
                        key="timestamp",
                        range=models.DatetimeRange(
                            gte=cutoff.isoformat()
                        )
                    )
                ]
            ),
            limit=1000,
            order_by="timestamp"
        )
        
        timeline = []
        for record in results[0]:
            payload = record.payload
            timeline.append({
                "timestamp": payload.get("timestamp", ""),
                "mood": payload.get("mood", "neutral"),
                "mood_score": payload.get("mood_score", 0)
            })
        
        return timeline
        
    except Exception as e:
        logger.error(f"Error retrieving mood timeline: {e}")
        return []


def render_mood_feedback_form(qdrant_client: QdrantClient, alert_id: str, patient_id: str):
    """
    Renders a feedback form for caretakers to provide input on mood alerts.
    This feeds the learning loop.
    """
    st.subheader("📝 Mood Alert Feedback")
    st.caption(f"Provide feedback for alert {alert_id[:8]}...")
    
    action = st.selectbox(
        "Action Taken",
        ["acknowledged", "dismissed", "corrective_action"],
        format_func=lambda x: {
            "acknowledged": "✅ Acknowledged - Reached out to patient",
            "dismissed": "❌ Dismissed - False positive",
            "corrective_action": "🔧 Corrective Action - Intervened"
        }[x]
    )
    
    notes = st.text_area("Notes (optional)", placeholder="Additional context or actions taken...")
    
    if st.button("Submit Feedback"):
        from lifelens.agents.mood_agent import store_mood_feedback
        success = store_mood_feedback(qdrant_client, alert_id, patient_id, action, notes)
        
        if success:
            st.success("✅ Feedback recorded. This helps improve future alerts.")
        else:
            st.error("Failed to record feedback.")


def _export_mood_data(qdrant_client: QdrantClient, patient_id: str) -> dict:
    """
    Exports all mood data for a patient.
    
    Returns:
        Dictionary with mood events, alerts, and metadata
    """
    try:
        # Fetch mood events
        mood_events = qdrant_client.scroll(
            collection_name="mood_events",
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="patient_id",
                        match=models.MatchValue(value=patient_id)
                    )
                ]
            ),
            limit=1000,
            order_by="timestamp"
        )[0]
        
        # Fetch alerts
        alerts = qdrant_client.scroll(
            collection_name="mood_alerts",
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="patient_id",
                        match=models.MatchValue(value=patient_id)
                    )
                ]
            ),
            limit=1000,
            order_by="timestamp"
        )[0]
        
        # Format data
        events_data = []
        for record in mood_events:
            payload = record.payload
            events_data.append({
                "id": record.id,
                "timestamp": payload.get("timestamp", ""),
                "mood": payload.get("mood", ""),
                "mood_score": payload.get("mood_score", 0),
                "source": payload.get("source", ""),
                "people": payload.get("people", []),
                "location": payload.get("location", ""),
                "milestone": payload.get("milestone", False)
            })
        
        alerts_data = []
        for record in alerts:
            payload = record.payload
            alerts_data.append({
                "id": record.id,
                "timestamp": payload.get("timestamp", ""),
                "verdict": payload.get("verdict", ""),
                "risk_score": payload.get("risk_score", 0),
                "summary": payload.get("summary", ""),
                "notified": payload.get("notified", False)
            })
        
        return {
            "patient_id": patient_id,
            "export_timestamp": datetime.now().isoformat(),
            "total_events": len(events_data),
            "total_alerts": len(alerts_data),
            "mood_events": events_data,
            "alerts": alerts_data
        }
        
    except Exception as e:
        logger.error(f"Error exporting mood data: {e}")
        return None


def _convert_to_csv(export_data: dict) -> str:
    """
    Converts mood export data to CSV format.
    
    Returns:
        CSV string with mood events
    """
    import csv
    import io
    
    output = io.StringIO()
    
    # Write mood events CSV
    output.write(f"# LifeLens Mood Data Export\n")
    output.write(f"# Patient ID: {export_data['patient_id']}\n")
    output.write(f"# Export Date: {export_data['export_timestamp']}\n")
    output.write(f"# Total Events: {export_data['total_events']}\n")
    output.write(f"# Total Alerts: {export_data['total_alerts']}\n\n")
    
    # Mood events table
    output.write("=== MOOD EVENTS ===\n")
    writer = csv.DictWriter(
        output, 
        fieldnames=["timestamp", "mood", "mood_score", "source", "people", "location", "milestone"]
    )
    writer.writeheader()
    
    for event in export_data['mood_events']:
        writer.writerow({
            "timestamp": event['timestamp'],
            "mood": event['mood'],
            "mood_score": f"{event['mood_score']:.2f}",
            "source": event['source'],
            "people": "; ".join(event.get('people', [])),
            "location": event.get('location', ''),
            "milestone": event.get('milestone', False)
        })
    
    # Alerts table
    output.write("\n\n=== MOOD ALERTS ===\n")
    alert_writer = csv.DictWriter(
        output,
        fieldnames=["timestamp", "verdict", "risk_score", "summary", "notified"]
    )
    alert_writer.writeheader()
    
    for alert in export_data['alerts']:
        alert_writer.writerow({
            "timestamp": alert['timestamp'],
            "verdict": alert['verdict'],
            "risk_score": f"{alert['risk_score']*100:.1f}%",
            "summary": alert['summary'],
            "notified": alert['notified']
        })
    
    return output.getvalue()
