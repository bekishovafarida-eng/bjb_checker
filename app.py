from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
from docx import Document
import os
import re

app = Flask(__name__)

# ===== ПАПКА =====
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ===== OCR (қарапайым placeholder) =====
def extract_text_from_image(image_file):
    return "Бұл жерде OCR жоқ (offline режим)"

# ===== БЖБ ТЕКСЕРУ =====
def check_with_gemini(student_text, answer_key, max_score):
    if answer_key.lower() in student_text.lower():
        score = int(max_score)
        decision = "Дұрыс"
    else:
        score = int(max_score) // 2
        decision = "Жартылай дұрыс"

    return {
        "score": score,
        "decision": decision,
        "feedback": "Offline режимде тексерілді"
    }

# ===== ЭССЕ ҚҰРУ =====
def generate_essay(topic, grade_level, word_count):
    text = f"""
Кіріспе:
{topic} тақырыбы қазіргі таңда өте маңызды.

Негізгі бөлім:
Бұл тақырып бойынша көптеген ойлар бар. Оқушылар үшін бұл тақырыпты түсіну маңызды.

Қорытынды:
Қорытындылай келе, {topic} тақырыбы маңызды және оны терең түсіну қажет.
"""
    return {
        "title": topic,
        "essay": text,
        "intro": "Кіріспе",
        "main": "Негізгі бөлім",
        "conclusion": "Қорытынды",
        "estimated_word_count": word_count
    }

# ===== ЭССЕ ТЕКСЕРУ =====
def check_essay_with_gemini(text, *args):
    return {
        "recognized_text": text,
        "estimated_word_count": len(text.split()),
        "topic_match": "Жартылай сәйкес",
        "mistakes": ["Қарапайым қателер болуы мүмкін"],
        "strengths": ["Жақсы жазылған"],
        "feedback": "Offline режимде тексерілді",
        "corrected_version": text
    }

# ===== ТЕСТ ҚҰРУ =====
def generate_test(subject, grade_level, question_count, difficulty):
    questions = []
    answer_key = {}

    for i in range(1, int(question_count) + 1):
        questions.append({
            "number": i,
            "question": f"{subject} пәнінен {i}-сұрақ",
            "options": {
                "A": "Нұсқа A",
                "B": "Нұсқа B",
                "C": "Нұсқа C",
                "D": "Нұсқа D"
            },
            "answer": "A"
        })
        answer_key[str(i)] = "A"

    return {
        "title": f"{subject} тесті",
        "questions": questions,
        "answer_key": answer_key
    }

# ===== ЖАУАП ПАРСИНГ =====
def parse_student_answers(answer_text):
    normalized = answer_text.upper()
    pairs = re.findall(r"(\d+)\s*([ABCD])", normalized)

    result = {}
    for num, ans in pairs:
        result[num] = ans
    return result

# ===== ТЕСТ ТЕКСЕРУ =====
def check_test_answers(answer_key, student_answers):
    total = len(answer_key)
    correct = 0

    for q, ans in answer_key.items():
        if student_answers.get(q) == ans:
            correct += 1

    wrong = total - correct
    percent = round((correct / total) * 100, 1)

    return {
        "total": total,
        "correct": correct,
        "wrong": wrong,
        "percent": percent
    }

# ===== БАСТЫ БЕТ =====
@app.route("/")
def home():
    return render_template("index.html")

# ===== БЖБ =====
@app.route("/bjb-checker", methods=["GET", "POST"])
def bjb():
    result = None
    student_text = ""

    if request.method == "POST":
        student_text = request.form["answer_key"]
        answer_key = request.form["answer_key"]
        max_score = request.form["max_score"]

        result = check_with_gemini(student_text, answer_key, max_score)

    return render_template("bjb.html", result=result, student_text=student_text)

# ===== ОҚУШЫЛАР =====
@app.route("/students", methods=["GET", "POST"])
def students():
    if request.method == "POST":
        name = request.form["student_name"]
        cls = request.form["class_name"]
        work = request.form["work_type"]
        images = request.files.getlist("images")

        for image in images:
            if image and image.filename:
                filename = secure_filename(image.filename)
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                image.save(filepath)

                with open(filepath + ".txt", "w", encoding="utf-8") as f:
                    f.write(f"{name} | {cls} | {work}")

        return redirect(url_for("success"))

    return render_template("students.html")

# ===== SUCCESS =====
@app.route("/success")
def success():
    return render_template("success.html")

# ===== МҰҒАЛІМ =====
@app.route("/teacher")
def teacher():
    files = []

    for filename in os.listdir(UPLOAD_FOLDER):
        if filename.endswith((".png", ".jpg", ".jpeg")):
            files.append({"filename": filename})

    return render_template("teacher.html", files=files)

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ===== ЭССЕ ҚҰРУ =====
@app.route("/essay-create", methods=["GET", "POST"])
def essay_create():
    essay_result = None

    if request.method == "POST":
        topic = request.form["topic"]
        grade_level = request.form["grade_level"]
        word_count = request.form["word_count"]

        essay_result = generate_essay(topic, grade_level, word_count)

    return render_template("essay_create.html", essay_result=essay_result)

# ===== ЭССЕ ТЕКСЕРУ =====
@app.route("/essay-check", methods=["GET", "POST"])
def essay_check():
    result = None

    if request.method == "POST":
        text = request.form.get("text", "")
        result = check_essay_with_gemini(text)

    return render_template("essay_check.html", essay_check_result=result)

# ===== ТЕСТ ҚҰРУ =====
@app.route("/test-create", methods=["GET", "POST"])
def test_create():
    test_result = None

    if request.method == "POST":
        subject = request.form["subject"]
        grade_level = request.form["grade_level"]
        question_count = request.form["question_count"]
        difficulty = request.form["difficulty"]

        test_result = generate_test(subject, grade_level, question_count, difficulty)

    return render_template("test_create.html", test_result=test_result)

# ===== ТЕСТ ТЕКСЕРУ =====
@app.route("/test-check", methods=["GET", "POST"])
def test_check():
    result = None

    if request.method == "POST":
        student_answers_raw = request.form["student_answers"]

        answer_key = {
            "1": "A",
            "2": "A",
            "3": "A"
        }

        student_answers = parse_student_answers(student_answers_raw)
        result = check_test_answers(answer_key, student_answers)

    return render_template("test_check.html", result=result)

# ===== RUN =====
if __name__ == "__main__":
    app.run(debug=True)