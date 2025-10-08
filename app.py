# app.py
import os
import json
from io import BytesIO
import streamlit as st
from google import genai
from google.genai import types
from dotenv import load_dotenv
import PyPDF2

# Load .env
load_dotenv()

# Configure Gemini client
client = genai.Client()

# Streamlit page config
st.set_page_config(page_title="HireMind — AI HR Assistant", layout="wide", page_icon="🤖")

# CSS for professional UI
st.markdown("""
<style>
body {background-color: #f5f7fa; font-family: 'Segoe UI', sans-serif;}
.panel {border-radius:12px; padding:20px; background:white; box-shadow:0 8px 24px rgba(0,0,0,0.06); margin-bottom:20px;}
.reportbox {background: linear-gradient(90deg, #ffffff, #f0f4f8); border-radius: 12px; padding: 20px; box-shadow: 0 6px 18px rgba(15,23,42,0.08); margin-bottom:20px;}
.skill {display:inline-block; background:#eef2ff; color:#3730a3; padding:8px 14px; border-radius:999px; margin:4px; font-weight:600;}
.chat-bubble {padding:16px 20px; border-radius:14px; margin:10px 0; max-width:90%; font-size:16px;}
.bot {background:#f3f4f6; color:#0f172a; text-align:left;}
.user {background:#0ea5a4; color:white; text-align:right; margin-left:auto;}
.progress-bar {height:22px; background:#e5e7eb; border-radius:12px; margin:6px 0;}
.progress-fill {height:100%; background:#0ea5a4; border-radius:12px; text-align:center; color:white; font-weight:bold;}
.text-area-large textarea {height:180px !important;}
</style>
""", unsafe_allow_html=True)

# Helper functions
def extract_text_from_pdf(uploaded_file):
    try:
        reader = PyPDF2.PdfReader(BytesIO(uploaded_file.read()))
        text = [page.extract_text() for page in reader.pages if page.extract_text()]
        return "\n".join(text)
    except:
        try:
            return uploaded_file.read().decode("utf-8", errors="ignore")
        except:
            return ""

def safe_parse_json(s):
    s = (s or "").strip()
    try:
        return json.loads(s)
    except:
        start = s.find("{")
        end = s.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(s[start:end+1])
            except:
                return None
        return None

# Gemini functions
def analyze_resume_with_gemini(resume_text, role):
    system_msg = "You are an expert recruiter. Return JSON with fit_score, top_skills, weaknesses, summary, recommended_questions."
    prompt = [{"text": system_msg}, {"text": f"Role: {role}\nResume:\n{resume_text}"}]
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt, config=types.GenerateContentConfig(temperature=0.15))
    parsed = safe_parse_json(response.text)
    return parsed if parsed else {"error":"Parsing failed","raw":response.text}

def generate_questions_with_gemini(resume_text, role):
    prompt = [
        {"text": "You are a senior interviewer. Return JSON only with keys 'technical' and 'behavioral' arrays."},
        {"text": f"Role: {role}\nResume:\n{resume_text}"}
    ]
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt, config=types.GenerateContentConfig(temperature=0.2))
    parsed = safe_parse_json(response.text)
    return parsed if parsed else {"error":"Parsing failed","raw":response.text}

def evaluate_answer_with_gemini(resume_text, question, answer):
    prompt = [
        {"text": "You are an interviewer. Return JSON {score:int, feedback:str}"},
        {"text": f"Resume:\n{resume_text}\nQuestion:\n{question}\nAnswer:\n{answer}"}
    ]
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt, config=types.GenerateContentConfig(temperature=0.0))
    parsed = safe_parse_json(response.text)
    return parsed if parsed else {"error":"Parsing failed","raw":response.text}

# UI Layout
st.title("🤝 HireMind — AI HR Assistant")
st.markdown("Smart resume screening & interactive interview simulation")

left, right = st.columns([2,3])

