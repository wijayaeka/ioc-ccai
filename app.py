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
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("SQLALCHEMY_DATABASE_URI")
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
    __tablename__ = 'request_data'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    auth_id = db.Column(db.String(50), nullable=False)
    session_id = db.Column(db.String(100), nullable=False)
    service_credential_id = db.Column(db.String(50), nullable=False)
    text_classification_id = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False)

    # Relasi ke ResponseData
    responses = db.relationship('ResponseData', backref='request', cascade="all, delete-orphan")


class ResponseData(db.Model):
    __tablename__ = 'response_data'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    request_id = db.Column(db.Integer, db.ForeignKey('request_data.id', ondelete="CASCADE"), nullable=False)
    auth_id = db.Column(db.String(50), nullable=False)  # Relasi ke auth_id dari RequestData
    session_id = db.Column(db.String(100), nullable=False)  # Relasi ke session_id dari RequestData
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



# Model untuk menyimpan data yang diterima dari API GET
class ReceivedData(db.Model):
    __tablename__ = 'received_data'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    auth_id = db.Column(db.String(50), nullable=False)
    session_id = db.Column(db.String(100), nullable=False)
    request_id = db.Column(db.Integer, nullable=False)
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
    db.drop_all()  # Hapus tabel lama jika perlu
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
        text = data.get("message")
        if not text:
            return jsonify({"error": "Text is required"}), 400

        request_entry = RequestData(
                auth_id=data["auth_id"],
                session_id=data["session_id"],
                service_credential_id=data["service_creadential_id"],
                text_classification_id=data["text_classification_id"],
                text=data["message"]
        )
        db.session.add(request_entry)
        db.session.commit()

        label_info2 = classifier.predict(text)
        # Tambahkan data baru ke dalam dictionary
        # label_info2["request_id"] = request_entry.id
        # label_info2["auth_id"] = request_entry.auth_id
        # label_info2["session_id"] = request_entry.session_id
        response_entry = ResponseData(
            request_id=request_entry.id,
            auth_id=request_entry.auth_id,  # Relasi auth_id
            session_id=request_entry.session_id,  # Relasi session_id
            category=label_info2["response"]["category"],
            category_id=label_info2["response"]["category_id"],
            detail_sub_category=label_info2["response"]["detail_sub_category"],
            group_level=label_info2["response"]["group_level"],
            impact=label_info2["response"]["impact"],
            layanan=label_info2["response"]["layanan"],
            nama_jenis_perangkat=label_info2["response"]["nama_jenis_perangkat"],
            priority=label_info2["response"]["priority"],
            remark=label_info2["response"]["remark"],
            scope=label_info2["response"]["scope"],
            sentiment=label_info2["response"]["sentiment"],
            sub_category=label_info2["response"]["sub_category"],
            subject=label_info2["response"]["subject"],
            symptom=label_info2["response"]["symptom"],
            type_incident=label_info2["response"]["type_incident"],
            urgency=label_info2["response"]["urgency"]
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


@app.route('/receive_data', methods=['POST'])
def receive_data():
    try:
        data = request.json  # Ambil data dari body JSON

        # Pastikan data memiliki format yang benar
        if not data or "auth_id" not in data or "data" not in data or "request_id" not in data or "session_id" not in data:
            return jsonify({"error": "Invalid data format"}), 400

        # Simpan data ke dalam tabel ReceivedData
        received_entry = ReceivedData(
            auth_id=data["auth_id"],
            session_id=data["session_id"],
            request_id=data["request_id"],
            category=data["data"]["Category"],
            category_id=data["data"]["CategoryID"],
            detail_sub_category=data["data"]["DetailSubCategory"],
            group_level=data["data"]["GroupLevel"],
            impact=data["data"]["Impact"],
            layanan=data["data"]["Layanan"],
            nama_jenis_perangkat=data["data"]["NamaJenisPerangkat"],
            priority=data["data"]["Priority"],
            remark=data["data"]["Remark"],
            scope=data["data"]["Scope"],
            sentiment=data["data"]["Sentiment"],
            sub_category=data["data"]["SubCategory"],
            subject=data["data"]["Subject"],
            symptom=data["data"]["Symptom"],
            type_incident=data["data"]["TypeIncident"],
            urgency=data["data"]["Urgency"]
        )

        db.session.add(received_entry)
        db.session.commit()

        return jsonify({"message": "Data received and saved successfully", "received_id": received_entry.id}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

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