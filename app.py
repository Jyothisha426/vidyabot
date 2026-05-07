from flask import Flask, render_template, request, jsonify, session
import json
from tutor import chat_with_tutor, check_ollama_running
from database import init_db, create_session, save_message, update_progress, get_student_progress

app = Flask(__name__)
app.secret_key = "vidyabot-secret-2026"

init_db()

with open("data/ncert_topics.json", "r", encoding="utf-8") as f:
    CURRICULUM = json.load(f)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/status")
def status():
    return jsonify({"ollama": check_ollama_running(), "model": "gemma2:2b"})

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
    subject = session.get("subject", "mathematics")
    class_level = session.get("class_level", "10")
    language = session.get("language", "English")
    session_id = session.get("session_id")

    welcomes = {
        "English": "Let's study " + topic + " today! First tell me — what do you already know about " + topic + "?",
        "Hindi": "आज हम " + topic + " पढ़ेंगे! पहले बताओ — इसके बारे में आप क्या जानते हैं?",
        "Telugu": "ఈరోజు " + topic + " చదువుదాం! ముందు చెప్పండి — దీని గురించి మీకు ఏమైనా తెలుసా?"
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

    reply, language, new_hint_count = chat_with_tutor(
        user_message, history, student_name, subject, class_level, hint_count, current_topic
    )

    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": reply})
    question_count += 1

    session["history"] = history[-20:]
    session["hint_count"] = new_hint_count
    session["question_count"] = question_count

    save_message(session_id, "assistant", reply)

    understood = any(w in user_message.lower() for w in
                     ["understand", "got it", "thank", "clear", "samajh"])
    update_progress(student_name, subject, current_topic, understood)

    summary = None
    if question_count > 0 and question_count % 5 == 0:
        summary = "Great focus! " + str(question_count) + " questions on " + str(current_topic) + " so far. Keep going!"

    return jsonify({
        "reply": reply,
        "language": language,
        "hint_count": new_hint_count,
        "question_count": question_count,
        "summary": summary
    })

@app.route("/api/progress/<student_name>")
def progress(student_name):
    return jsonify(get_student_progress(student_name))

if __name__ == "__main__":
    print("=" * 50)
    print("  VidyaBot - AI Tutor for Rural India")
    print("=" * 50)
    print("  Ollama:", "RUNNING" if check_ollama_running() else "NOT RUNNING")
    print("  Open http://localhost:5000 in your browser")
    print("=" * 50)
    app.run(debug=True, host="0.0.0.0", port=5000)
