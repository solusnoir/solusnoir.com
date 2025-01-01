from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import traceback
import openai
import logging
from dotenv import load_dotenv
from PIL import Image, ImageDraw
import random

# Initialize logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configuration
class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    RESULTS_FOLDER = os.path.join(BASE_DIR, 'results')
    ALLOWED_EXTENSIONS = {'mp3', 'wav', 'm4a', 'flac', 'png'}
    SERVICE_ACCOUNT_FILE = os.path.join(os.getcwd(), 'solusnoir-446321-79801a466e30.json')
    BEATS_FOLDER_ID = '1TYAR-H1YPPvoZprwCy2Chr1w2bVC6jad'  # Folder for beats
    UPLOADS_FOLDER_ID = '16dv0flzGnrHjlSGK_ykGEYtfU7aARLRJ'  # Folder for uploads
    
app.config.from_object(Config)

# Create required directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)

# Initialize Google Drive service
def init_drive_service():
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    credentials = service_account.Credentials.from_service_account_file(
        Config.SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=credentials)

drive_service = init_drive_service()

# Error handling decorator
def handle_errors(f):
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {f.__name__}: {str(e)}\n{traceback.format_exc()}")
            return render_template('error.html', error=str(e)), 500
    decorated_function.__name__ = f.__name__  # Ensure the name is set properly for each view function
    return decorated_function

# Utility functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def list_drive_files():
    try:
        audio_files = {'beats': [], 'demos': [], 'new': []}
        results = drive_service.files().list(
            q=f"'{Config.BEATS_FOLDER_ID}' in parents",
            pageSize=100,
            fields="nextPageToken, files(id, name)"
        ).execute()
        audio_files['beats'] = results.get('files', [])
        
        # List other files
        # Add any other file folder listing logic as needed.
        
        return audio_files
    except Exception as e:
        logger.error(f"Error listing files from Google Drive: {traceback.format_exc()}")
        return {}

def upload_file_to_drive(file_path, is_beat=False):
    try:
        file_metadata = {'name': os.path.basename(file_path)}
        media = MediaFileUpload(file_path, mimetype='audio/mpeg')
        folder_id = Config.BEATS_FOLDER_ID if is_beat else Config.UPLOADS_FOLDER_ID
        file_metadata['parents'] = [folder_id]
        
        file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        logger.info(f"File uploaded to Google Drive with ID: {file['id']}")
        return file['id']
    except Exception as e:
        logger.error(f"Error uploading file to Google Drive: {traceback.format_exc()}")
        return None

def create_random_art(width=800, height=800):
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)

    for _ in range(100):
        shape_type = random.choice(['rectangle', 'ellipse'])
        color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        coordinates = [random.randint(0, width) for _ in range(4)]
        
        if shape_type == 'rectangle':
            draw.rectangle(coordinates, fill=color)
        else:
            draw.ellipse(coordinates, fill=color)

    art_path = os.path.join(app.config['UPLOAD_FOLDER'], 'random_art.png')
    image.save(art_path)
    return art_path

# Routes
@app.route('/')
@handle_errors
def home():
    art_image_path = create_random_art()
    return render_template('index.html', art_image_path=url_for('uploaded_file', filename='random_art.png'))

@app.route('/upload', methods=['GET', 'POST'])
@handle_errors
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        if file and allowed_file(file.filename):
            filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filename)
            
            # Determine if this is a beat file and upload accordingly
            is_beat = 'beat' in file.filename.lower()  # Assumption: file name contains 'beat' for beats
            upload_file_to_drive(filename, is_beat)
            return redirect(url_for('portfolio'))

    return render_template('upload.html')

@app.route('/portfolio')
@handle_errors
def portfolio():
    audio_files_info = list_drive_files()
    
    # Add local files to 'new' section
    local_audio_files = os.listdir(app.config['UPLOAD_FOLDER'])
    for file in local_audio_files:
        if allowed_file(file):
            audio_files_info['new'].append({
                "name": file,
                "url": url_for('uploaded_file', filename=file)
            })
    
    return render_template('portfolio.html', audio_files_info=audio_files_info)

@app.route('/uploads/<filename>')
@handle_errors
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/generate-completion', methods=['POST'])
@handle_errors
def generate_completion():
    data = request.get_json()
    prompt = data.get('prompt', '')

    if not prompt:
        return jsonify({"error": "No prompt provided."}), 400

    try:
        openai.api_key = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")
        response = openai.Completion.create(
            model="text-davinci-003",
            prompt=prompt,
            max_tokens=150
        )
        return jsonify({"completion": response.choices[0].text.strip()}), 200
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        return jsonify({"error": str(e)}), 500

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error="Internal server error"), 500

if __name__ == '__main__':
    app.run(debug=True, port=5004)  # Changed port to 5004 in case port 5003 is occupied
