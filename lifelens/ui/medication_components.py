"""
Medication UI Components

Streamlit components for medication tracking interface.
"""

import streamlit as st
from typing import Dict, List, Optional
from datetime import datetime, time
from qdrant_client import QdrantClient


def render_patient_medication_list(client: QdrantClient, patient_id: str):
    """
    Renders today's medication list for patients with action buttons.
    
    Args:
        client: Qdrant client instance
        patient_id: Patient identifier
    """
    from lifelens.agents.medication_scheduler import get_todays_medications
    from lifelens.utils.medication_utils import record_medication_event, format_time_for_display
    
    st.subheader("💊 Today's Medications")
    
    # Get today's schedule
    todays_meds = get_todays_medications(client, patient_id)
    
    if not todays_meds:
        st.info("No medications scheduled for today.")
        return
    
    # Group by status
    pending_meds = [m for m in todays_meds if m["status"] == "pending" and not m["is_overdue"]]
    overdue_meds = [m for m in todays_meds if m["status"] == "pending" and m["is_overdue"]]
    completed_meds = [m for m in todays_meds if m["status"] in ["taken", "skipped"]]
    
    # Display overdue medications first
    if overdue_meds:
        st.error(f"⚠️ {len(overdue_meds)} dose(s) overdue!")
        for med in overdue_meds:
            _render_medication_card(client, patient_id, med, is_overdue=True)
    
    # Display upcoming/pending medications
    if pending_meds:
        st.markdown("### Upcoming Doses")
        for med in pending_meds:
            _render_medication_card(client, patient_id, med, is_overdue=False)
    
    # Display completed medications (collapsible)
    if completed_meds:
        with st.expander(f"✅ Completed Today ({len(completed_meds)})"):
            for med in completed_meds:
                _render_completed_medication(med)


def _render_medication_card(client: QdrantClient, patient_id: str, 
                           med: Dict, is_overdue: bool):
    """
    Renders an individual medication card with action buttons.
    """
    from lifelens.utils.medication_utils import record_medication_event, format_time_for_display
    
    # Create container with border
    container = st.container()
    
    with container:
        col1, col2 = st.columns([3, 2])
        
        with col1:
            # Medication name and details
            st.markdown(f"### {med['medication_name']}")
            st.caption(f"**Dosage:** {med['dosage']}")
            st.caption(f"**Time:** {format_time_for_display(med['scheduled_time'])}")
            
            if med.get('notes'):
                st.caption(f"📝 {med['notes']}")
        
        with col2:
            # Action buttons
            button_key = f"med_{med['medication_id']}_{med['scheduled_time']}".replace(":", "_")
            
            # Initialize skip mode in session state
            skip_key = f"skip_mode_{button_key}"
            if skip_key not in st.session_state:
                st.session_state[skip_key] = False
            
            # If not in skip mode, show main buttons
            if not st.session_state[skip_key]:
                col_btn1, col_btn2 = st.columns(2)
                
                with col_btn1:
                    if st.button("✅ Taken", key=f"taken_{button_key}", 
                                type="primary", width="stretch"):
                        event_data = {
                            "patient_id": patient_id,
                            "medication_id": med['medication_id'],
                            "status": "taken",
                            "reported_by": "patient",
                            "dose_time": med['scheduled_time'],
                            "dose_date": datetime.now().date().isoformat()
                        }
                        
                        if record_medication_event(client, event_data):
                            st.success(f"✅ Marked as taken!")
                            st.rerun()
                        else:
                            st.error("Failed to record. Please try again.")
                
                with col_btn2:
                    if st.button("⏭️ Skip", key=f"skip_btn_{button_key}", 
                                width="stretch"):
                        st.session_state[skip_key] = True
                        st.rerun()
            
            # If in skip mode, show reason input
            else:
                reason = st.text_input("Why are you skipping this dose?", 
                                      key=f"reason_{button_key}",
                                      placeholder="e.g., Already took it, Side effects")
                
                col_confirm, col_cancel = st.columns(2)
                
                with col_confirm:
                    if st.button("✓ Confirm", key=f"confirm_{button_key}", 
                                type="primary", width="stretch"):
                        event_data = {
                            "patient_id": patient_id,
                            "medication_id": med['medication_id'],
                            "status": "skipped",
                            "reported_by": "patient",
                            "note": reason if reason else "No reason provided",
                            "dose_time": med['scheduled_time'],
                            "dose_date": datetime.now().date().isoformat()
                        }
                        
                        if record_medication_event(client, event_data):
                            st.success("⏭️ Marked as skipped")
                            st.session_state[skip_key] = False
                            st.rerun()
                        else:
                            st.error("Failed to record. Please try again.")
                
                with col_cancel:
                    if st.button("✕ Cancel", key=f"cancel_{button_key}", 
                                width="stretch"):
                        st.session_state[skip_key] = False
                        st.rerun()
        
        st.markdown("---")