# LEFT PANEL
with left:
    st.markdown("<div class='panel'>", unsafe_allow_html=True)
    st.header("📄 Upload Resume")
    uploaded = st.file_uploader("PDF or TXT", type=["pdf","txt"])
    role = st.text_input("Target Role", value="Backend Software Engineer")

    if uploaded:
        with st.expander("Preview Extracted Text"):
            extracted = extract_text_from_pdf(uploaded)
            st.text_area("Resume Text", value=extracted[:4000], height=220)
        if st.button("Analyze Resume"):
            analysis = analyze_resume_with_gemini(extracted, role)
            st.session_state.analysis = analysis
            st.session_state.resume_text = extracted

    st.markdown("---")
    st.header("💡 Interview Simulator")
    if st.session_state.get("analysis"):
        if st.button("Generate Questions"):
            q = generate_questions_with_gemini(st.session_state.get("resume_text", ""), role)
            st.session_state.questions = q
            st.session_state.interview_idx = 0
            st.session_state.interview_scores = []

        if st.session_state.get("questions"):
            if st.button("Start Interview"):
                st.session_state.interview_questions = st.session_state.questions.get("technical", []) + st.session_state.questions.get("behavioral", [])
                st.session_state.interview_idx = 0
                st.session_state.interview_scores = []

    st.markdown("---")
    if st.button("Use Sample Resume"):
        sample = "Jane Developer\nBackend engineer: Python, Django, REST, Postgres, Docker."
        st.session_state.resume_text = sample
        st.session_state.analysis = analyze_resume_with_gemini(sample, role)
        st.session_state.questions = None
        st.session_state.interview_idx = 0
        st.session_state.interview_scores = []

# RIGHT PANEL
with right:
    st.markdown("<div class='panel'>", unsafe_allow_html=True)
    st.header("📊 Snapshot")
    analysis = st.session_state.get("analysis")
    if analysis and "error" not in analysis:
        st.markdown("<div class='reportbox'>", unsafe_allow_html=True)
        st.markdown(f"**Fit Score:** {analysis.get('fit_score','—')}/100")
        fit_pct = int(analysis.get('fit_score',0))
        st.markdown(f"<div class='progress-bar'><div class='progress-fill' style='width:{fit_pct}%'>{fit_pct}%</div></div>", unsafe_allow_html=True)
        st.markdown("**Top Skills:**")
        for skill in analysis.get("top_skills", []):
            st.markdown(f"<span class='skill'>{skill}</span>", unsafe_allow_html=True)
        st.markdown("**Weaknesses:**")
        for w in analysis.get("weaknesses", []):
            st.markdown(f"- {w}")
        st.markdown("**Summary:**")
        st.write(analysis.get("summary",""))
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("No analysis yet.")

    st.markdown("---")
    st.header("💬 Interview Simulation")
    idx = st.session_state.get("interview_idx",0)
    questions = st.session_state.get("interview_questions",[])
    if questions and idx < len(questions):
        current_q = questions[idx]
        st.markdown(f"<div class='chat-bubble bot'>{current_q}</div>", unsafe_allow_html=True)
        answer = st.text_area("Your Answer:", key=f"ans_{idx}", height=220)
        if st.button("Submit Answer", key=f"submit_{idx}"):
            evaluation = evaluate_answer_with_gemini(st.session_state.get("resume_text", ""), current_q, answer)
            st.session_state.interview_scores.append({"question": current_q, "answer": answer, "evaluation": evaluation})
            st.session_state.interview_idx += 1

    elif questions and idx >= len(questions):
        st.success("✅ Interview Finished")
        scores = st.session_state.get("interview_scores",[])
        numeric_scores = [int(item['evaluation'].get('score',0)) for item in scores if isinstance(item.get('evaluation',{}),dict)]
        avg = round(sum(numeric_scores)/len(numeric_scores),2) if numeric_scores else 'N/A'
        st.markdown(f"**Average Score:** {avg}")
        st.write("### Detailed Feedback")
        for i,r in enumerate(scores,1):
            ev = r.get('evaluation',{})
            st.write(f"**Q{i}:** {r['question']}")
            st.write(f"- Answer: {r['answer']}")
            st.write(f"- Score: {ev.get('score','—')} | Feedback: {ev.get('feedback','—')}")
        if st.button("Reset Interview"):
            for k in ['interview_idx','interview_questions','interview_scores']:
                if k in st.session_state: del st.session_state[k]

    else:
        st.info("No live interview running. Generate questions and start interview from left panel.")

    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")
st.caption("HireMind — Built with Gemini API • Keep your API key secret")
