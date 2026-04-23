from flask import Flask, render_template, request
from google.cloud import vision
from google import genai
from dotenv import load_dotenv
from docx import Document
import os
import io
import json

load_dotenv()

app = Flask(__name__)

# API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Google Vision JSON кілті
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "dogwood-terra-492109-p4-4aea15c16564.json"

vision_client = vision.ImageAnnotatorClient()
gemini_client = genai.Client(api_key=GEMINI_API_KEY)


def extract_text_from_image(image_file):
    content = image_file.read()
    image = vision.Image(content=content)
    response = vision_client.document_text_detection(image=image)

    if response.full_text_annotation.text:
        return response.full_text_annotation.text
    return "Мәтін табылмады"


def check_with_gemini(student_text, answer_key, max_score):
    prompt = f"""
Сен мұғалімнің көмекшісі боласың.
Оқушы жауабын дұрыс жауаппен салыстырып, алдын ала тексер.

ДҰРЫС ЖАУАП:
{answer_key}

ОҚУШЫ ЖАУАБЫ:
{student_text}

Максималды ұпай: {max_score}

Жауапты тек мына JSON форматында қайтар:
{{
  "score": сан,
  "decision": "Дұрыс/Жартылай дұрыс/Қате",
  "feedback": "Қысқаша қазақша кері байланыс"
}}
"""

    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    text = response.text.strip()
    text = text.replace("```json", "").replace("```", "").strip()

    return json.loads(text)


def save_to_word(student_text, result, max_score):
    doc = Document()
    doc.add_heading("БЖБ/ТЖБ тексеру нәтижесі", 0)

    doc.add_heading("Танылған мәтін", level=1)
    doc.add_paragraph(student_text)

    doc.add_heading("Тексеру нәтижесі", level=1)
    doc.add_paragraph(f"Ұпай: {result['score']} / {max_score}")
    doc.add_paragraph(f"Қорытынды: {result['decision']}")
    doc.add_paragraph(f"Кері байланыс: {result['feedback']}")

    doc.save("result.docx")


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


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)