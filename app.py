from flask import Flask, render_template, request
from google.cloud import vision
from google import genai
from dotenv import load_dotenv
from docx import Document
import os
import json

# ENV жүктеу
load_dotenv()

app = Flask(__name__)

# ===== GOOGLE JSON (ENV арқылы) =====
google_json = os.getenv("GOOGLE_CREDENTIALS_JSON")

# файлға жазу
with open("key.json", "w", encoding="utf-8") as f:
    f.write(google_json)

# жүйеге тіркеу
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "key.json"

# ===== API =====
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

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

Тек JSON формат:
{{
  "score": сан,
  "decision": "Дұрыс/Жартылай дұрыс/Қате",
  "feedback": "Қысқаша пікір"
}}
"""

    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    text = response.text.strip()
    text = text.replace("```json", "").replace("```", "").strip()

    return json.loads(text)


# ===== WORD ФАЙЛ =====
def save_to_word(student_text, result, max_score):
    doc = Document()
    doc.add_heading("БЖБ/ТЖБ тексеру", 0)

    doc.add_heading("Мәтін", level=1)
    doc.add_paragraph(student_text)

    doc.add_heading("Нәтиже", level=1)
    doc.add_paragraph(f"Ұпай: {result['score']} / {max_score}")
    doc.add_paragraph(f"Қорытынды: {result['decision']}")
    doc.add_paragraph(f"Кері байланыс: {result['feedback']}")

    doc.save("result.docx")


# ===== WEB =====
@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    student_text = ""
    error = ""

    if request.method == "POST":
        try:
            image = request.files["image"]
            answer_key = request.form["answer_key"]
            max_score = request.form["max_score"]

            student_text = extract_text_from_image(image)
            result = check_with_gemini(student_text, answer_key, max_score)
            save_to_word(student_text, result, max_score)

        except Exception as e:
            error = str(e)

    return render_template("index.html", result=result, student_text=student_text, error=error)


# ===== RUN =====
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))