from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from google.cloud import vision
from google import genai
from dotenv import load_dotenv
from docx import Document
from werkzeug.utils import secure_filename
import os
import json

load_dotenv()

app = Flask(__name__)

# ===== ПАПКА =====
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ===== GOOGLE / API =====
google_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
if not google_json:
    raise ValueError("GOOGLE_CREDENTIALS_JSON табылмады")

with open("key.json", "w", encoding="utf-8") as f:
    f.write(google_json)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "key.json"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY табылмады")

vision_client = vision.ImageAnnotatorClient()
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# ===== OCR =====
def extract_text_from_image(image_file):
    content = image_file.read()
    image = vision.Image(content=content)
    response = vision_client.document_text_detection(image=image)

    if response.full_text_annotation.text:
        return response.full_text_annotation.text
    return "Мәтін табылмады"

# ===== ТЕКСЕРУ =====
def check_with_gemini(student_text, answer_key, max_score):
    prompt = f"""
Сен мұғалімнің көмекшісі боласың.
Оқушы жауабын дұрыс жауаппен салыстырып, тексер.

ДҰРЫС ЖАУАП:
{answer_key}

ОҚУШЫ ЖАУАБЫ:
{student_text}

Максималды ұпай: {max_score}

Тек JSON форматында қайтар:
{{
  "score": сан,
  "decision": "Дұрыс/Жартылай дұрыс/Қате",
  "feedback": "Қысқаша қазақша пікір"
}}
"""

    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    text = response.text.strip()
    text = text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)

# ===== WORD =====
def save_to_word(student_text, result, max_score):
    doc = Document()
    doc.add_heading("БЖБ тексеру нәтижесі", 0)

    doc.add_heading("Оқушы жауабы", level=1)
    doc.add_paragraph(student_text)

    doc.add_heading("Нәтиже", level=1)
    doc.add_paragraph(f"Ұпай: {result['score']} / {max_score}")
    doc.add_paragraph(f"Қорытынды: {result['decision']}")
    doc.add_paragraph(f"Кері байланыс: {result['feedback']}")

    doc.save("result.docx")

# ===== БАСТЫ БЕТ =====
@app.route("/")
def home():
    return render_template("index.html")

# ===== БЖБ ТЕКСЕРУ =====
@app.route("/bjb-checker", methods=["GET", "POST"])
def bjb():
    result = None
    student_text = ""
    error = ""
    max_score = ""

    if request.method == "POST":
        try:
            images = request.files.getlist("images")
            answer_key = request.form["answer_key"]
            max_score = request.form["max_score"]

            all_texts = []

            for image in images:
                if image and image.filename:
                    text = extract_text_from_image(image)
                    all_texts.append(text)

            student_text = "\n\n----- КЕЛЕСІ БЕТ -----\n\n".join(all_texts)

            result = check_with_gemini(student_text, answer_key, max_score)
            save_to_word(student_text, result, max_score)

        except Exception as e:
            error = str(e)

    return render_template(
        "bjb.html",
        result=result,
        student_text=student_text,
        error=error,
        max_score=max_score
    )
# ===== ОҚУШЫЛАР =====
@app.route("/students", methods=["GET", "POST"])
def students():
    error = ""

    if request.method == "POST":
        try:
            name = request.form["student_name"]
            cls = request.form["class_name"]
            work = request.form["work_type"]
            images = request.files.getlist("images")

            saved_files = []

            for image in images:
                if image and image.filename:
                    filename = secure_filename(image.filename)
                    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                    image.save(filepath)
                    saved_files.append(filename)

                    with open(filepath + ".txt", "w", encoding="utf-8") as f:
                        f.write(f"{name} | {cls} | {work}")

            return redirect(url_for("success"))

        except Exception as e:
            error = str(e)

    return render_template("students.html", error=error)
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
            info = ""
            txt_path = os.path.join(UPLOAD_FOLDER, filename + ".txt")

            if os.path.exists(txt_path):
                with open(txt_path, "r", encoding="utf-8") as f:
                    info = f.read()

            files.append({
                "filename": filename,
                "info": info
            })

    return render_template("teacher.html", files=files)

# ===== UPLOAD ФАЙЛДАР =====
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ===== RUN =====
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))