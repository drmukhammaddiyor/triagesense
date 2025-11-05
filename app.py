# app.py — TriageSense with multi-turn conversation support
import os
import sqlite3
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

# Load .env
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY not set. Put your key in the .env file or export it in the environment.")

# OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI(title="TriageSense API")

# Mount static directory to serve the frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve index.html at site root


@app.get("/", include_in_schema=False)
def root():
    return FileResponse("static/index.html")


# --------------- Database ----------------
DB_PATH = "triagesense.db"


def get_db_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_conn()
    cur = conn.cursor()
    # submissions table (existing)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symptoms TEXT NOT NULL,
        reply TEXT NOT NULL,
        triage_level TEXT,
        triage_reason TEXT,
        created_at TEXT NOT NULL
    )
    """)
    # messages table for multi-turn conversation
    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        submission_id INTEGER NOT NULL,
        role TEXT NOT NULL, -- 'user' or 'assistant' or 'system'
        content TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(submission_id) REFERENCES submissions(id)
    )
    """)
    conn.commit()
    conn.close()


@app.on_event("startup")
def startup_event():
    init_db()


# --------------- Prompt / AI config ----------------
SYSTEM_INSTRUCTION = (
    "You are TriageSense, a professional medical triage assistant developed for educational use. "
    "You analyze patient-reported symptoms and produce structured, evidence-based summaries. "
    "Your tone is professional, calm, and clear—similar to how a licensed nurse or triage practitioner would speak. "
    "Avoid generic AI disclaimers, but include a single, polite reminder that the output is not medical advice. "
    "Always prioritize safety, clinical reasoning, and clarity. "
    "Use clean, bullet-based formatting. Use short paragraphs. "
    "Never list unnecessary causes or filler sentences. "
    "Ensure the response reads as a professional triage note, not a chatbot reply."
)

USER_TEMPLATE = (
    "Patient statement: ```{symptoms}```\n\n"
    "Generate **three clearly separated sections**, titled exactly as follows:\n\n"
    "### 1. Summary of Symptoms\n"
    "Briefly restate what the patient described in professional clinical tone (2–3 concise sentences). "
    "Capture key features like duration, intensity, and main body areas involved.\n\n"
    "### 2. Probable Causes or Clinical Considerations\n"
    "List up to 5 plausible medical explanations in bullet form. "
    "Each item must include: condition name (bold), and a short rationale (why it fits).\n\n"
    "### 3. Immediate Actions and Safe Self-Care Steps\n"
    "Provide clear, practical advice (4–6 short bullet points). Include general self-care measures, precautions, and warning signs that require urgent evaluation. "
    "If any symptom suggests life-threatening emergency (e.g., chest pain, difficulty breathing, fainting, stroke signs, heavy bleeding, severe allergic reaction), begin with: "
    "**'⚠️ Seek emergency care immediately if any severe or worsening symptoms occur.'**\n\n"
    "End with one line: _This information is educational and not a substitute for medical assessment._"
)

# --------------- Simple triage classifier ----------------
EMERGENCY_KEYWORDS = [
    "chest pain", "not breathing", "severe shortness", "shortness of breath",
    "difficulty breathing", "unconscious", "faint", "fainting", "severe bleeding",
    "stroke", "face droop", "slurred speech", "sudden weakness", "seizure", "anaphylaxis"
]

URGENT_KEYWORDS = [
    "high fever", "fever 39", "fever 38.5", "persistent vomiting", "severe pain",
    "worsening", "progressive", "rapidly", "heavy", "dehydration", "very weak",
    "cannot hold down", "difficulty speaking", "confusion"
]


def determine_triage_level(symptoms_text: str) -> (str, str):
    text = (symptoms_text or "").lower()
    for k in EMERGENCY_KEYWORDS:
        if k in text:
            return "Emergency", f"Contains emergency sign/keyword: '{k}'. Immediate evaluation recommended."
    for k in URGENT_KEYWORDS:
        if k in text:
            return "Urgent", f"Contains concerning feature: '{k}', consider urgent assessment."
    mild_indicators = ["runny nose", "mild sore", "mild cough", "sore throat", "sneezing", "congestion", "nasal",
                       "itchy eyes", "minor headache", "slight cough", "low-grade fever", "1 day", "2 days"]
    mild_count = sum(1 for k in mild_indicators if k in text)
    if mild_count >= 1 and "severe" not in text and "worsen" not in text and "persistent" not in text:
        return "Self-care", "Symptoms appear mild; self-care and watchful waiting may be appropriate."
    return "Non-urgent", "No immediate warning signs detected; consider primary care or self-care as appropriate."

