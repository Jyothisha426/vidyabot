import requests
from langdetect import detect

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "gemma2:2b"

def detect_language(text):
    try:
        lang = detect(text)
        if lang == "te": return "Telugu"
        elif lang == "hi": return "Hindi"
        else: return "English"
    except:
        return "English"

def is_hint_request(text):
    return any(w in text.lower() for w in ["hint", "clue", "stuck", "dont know", "don't know"])

def get_hint_level_prompt(hint_count, language):
    if language == "Telugu":
        levels = [
            "చిన్న సూచన మాత్రమే ఇవ్వండి - సమాధానం చెప్పకండి.",
            "కొంచెం పెద్ద సూచన ఇవ్వండి, మొదటి అడుగు చూపించండి.",
            "దాదాపు పూర్తి సహాయం ఇవ్వండి, చివరి అడుగు మాత్రం విద్యార్థికి వదిలేయండి."
        ]
    elif language == "Hindi":
        levels = [
            "केवल एक छोटा संकेत दें - उत्तर मत बताएं।",
            "थोड़ा बड़ा संकेत दें, पहला कदम दिखाएं।",
            "लगभग पूरी मदद करें, बस आखिरी कदम छात्र के लिए छोड़ें।"
        ]
    else:
        levels = [
            "Give only a tiny one-sentence hint. Do NOT give the answer.",
            "Give a medium hint showing the first step. Still no full answer.",
            "Give a large hint with most working shown. Leave only the final step for the student."
        ]
    return levels[min(hint_count - 1, 2)]

def get_system_prompt(language, subject, class_level, student_name, hint_count=0, topic="general"):
    if language == "Telugu":
        lang_rule = "MANDATORY: తెలుగులో మాత్రమే జవాబు ఇవ్వాలి. ఆంగ్లం వాడకండి."
    elif language == "Hindi":
        lang_rule = "MANDATORY: केवल हिंदी में जवाब दें। अंग्रेजी मत बोलो।"
    else:
        lang_rule = "Reply in simple clear English only."

    if topic and topic != "general":
        topic_line = "TODAY'S LESSON TOPIC: " + topic + " (part of " + subject + " Class " + class_level + "). Keep all questions and explanations strictly about this topic."
    else:
        topic_line = "Help the student with any " + subject + " Class " + class_level + " question."

    hint_rule = ""
    if hint_count > 0:
        hint_rule = "\nHINT LEVEL " + str(hint_count) + ": " + get_hint_level_prompt(hint_count, language)

    prompt = "You are VidyaBot, a warm patient tutor.\n"
    prompt += "Student name: " + student_name + " (this is just their name, NOT a topic).\n"
    prompt += "\n" + lang_rule + "\n"
    prompt += "\n" + topic_line + "\n"
    prompt += hint_rule
    prompt += """
STRICT RULES:
1. NEVER give the direct answer unless hint level 3.
2. Ask guiding questions about the LESSON TOPIC only.
3. Max 3 sentences per reply.
4. End with exactly one question about the topic.
5. No meta-commentary. No "Explanation:" or "Note:".
6. Be encouraging. Never discuss the student's name as a subject.
"""
    return prompt

def build_prompt(message, history, student_name, subject, class_level, language, hint_count, topic):
    system = get_system_prompt(language, subject, class_level, student_name, hint_count, topic)
    prompt = system + "\n"
    for msg in history[-6:]:
        role = "Student" if msg["role"] == "user" else "VidyaBot"
        prompt += role + ": " + msg["content"] + "\n"
    prompt += "Student: " + message + "\nVidyaBot:"
    return prompt

def chat_with_tutor(message, history, student_name, subject, class_level, hint_count=0, topic="general"):
    language = detect_language(message)
    if is_hint_request(message):
        hint_count += 1
    prompt = build_prompt(message, history, student_name, subject, class_level, language, hint_count, topic)

    try:
        r = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 150,
                "stop": ["Student:", "Explanation:", "Note:"]
            }
        }, timeout=120)
        r.raise_for_status()
        return r.json().get("response", "").strip(), language, hint_count
    except requests.exceptions.ConnectionError:
        return "VidyaBot is not connected. Please make sure Ollama is running.", "English", hint_count
    except Exception as e:
        return "Error: " + str(e), "English", hint_count

def check_ollama_running():
    try:
        return requests.get("http://localhost:11434/api/tags", timeout=5).status_code == 200
    except:
        return False
