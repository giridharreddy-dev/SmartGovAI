import os
import json
import uuid
from flask import Flask, render_template, request, jsonify, url_for, session
from google import genai
from google.genai import types
import pdfplumber
from gtts import gTTS
from dotenv import load_dotenv
import database  # our new module

# Optional OCR imports
try:
    import pytesseract
    from pdf2image import convert_from_path
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("⚠️ OCR not available. Install pytesseract and pdf2image for scanned PDF support.")

load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-for-session')  # needed for session

# Initialize database
database.init_db()

# Ensure folders exist
os.makedirs('static/audio', exist_ok=True)
os.makedirs('uploads', exist_ok=True)

# Gemini setup
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("No GEMINI_API_KEY set.")
client = genai.Client(api_key=api_key)
model_name = "gemini-2.5-flash"

with open('schemes_complex.json', 'r', encoding='utf-8') as f:
    schemes = json.load(f)

# ---------- HELPER FUNCTIONS (unchanged from your fixed version) ----------
def extract_text_from_pdf(file_path):
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()

def extract_text_with_ocr_fallback(file_path):
    text = extract_text_from_pdf(file_path)
    if len(text) > 100:
        return text
    if not OCR_AVAILABLE:
        return text
    try:
        print("📄 Low text extraction, trying OCR...")
        images = convert_from_path(file_path, dpi=200)
        ocr_text = ""
        for img in images:
            ocr_text += pytesseract.image_to_string(img, lang='hin+eng') + "\n"
        return ocr_text.strip()
    except Exception as e:
        print(f"OCR failed: {e}")
        return text

def call_gemini_simplify(complex_text, scheme_name):
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
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2
            )
        )
        result = json.loads(response.text)
        if "simplified" not in result or "telugu" not in result:
            raise ValueError("Missing keys")
        return result
    except Exception as e:
        print(f"Gemini error: {e}")
        return {
            "simplified": {
                "eligibility": "Unable to fetch. Please try again.",
                "benefits": "Unable to fetch.",
                "documents": "Unable to fetch.",
                "steps": "Unable to fetch."
            },
            "telugu": {
                "eligibility": "దయచేసి మళ్లీ ప్రయత్నించండి",
                "benefits": "సమాచారం లేదు",
                "documents": "సమాచారం లేదు",
                "steps": "సమాచారం లేదు"
            }
        }

def generate_telugu_audio(telugu_data, scheme_name):
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

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large (max 10MB)'}), 413

# ---------- ROUTES ----------
@app.route('/')
def index():
    return render_template('index.html', schemes=list(schemes.keys()))

@app.route('/simplify', methods=['POST'])
def simplify():
    # --- PDF UPLOAD ---
    if request.files and 'document' in request.files:
        file = request.files['document']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'Only PDF files are supported'}), 400
        
        temp_path = os.path.join('uploads', f"{uuid.uuid4()}.pdf")
        file.save(temp_path)
        try:
            complex_text = extract_text_with_ocr_fallback(temp_path)
        except Exception as e:
            return jsonify({'error': f'Failed to read PDF: {str(e)}'}), 500
        finally:
            os.remove(temp_path)
        
        if not complex_text:
            return jsonify({'error': 'No text could be extracted.'}), 400
        
        scheme_name = os.path.splitext(file.filename)[0]
        source = 'pdf'
        # Log request and get ID
        request_id = database.log_request(scheme_name, source)
        
        ai_result = call_gemini_simplify(complex_text, scheme_name)
        voice_url = generate_telugu_audio(ai_result['telugu'], scheme_name)
        
        return jsonify({
            'request_id': request_id,
            'simplified': ai_result['simplified'],
            'telugu': ai_result['telugu'],
            'voice_url': voice_url
        })
    
    # --- DROPDOWN SCHEME ---
    else:
        data = request.get_json()
        if not data or 'scheme_name' not in data:
            return jsonify({'error': 'Missing scheme_name'}), 400
        
        scheme_name = data['scheme_name']
        scheme_data = schemes.get(scheme_name)
        if not scheme_data:
            return jsonify({'error': 'Scheme not found'}), 404
        
        complex_text = scheme_data.get('original_complex_text')
        if not complex_text:
            return jsonify({'error': 'No description available'}), 400
        
        source = 'dropdown'
        request_id = database.log_request(scheme_name, source)
        
        ai_result = call_gemini_simplify(complex_text, scheme_name)
        voice_url = generate_telugu_audio(ai_result['telugu'], scheme_name)
        
        return jsonify({
            'request_id': request_id,
            'simplified': ai_result['simplified'],
            'telugu': ai_result['telugu'],
            'voice_url': voice_url
        })
    

@app.route('/analytics')
def analytics():
    import sqlite3
    conn = sqlite3.connect('feedback.db')
    cur = conn.cursor()
    cur.execute("""
        SELECT r.scheme_name, 
               COUNT(f.id) as feedback_count,
               ROUND(AVG(f.rating), 2) as avg_rating
        FROM requests r
        LEFT JOIN feedback f ON r.id = f.request_id
        GROUP BY r.scheme_name
        ORDER BY avg_rating DESC
    """)
    stats = cur.fetchall()
    conn.close()
    return render_template('analytics.html', stats=stats)

@app.route('/feedback', methods=['POST'])
def feedback():
    """Receive rating and comment from frontend."""
    data = request.get_json()
    if not data or 'request_id' not in data or 'rating' not in data:
        return jsonify({'error': 'Missing request_id or rating'}), 400
    
    request_id = data['request_id']
    rating = data['rating']
    comment = data.get('comment', '')
    
    try:
        database.save_feedback(request_id, rating, comment)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
