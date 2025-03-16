from flask import Flask, request, jsonify
from PIL import Image, ExifTags
import openai
import json
import re
import logging
from model_service import classifier  # Import service model
import cv2
import math
import numpy as np
import io
import os
from dotenv import load_dotenv
load_dotenv()
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pymysql
from flask_mail import Mail, Message





AI_KEY = os.getenv("AI_KEY")
GROQ_KEY = os.getenv("GROQ_KEY")
pymysql.install_as_MySQLdb()

app = Flask(__name__)


# Konfigurasi database MySQL
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("SQLALCHEMY_DATABASE_URI_DEV")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Konfigurasi SMTP Gmail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'threeatech.development@gmail.com'  # Ganti dengan email Anda
app.config['MAIL_PASSWORD'] = 'qqkl imgy rxbq cjrk'  # Ganti dengan password atau App Password
app.config['MAIL_DEFAULT_SENDER'] = 'threeatech.development@gmail.com'

mail = Mail(app)

# Konfigurasi Logging
logging.basicConfig(level=logging.INFO)

# Konfigurasi OpenAI Client
openai_client = openai.AzureOpenAI(
    api_key=f"{AI_KEY}",
    azure_endpoint="https://openai-ai-gpt.openai.azure.com/",
    api_version="2024-08-01-preview"
)

class OpenAIResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prompt = db.Column(db.Text, nullable=False)
    created = db.Column(db.BigInteger, nullable=False)
    model = db.Column(db.String(255), nullable=False)
    object_type = db.Column(db.String(255), nullable=False)
    system_fingerprint = db.Column(db.String(255), nullable=True)
    usage = db.Column(db.Text, nullable=False)  # Pastikan bisa menyimpan JSON
    prompt_tokens = db.Column(db.Integer, nullable=False)
    total_tokens = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)  # Tambahkan waktu saat insert

    def __repr__(self):
        return f'<OpenAIResponse {self.model} - {self.created}>'


# Model Database
class RequestData(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    auth_id = db.Column(db.String(50), nullable=False)
    session_id = db.Column(db.String(100), nullable=False)
    service_credential_id = db.Column(db.String(50), nullable=False)
    text_classification_id = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False)