# ----------------- Models -----------------


class SymptomsIn(BaseModel):
    symptoms: str


class ConverseIn(BaseModel):
    submission_id: int
    message: str

# ----------------- Endpoints -----------------


@app.post("/triage")
async def triage(input: SymptomsIn):
    symptoms_text = input.symptoms.strip()
    if not symptoms_text:
        raise HTTPException(
            status_code=400, detail="symptoms must be provided")

    messages = [
        {"role": "system", "content": SYSTEM_INSTRUCTION},
        {"role": "user", "content": USER_TEMPLATE.format(
            symptoms=symptoms_text)}
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=800,
            temperature=0.18
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI API error: {e}")

    # Extract assistant reply
    try:
        content = response.choices[0].message["content"]
    except Exception:
        content = getattr(
            response.choices[0].message, "content", str(response))

    triage_level, triage_reason = determine_triage_level(symptoms_text)

    # Save submission
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO submissions (symptoms, reply, triage_level, triage_reason, created_at) VALUES (?, ?, ?, ?, ?)",
            (symptoms_text, content, triage_level,
             triage_reason, datetime.utcnow().isoformat())
        )
        submission_id = cur.lastrowid
        # Save initial assistant message as a messages row (so conversation history starts)
        cur.execute(
            "INSERT INTO messages (submission_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (submission_id, "assistant", content, datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print("DB save error:", e)

    return {"submission_id": submission_id, "triage_reply": content, "triage_level": triage_level, "triage_reason": triage_reason}


@app.post("/converse")
async def converse(input: ConverseIn):
    # Validate submission exists
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, symptoms, reply FROM submissions WHERE id = ?",
                (input.submission_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Submission not found")

    # Save the incoming user message to messages table
    user_msg = input.message.strip()
    if not user_msg:
        conn.close()
        raise HTTPException(status_code=400, detail="message must be provided")

    try:
        cur.execute(
            "INSERT INTO messages (submission_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (input.submission_id, "user", user_msg, datetime.utcnow().isoformat())
        )
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"DB save error: {e}")

    # Reconstruct conversation history: system instruction, then all messages for this submission (ordered)
    try:
        cur.execute(
            "SELECT role, content FROM messages WHERE submission_id = ? ORDER BY id ASC", (input.submission_id,))
        rows = cur.fetchall()
        messages = [{"role": "system", "content": SYSTEM_INSTRUCTION}]
        for r in rows:
            # Chat API expects roles 'user' or 'assistant'
            role = r["role"]
            messages.append({"role": role, "content": r["content"]})
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"DB read error: {e}")

    # Call the model with the conversation history
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=600,
            temperature=0.18
        )
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"OpenAI API error: {e}")

    # Extract assistant reply and save it
    try:
        assistant_content = response.choices[0].message["content"]
    except Exception:
        assistant_content = getattr(
            response.choices[0].message, "content", str(response))

    try:
        cur.execute(
            "INSERT INTO messages (submission_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (input.submission_id, "assistant",
             assistant_content, datetime.utcnow().isoformat())
        )
        conn.commit()
    except Exception as e:
        # still return assistant reply even if saving fails
        print("DB save error (assistant):", e)

    # Fetch latest conversation rows to return
    try:
        cur.execute(
            "SELECT id, role, content, created_at FROM messages WHERE submission_id = ? ORDER BY id ASC", (input.submission_id,))
        conv_rows = cur.fetchall()
        conv = [{"id": r["id"], "role": r["role"], "content": r["content"],
                 "created_at": r["created_at"]} for r in conv_rows]
    except Exception as e:
        conn.close()
        raise HTTPException(
            status_code=500, detail=f"DB read error after save: {e}")

    conn.close()
    return {"assistant_reply": assistant_content, "conversation": conv}


@app.get("/submissions")
def list_submissions(limit: int = 50):
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, symptoms, reply, triage_level, triage_reason, created_at FROM submissions ORDER BY id DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        conn.close()
        results = []
        for r in rows:
            results.append({
                "id": r["id"],
                "symptoms": r["symptoms"],
                "reply": r["reply"],
                "triage_level": r["triage_level"],
                "triage_reason": r["triage_reason"],
                "created_at": r["created_at"]
            })
        return JSONResponse(content={"submissions": results})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB read error: {e}")
