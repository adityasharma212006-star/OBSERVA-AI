import os
import time
import tempfile
import streamlit as st
from PIL import Image
from ai_engine import analyze_image

# ----------------- PAGE & MOBILE HUD CONFIG -----------------
st.set_page_config(
    page_title="OBSERVA AI",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS for Mobile App View & Clean Dark Theme
st.markdown("""
<style>
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 540px !important;
        margin: auto;
    }
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3.2rem;
        font-weight: 600;
        font-size: 1rem;
        background-color: #ef4444;
        color: white;
        border: none;
    }
    .stButton>button:hover {
        background-color: #dc2626;
        color: white;
    }
    .timer-box {
        font-size: 2.2rem;
        font-weight: 800;
        text-align: center;
        color: #ef4444;
        padding: 0.5rem;
        border-radius: 12px;
        background: rgba(239, 68, 68, 0.1);
        border: 1px solid rgba(239, 68, 68, 0.25);
        margin-bottom: 1rem;
    }
    img {
        border-radius: 14px;
        max-width: 100% !important;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- SESSION STATE -----------------
if "phase" not in st.session_state:
    st.session_state.phase = "upload"  # upload -> observe -> question -> result
if "analysis" not in st.session_state:
    st.session_state.analysis = None
if "image_path" not in st.session_state:
    st.session_state.image_path = None

# ----------------- HEADER -----------------
st.markdown("## 🧠 OBSERVA AI")
st.caption("AI-Powered Visual Observation & Cognitive Assessment System")

tab_challenge, tab_analytics = st.tabs(["🎯 Challenge", "📊 Analytics"])

# ================= TAB 1: CHALLENGE =================
with tab_challenge:

    # 1. SETUP / UPLOAD PHASE
    if st.session_state.phase == "upload":
        st.info("Upload or photograph a scene. OBSERVA will analyze it, give you a timed window to observe, hide the image, and test your recall.")

        # Mobile input mode selector
        input_type = st.radio("Image Source:", ["📁 Upload Image", "📸 Mobile Camera"], horizontal=True)

        uploaded_file = None
        if input_type == "📁 Upload Image":
            uploaded_file = st.file_uploader("Upload challenge image", type=["jpg", "jpeg", "png"])
        else:
            uploaded_file = st.camera_input("Take a photo")

        col1, col2 = st.columns(2)
        with col1:
            difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"], index=1)
        with col2:
            obs_time = st.slider("Observation time (sec)", 5, 30, 10)

        use_gemini = st.checkbox("Use Gemini Vision (optional)", value=False)

        if uploaded_file is not None:
            if st.button("🚀 Start Observation Challenge"):
                # Save uploaded image to temp file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                    tmp.write(uploaded_file.getvalue())
                    st.session_state.image_path = tmp.name

                with st.spinner("AI is analyzing scene features..."):
                    st.session_state.analysis = analyze_image(
                        st.session_state.image_path,
                        use_gemini=use_gemini,
                        difficulty=difficulty
                    )
                st.session_state.obs_time = obs_time
                st.session_state.difficulty = difficulty
                st.session_state.phase = "observe"
                st.rerun()

    # 2. OBSERVATION PHASE (COUNTDOWN)
    elif st.session_state.phase == "observe":
        st.markdown(f"### 👁️ Observe closely! ({st.session_state.difficulty} Mode)")
        countdown_placeholder = st.empty()
        img_placeholder = st.empty()

        img_placeholder.image(st.session_state.image_path, use_container_width=True)

        for remaining in range(st.session_state.obs_time, 0, -1):
            countdown_placeholder.markdown(f'<div class="timer-box">⏱️ {remaining}s</div>', unsafe_allow_html=True)
            time.sleep(1)

        countdown_placeholder.empty()
        img_placeholder.empty()
        st.session_state.phase = "question"
        st.rerun()

    # 3. QUESTIONING PHASE (IMAGE HIDDEN)
    elif st.session_state.phase == "question":
        st.markdown("### ❓ Answer without looking at the image")
        st.caption(f"Difficulty: **{st.session_state.difficulty}** • Each answer is evaluated against detected visual features.")

        questions = st.session_state.analysis["questions"]
        user_answers = {}

        with st.form("q_form"):
            for idx, q in enumerate(questions):
                st.markdown(f"**Q{idx+1}. {q['question']}**")
                st.caption(f"*Category: {q['category']}*")
                user_answers[idx] = st.text_input(f"Your answer for Q{idx+1}", key=f"ans_{idx}").strip().lower()
                st.write("")

            submitted = st.form_submit_button("Submit Answers")
            if submitted:
                st.session_state.user_answers = user_answers
                st.session_state.phase = "result"
                st.rerun()

    # 4. RESULTS & SCORE
    elif st.session_state.phase == "result":
        st.markdown("### 🏆 Challenge Results")
        questions = st.session_state.analysis["questions"]
        user_answers = st.session_state.user_answers

        score = 0
        total = len(questions)

        for idx, q in enumerate(questions):
            user_ans = user_answers.get(idx, "")
            correct_ans = str(q.get("answer", "")).lower().strip()
            
            is_correct = (user_ans == correct_ans) or (correct_ans in user_ans and len(user_ans) > 0)
            if is_correct:
                score += 1
                st.success(f"**Q{idx+1}: Correct!** ({q['question']})\n- Your Answer: `{user_ans}`")
            else:
                st.error(f"**Q{idx+1}: Incorrect** ({q['question']})\n- Your Answer: `{user_ans or 'None'}`\n- Correct Answer: `{correct_ans}`")

        percent = int((score / total) * 100)
        st.metric(label="Visual Accuracy Score", value=f"{percent}%", delta=f"{score}/{total} correct")

        # Reveal Original Image
        with st.expander("🔍 Review Original Image"):
            st.image(st.session_state.image_path, use_container_width=True)

        if st.button("🔄 Try Another Image"):
            st.session_state.phase = "upload"
            st.session_state.analysis = None
            st.session_state.image_path = None
            st.rerun()

# ================= TAB 2: ANALYTICS =================
with tab_analytics:
    st.markdown("### 📊 Cognitive Metrics")
    st.write("Visual processing telemetry:")
    if st.session_state.analysis:
        feat = st.session_state.analysis.get("features", {})
        col1, col2 = st.columns(2)
        col1.metric("Dominant Tone", str(feat.get("dominant_color", "N/A")).capitalize())
        col2.metric("Brightness", str(feat.get("brightness", "N/A")).capitalize())
        col1.metric("Aspect Ratio", str(feat.get("aspect_ratio", "N/A")).capitalize())
        col2.metric("Salient Regions", feat.get("object_count", 0))
    else:
        st.info("Complete an observation challenge to view your analytics breakdown.")
