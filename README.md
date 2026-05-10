---
title: VidyaBot
emoji: 📚
colorFrom: green
colorTo: blue
sdk: docker
pinned: false
---

# VidyaBot — Offline AI Tutor for Rural India

> Built for the Gemma 4 Good Hackathon · Future of Education Track

## The Problem

250+ million students in rural India have no access to quality tutors. A student in a village outside Warangal struggles with Class 10 math while a student in Hyderabad has 3 private tutors. VidyaBot bridges this gap.

## What VidyaBot Does

VidyaBot is a fully offline, multilingual AI tutor powered by Gemma 2 (via Ollama) that:

- Runs completely offline on a cheap laptop or phone — no internet needed
- Tutors in Telugu, Hindi, and English — auto-detects the student language
- Uses the Socratic method — never gives direct answers, guides students to discover answers themselves
- Follows the NCERT curriculum for Classes 6-10 (Mathematics, Science, Social Science)
- Tracks student progress locally in SQLite
- Provides progressive hints when students are stuck

## Demo

[![VidyaBot Demo](https://img.shields.io/badge/Watch-Demo%20Video-red?logo=youtube)](YOUR_YOUTUBE_LINK)

## Architecture

`
Student Browser
      |
Flask Backend (app.py)
      |
Ollama (local) --> Gemma 2 2B model
      |
SQLite (progress tracking)
      |
NCERT Curriculum JSON (data/ncert_topics.json)
`

## Tech Stack

| Component | Technology |
|-----------|-----------|
| AI Model | Gemma 2 2B via Ollama |
| Backend | Python + Flask |
| Frontend | Vanilla HTML/CSS/JS |
| Database | SQLite |
| Language Detection | langdetect |
| Deployment | Fully local / offline |

## Key Features

### Socratic Tutoring
VidyaBot never gives direct answers. It asks guiding questions, building the student up to discover the answer themselves — exactly how a great human tutor works.

### Progressive Hint System
Students can type hint at any time. Each hint request gives progressively more guidance:
- Hint 1: Tiny nudge in the right direction
- Hint 2: First step shown
- Hint 3: Near-complete guidance

### Multilingual Auto-Detection
VidyaBot automatically detects whether the student is writing in Telugu, Hindi, or English and responds in the same language — no configuration needed.

### NCERT Curriculum Alignment
Topics are mapped to the official NCERT syllabus for Classes 6-10, covering Mathematics, Science, and Social Science.

## Setup & Installation

### Requirements
- Python 3.9+
- [Ollama](https://ollama.com) installed

### Steps

`ash
# 1. Clone the repo
git clone https://github.com/Jyothisha426/vidyabot.git
cd vidyabot

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Pull the Gemma model
ollama pull gemma2:2b

# 5. Run the app
python app.py
`

Then open http://localhost:5000 in your browser.

## Usage

1. Enter your name, class, subject, and preferred language
2. Pick a topic from the NCERT curriculum
3. Start chatting — ask doubts in Telugu, Hindi, or English
4. Type hint if you get stuck

## Impact

- Works offline — no internet, no data charges
- Runs on basic hardware (tested on 8GB RAM laptop)
- Supports 3 languages spoken by 1.5 billion people
- Covers NCERT curriculum used by 250M+ students
- Free to use — no subscription, no fees

## Tracks

- Main Track
- Future of Education Impact Track
- Ollama Special Technology Track

## License

MIT
