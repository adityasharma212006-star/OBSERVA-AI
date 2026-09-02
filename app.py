import streamlit as st
import time
from pathlib import Path
import random
import sqlite3
import pandas as pd
import plotly.express as px
from ai_engine import analyze_image, generate_questions, evaluate_answers, adapt_difficulty, save_round, get_history

st.set_page_config(page_title="OBSERVA AI", page_icon="🧠", layout="wide")

def init():
    defaults = {"stage":"home","image":None,"analysis":None,"questions":None,
                "answers":{},"difficulty":"Medium","round_start":None}
    for k,v in defaults.items():
        if k not in st.session_state: st.session_state[k]=v
init()

st.title("🧠 OBSERVA AI")
st.caption("AI-Powered Visual Observation & Cognitive Assessment System")

tab1, tab2 = st.tabs(["🎯 Challenge", "📊 Analytics"])

with tab1:
    if st.session_state.stage == "home":
        st.info("Upload a scene image. OBSERVA will analyse it, generate questions, hide the image after a timed observation period, evaluate your answers, and adapt the next difficulty.")
        uploaded = st.file_uploader("Upload challenge image", type=["jpg","jpeg","png"])
        c1,c2,c3 = st.columns(3)
        difficulty = c1.selectbox("Starting difficulty", ["Easy","Medium","Hard"], index=["Easy","Medium","Hard"].index(st.session_state.difficulty))
        observe_seconds = c2.select_slider("Observation time", options=[3,5,10,15], value=10)
        ai_mode = c3.checkbox("Use Gemini Vision (optional)", value=False)
        if uploaded and st.button("Prepare AI Challenge", type="primary"):
            path = Path("data/uploads"); path.mkdir(parents=True, exist_ok=True)
            image_path = path / f"{int(time.time())}_{uploaded.name}"
            image_path.write_bytes(uploaded.getvalue())
            with st.spinner("Analysing image and creating questions..."):
                analysis = analyze_image(str(image_path), use_gemini=ai_mode)
                questions = generate_questions(analysis, difficulty)
            if not questions:
                st.error("Could not generate enough reliable questions. Try another image.")
            else:
                st.session_state.update({"image":str(image_path),"analysis":analysis,"questions":questions,
                                         "difficulty":difficulty,"stage":"observe","observe_seconds":observe_seconds})
                st.rerun()

    elif st.session_state.stage == "observe":
        st.subheader("Observe carefully")
        st.image(st.session_state.image, use_container_width=True)
        st.warning(f"You have {st.session_state.observe_seconds} seconds. The image will disappear when you start.")
        if st.button("Start Observation Timer", type="primary"):
            placeholder=st.empty()
            for remaining in range(st.session_state.observe_seconds, 0, -1):
                placeholder.metric("Time remaining", f"{remaining}s")
                time.sleep(1)
            placeholder.empty()
            st.session_state.stage="questions"
            st.session_state.round_start=time.time()
            st.rerun()

    elif st.session_state.stage == "questions":
        st.subheader("Answer without looking at the image")
        st.caption("Each answer is evaluated against the visual information extracted during analysis.")
        with st.form("answers"):
            answers={}
            for i,q in enumerate(st.session_state.questions):
                st.markdown(f"**Q{i+1}. {q['question']}**  \n*Category: {q['category']}*")
                answers[str(i)] = st.text_input("Your answer", key=f"a{i}", label_visibility="collapsed")
            submitted=st.form_submit_button("Submit Answers", type="primary")
        if submitted:
            response_time=time.time()-st.session_state.round_start
            result=evaluate_answers(st.session_state.questions, answers, response_time)
            result["difficulty"]=st.session_state.difficulty
            result["next_difficulty"]=adapt_difficulty(result, st.session_state.difficulty)
            save_round(result)
            st.session_state.result=result
            st.session_state.stage="result"
            st.rerun()

    elif st.session_state.stage == "result":
        r=st.session_state.result
        st.success(f"Overall Observation Score: {r['score']}%")
        a,b,c=st.columns(3)
        a.metric("Correct", f"{r['correct']}/{r['total']}")
        b.metric("Accuracy", f"{r['accuracy']}%")
        c.metric("Response time", f"{r['response_time']} sec")
        st.subheader("Skill-wise profile")
        df=pd.DataFrame([{"Category":k,"Accuracy":v} for k,v in r["category_scores"].items()])
        if not df.empty: st.bar_chart(df.set_index("Category"))
        st.info(r["insight"])
        st.markdown(f"### Next recommended difficulty: **{r['next_difficulty']}**")
        st.session_state.difficulty=r["next_difficulty"]
        if st.button("Start Next Challenge", type="primary"):
            st.session_state.stage="home"
            st.rerun()

with tab2:
    history=get_history()
    if history.empty:
        st.info("Complete a challenge to unlock analytics.")
    else:
        st.metric("Rounds completed", len(history))
        fig=px.line(history, x="created_at", y="score", markers=True, title="Observation Score Progress")
        st.plotly_chart(fig, use_container_width=True)
        cat=history.groupby("difficulty", as_index=False)["score"].mean()
        st.plotly_chart(px.bar(cat,x="difficulty",y="score",title="Average Score by Difficulty"), use_container_width=True)
        st.dataframe(history.sort_values("created_at",ascending=False), use_container_width=True)
