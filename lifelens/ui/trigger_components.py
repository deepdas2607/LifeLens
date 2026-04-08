"""
LifeLens Trigger UI Components

Streamlit UI components for displaying triggers and notifications.
"""

import streamlit as st
from typing import List, Dict


import time
from lifelens.utils.trigger_agent import generate_triggers
from lifelens.utils.trigger_storage import load_triggers, save_trigger, dismiss_trigger
from lifelens.utils.ntfy_notifications import send_trigger_notification, send_ntfy
from lifelens.config import TRIGGER_CHECK_INTERVAL_MINUTES, NTFY_TOPIC_URL


def handle_trigger_lifecycle(client, patient_id):
    """
    Shared logic to handle trigger generation, notification, and display.
    Used across Patient, Caretaker, and Family portals.
    """
    if not patient_id:
        return

    try:
        # 1. Load existing triggers
        existing_triggers = load_triggers(patient_id)
        
        # 2. Controls Section in Sidebar
        st.sidebar.markdown("---")
        st.sidebar.subheader("🤖 Trigger Controls (Demo)")
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            manual_refresh = st.button("🔄 Refresh", help="Force agent to analyze memories", key="trigger_refresh_btn")
        with col2:
            test_notif = st.button("🔔 Test Push", help="Send a test ntfy notification", key="trigger_test_notif_btn")

        if test_notif:
            success = send_ntfy("LifeLens Test", "If you see this, push notifications are working!", priority="high")
            if success:
                st.sidebar.success("Test sent! Check ntfy.sh topic.")
            else:
                st.sidebar.error("Failed to send test.")
        
        # Subscription Info
        with st.sidebar.expander("❓ How to get Push Notifications"):
            st.markdown(f"""
            1. Visit: [ntfy.sh Topic]({NTFY_TOPIC_URL})
            2. Click **'Subscribe'** or **'Allow Notifications'**.
            3. Triggers will then appear on your phone/browser.
            """)

        # 3. Detection Logic
        last_check = st.session_state.get('last_trigger_check', 0)
        current_time = time.time()
        should_check_auto = (current_time - last_check) > (TRIGGER_CHECK_INTERVAL_MINUTES * 60)
        
        if should_check_auto or manual_refresh:
            with st.sidebar:
                with st.spinner("Analyzing..."):
                    new_triggers = generate_triggers(client, patient_id)
                    new_types = [t.get('type') for t in new_triggers]
                    
                    # Reconciliation: Dismiss old triggers of types that are NO LONGER detected
                    # and types that ARE detected (we'll replace them with fresh ones)
                    detectable_types = ['memory_gap', 'media_gap', 'mood_trend', 'milestone_anniversary']
                    for t in existing_triggers:
                        t_type = t.get('type')
                        if not t.get('dismissed', False) and t_type in detectable_types:
                            # If it's a gap/trend trigger, we want to replace it or clear it
                            dismiss_trigger(t.get('id'), patient_id)
                    
                    # 4. Save new triggers
                    for trigger in new_triggers:
                        save_trigger(trigger, patient_id)
                        if trigger.get('priority') in ['high', 'urgent']:
                            send_trigger_notification(trigger)
            
            st.session_state.last_trigger_check = current_time
            existing_triggers = load_triggers(patient_id)
            if manual_refresh:
                st.sidebar.success("Analysis complete!")

        # 4. Render Active Triggers
        render_trigger_sidebar(existing_triggers)
        
    except Exception as e:
        import logging
        logging.error(f"Trigger lifecycle error: {e}")
        st.sidebar.error("Trigger system error. See logs.")


def render_trigger_sidebar(triggers: List[Dict]):
    """
    Displays triggers in sidebar with alert cards.
    """
    if not triggers:
        return
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔔 Agent Suggestions")
    
    for trigger in triggers:
        priority = trigger.get("priority", "medium")
        title = trigger.get("title", "Reminder")
        message = trigger.get("message", "")
        trigger_id = trigger.get("id", "")
        
        # UI Presentation
        with st.sidebar:
            if priority == "urgent":
                st.error(f"**{title}**\n\n{message}")
            elif priority == "high":
                st.warning(f"**{title}**\n\n{message}")
            else:
                st.info(f"**{title}**\n\n{message}")
            
            if trigger_id:
                if st.button(f"Dismiss", key=f"dismiss_{trigger_id}"):
                    from lifelens.auth.session import get_active_patient_id
                    pid = get_active_patient_id()
                    if pid:
                        dismiss_trigger(trigger_id, pid)
                        st.rerun()


def render_trigger_banner(trigger: Dict):
    """
    Shows high-priority triggers as banners.
    
    Args:
        trigger: Trigger dictionary
    """
    priority = trigger.get("priority", "medium")
    
    if priority in ["urgent", "high"]:
        title = trigger.get("title", "Important Reminder")
        message = trigger.get("message", "")
        
        if priority == "urgent":
            st.error(f"🚨 **{title}**\n\n{message}")
        else:
            st.warning(f"⚠️ **{title}**\n\n{message}")


