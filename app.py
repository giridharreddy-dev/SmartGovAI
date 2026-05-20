from flask import Flask, render_template, request, jsonify
import json

app = Flask(__name__)

# Load schemes from JSON once at startup
with open('schemes.json', 'r', encoding='utf-8') as f:
    schemes = json.load(f)

@app.route('/')
def index():
    return render_template('index.html', schemes=list(schemes.keys()))

@app.route('/simplify', methods=['POST'])
def simplify():
    scheme_name = request.json.get('scheme_name')
    data = schemes.get(scheme_name)
    
    if not data:
        return jsonify({'error': 'Scheme not found'}), 404
    
    # Return precomputed data (no translation, no TTS generation)
    return jsonify({
        'simplified': {
            'eligibility': data['eligibility_en'],
            'benefits': data['benefits_en'],
            'documents': data['documents_en'],
            'steps': data['steps_en']
        },
        'telugu': {
            'eligibility': data['eligibility_te'],
            'benefits': data['benefits_te'],
            'documents': data['documents_te'],
            'steps': data['steps_te']
        },
        'voice_url': data['audio_file']
    })

if __name__ == '__main__':
    app.run(debug=True)