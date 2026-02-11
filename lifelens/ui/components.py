import streamlit as st

def card(title, content, icon="📄"):
    """
    Renders a glassmorphism card.
    """
    with st.container():
        st.markdown(f"""
        <div class="glass-card">
            <h3>{icon} {title}</h3>
            <p>{content}</p>
        </div>
        """, unsafe_allow_html=True)

def metric_card(label, value, delta=None):
    """
    Renders a styled metric card.
    """
    delta_html = f"<span style='color: #4ade80'>▲ {delta}</span>" if delta else ""
    st.markdown(f"""
    <div style="background: rgba(255,255,255,0.05); padding: 1rem; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);">
        <div style="color: #94a3b8; font-size: 0.9rem;">{label}</div>
        <div style="font-size: 1.8rem; font-weight: bold; color: white;">{value}</div>
        <div style="font-size: 0.8rem;">{delta_html}</div>
    </div>
    """, unsafe_allow_html=True)

def load_css():
    """
    Injects the custom CSS from styles.css
    """
    import os
    css_path = os.path.join(os.path.dirname(__file__), "styles.css")
    with open(css_path, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
