"""
Agent Trace Panel - UI Component for Agent Decision Visibility

Provides expandable UI panel showing agent reasoning, plans, and verdicts.
As defined in multiagent.md Fix #4.
"""

import streamlit as st
from typing import List, Dict, Optional
from datetime import datetime


def render_agent_trace_panel(
    decisions: List[Dict],
    title: str = "🧠 Agent Reasoning",
    expanded: bool = False
) -> None:
    """
    Renders an expandable accordion showing agent decision trace.
    
    Args:
        decisions: List of formatted decision dictionaries
        title: Panel title
        expanded: Whether to show expanded by default
    """
    if not decisions:
        return
    
    with st.expander(title, expanded=expanded):
        st.markdown("### Agent Decision Trace")
        st.caption("Shows how agents processed this request")
        
        for i, decision in enumerate(decisions):
            _render_decision_card(decision, i + 1)


def _render_decision_card(decision: Dict, step_num: int) -> None:
    """Renders a single decision card."""
    
    agent = decision.get("agent", "Unknown")
    verdict = decision.get("verdict")
    attempt = decision.get("attempt", 0)
    timestamp = decision.get("timestamp", "")
    reasoning = decision.get("reasoning", "No reasoning provided")
    plan_summary = decision.get("plan_summary", "")
    
    # Format timestamp
    try:
        if timestamp:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            time_str = dt.strftime("%H:%M:%S")
        else:
            time_str = ""
    except:
        time_str = timestamp
    
    # Choose color based on verdict
    if verdict == "OK":
        verdict_color = "🟢"
        card_color = "#e8f5e9"
    elif verdict == "RETRY":
        verdict_color = "🟡"
        card_color = "#fff3e0"
    elif verdict in ("NOT_ENOUGH_EVIDENCE", "SUGGEST_TRIGGER"):
        verdict_color = "🔴"
        card_color = "#ffebee"
    elif verdict == "IGNORE":
        verdict_color = "⚪"
        card_color = "#f5f5f5"
    else:
        verdict_color = "🔵"
        card_color = "#e3f2fd"
    
    # Render card
    st.markdown(f"""
    <div style="
        background: {card_color};
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
        border-left: 4px solid {"#4caf50" if verdict == "OK" else "#ff9800"};
    ">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <div style="font-weight: 600; font-size: 14px;">
                Step {step_num}: {agent.upper()}
            </div>
            <div style="font-size: 12px; color: #666;">
                {time_str}
            </div>
        </div>
        <div style="margin-bottom: 8px;">
            <span style="background: white; padding: 4px 8px; border-radius: 4px; font-size: 12px;">
                {verdict_color} {verdict or "Processing"}
            </span>
            {f'<span style="background: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; margin-left: 8px;">Attempt {attempt + 1}</span>' if attempt > 0 else ''}
        </div>
        <div style="font-size: 13px; color: #333; margin-bottom: 8px;">
            {reasoning}
        </div>
        {f'<div style="font-size: 12px; color: #666; font-style: italic;">{plan_summary}</div>' if plan_summary and plan_summary != "No plan" else ''}
    </div>
    """, unsafe_allow_html=True)


def render_live_agent_status(
    current_agent: str,
    status: str,
    progress: Optional[float] = None
) -> None:
    """
    Renders a live status indicator for currently executing agent.
    
    Args:
        current_agent: Name of agent currently executing
        status: Status message
        progress: Optional progress value (0.0-1.0)
    """
    st.markdown(f"""
    <div style="
        background: #e3f2fd;
        padding: 12px;
        border-radius: 6px;
        border-left: 4px solid #2196f3;
        margin-bottom: 15px;
    ">
        <div style="display: flex; align-items: center; gap: 10px;">
            <div class="spinner" style="
                width: 16px;
                height: 16px;
                border: 2px solid #2196f3;
                border-top-color: transparent;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            "></div>
            <div>
                <div style="font-weight: 600; font-size: 13px; color: #1976d2;">
                    {current_agent.upper()} Agent
                </div>
                <div style="font-size: 12px; color: #666;">
                    {status}
                </div>
            </div>
        </div>
    </div>
    <style>
        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}
    </style>
    """, unsafe_allow_html=True)
    
    if progress is not None:
        st.progress(progress)


