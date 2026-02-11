import streamlit as st
import base64
import os
from datetime import datetime

def display_memory(memory):
    """
    Renders a single memory item in Streamlit.
    """
    # Convert timestamp to readable format
    timestamp = memory.get('timestamp', 0)
    readable_time = datetime.fromtimestamp(timestamp).strftime("%B %d, %Y at %I:%M %p")
    
    # Get category/milestone info
    category = memory.get('category')
    is_milestone = memory.get('is_milestone', False) or category in ["Achievement", "Event", "Milestone"]
    
    title_prefix = "🎉 MILESTONE: " if is_milestone else ""
    title = f"{title_prefix}{memory['type'].upper()} - {readable_time}"
    
    with st.expander(title, expanded=True):
        col1, col2 = st.columns([1, 3])
        
        with col1:
            if memory['type'] == 'image' and memory.get('source_image_base64'):
                # Decode base64 to display
                try:
                    st.image(base64.b64decode(memory['source_image_base64']))
                except Exception:
                    st.info("📷 Image preview unavailable")
            elif memory['type'] == 'audio':
                try:
                    audio_data = memory.get('source_audio_base64')
                    if audio_data and len(audio_data) > 20:  # Valid base64 is longer
                        st.audio(base64.b64decode(audio_data), format='audio/wav')
                    else:
                        st.info("🎤 Audio content (preview unavailable)")
                except Exception:
                    st.info("🎤 Audio content (preview unavailable)")
            elif memory['type'] == 'text':
                st.markdown("📝 **Note**")
            elif memory['type'] == 'video':
                st.markdown("📹 **Video**")
                # Play video if path exists
                if memory.get('video_path') and os.path.exists(memory['video_path']):
                    st.video(memory['video_path'])
                else:
                    st.warning("Video file not found locally.")
                
                # Display location if available
                location = memory.get('location')
                if location and isinstance(location, dict):
                    st.caption(location.get('name', ''))

        with col2:
            # Display Person Tags if available
            if memory.get('person_tags'):
                st.markdown(f"### 👤 {memory['person_tags']}")
                st.markdown("---")
            
            # Display Sentiment if available
            if memory.get('sentiment'):
                sentiment_colors = {
                    "Happy": "🟢",
                    "Sad": "🔵", 
                    "Angry": "🔴",
                    "Confused": "🟡",
                    "Neutral": "⚪"
                }
                icon = sentiment_colors.get(memory['sentiment'], "⚪")
                st.markdown(f"{icon} **Mood:** {memory['sentiment']}")
            
            if memory.get('caption'):
                st.markdown(f"**Caption:** {memory['caption']}")
            if memory.get('transcript'):
                st.markdown(f"**Transcript:** {memory['transcript']}")
            if memory.get('content'):
                st.markdown(f"**Content:** {memory['content']}")
            if memory.get('analysis'):
                st.markdown(f"**AI Analysis:** {memory['analysis']}")
                
            st.caption(f"Score: {memory.get('score', 0):.4f}")