class ResponseData(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    request_id = db.Column(db.Integer, db.ForeignKey('request_data.id'), nullable=False)
    category = db.Column(db.String(100))
    category_id = db.Column(db.String(50))
    detail_sub_category = db.Column(db.String(255))
    group_level = db.Column(db.String(50))
    impact = db.Column(db.String(50))
    layanan = db.Column(db.String(255))
    nama_jenis_perangkat = db.Column(db.String(255))
    priority = db.Column(db.String(50))
    remark = db.Column(db.Text)
    scope = db.Column(db.String(100))
    sentiment = db.Column(db.String(50))
    sub_category = db.Column(db.String(100))
    subject = db.Column(db.String(255))
    symptom = db.Column(db.String(255))
    type_incident = db.Column(db.String(100))
    urgency = db.Column(db.String(100))
# Buat tabel di database
with app.app_context():
    db.create_all()

def save_openai_response(response_data):
    with app.app_context():
        for data in response_data:
            # Konversi objek `CompletionUsage` ke dictionary
            usage_dict = data["usage"].__dict__ if hasattr(data["usage"], "__dict__") else data["usage"]

            openai_response = OpenAIResponse(
                prompt=data["prompt"],
                created=data["created"],
                model=data["model"],
                object_type=data["object"],
                system_fingerprint=data.get("system_fingerprint"),
                usage=json.dumps(usage_dict),  # Simpan dalam bentuk JSON
                prompt_tokens=data["prompt_tokens"],
                total_tokens=data["total_tokens"],
                timestamp=datetime.utcnow()
            )
            db.session.add(openai_response)
        db.session.commit()

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json()
        text = data.get("text")
        if not text:
            return jsonify({"error": "Text is required"}), 400

        request_entry = RequestData(
                auth_id=data["auth_id"],
                session_id=data["session_id"],
                service_credential_id=data["service_creadential_id"],
                text_classification_id=data["text_classification_id"],
                text=data["text"]
        )
        db.session.add(request_entry)
        db.session.commit()

        label_info2 = classifier.predict(text)
        response_entry = ResponseData(
            request_id=request_entry.id,
            category=label_info2["data"]["Category"],
            category_id=label_info2["data"]["CategoryID"],
            detail_sub_category=label_info2["data"]["DetailSubCategory"],
            group_level=label_info2["data"]["GroupLevel"],
            impact=label_info2["data"]["Impact"],
            layanan=label_info2["data"]["Layanan"],
            nama_jenis_perangkat=label_info2["data"]["NamaJenisPerangkat"],
            priority=label_info2["data"]["Priority"],
            remark=label_info2["data"]["Remark"],
            scope=label_info2["data"]["Scope"],
            sentiment=label_info2["data"]["Sentiment"],
            sub_category=label_info2["data"]["SubCategory"],
            subject=label_info2["data"]["Subject"],
            symptom=label_info2["data"]["Symptom"],
            type_incident=label_info2["data"]["TypeIncident"],
            urgency=label_info2["data"]["Urgency"]
        )
        db.session.add(response_entry)
        db.session.commit()
        return jsonify(label_info2)

    except Exception as e:
        logging.error(f"Error in /predict: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/email-checker", methods=["POST"])
def email_checker():
    try:
        email_content = request.form.get("emailContent") or request.data.decode("utf-8")
        email_sender = request.form.get("email") or request.data.decode("utf-8")

        if not email_content:
            return jsonify({"error": "emailContent is required"}), 400

        sanitized_content = email_content.replace("\t", "\\t").replace("\n", "\\n")

        prompt = f"""
        Ekstrak informasi berikut dari konten email berikut:

        \"\"\"{sanitized_content}\"\"\".

        Periksa apakah konten email memiliki semua informasi berikut menggunakan pendekatan **similarity matching**:

        1. **Jenis Laporan** (Permintaan/Gangguan/Informasi)  
        2. **Layanan** (Nama layanan yang disebutkan dalam email)  
        3. **No. Telp Layanan** (Nomor telepon untuk koordinasi layanan)  
        4. **Lokasi** (Lokasi layanan yang disebutkan)  
        5. **Nama Manager Layanan** (Nama manager yang terkait dalam layanan)  
        6. **Nama Pelapor** (Nama orang yang melaporkan permintaan)  
        7. **Email Pelapor** (Email pelapor, jika tidak ada, anggap tidak ditemukan)  
        8. **Nomor Telepon** (Nomor telepon pelapor)  
        9. **Deskripsi** (Isi permintaan atau masalah yang disebutkan dalam email)  

        Jika ada informasi yang tidak ditemukan atau kosong, catat dalam daftar **missing_fields**.  

        **Format Jawaban:**  
        Jika semua data ditemukan:  

        ```json
        
        
        {{
        "sender":{email_sender},
          "status": "Lengkap",
          "completed_fields": [
            {{
              "Id": 1,
              "detail": "Jenis Laporan",
              "value": "Informasi"
            }},
            {{
              "Id": 2,
              "detail": "Layanan",
              "value": "Garuda"
            }}
          ]
        }}
        Jika ada data yang tidak ditemukan:
        {{
        "sender":{email_sender},
  "status": "Tidak Lengkap",
  "missing_fields": [
    {{
      "Id": 5,
      "detail": "Nama Pelapor"
    }},
    {{
      "Id": 6,
      "detail": "Deskripsi"
    }}
  ],
  "completed_fields": [
    {{
      "Id": 1,
      "detail": "Jenis Laporan",
      "value": "Informasi"
    }},
    {{
      "Id": 2,
      "detail": "Layanan",
      "value": "Garuda"
    }}
  ]
}}
"""
        #print(prompt)
        # Panggil OpenAI API dengan timeout
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system",
                 "content": "Kamu adalah asisten yang membantu mengidentifikasi informasi dalam email."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            timeout=10  # Tambahkan timeout 10 detik
        )

        raw_response = response.choices[0].message.content.strip()
        # print(response)
        # Bersihkan output JSON
        clean_json_str = re.sub(r"```json|```", "", raw_response).strip()

        response_data = [{
            "prompt": prompt,
            "created": response.created,
            "model": response.model,
            "object": response.object,
            "system_fingerprint": response.system_fingerprint,
            "usage": response.usage.model_dump(),  # Konversi `response.usage` menjadi dictionary
            "prompt_tokens": response.usage.prompt_tokens,
            "total_tokens": response.usage.total_tokens,

        }]

        # print(response_data)
        save_openai_response(response_data)
        try:
            ai_response = json.loads(clean_json_str)
        except json.JSONDecodeError as e:
            logging.error(f"JSON Decode Error: {e}")
            return jsonify({"error": "Invalid JSON response", "raw": clean_json_str}), 500

        return jsonify({"response": ai_response})

    except Exception as e:
        logging.error(f"Error in /email-checker: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/metaimage", methods=["POST"])