def _render_completed_medication(med: Dict):
    """
    Renders a completed medication (read-only).
    """
    from lifelens.utils.medication_utils import format_time_for_display
    
    status_icon = "✅" if med["status"] == "taken" else "⏭️"
    st.markdown(f"{status_icon} **{med['medication_name']}** {med['dosage']} - {format_time_for_display(med['scheduled_time'])}")


def render_caretaker_medication_manager(client: QdrantClient, patient_id: str):
    """
    Renders medication management interface for caretakers.
    
    Args:
        client: Qdrant client instance
        patient_id: Patient identifier
    """
    st.subheader("💊 Medication Management")
    
    tabs = st.tabs(["📋 Active Medications", "➕ Add Medication", "📊 Adherence Analytics"])
    
    with tabs[0]:
        _render_active_medications_tab(client, patient_id)
    
    with tabs[1]:
        _render_add_medication_tab(client, patient_id)
    
    with tabs[2]:
        _render_adherence_analytics_tab(client, patient_id)


def _render_active_medications_tab(client: QdrantClient, patient_id: str):
    """
    Displays list of active medications with edit/delete options.
    """
    from lifelens.utils.medication_utils import get_all_patient_medications
    from lifelens.agents.medication_planner import deactivate_medication
    
    st.markdown("### Active Medications")
    
    medications = get_all_patient_medications(client, patient_id, active_only=True)
    
    if not medications:
        st.info("No active medications. Add one using the 'Add Medication' tab.")
        return
    
    for med in medications:
        with st.expander(f"💊 {med['name']} - {med['dosage']}"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**Schedule:** {', '.join(med['schedule'])}")
                st.write(f"**Start Date:** {med['start_date']}")
                if med.get('end_date'):
                    st.write(f"**End Date:** {med['end_date']}")
                if med.get('notes'):
                    st.write(f"**Notes:** {med['notes']}")
                st.caption(f"Medication ID: {med['medication_id']}")
            
            with col2:
                if st.button("🗑️ Deactivate", key=f"deactivate_{med['medication_id']}"):
                    if deactivate_medication(client, med['medication_id'], patient_id):
                        st.success(f"Deactivated {med['name']}")
                        st.rerun()
                    else:
                        st.error("Failed to deactivate medication")


def _render_add_medication_tab(client: QdrantClient, patient_id: str):
    """
    Renders form to add new medication.
    """
    from lifelens.agents.medication_planner import plan_medication_schedule
    from lifelens.auth.session import get_current_user
    
    st.markdown("### Add New Medication")
    
    with st.form("add_medication_form"):
        med_name = st.text_input("Medication Name *", placeholder="e.g., Donepezil")
        dosage = st.text_input("Dosage *", placeholder="e.g., 10mg")
        
        st.markdown("**Daily Schedule (Times) ***")
        st.caption("Enter times in 24-hour format (HH:MM)")
        
        # Allow multiple time inputs
        num_doses = st.number_input("Number of daily doses", min_value=1, max_value=6, value=1)
        
        schedule = []
        cols = st.columns(min(num_doses, 3))
        for i in range(num_doses):
            with cols[i % 3]:
                time_input = st.time_input(f"Dose {i+1}", 
                                          value=time(9, 0) if i == 0 else time(21, 0),
                                          key=f"time_{i}")
                schedule.append(time_input.strftime("%H:%M"))
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date *", value=datetime.now())
        with col2:
            has_end_date = st.checkbox("Set End Date")
            if has_end_date:
                end_date = st.date_input("End Date", value=datetime.now())
            else:
                end_date = None
        
        notes = st.text_area("Notes", placeholder="e.g., Take after food")
        
        submitted = st.form_submit_button("➕ Add Medication", type="primary")
        
        if submitted:
            if not med_name or not dosage:
                st.error("Please fill in all required fields")
            else:
                user = get_current_user()
                
                medication_data = {
                    "patient_id": patient_id,
                    "name": med_name,
                    "dosage": dosage,
                    "schedule": schedule,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat() if end_date else None,
                    "notes": notes,
                    "prescribed_by": user.get("username", "caretaker")
                }
                
                result = plan_medication_schedule(medication_data, client)
                
                if result["success"]:
                    st.success(f"✅ Medication added successfully! ID: {result['medication_id']}")
                    st.info(result['plan']['reminder_plan'])
                    st.rerun()
                else:
                    st.error(f"Failed to add medication: {result['error']}")


def _render_adherence_analytics_tab(client: QdrantClient, patient_id: str):
    """
    Displays adherence analytics and insights.
    """
    from lifelens.utils.medication_utils import (
        get_adherence_calendar, 
        calculate_adherence_rate,
        get_medication_insights_for_patient,
        get_medication_history
    )
    
    st.markdown("### Adherence Analytics")
    
    # Time period selector
    period = st.selectbox("Time Period", ["7 Days", "14 Days", "30 Days"], index=0)
    days = int(period.split()[0])
    
    # Calculate adherence rate
    adherence_rate = calculate_adherence_rate(client, patient_id, days=days)
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Adherence Rate", f"{adherence_rate*100:.1f}%")
    
    with col2:
        history = get_medication_history(client, patient_id, days=days)
        missed_count = len([e for e in history if e.get("status") == "missed"])
        st.metric("Missed Doses", missed_count)
    
    with col3:
        taken_count = len([e for e in history if e.get("status") == "taken"])
        st.metric("Doses Taken", taken_count)
    
    st.markdown("---")
    
    # Get latest insights
    insights = get_medication_insights_for_patient(client, patient_id)
    
    if insights:
        st.markdown("### 📊 Latest Insights")
        
        verdict = insights.get("verdict", "IGNORE")
        if verdict == "ALERT":
            st.error(f"⚠️ **Alert:** {insights.get('summary', 'Action needed')}")
        elif verdict == "MONITOR":
            st.warning(f"👀 **Monitor:** {insights.get('summary', 'Watch closely')}")
        else:
            st.success(f"✅ **Good:** {insights.get('summary', 'No concerns')}")
        
        # Show metrics
        metrics = insights.get("metrics", {})
        if metrics:
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Total Doses Tracked:** {metrics.get('total_doses', 0)}")
                st.write(f"**Taken:** {metrics.get('taken', 0)}")
            with col2:
                st.write(f"**Missed:** {metrics.get('missed', 0)}")
                st.write(f"**Skipped:** {metrics.get('skipped', 0)}")
        
        # Show streaks
        streaks = insights.get("streaks", {})
        if streaks.get("current_missed_streak", 0) > 0:
            st.warning(f"⚠️ Current missed streak: {streaks['current_missed_streak']} doses")
    
    else:
        st.info("No analytics available yet. Analytics are generated nightly.")
    
    # Calendar view
    st.markdown("### 📅 Adherence Calendar")
    calendar_data = get_adherence_calendar(client, patient_id, days=days)
    
    if calendar_data:
        import pandas as pd
        
        # Convert to dataframe for display
        df_data = []
        for date, stats in calendar_data.items():
            df_data.append({
                "Date": date,
                "Total": stats["total"],
                "Taken": stats.get("taken", 0),
                "Missed": stats.get("missed", 0),
                "Skipped": stats.get("skipped", 0),
                "Rate": f"{(stats.get('taken', 0) / stats['total'] * 100):.0f}%" if stats['total'] > 0 else "0%"
            })
        
        df = pd.DataFrame(df_data)
        df = df.sort_values("Date", ascending=False)
        
        st.dataframe(df, width="stretch", hide_index=True)
    else:
        st.info("No medication history available for the selected period.")


def show_medication_reminder_banner(dose_info: Dict):
    """
    Displays a prominent reminder banner for upcoming medication.
    
    Args:
        dose_info: Dictionary containing dose details
    """
    from lifelens.utils.medication_utils import format_time_for_display
    
    st.info(f"""
    ### 💊 Medication Reminder
    
    **{dose_info['medication_name']}** {dose_info['dosage']}
    
    Scheduled Time: {format_time_for_display(dose_info['scheduled_time'])}
    
    {dose_info.get('notes', '')}
    """)


def render_medication_overview_widget(client: QdrantClient, patient_id: str):
    """
    Renders a compact medication overview widget for dashboards.
    
    Args:
        client: Qdrant client instance
        patient_id: Patient identifier
    """
    from lifelens.agents.medication_scheduler import get_todays_medications
    from lifelens.utils.medication_utils import calculate_adherence_rate
    
    st.markdown("### 💊 Medications")
    
    todays_meds = get_todays_medications(client, patient_id)
    
    if not todays_meds:
        st.info("No medications scheduled")
        return
    
    pending = len([m for m in todays_meds if m["status"] == "pending"])
    completed = len([m for m in todays_meds if m["status"] in ["taken", "skipped"]])
    overdue = len([m for m in todays_meds if m["is_overdue"] and m["status"] == "pending"])
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Today's Doses", len(todays_meds))
    with col2:
        st.metric("Completed", completed)
    with col3:
        if overdue > 0:
            st.metric("Overdue", overdue, delta=overdue, delta_color="inverse")
        else:
            st.metric("Overdue", 0)
    
    # 7-day adherence
    adherence = calculate_adherence_rate(client, patient_id, days=7)
    st.progress(adherence, text=f"7-Day Adherence: {adherence*100:.0f}%")
