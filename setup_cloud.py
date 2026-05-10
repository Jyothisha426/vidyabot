"""
Run this from C:\\Users\\jyoth\\vidyabot\\vidyabot
Creates all files needed for HuggingFace Spaces deployment
"""

# ── app_cloud.py ──────────────────────────────────────────────
APP_CLOUD = '''from flask import Flask, render_template, request, jsonify, session
import json
import os
import requests as http_requests
from database import init_db, create_session, save_message, update_progress, get_student_progress

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "vidyabot-2026")

HF_TOKEN = os.environ.get("HF_TOKEN", "")
HF_MODEL = "google/gemma-2-2b-it"
HF_API_URL = "https://api-inference.huggingface.co/models/" + HF_MODEL

init_db()

with open("data/ncert_topics.json", "r", encoding="utf-8") as f:
    CURRICULUM = json.load(f)

def query_gemma(prompt):
    headers = {"Authorization": "Bearer " + HF_TOKEN}
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 200,
            "temperature": 0.7,
            "return_full_text": False
        }
    }
    try:
        r = http_requests.post(HF_API_URL, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        result = r.json()
        if isinstance(result, list) and len(result) > 0:
            return result[0].get("generated_text", "").strip()
        return "I could not generate a response. Please try again."
    except Exception as e:
        return "Error: " + str(e)

def detect_language(text):
    try:
        from langdetect import detect
        lang = detect(text)
        if lang == "te": return "Telugu"
        elif lang == "hi": return "Hindi"
        else: return "English"
    except:
        return "English"

def build_prompt(message, history, student_name, subject, class_level, hint_count, topic):
    if topic and topic != "general":
        topic_line = "TODAY TOPIC: " + topic + " (" + subject + " Class " + class_level + ")"
    else:
        topic_line = "Subject: " + subject + " Class " + class_level

    hint_rule = ""
    if hint_count == 1:
        hint_rule = "\\nHINT LEVEL 1: Give only a tiny one-sentence hint. No full answer."
    elif hint_count == 2:
        hint_rule = "\\nHINT LEVEL 2: Show the first step. Still no full answer."
    elif hint_count >= 3:
        hint_rule = "\\nHINT LEVEL 3: Give most of the working. Leave final step for student."

    system = """You are VidyaBot, a warm patient tutor.
Student name: """ + student_name + """ (this is their NAME, not a topic).
""" + topic_line + """
RULES: Never give the direct answer. Use Socratic method. Ask guiding questions.
Max 3 sentences. End with one question. Be encouraging.""" + hint_rule + """
"""
    prompt = system + "\\n"
    for msg in history[-6:]:
        role = "Student" if msg["role"] == "user" else "VidyaBot"
        prompt += role + ": " + msg["content"] + "\\n"
    prompt += "Student: " + message + "\\nVidyaBot:"
    return prompt

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/status")
def status():
    return jsonify({"ollama": True, "model": HF_MODEL})

@app.route("/api/start", methods=["POST"])
def start_session():
    data = request.json
    student_name = data.get("student_name", "Student")
    subject = data.get("subject", "mathematics")
    class_level = data.get("class_level", "10")
    language = data.get("language", "English")

    session_id = create_session(student_name, subject, class_level, language)
    session["session_id"] = session_id
    session["student_name"] = student_name
    session["subject"] = subject
    session["class_level"] = class_level
    session["language"] = language
    session["history"] = []
    session["hint_count"] = 0
    session["question_count"] = 0
    session["current_topic"] = None

    key = "class_" + class_level
    topics = CURRICULUM.get(subject, {}).get(key, [])
    return jsonify({"topics": topics, "status": "ok"})

@app.route("/api/begin-topic", methods=["POST"])
def begin_topic():
    data = request.json
    topic = data.get("topic", "general")
    session["current_topic"] = topic
    session["hint_count"] = 0
    session["history"] = []

    student_name = session.get("student_name", "Student")
    language = session.get("language", "English")
    subject = session.get("subject", "mathematics")
    session_id = session.get("session_id")

    welcomes = {
        "English": "Let\'s study " + topic + " today! What do you already know about " + topic + "?",
        "Hindi": "आज हम " + topic + " पढ़ेंगे! इसके बारे में आप क्या जानते हैं?",
        "Telugu": "ఈరోజు " + topic + " చదువుదాం! దీని గురించి మీకు ఏమైనా తెలుసా?"
    }
    welcome = welcomes.get(language, welcomes["English"])
    save_message(session_id, "assistant", welcome)
    return jsonify({"welcome": welcome, "topic": topic})

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    session_id = session.get("session_id")
    if not session_id:
        return jsonify({"error": "No active session."}), 400

    student_name = session.get("student_name", "Student")
    subject = session.get("subject", "mathematics")
    class_level = session.get("class_level", "10")
    history = session.get("history", [])
    hint_count = session.get("hint_count", 0)
    question_count = session.get("question_count", 0)
    current_topic = session.get("current_topic", "general")

    save_message(session_id, "user", user_message)

    hint_words = ["hint", "clue", "stuck", "dont know", "don\'t know"]
    if any(w in user_message.lower() for w in hint_words):
        hint_count += 1

    language = detect_language(user_message)
    prompt = build_prompt(user_message, history, student_name, subject, class_level, hint_count, current_topic)
    reply = query_gemma(prompt)

    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": reply})
    question_count += 1

    session["history"] = history[-20:]
    session["hint_count"] = hint_count
    session["question_count"] = question_count

    save_message(session_id, "assistant", reply)
    understood = any(w in user_message.lower() for w in ["understand", "got it", "thank", "clear"])
    update_progress(student_name, subject, current_topic, understood)

    summary = None
    if question_count % 5 == 0:
        summary = "Great work! " + str(question_count) + " questions on " + str(current_topic) + " so far!"

    return jsonify({
        "reply": reply,
        "language": language,
        "hint_count": hint_count,
        "question_count": question_count,
        "summary": summary
    })

@app.route("/api/progress/<student_name>")
def progress(student_name):
    return jsonify(get_student_progress(student_name))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    print("VidyaBot starting on port", port)
    app.run(host="0.0.0.0", port=port)
'''

# ── Dockerfile ────────────────────────────────────────────────
DOCKERFILE = '''FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data static

EXPOSE 7860

ENV FLASK_ENV=production

CMD ["python", "app_cloud.py"]
'''

# ── requirements.txt (updated) ────────────────────────────────
REQUIREMENTS = '''flask
requests
langdetect
gunicorn
'''

# ── .env.example ─────────────────────────────────────────────
ENV_EXAMPLE = '''HF_TOKEN=your_huggingface_token_here
SECRET_KEY=your_secret_key_here
'''

# Write all files
import os

with open("app_cloud.py", "w", encoding="utf-8") as f:
    f.write(APP_CLOUD)
print("app_cloud.py created")

with open("Dockerfile", "w", encoding="utf-8") as f:
    f.write(DOCKERFILE)
print("Dockerfile created")

with open("requirements.txt", "w", encoding="utf-8") as f:
    f.write(REQUIREMENTS)
print("requirements.txt updated")

with open(".env.example", "w", encoding="utf-8") as f:
    f.write(ENV_EXAMPLE)
print(".env.example created")

print("""
All files created!

Next steps:
1. Run: git add .
2. Run: git commit -m 'Add cloud deployment files'
3. Run: git push

Then we set up HuggingFace Spaces to pull from GitHub.
""")