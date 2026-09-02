import os
import time
import sqlite3
import tempfile
import pandas as pd
import plotly.express as px
import streamlit as st
from PIL import Image
from ai_engine import analyze_image

# ================= DATABASE SETUP (SQLite) =================
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

# ================= STREAMLIT CONFIG & MODERN UI =================
st.set_page_config(
    page_title="OBSERVA AI • Cognitive Vision",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom High-End Cyber/Neuro Aesthetic (Mobile-First)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    /* Mobile container constraint */
    .block-container {
        max-width: 620px !important;
        padding-top: 1.5rem !important;
        padding-bottom: 2.5rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }

    /* Glassmorphic card styling */
    .glass-card {
        background: rgba(15, 23, 42, 0.7);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(56, 189, 248, 0.15);
        border-radius: 20px;
        padding: 1.25rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
    }

    /* Hero title accent */
    .app-title {
        font-weight: 800;
        letter-spacing: -0.5px;
        background: linear-gradient(135deg, #38bdf8 0%, #818cf8 50%, #c084fc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 1.9rem;
        margin-bottom: 0.2rem;
    }

    /* Primary futuristic button */
    .stButton>button {
        width: 100%;
        background: linear-gradient(135deg, #0284c7 0%, #6366f1 100%);
        color: #ffffff;
        font-weight: 700;
        font-size: 1.05rem;
        border: none;
        border-radius: 14px;
        padding: 0.8rem 1.5rem;
        transition: all 0.25s ease;
        box-shadow: 0 8px 20px -6px rgba(99, 102, 241, 0.5);
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 24px -6px rgba(99, 102, 241, 0.7);
        color: #ffffff;
    }

    /* Countdown HUD timer */
    .timer-badge {
        font-family: 'JetBrains Mono', monospace;
        font-size: 2.5rem;
        font-weight: 800;
        text-align: center;
        color: #38bdf8;
        background: rgba(14, 165, 233, 0.1);
        border: 1px solid rgba(56, 189, 248, 0.4);
        border-radius: 18px;
        padding: 0.6rem;
        margin-bottom: 1rem;
        box-shadow: 0 0 25px rgba(56, 189, 248, 0.2);
    }

    /* Question cards */
    .q-box {
        background: rgba(30, 41, 59, 0.6);
        border-left: 3px solid #38bdf8;
        border-radius: 12px;
        padding: 0.9rem;
        margin-bottom: 0.8rem;
    }

    /* Responsive image viewports */
    img {
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
</style>
""", unsafe_allow_html=True)

# ================= SESSION STATE =================
if "phase" not in st.session_state:
    st.session_state.phase = "upload"  # upload -> observe -> question -> result
if "analysis" not in st.session_state:
    st.session_state.analysis = None
if "image_path" not in st.session_state:
    st.session_state.image_path = None
if "saved_this_round" not in st.session_state:
    st.session_state.saved_this_round = False

# ================= HEADER =================
st.markdown('<div class="app-title">🧠 OBSERVA AI</div>', unsafe_allow_html=True)
st.caption("Neuro-Cognitive Visual Observation & Memory Training System")

tab_challenge, tab_analytics = st.tabs(["🎯 Challenge Deck", "📊 Cognitive Profile"])

# =================================================================
# TAB 1: CHALLENGE DECK
# =================================================================
with tab_challenge:

    # 1. SETUP / UPLOAD PHASE
    if st.session_state.phase == "upload":
        st.session_state.saved_this_round = False
        
        with st.container():
            st.markdown("""
            <div class="glass-card">
                <div style="font-size: 0.88rem; color: #94a3b8; line-height: 1.5;">
                    Upload or snap an environment scene. OBSERVA will analyze visual features, give you a timed window to inspect it, conceal the image, and evaluate your recall accuracy.
                </div>
            </div>
            """, unsafe_allow_html=True)

            source = st.radio("Capture Method", ["📸 Snap Photo", "📁 Upload File"], horizontal=True, label_visibility="collapsed")
            
            uploaded_file = None
            if source == "📸 Snap Photo":
                uploaded_file = st.camera_input("Capture scene directly")
            else:
                uploaded_file = st.file_uploader("Select scene image", type=["jpg", "jpeg", "png"])

            c1, c2 = st.columns(2)
            with c1:
                difficulty = st.selectbox("Difficulty Target", ["Easy", "Medium", "Hard"], index=1)
            with c2:
                obs_time = st.slider("Observe Window (sec)", 5, 25, 10)

            use_gemini = st.checkbox("Enable Gemini Multimodal Vision", value=False)

            if uploaded_file is not None:
                if st.button("🚀 Initialize Cognitive Assessment"):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                        tmp.write(uploaded_file.getvalue())
                        st.session_state.image_path = tmp.name

                    with st.spinner("Extracting visual features & spatial quadrants..."):
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
        st.markdown(f"#### 👁️ Commit scene details to memory ({st.session_state.difficulty})")
        timer_box = st.empty()
        img_box = st.empty()

        img_box.image(st.session_state.image_path, use_container_width=True)

        for remaining in range(st.session_state.obs_time, 0, -1):
            timer_box.markdown(f'<div class="timer-badge">⏱️ {remaining:02d}s</div>', unsafe_allow_html=True)
            time.sleep(1)

        timer_box.empty()
        img_box.empty()
        st.session_state.phase = "question"
        st.rerun()

    # 3. QUESTIONING PHASE (IMAGE CONCEALED)
    elif st.session_state.phase == "question":
        st.markdown("#### ❓ Recall Challenge")
        st.caption(f"Mode: **{st.session_state.difficulty}** • The image is hidden. Answer based on what you observed.")

        questions = st.session_state.analysis.get("questions", [])
        user_answers = {}

        with st.form("answers_form"):
            for i, q in enumerate(questions):
                st.markdown(f"""
                <div class="q-box">
                    <span style="font-size: 0.75rem; color: #38bdf8; font-weight: 700; text-transform: uppercase;">{q.get('category', 'Visual Detail')}</span>
                    <div style="font-weight: 600; font-size: 0.95rem; margin-top: 0.2rem; color: #f1f5f9;">Q{i+1}. {q.get('question')}</div>
                </div>
                """, unsafe_allow_html=True)
                user_answers[i] = st.text_input(f"Answer Q{i+1}", key=f"ans_field_{i}", placeholder="Type your answer here...").strip().lower()
                st.write("")

            if st.form_submit_button("Submit Assessment"):
                st.session_state.user_answers = user_answers
                st.session_state.phase = "result"
                st.rerun()

    # 4. RESULT PHASE & DATABASE COMMIT
    elif st.session_state.phase == "result":
        st.markdown("#### 🎯 Evaluation Report")
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
                st.success(f"**Q{i+1} Passed**: {q.get('question')}\n\n*Your Answer:* `{user_val}`")
            else:
                st.error(f"**Q{i+1} Missed**: {q.get('question')}\n\n*Your Answer:* `{user_val or 'Empty'}` • *Expected:* `{correct_val}`")

        accuracy_pct = round((score / total) * 100, 1) if total > 0 else 0

        # Save to SQLite database (guarded so it only saves once per challenge)
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
        <div class="glass-card" style="text-align: center; border-color: rgba(99, 102, 241, 0.4);">
            <div style="font-size: 0.85rem; color: #94a3b8; font-weight: 600;">COGNITIVE ACCURACY SCORE</div>
            <div style="font-size: 3rem; font-weight: 800; color: #38bdf8;">{accuracy_pct}%</div>
            <div style="font-size: 0.9rem; color: #cbd5e1;">Logged {score} out of {total} correct answers to database.</div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("🔍 Inspect Scene Ground Truth"):
            st.image(st.session_state.image_path, use_container_width=True)

        if st.button("🔄 Launch New Challenge"):
            st.session_state.phase = "upload"
            st.session_state.analysis = None
            st.session_state.image_path = None
            st.rerun()

# =================================================================
# TAB 2: ANALYTICS & DATABASE HISTORY
# =================================================================
with tab_analytics:
    st.markdown("#### 📈 Cognitive Progress & Database Records")
    
    df_history = get_history()

    if df_history.empty:
        st.info("No assessments logged yet. Complete your first challenge to see your cognitive progression curves!")
    else:
        # Top High-Level Metrics
        total_tests = len(df_history)
        avg_accuracy = round(df_history["accuracy"].mean(), 1)
        best_accuracy = round(df_history["accuracy"].max(), 1)

        m1, m2, m3 = st.columns(3)
        m1.metric("Tests Taken", total_tests)
        m2.metric("Avg Accuracy", f"{avg_accuracy}%")
        m3.metric("Peak Score", f"{best_accuracy}%")

        # Interactive Performance Trend Chart (Plotly)
        st.markdown("##### Accuracy Progression Over Time")
        chart_df = df_history.sort_values(by="id")
        fig = px.line(
            chart_df,
            x="id",
            y="accuracy",
            markers=True,
            color="difficulty",
            color_discrete_map={"Easy": "#34d399", "Medium": "#38bdf8", "Hard": "#f43f5e"},
            labels={"id": "Test Run #", "accuracy": "Accuracy (%)"}
        )
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=20, b=20),
            height=280
        )
        st.plotly_chart(fig, use_container_width=True)

        # Database Records Table
        st.markdown("##### Assessment History Log")
        display_df = df_history[["id", "timestamp", "difficulty", "score", "total", "accuracy", "dominant_color"]]
        display_df.columns = ["#", "Date / Time", "Difficulty", "Correct", "Total", "Accuracy %", "Dominant Tone"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        # Clear Database Option
        with st.expander("⚙️ Database Management"):
            if st.button("🗑️ Reset All Assessment Records"):
                clear_history()
                st.success("Database cleared!")
                st.rerun()