def render_session_summary(
    session_id: str,
    total_agents: int,
    total_retries: int,
    final_verdict: str,
    execution_time: Optional[float] = None
) -> None:
    """
    Renders a summary card for the entire agent session.
    
    Args:
        session_id: Session identifier
        total_agents: Total number of agents invoked
        total_retries: Total retry attempts
        final_verdict: Final verdict from critic
        execution_time: Optional execution time in seconds
    """
    verdict_emoji = "✅" if final_verdict == "OK" else "⚠️"
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Agents Invoked", total_agents)
    
    with col2:
        st.metric("Retries", total_retries)
    
    with col3:
        st.metric("Final Verdict", f"{verdict_emoji} {final_verdict}")
    
    with col4:
        if execution_time:
            st.metric("Execution Time", f"{execution_time:.2f}s")
        else:
            st.metric("Session ID", session_id[:8])


def render_agent_analytics(decisions: List[Dict]) -> None:
    """
    Renders analytics about agent behavior from decision history.
    
    Args:
        decisions: List of decision payloads
    """
    if not decisions:
        st.info("No agent decisions to analyze")
        return
    
    # Calculate metrics
    total_decisions = len(decisions)
    agents_used = set(d.get("agent") for d in decisions)
    verdict_counts = {}
    retry_count = 0
    
    for decision in decisions:
        verdict = decision.get("verdict")
        if verdict:
            verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
        
        attempt = decision.get("attempt", 0)
        if attempt > 0:
            retry_count += 1
    
    # Display metrics
    st.markdown("### 📊 Agent Analytics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Decisions", total_decisions)
        st.caption(f"Across {len(agents_used)} different agents")
    
    with col2:
        st.metric("Retry Rate", f"{(retry_count/total_decisions*100):.1f}%")
        st.caption(f"{retry_count} retries out of {total_decisions}")
    
    with col3:
        ok_count = verdict_counts.get("OK", 0)
        success_rate = (ok_count / total_decisions * 100) if total_decisions > 0 else 0
        st.metric("Success Rate", f"{success_rate:.1f}%")
        st.caption(f"{ok_count} OK verdicts")
    
    # Verdict breakdown
    if verdict_counts:
        st.markdown("#### Verdict Distribution")
        
        for verdict, count in sorted(verdict_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_decisions * 100)
            st.progress(percentage / 100, text=f"{verdict}: {count} ({percentage:.1f}%)")


def render_agent_debug_panel(
    session_id: str,
    plan: Dict,
    retrieval_results: List[Dict],
    critic_feedback: str
) -> None:
    """
    Renders detailed debug panel for caretakers/admins.
    
    Args:
        session_id: Session identifier
        plan: The plan dictionary
        retrieval_results: Results from retriever
        critic_feedback: Feedback from critic
    """
    with st.expander("🔍 Debug Panel (Admin)", expanded=False):
        tab1, tab2, tab3, tab4 = st.tabs(["Plan", "Retrieval", "Critic", "Session"])
        
        with tab1:
            st.json(plan)
        
        with tab2:
            st.write(f"**Results found:** {len(retrieval_results)}")
            if retrieval_results:
                for i, result in enumerate(retrieval_results[:5]):
                    st.markdown(f"**Result {i+1}** (score: {result.get('score', 0):.3f})")
                    st.text(result.get("content", "")[:200])
        
        with tab3:
            st.markdown("**Critic Feedback:**")
            st.info(critic_feedback)
        
        with tab4:
            st.code(f"Session ID: {session_id}")
            st.caption("Use this ID to trace full agent flow in logs")