def render_suggested_capture_button(trigger: Dict):
    """
    Action button for capture suggestions.
    
    Args:
        trigger: Trigger dictionary
    """
    action = trigger.get("action", "")
    
    if action == "capture_memory":
        if st.button("📥 Add Memory Now", type="primary"):
            st.info("👆 Use the 'Remember This' tab above to add a new memory!")
    
    elif action == "capture_photo":
        if st.button("📸 Take Photo Now", type="primary"):
            st.info("👆 Use the 'Remember This' tab and select 'Image' to add a photo!")
    
    elif action == "tag_people":
        if st.button("👤 Tag People Now", type="primary"):
            st.info("Review your recent photos and add people tags to help with memory recall!")


def render_trigger_list(triggers: List[Dict]):
    """
    Full list view of all active triggers.
    
    Args:
        triggers: List of trigger dictionaries
    """
    if not triggers:
        st.info("✅ No active suggestions at this time. Keep capturing memories!")
        return
    
    st.subheader("🔔 Active Suggestions")
    
    # Group by priority
    urgent = [t for t in triggers if t.get("priority") == "urgent"]
    high = [t for t in triggers if t.get("priority") == "high"]
    medium = [t for t in triggers if t.get("priority") == "medium"]
    low = [t for t in triggers if t.get("priority") == "low"]
    
    # Display urgent triggers
    if urgent:
        st.markdown("### 🚨 Urgent")
        for trigger in urgent:
            with st.expander(f"**{trigger.get('title')}**", expanded=True):
                st.write(trigger.get("message"))
                render_suggested_capture_button(trigger)
                
                if st.button("Dismiss", key=f"list_dismiss_{trigger.get('id')}"):
                    from lifelens.utils.trigger_storage import dismiss_trigger
                    from lifelens.auth.session import get_active_patient_id
                    
                    patient_id = get_active_patient_id()
                    if patient_id:
                        dismiss_trigger(trigger.get('id'), patient_id)
                        st.rerun()
    
    # Display high priority triggers
    if high:
        st.markdown("### ⚠️ High Priority")
        for trigger in high:
            with st.expander(f"**{trigger.get('title')}**"):
                st.write(trigger.get("message"))
                render_suggested_capture_button(trigger)
                
                if st.button("Dismiss", key=f"list_dismiss_{trigger.get('id')}"):
                    from lifelens.utils.trigger_storage import dismiss_trigger
                    from lifelens.auth.session import get_active_patient_id
                    
                    patient_id = get_active_patient_id()
                    if patient_id:
                        dismiss_trigger(trigger.get('id'), patient_id)
                        st.rerun()
    
    # Display medium priority triggers
    if medium:
        st.markdown("### ℹ️ Suggestions")
        for trigger in medium:
            with st.expander(f"{trigger.get('title')}"):
                st.write(trigger.get("message"))
                render_suggested_capture_button(trigger)
                
                if st.button("Dismiss", key=f"list_dismiss_{trigger.get('id')}"):
                    from lifelens.utils.trigger_storage import dismiss_trigger
                    from lifelens.auth.session import get_active_patient_id
                    
                    patient_id = get_active_patient_id()
                    if patient_id:
                        dismiss_trigger(trigger.get('id'), patient_id)
                        st.rerun()
    
    # Display low priority triggers
    if low:
        st.markdown("### 💡 Tips")
        for trigger in low:
            with st.expander(f"{trigger.get('title')}"):
                st.write(trigger.get("message"))
                render_suggested_capture_button(trigger)
                
                if st.button("Dismiss", key=f"list_dismiss_{trigger.get('id')}"):
                    from lifelens.utils.trigger_storage import dismiss_trigger
                    from lifelens.auth.session import get_active_patient_id
                    
                    patient_id = get_active_patient_id()
                    if patient_id:
                        dismiss_trigger(trigger.get('id'), patient_id)
                        st.rerun()


def render_trigger_settings():
    """
    Renders trigger settings and preferences.
    """
    st.subheader("⚙️ Trigger Settings")
    
    enable_triggers = st.checkbox("Enable Agent Suggestions", value=True, 
                                   help="Allow LifeLens to generate helpful reminders and suggestions")
    
    enable_ntfy = st.checkbox("Enable Push Notifications", value=False,
                              help="Receive push notifications via ntfy (requires subscription)")
    
    if enable_ntfy:
        st.info("""
        📱 **To receive push notifications:**
        1. Visit https://ntfy.sh/lifelens-caregiver-alerts on your phone or browser
        2. Tap "Subscribe" and enable notifications
        3. You'll receive reminders even when not using LifeLens
        """)
    
    trigger_frequency = st.select_slider(
        "Check for new suggestions every:",
        options=["1 hour", "3 hours", "6 hours", "12 hours", "24 hours"],
        value="6 hours"
    )
    
    if st.button("Save Settings"):
        st.success("Settings saved! (Note: Settings persistence requires session state implementation)")
    
    return {
        "enable_triggers": enable_triggers,
        "enable_ntfy": enable_ntfy,
        "trigger_frequency": trigger_frequency
    }
