import streamlit as st

def apply_styles():
    """
    Injects custom CSS for 'Senior Mode' accessibility.
    Larger fonts, high contrast, bigger buttons.
    """
    st.markdown("""
        <style>
        /* Base Font Size Increase */
        html, body, [class*="css"] {
            font-size: 20px;
        }
        
        /* Headers */
        h1 { font-size: 3rem !important; color: #2C3E50; }
        h2 { font-size: 2.5rem !important; color: #34495E; }
        h3 { font-size: 2rem !important; }
        
        /* Input Fields - Larger text */
        .stTextInput > div > div > input, .stTextArea > div > div > textarea {
            font-size: 20px !important;
            padding: 15px !important;
        }
        
        /* Buttons - Big and Tappable */
        .stButton > button {
            height: 3.5rem;
            width: 100%;
            font-size: 22px !important;
            font-weight: 600;
            border-radius: 12px;
            background-color: #E8F6F3; 
            border: 2px solid #1ABC9C;
            color: #16A085;
            transition: all 0.3s ease;
        }
        .stButton > button:hover {
            background-color: #1ABC9C;
            color: white;
            transform: scale(1.02);
        }
        
        /* Tabs - Big Labels */
        button[data-baseweb="tab"] {
            font-size: 22px !important;
            padding: 15px 30px !important;
        }
        
        /* Chat Messages */
        .stChatMessage {
            font-size: 20px !important;
            border: 1px solid #ddd;
            border-radius: 15px;
            padding: 10px;
            margin-bottom: 10px;
        }
        
        /* Expander */
        .streamlit-expanderHeader {
            font-size: 20px !important;
        }
        </style>
    """, unsafe_allow_html=True)