def metaimage():
    try:
        file = request.files['image']
        site_coordinate_location = request.form['site_coordinate_location']
    except KeyError as e:
        return jsonify({'error': f'Missing parameter: {str(e)}'}), 400

    img = get_metadata(file)
    blur_percentage = calculate_blur(file)
    quality = 'Good' if blur_percentage >= 100 else 'Blurred'
    gps_location = ''
    distance2 = 'null'
    distance = 'null'

    img_date = img.get('DateTime', None)
    gps_info = img.get('GPSInfo', {})

    if gps_info:
        try:
            latitude_dms = gps_info.get(2, [float('nan'), float('nan'), float('nan')])
            latitude_hemisphere = gps_info.get(1, ' ')
            longitude_dms = gps_info.get(4, [float('nan'), float('nan'), float('nan')])
            longitude_hemisphere = gps_info.get(3, ' ')

            if is_valid_dms(latitude_dms) and is_valid_hemisphere(latitude_hemisphere):
                latitude = dms_to_decimal(*latitude_dms)
                if latitude_hemisphere == 'S':
                    latitude = -latitude
            else:
                raise ValueError("Invalid latitude DMS or hemisphere")

            if is_valid_dms(longitude_dms) and is_valid_hemisphere(longitude_hemisphere):
                longitude = dms_to_decimal(*longitude_dms)
                if longitude_hemisphere == 'W':
                    longitude = -longitude
            else:
                raise ValueError("Invalid longitude DMS or hemisphere")

            lat_str, lon_str = site_coordinate_location.split()
            site_lat = float(lat_str)
            site_long = float(lon_str)
            distance = haversine(site_lat, site_long, latitude, longitude)
            distance2 = round(distance, 1)
            gps_location = f"{latitude} {longitude}"
        except (ValueError, KeyError) as e:
            print(f"Error processing GPSInfo for image: {e}")
            gps_location = "Invalid GPS data"
            distance2 = 'null'

    image_data = [{
        'distance': distance2,
        'gps_location': gps_location,
        'blur_percentage': blur_percentage,
        'quality': quality,
        'img_date': img_date
    }]

    response_data = {'status': 'success', 'message': 'Image processing initiated!', 'image_data': image_data}
    return jsonify(response_data), 201

def get_metadata(file):
    def convert_value(value):
        if isinstance(value, bytes):
            try:
                value = value.decode('utf-8', 'ignore')
            except UnicodeDecodeError:
                value = value.hex()
        elif isinstance(value, (int, float, str)):
            pass
        elif isinstance(value, (tuple, list)):
            value = [convert_value(v) for v in value]
        elif hasattr(value, 'numerator') and hasattr(value, 'denominator') and value.denominator != 0:
            value = float(value.numerator) / float(value.denominator)
        elif isinstance(value, dict):
            value = {convert_value(k): convert_value(v) for k, v in value.items()}
        else:
            value = str(value)
        return value

    image = Image.open(io.BytesIO(file.read()))
    info = image._getexif()
    file.seek(0)
    if info:
        metadata = {ExifTags.TAGS.get(tag, tag): convert_value(value) for tag, value in info.items() if ExifTags.TAGS.get(tag, tag) != 'MakerNote'}
        return metadata
    return {}

def calculate_blur(file, roi=None):
    file_bytes = np.asarray(bytearray(file.read()), dtype=np.uint8)
    file.seek(0)
    image = cv2.imdecode(file_bytes, cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError("Image could not be loaded. Check the file path.")

    h, w = image.shape
    roi = roi or (w // 4, h // 4, w // 2, h // 2)
    x, y, w, h = roi
    image_roi = image[y:y + h, x:x + w]
    laplacian = cv2.Laplacian(image_roi, cv2.CV_64F)
    return round(laplacian.var()) if laplacian.var() > 0 else 0

def is_valid_dms(dms):
    return len(dms) == 3 and all(isinstance(x, (int, float)) and not math.isnan(x) for x in dms)

def is_valid_hemisphere(hemisphere):
    return hemisphere in ['N', 'S', 'E', 'W']

def dms_to_decimal(degrees, minutes, seconds):
    return degrees + (minutes / 60) + (seconds / 3600)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1_rad, lon1_rad = map(math.radians, [lat1, lon1])
    lat2_rad, lon2_rad = map(math.radians, [lat2, lon2])
    dlat, dlon = lat2_rad - lat1_rad, lon2_rad - lon1_rad
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@app.route('/send_email', methods=['GET'])
def send_email():
    try:
        msg = Message(
            subject="Hello from Flask",
            sender=app.config['MAIL_DEFAULT_SENDER'],
            recipients=["wijayaeka2014@gmail.com.com"],  # Ganti dengan email tujuan
            body="This is a test email sent from a Flask app!"
        )
        mail.send(msg)
        return "Email sent successfully!"
    except Exception as e:
        return f"Error sending email: {str(e)}"

if __name__ == '__main__':
    # Gantilah `0.0.0.0` dengan `127.0.0.1` untuk menghindari masalah akses di Windows
    app.run(host='0.0.0.0', port=6400, debug=True)