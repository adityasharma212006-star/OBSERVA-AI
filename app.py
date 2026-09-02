import os
import time
import sqlite3
import tempfile
import pandas as pd
import plotly.express as px
import streamlit as st
from PIL import Image
from ai_engine import analyze_image

# ================= DATABASE SETUP =================
DB_FILE = "observa_cognitive.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS challenge_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            difficulty TEXT,
            observation_time INTEGER,
            score INTEGER,
            total INTEGER,
            accuracy REAL,
            dominant_color TEXT,
            brightness TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_result(difficulty, obs_time, score, total, accuracy, dominant_color, brightness):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO challenge_history 
        (difficulty, observation_time, score, total, accuracy, dominant_color, brightness)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (difficulty, obs_time, score, total, accuracy, dominant_color, brightness))
    conn.commit()
    conn.close()

def get_history():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM challenge_history ORDER BY id DESC", conn)
    conn.close()
    return df

def clear_history():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM challenge_history")
    conn.commit()
    conn.close()

init_db()

# ================= PAGE SETUP =================
st.set_page_config(
    page_title="OBSERVA AI",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ================= ROBUST STYLING (NO CLIPPING) =================
st.markdown("""
<style>
    /* Give safe spacing from top of screen */
    .block-container {
        max-width: 580px !important;
        padding-top: 3.5rem !important;
        padding-bottom: 3rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }

    /* Modern Primary Buttons */
    .stButton > button {
        width: 100% !important;
        background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%) !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
        border-radius: 12px !important;
        border: none !important;
        padding: 0.75rem 1.2rem !important;
        box-shadow: 0 4px 15px rgba(14, 165, 233, 0.35) !important;
        transition: transform 0.1s ease !important;
    }
    .stButton > button:active {
        transform: scale(0.98) !important;
    }

    /* Style the countdown HUD */
    .hud-timer {
        font-size: 2.8rem;
        font-weight: 800;
        text-align: center;
        color: #38bdf8;
        background: rgba(14, 165, 233, 0.1);
        border: 2px solid rgba(56, 189, 248, 0.4);
        border-radius: 16px;
        padding: 0.6rem;
        margin-bottom: 1rem;
    }

    /* Hide Streamlit Default Chrome */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ================= BULLETPROOF HEADER =================
st.markdown("""
<div style="text-align: center; margin-bottom: 1.5rem; padding-top: 0.5rem;">
    <div style="display: inline-block; padding: 4px 12px; background: rgba(56, 189, 248, 0.12); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 20px; color: #38bdf8; font-size: 11px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 8px;">
        AI VISUAL COGNITION LAB
    </div>
    <div style="font-size: 34px; font-weight: 800; color: #ffffff; line-height: 1.4; margin: 0; padding: 0;">
        🧠 OBSERVA <span style="color: #38bdf8;">AI</span>
    </div>
    <div style="color: #94a3b8; font-size: 13px; font-weight: 500; margin-top: 4px;">
        Visual Observation & Memory Training System
    </div>
</div>
""", unsafe_allow_html=True)

# ================= SESSION STATE =================
if "phase" not in st.session_state:
    st.session_state.phase = "upload"
if "analysis" not in st.session_state:
    st.session_state.analysis = None
if "image_path" not in st.session_state:
    st.session_state.image_path = None
if "saved_this_round" not in st.session_state:
    st.session_state.saved_this_round = False

# Navigation Tabs
tab_challenge, tab_analytics = st.tabs(["🎯 Challenge Deck", "📊 Cognitive Profile"])

# ================= TAB 1: CHALLENGE =================
with tab_challenge:

    # 1. SETUP PHASE
    if st.session_state.phase == "upload":
        st.session_state.saved_this_round = False

        st.info("Observe an environment under a timed countdown. The image will be hidden, and your recall will be evaluated across visual detail, colors, and quadrants.")

        source = st.radio("Capture Method", ["📸 Camera Snap", "📁 Upload File"], horizontal=True)

        uploaded_file = None
        if source == "📸 Camera Snap":
            uploaded_file = st.camera_input("Take scene photo")
        else:
            uploaded_file = st.file_uploader("Upload scene image", type=["jpg", "jpeg", "png"])

        col1, col2 = st.columns(2)
        with col1:
            difficulty = st.selectbox("Difficulty Tier", ["Easy", "Medium", "Hard"], index=1)
        with col2:
            obs_time = st.slider("Observe Window (sec)", 5, 25, 10)

        use_gemini = st.checkbox("Use Gemini Multimodal Vision", value=False)

        if uploaded_file is not None:
            st.write("")
            if st.button("🚀 Start Challenge"):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                    tmp.write(uploaded_file.getvalue())
                    st.session_state.image_path = tmp.name

                with st.spinner("Extracting scene details..."):
                    st.session_state.analysis = analyze_image(
                        st.session_state.image_path,
                        use_gemini=use_gemini,
                        difficulty=difficulty
                    )
                st.session_state.obs_time = obs_time
                st.session_state.difficulty = difficulty
                st.session_state.phase = "observe"
                st.rerun()

    # 2. OBSERVATION COUNTDOWN
    elif st.session_state.phase == "observe":
        st.markdown(f"#### 👁️ Memorize the Scene ({st.session_state.difficulty} Mode)")
        timer_box = st.empty()
        img_box = st.empty()

        img_box.image(st.session_state.image_path, use_container_width=True)

        for remaining in range(st.session_state.obs_time, 0, -1):
            timer_box.markdown(f'<div class="hud-timer">⏱️ {remaining:02d}s</div>', unsafe_allow_html=True)
            time.sleep(1)

        timer_box.empty()
        img_box.empty()
        st.session_state.phase = "question"
        st.rerun()

    # 3. QUESTION RECALL
    elif st.session_state.phase == "question":
        st.markdown("#### ❓ Recall Challenge")
        st.caption(f"Difficulty: **{st.session_state.difficulty}** • The image is hidden. Answer what you observed.")

        questions = st.session_state.analysis.get("questions", [])
        user_answers = {}

        with st.form("assessment_form"):
            for i, q in enumerate(questions):
                st.markdown(f"""
                <div style="background: rgba(30, 41, 59, 0.7); border-left: 4px solid #38bdf8; border-radius: 10px; padding: 12px; margin-bottom: 12px;">
                    <div style="font-size: 11px; font-weight: 700; color: #38bdf8; text-transform: uppercase;">{q.get('category', 'Visual Detail')}</div>
                    <div style="font-size: 15px; font-weight: 600; color: #f8fafc; margin-top: 4px;">Q{i+1}. {q.get('question')}</div>
                </div>
                """, unsafe_allow_html=True)
                user_answers[i] = st.text_input(f"Your answer for Q{i+1}", key=f"q_in_{i}").strip().lower()

            st.write("")
            if st.form_submit_button("Submit Answers"):
                st.session_state.user_answers = user_answers
                st.session_state.phase = "result"
                st.rerun()

    # 4. RESULTS & DATABASE LOGGING
    elif st.session_state.phase == "result":
        st.markdown("#### 🎯 Challenge Evaluation")
        questions = st.session_state.analysis.get("questions", [])
        feat = st.session_state.analysis.get("features", {})
        user_answers = st.session_state.user_answers

        score = 0
        total = len(questions)

        for i, q in enumerate(questions):
            user_val = user_answers.get(i, "")
            correct_val = str(q.get("answer", "")).lower().strip()
            is_match = (user_val == correct_val) or (correct_val in user_val and len(user_val) > 0)

            if is_match:
                score += 1
                st.success(f"**Q{i+1} Correct**: {q.get('question')}\n\n*Your Answer:* `{user_val}`")
            else:
                st.error(f"**Q{i+1} Missed**: {q.get('question')}\n\n*Your Answer:* `{user_val or 'Empty'}` • *Expected:* `{correct_val}`")

        accuracy_pct = round((score / total) * 100, 1) if total > 0 else 0

        # Commit to SQLite Database
        if not st.session_state.saved_this_round:
            save_result(
                difficulty=st.session_state.difficulty,
                obs_time=st.session_state.obs_time,
                score=score,
                total=total,
                accuracy=accuracy_pct,
                dominant_color=feat.get("dominant_color", "N/A"),
                brightness=feat.get("brightness", "N/A")
            )
            st.session_state.saved_this_round = True

        st.markdown(f"""
        <div style="background: rgba(15, 23, 42, 0.85); border: 1.5px solid rgba(56, 189, 248, 0.4); border-radius: 18px; padding: 20px; text-align: center; margin: 15px 0;">
            <div style="font-size: 12px; font-weight: 700; color: #94a3b8; letter-spacing: 1px;">ACCURACY SCORE</div>
            <div style="font-size: 48px; font-weight: 800; color: #38bdf8; font-family: monospace;">{accuracy_pct}%</div>
            <div style="font-size: 14px; color: #cbd5e1;">Logged {score} of {total} correct answers to database.</div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("🔍 View Scene Ground Truth"):
            st.image(st.session_state.image_path, use_container_width=True)

        if st.button("🔄 Start New Challenge"):
            st.session_state.phase = "upload"
            st.session_state.analysis = None
            st.session_state.image_path = None
            st.rerun()

# ================= TAB 2: ANALYTICS =================
with tab_analytics:
    st.markdown("#### 📈 Cognitive Progression Ledger")

    df_history = get_history()

    if df_history.empty:
        st.info("No assessments logged yet. Complete a challenge to view your cognitive performance graphs!")
    else:
        total_tests = len(df_history)
        avg_acc = round(df_history["accuracy"].mean(), 1)
        best_acc = round(df_history["accuracy"].max(), 1)

        m1, m2, m3 = st.columns(3)
        m1.metric("Tests", total_tests)
        m2.metric("Avg Score", f"{avg_acc}%")
        m3.metric("Peak", f"{best_acc}%")

        st.markdown("##### Accuracy Progression Over Time")
        chart_df = df_history.sort_values(by="id")
        fig = px.line(
            chart_df,
            x="id",
            y="accuracy",
            markers=True,
            color="difficulty",
            color_discrete_map={"Easy": "#34d399", "Medium": "#38bdf8", "Hard": "#f43f5e"},
            labels={"id": "Run #", "accuracy": "Accuracy (%)"}
        )
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=15, b=15),
            height=260
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("##### Assessment History")
        display_df = df_history[["id", "timestamp", "difficulty", "score", "total", "accuracy", "dominant_color"]]
        display_df.columns = ["#", "Date/Time", "Tier", "Correct", "Total", "Accuracy %", "Tone"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        with st.expander("⚙️ Database Controls"):
            if st.button("🗑️ Reset All Records"):
                clear_history()
                st.success("Database records cleared!")
                st.rerun()
