import os
import json
import uuid
from flask import Flask, render_template, request, jsonify, url_for
from google import genai
from google.genai import types
import pdfplumber
from gtts import gTTS

from dotenv import load_dotenv
load_dotenv()  # loads variables from .env file

app = Flask(__name__)

# ---------- CONFIGURATION ----------
# Ensure folders exist
os.makedirs('static/audio', exist_ok=True)
os.makedirs('uploads', exist_ok=True)

# Gemini API key from environment variable
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("No GEMINI_API_KEY set for Flask application.")

client = genai.Client(api_key=api_key)
model_name = "gemini-2.5-flash"  # Using a stable, recommended model

# Load schemes with original complex text
with open('schemes_complex.json', 'r', encoding='utf-8') as f:
    schemes = json.load(f)

# ---------- HELPER FUNCTIONS ----------
def extract_text_from_pdf(file_path):
    """Extract all text from a PDF using pdfplumber."""
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()

def call_gemini_simplify(complex_text, scheme_name):
    """Send complex text to Gemini and get simplified + Telugu output."""
    prompt = f"""
You are an expert at simplifying complex government schemes for rural citizens.

Analyze the following scheme description (Name: {scheme_name}):
"{complex_text}"

Extract and simplify the information into four categories using clear, easy‑to‑understand English (6th grade level). Then provide an accurate Telugu translation for each category.

You MUST return the output strictly as a JSON object matching this schema:
{{
    "simplified": {{
        "eligibility": "Who can apply?",
        "benefits": "What do they get?",
        "documents": "What documents are needed?",
        "steps": "How to apply step by step?"
    }},
    "telugu": {{
        "eligibility": "Telugu translation of eligibility",
        "benefits": "Telugu translation of benefits",
        "documents": "Telugu translation of documents",
        "steps": "Telugu translation of steps"
    }}
}}
"""
    # NEW (add this)
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2
        )
    )
    return json.loads(response.text)

def generate_telugu_audio(telugu_data, scheme_name):
    """Combine Telugu fields into one paragraph and generate MP3."""
    telugu_full = (
        f"{scheme_name} పథకం. "
        f"అర్హత: {telugu_data['eligibility']}. "
        f"ప్రయోజనాలు: {telugu_data['benefits']}. "
        f"అవసరమైన పత్రాలు: {telugu_data['documents']}. "
        f"దరఖాస్తు దశలు: {telugu_data['steps']}."
    )
    filename = f"static/audio/{uuid.uuid4()}.mp3"
    tts = gTTS(text=telugu_full, lang="te", slow=False)
    tts.save(filename)
    return url_for('static', filename=filename.split('static/')[1])

# ---------- ROUTES ----------
@app.route('/')
def index():
    return render_template('index.html', schemes=list(schemes.keys()))

@app.route('/simplify', methods=['POST'])
def simplify():
    # Determine if the request contains a file upload or a JSON (dropdown)
    if request.files and 'document' in request.files:
        # ---------- PDF UPLOAD ----------
        file = request.files['document']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'Only PDF files are supported'}), 400
        
        # Save temporarily
        temp_path = os.path.join('uploads', f"{uuid.uuid4()}.pdf")
        file.save(temp_path)
        try:
            complex_text = extract_text_from_pdf(temp_path)
        except Exception as e:
            return jsonify({'error': f'Failed to read PDF: {str(e)}'}), 500
        finally:
            os.remove(temp_path)  # clean up
        
        if not complex_text:
            return jsonify({'error': 'No text could be extracted from the PDF'}), 400
        
        # Use filename as scheme name for display
        scheme_name = os.path.splitext(file.filename)[0]
        ai_result = call_gemini_simplify(complex_text, scheme_name)
        voice_url = generate_telugu_audio(ai_result['telugu'], scheme_name)
        
        return jsonify({
            'simplified': ai_result['simplified'],
            'telugu': ai_result['telugu'],
            'voice_url': voice_url
        })
    
    else:
        # ---------- DROPDOWN SCHEME (JSON input) ----------
        data = request.get_json()
        if not data or 'scheme_name' not in data:
            return jsonify({'error': 'Missing scheme_name'}), 400
        
        scheme_name = data['scheme_name']
        scheme_data = schemes.get(scheme_name)
        if not scheme_data:
            return jsonify({'error': 'Scheme not found'}), 404
        
        complex_text = scheme_data.get('original_complex_text')
        if not complex_text:
            return jsonify({'error': 'No description available for this scheme'}), 400
        
        ai_result = call_gemini_simplify(complex_text, scheme_name)
        voice_url = generate_telugu_audio(ai_result['telugu'], scheme_name)
        
        return jsonify({
            'simplified': ai_result['simplified'],
            'telugu': ai_result['telugu'],
            'voice_url': voice_url
        })

if __name__ == '__main__':
    app.run(debug=True)
