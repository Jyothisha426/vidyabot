"""
Fixes:
1. Session issue on HuggingFace - use filesystem sessions
2. undefined response in frontend
"""

# Fix app_cloud.py - use a simple in-memory store instead of Flask session
APP_CLOUD = '''from flask import Flask, render_template, request, jsonify, session
import json
import os
import uuid
import requests as http_requests
from database import init_db, create_session, save_message, update_progress, get_student_progress

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "vidyabot-hf-2026-secret")

HF_TOKEN = os.environ.get("HF_TOKEN", "")
HF_MODEL = "google/gemma-2-2b-it"
HF_API_URL = "https://api-inference.huggingface.co/models/" + HF_MODEL

init_db()

with open("data/ncert_topics.json", "r", encoding="utf-8") as f:
    CURRICULUM = json.load(f)

# In-memory session store (works for demo purposes)
SESSIONS = {}

def query_gemma(prompt):
    if not HF_TOKEN:
        return "HF_TOKEN not set. Please add it in Space settings."
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
            text = result[0].get("generated_text", "").strip()
            return text if text else "I could not generate a response. Please try again."
        elif isinstance(result, dict) and "error" in result:
            return "Model is loading, please wait a moment and try again."
        return "I could not generate a response. Please try again."
    except Exception as e:
        return "Error connecting to AI: " + str(e)

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
        topic_line = "TODAY TOPIC: " + topic + " (" + subject + " Class " + class_level + "). Stay focused on this topic only."
    else:
        topic_line = "Subject: " + subject + " Class " + class_level

    hint_rule = ""
    if hint_count == 1:
        hint_rule = "\\nHINT LEVEL 1: Give only a tiny one-sentence hint. No full answer."
    elif hint_count == 2:
        hint_rule = "\\nHINT LEVEL 2: Show the first step. Still no full answer."
    elif hint_count >= 3:
        hint_rule = "\\nHINT LEVEL 3: Give most of the working. Leave only the final step."

    system = "You are VidyaBot, a warm patient tutor.\\n"
    system += "Student name: " + student_name + " (NAME only, not a topic).\\n"
    system += topic_line + "\\n"
    system += "RULES: Never give the direct answer. Use Socratic method. Ask guiding questions. Max 3 sentences. End with one question. Be encouraging." + hint_rule + "\\n"

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
    return jsonify({"ollama": True, "model": "Gemma 2B (HuggingFace)"})

@app.route("/api/start", methods=["POST"])
def start_session():
    data = request.json
    student_name = data.get("student_name", "Student")
    subject = data.get("subject", "mathematics")
    class_level = data.get("class_level", "10")
    language = data.get("language", "English")

    # Create unique session ID
    sid = str(uuid.uuid4())
    session["sid"] = sid

    db_session_id = create_session(student_name, subject, class_level, language)

    SESSIONS[sid] = {
        "session_id": db_session_id,
        "student_name": student_name,
        "subject": subject,
        "class_level": class_level,
        "language": language,
        "history": [],
        "hint_count": 0,
        "question_count": 0,
        "current_topic": None
    }

    key = "class_" + class_level
    topics = CURRICULUM.get(subject, {}).get(key, [])
    return jsonify({"topics": topics, "status": "ok", "sid": sid})

@app.route("/api/begin-topic", methods=["POST"])
def begin_topic():
    data = request.json
    topic = data.get("topic", "general")
    sid = data.get("sid") or session.get("sid")

    if not sid or sid not in SESSIONS:
        return jsonify({"error": "Session not found"}), 400

    s = SESSIONS[sid]
    s["current_topic"] = topic
    s["hint_count"] = 0
    s["history"] = []

    language = s.get("language", "English")
    welcomes = {
        "English": "Let\'s study " + topic + " today! What do you already know about " + topic + "?",
        "Hindi": "आज हम " + topic + " पढ़ेंगे! इसके बारे में आप क्या जानते हैं?",
        "Telugu": "ఈరోజు " + topic + " చదువుదాం! దీని గురించి మీకు ఏమైనా తెలుసా?"
    }
    welcome = welcomes.get(language, welcomes["English"])
    save_message(s["session_id"], "assistant", welcome)
    return jsonify({"welcome": welcome, "topic": topic})

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message", "").strip()
    sid = data.get("sid") or session.get("sid")

    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    if not sid or sid not in SESSIONS:
        return jsonify({"error": "Session expired. Please refresh and start again."}), 400

    s = SESSIONS[sid]
    student_name = s["student_name"]
    subject = s["subject"]
    class_level = s["class_level"]
    history = s["history"]
    hint_count = s["hint_count"]
    question_count = s["question_count"]
    current_topic = s.get("current_topic", "general")

    save_message(s["session_id"], "user", user_message)

    hint_words = ["hint", "clue", "stuck", "dont know", "don\'t know"]
    if any(w in user_message.lower() for w in hint_words):
        hint_count += 1

    language = detect_language(user_message)
    prompt = build_prompt(user_message, history, student_name, subject, class_level, hint_count, current_topic)
    reply = query_gemma(prompt)

    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": reply})
    question_count += 1

    s["history"] = history[-20:]
    s["hint_count"] = hint_count
    s["question_count"] = question_count

    save_message(s["session_id"], "assistant", reply)
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

# Fix index.html - pass sid with every request
import os

# Read current HTML
with open("templates/index.html", "r", encoding="utf-8-sig") as f:
    html = f.read()

# Add sid tracking - inject after var STATE = {};
old = "var STATE = {};"
new = "var STATE = {};\nvar SID = null;"
if old in html:
    html = html.replace(old, new)
    print("Added SID variable")

# Fix startSession to capture sid
old = '    return jsonify({"topics": topics, "status": "ok"})'
# This is in Python - fix the JS instead

# Fix the fetch /api/start response to capture sid
old_js = "    STATE = {\n      student_name: name,\n      subject: document.getElementById('subject').value,\n      class_level: document.getElementById('classLevel').value,\n      language: document.getElementById('language').value\n    };"
new_js = "    STATE = {\n      student_name: name,\n      subject: document.getElementById('subject').value,\n      class_level: document.getElementById('classLevel').value,\n      language: document.getElementById('language').value\n    };"

# Find and fix the sid capture after fetch
old2 = "    console.log('API /start response:', d);\n    console.log('Topics:', d.topics);"
new2 = "    console.log('API /start response:', d);\n    console.log('Topics:', d.topics);\n    SID = d.sid || null;\n    console.log('SID:', SID);"
if old2 in html:
    html = html.replace(old2, new2)
    print("Fixed SID capture")

# Fix beginTopic to send sid
old3 = "      body: JSON.stringify({topic: selectedTopic})"
new3 = "      body: JSON.stringify({topic: selectedTopic, sid: SID})"
if old3 in html:
    html = html.replace(old3, new3)
    print("Fixed beginTopic sid")

# Fix sendMessage to send sid
old4 = "      body: JSON.stringify({message: msg})"
new4 = "      body: JSON.stringify({message: msg, sid: SID})"
if old4 in html:
    html = html.replace(old4, new4)
    print("Fixed sendMessage sid")

# Fix undefined response
old5 = "    addMsg(d.reply, 'bot');"
new5 = "    addMsg(d.reply || d.error || 'Something went wrong.', 'bot');"
if old5 in html:
    html = html.replace(old5, new5)
    print("Fixed undefined response")

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(html)
print("index.html updated")

with open("app_cloud.py", "w", encoding="utf-8") as f:
    f.write(APP_CLOUD)
print("app_cloud.py updated")

print("\nDone! Now run:")
print("git add .")
print('git commit -m "Fix cloud session handling and undefined response"')
print("git push origin main")
print("git push space main")