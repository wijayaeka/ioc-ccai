from flask import Flask, render_template_string, request, jsonify
import openai
import json
import re
import logging
from model_service import classifier  # Import service model
import os
from dotenv import load_dotenv
load_dotenv()
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pymysql
from flask_mail import Mail, Message
import requests
import logging
from flask_migrate import Migrate






AI_KEY = os.getenv("AI_KEY")
GROQ_KEY = os.getenv("GROQ_KEY")
pymysql.install_as_MySQLdb()

app = Flask(__name__)


# Konfigurasi database MySQL
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("SQLALCHEMY_DATABASE_URI")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

migrate = Migrate(app, db)
# Konfigurasi SMTP Gmail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'threeatech.development@gmail.com'  # Ganti dengan email Anda
app.config['MAIL_PASSWORD'] = 'qqkl imgy rxbq cjrk'  # Ganti dengan password atau App Password
app.config['MAIL_DEFAULT_SENDER'] = 'threeatech.development@gmail.com'
EMAIL_API_URL = "https://xemail.onx.co.id/v1/account/threeatech.development@gmail.com/submit?access_token=b8db9319b16ebca92dd0d6631ca05729db1f43cd690ad0f5862f113541c1f1d5"
ACCESS_TOKEN = "b8db9319b16ebca92dd0d6631ca05729db1f43cd690ad0f5862f113541c1f1d5"  # Ganti dengan token akses yang valid
mail = Mail(app)
OMNIX_API_URL = "https://middleware-staging.omnix.co.id/incoming/email/ems-v2/onx_ioc"
OMNIX_API_URL_DEV = "https://webhook-dev.omnix.co.id/onx_ioc/api/v2/incoming/email/ems-v2"
html_template3 = """
<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Pelaporan Detail</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: 'Arial', sans-serif;
      background-color: #f7f7f7;
      color: #333;
      display: flex;
      justify-content: center;
      align-items: flex-start;
      min-height: 100vh;
      padding: 20px;
    }
    .container {
      background-color: #fff;
      border-radius: 10px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
      max-width: 800px;
      width: 100%;
      padding: 30px;
    }
    .header {
      display: flex;
      align-items: center;
      justify-content: center;
      margin-bottom: 20px;
      border-bottom: 2px solid #e0e0e0;
      padding-bottom: 10px;
    }
    .header img.logo {
      width: 40px;
      height: 40px;
      margin-right: 15px;
    }
    .header h2 {
      font-size: 1.8em;
      color: #4e54c8;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin: 0 auto 20px;
    }
    table th, table td {
      text-align: left;
      padding: 12px 15px;
      border-bottom: 1px solid #e0e0e0;
      vertical-align: top;
    }
    table th {
      width: 30%;
      background-color: #f9f9f9;
      font-weight: 600;
    }
    .note {
      margin-top: 20px;
      padding: 15px;
      border-left: 4px solid #4e54c8;
      background-color: #f0f0f0;
      font-size: 1em;
      line-height: 1.5;
      display: flex;
      align-items: flex-start;
    }
    .note img {
      width: 20px;
      height: 20px;
      margin-right: 10px;
      margin-top: 4px;
    }
    @media (max-width: 600px) {
      .container { padding: 20px; }
      .header { flex-direction: column; text-align: center; }
      .header img.logo { margin-bottom: 10px; }
      table th, table td {
        display: block;
        width: 100%;
      }
      table th {
        background-color: transparent;
        border-bottom: none;
        padding-bottom: 5px;
      }
      table td {
        border-bottom: 1px solid #e0e0e0;
        padding-left: 0;
      }
    }
    .logo {
      height: auto;
      width: 280px;
      object-fit: contain;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <img src="https://recruit.infomedia.co.id/assets/frontend/Logo_Infomedia_color.png" alt="Logo Perusahaan" class="logo" />
      <h2>Detail Laporan</h2>
    </div>

    <table>
  <tbody>
    {% for field in all_fields %}
      <tr>
        <th>{{ field.detail }}</th>
        <td style="background-color: {{ '#fff' if field.value else '#ffd6d6' }};">
          {{ field.value if field.value else "Belum diisi" }}
        </td>
      </tr>
    {% endfor %}
  </tbody>
</table>


    <div class="note">
      <img src="https://static.vecteezy.com/system/resources/previews/012/042/292/original/warning-sign-icon-transparent-background-free-png.png" alt="Alert Icon" />
      <p>
        Mohon maaf, isi pelaporan yang kami butuhkan belum terisi secara keseluruhan.  
        Mohon untuk dapat mengisi tabel ini dengan cara <strong>"Salin Tabel ini secara keseluruhan kemudian isi yang masih belum ada dan kirimkan kembali ke kami ya"</strong>.  
        Terimakasih atas perhatiannya.
      </p>
    </div>
  </div>
</body>
</html>

"""
# Template HTML untuk email
html_template2 = """
<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Pelaporan Detail</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: 'Arial', sans-serif;
      background-color: #f7f7f7;
      color: #333;
      display: flex;
      justify-content: center;
      align-items: flex-start;
      min-height: 100vh;
      padding: 20px;
    }
    .container {
      background-color: #fff;
      border-radius: 10px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
      max-width: 800px;
      width: 100%;
      padding: 30px;
    }
    .header {
      display: flex;
      align-items: center;
      justify-content: center;
      margin-bottom: 20px;
      border-bottom: 2px solid #e0e0e0;
      padding-bottom: 10px;
    }
    .header img.logo {
      width: 40px;
      height: 40px;
      margin-right: 15px;
    }
    .header h2 {
      font-size: 1.8em;
      color: #4e54c8;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin: 0 auto 20px;
    }
    table th, table td {
      text-align: left;
      padding: 12px 15px;
      border-bottom: 1px solid #e0e0e0;
      vertical-align: top;
    }
    table th {
      width: 30%;
      background-color: #f9f9f9;
      font-weight: 600;
    }
    .note {
      margin-top: 20px;
      padding: 15px;
      border-left: 4px solid #4e54c8;
      background-color: #f0f0f0;
      font-size: 1em;
      line-height: 1.5;
      display: flex;
      align-items: flex-start;
    }
    .note img {
      width: 20px;
      height: 20px;
      margin-right: 10px;
      margin-top: 4px;
    }
    @media (max-width: 600px) {
      .container { padding: 20px; }
      .header { flex-direction: column; text-align: center; }
      .header img.logo { margin-bottom: 10px; }
      table th, table td {
        display: block;
        width: 100%;
      }
      table th {
        background-color: transparent;
        border-bottom: none;
        padding-bottom: 5px;
      }
      table td {
        border-bottom: 1px solid #e0e0e0;
        padding-left: 0;
      }
    }
    .logo {
      height: auto;
      width: 280px;
      object-fit: contain;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <img src="https://recruit.infomedia.co.id/assets/frontend/Logo_Infomedia_color.png" alt="Logo Perusahaan" class="logo" />
      <h2>Detail Laporan</h2>
    </div>

    <table>
  <tbody>
    {% for field in all_fields %}
      <tr>
        <th>{{ field.detail }}</th>
        <td style="background-color: {{ '#fff' if field.value else '#ffd6d6' }};">
          {{ field.value if field.value else "Belum diisi" }}
        </td>
      </tr>
    {% endfor %}
  </tbody>
</table>


    <div class="note">
      <img src="https://static.vecteezy.com/system/resources/previews/012/042/292/original/warning-sign-icon-transparent-background-free-png.png" alt="Alert Icon" />
      <p>
        Mohon maaf, isi pelaporan yang kami butuhkan belum terisi secara keseluruhan.  
        Mohon untuk dapat mengisi tabel ini dengan cara <strong>"Salin Tabel ini secara keseluruhan kemudian isi yang masih belum ada dan kirimkan kembali ke kami ya"</strong>.  
        Terimakasih atas perhatiannya.
      </p>
    </div>
  </div>
</body>
</html>
"""
html_template = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kelengkapan Data</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; padding: 20px; }
        .container { max-width: 600px; margin: auto; border: 1px solid #ccc; padding: 20px; border-radius: 10px; }
        h2 { text-align: center; }
        .status { font-weight: bold; color: red; }
        .completed li { color: green; }
        .missing li { color: red; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Informasi Kelengkapan Data</h2>
        <p><strong>Pengirim:</strong> {{ sender }}</p>
        <p class="status">Status: {{ status }}</p>

        {% if missing_fields|length > 0 %}
        <div class="missing">
            <h3>Data yang Belum Lengkap:</h3>
            <ul>
                {% for field in missing_fields %}
                    <li>{{ field.detail }}</li>
                {% endfor %}
            </ul>
        </div>
        {% endif %}

        {% if completed_fields|length > 0 %}
        <div class="completed">
            <h3>Data yang Lengkap:</h3>
            <ul>
                {% for field in completed_fields %}
                    <li>{{ field.detail }}: {{ field.value }}</li>
                {% endfor %}
            </ul>
        </div>
        {% endif %}
    </div>
</body>
</html>

"""
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
    email_sender = db.Column(db.Text, nullable=False)
    message_id = db.Column(db.Text, nullable=False)
    created = db.Column(db.BigInteger, nullable=False)
    content = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=False)
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
    id_layanan = db.Column(db.String(50))
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


class EmailLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    response = db.Column(db.String(255), nullable=False)
    message_id = db.Column(db.String(255), nullable=False)
    send_at = db.Column(db.DateTime, nullable=False)
    queue_id = db.Column(db.String(255), nullable=False)

class EmailResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    account = db.Column(db.String(255))
    message_id = db.Column(db.String(255), unique=True)
    from_id = db.Column(db.String(255))
    from_name = db.Column(db.String(255))
    subject = db.Column(db.Text)
    message_text = db.Column(db.Text)
    message_html = db.Column(db.Text)
    date_middleware = db.Column(db.DateTime)
    date_origin = db.Column(db.DateTime)

    def __init__(self, account, message_id, from_id, from_name, subject, message_text, message_html, date_middleware, date_origin):
        self.account = account
        self.message_id = message_id
        self.from_id = from_id
        self.from_name = from_name
        self.subject = subject
        self.message_text = message_text
        self.message_html = message_html
        self.date_middleware = date_middleware
        self.date_origin = date_origin

class IncomingEmail(db.Model):
    # id = db.Column(db.String(20), primary_key=True)
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    message_id = db.Column(db.String(255))
    rcpt_to = db.Column(db.String(255))
    account = db.Column(db.String(100))
    tenant_code = db.Column(db.String(50))
    mail_from = db.Column(db.String(100))
    subject = db.Column(db.String(255))
    date = db.Column(db.String(50))
    timestamp = db.Column(db.String(50))
    plain_body = db.Column(db.Text)
    html_body = db.Column(db.Text)
    attachment_quantity = db.Column(db.Integer)
    path = db.Column(db.String(50))
    to = db.Column(db.String(255))
    uid = db.Column(db.Integer)
    try_attempt = db.Column(db.Integer)

    def __init__(self, **kwargs):
        for field in kwargs:
            if hasattr(self, field):
                setattr(self, field, kwargs[field])




# Buat tabel di database
with app.app_context():
    # db.drop_all()  # Hapus tabel lama jika perlu
    db.create_all()

def clean_json(json_str):
    # Perbaiki format kutipan ganda di dalam html_body
    json_str = re.sub(r'(<divdir=)"', r'\1\\"', json_str)  # Perbaiki `html_body`

    # Perbaiki format tanggal yang salah
    json_str = re.sub(r'(\d{4}-\d{2}-\d{2})(\d{2}:\s?\d{2}:\s?\d{2})', r'\1 \2', json_str)

    # Perbaiki masalah di "rcpt_to" dan "to"
    json_str = re.sub(r'(\w+@[\w.]+)<(\w+@[\w.]+)>', r'\1', json_str)  # Hapus format <email>

    return json_str
def save_openai_response(response_data):
    with app.app_context():
        for data in response_data:
            # Konversi objek `CompletionUsage` ke dictionary
            usage_dict = data["usage"].__dict__ if hasattr(data["usage"], "__dict__") else data["usage"]

            openai_response = OpenAIResponse(
                prompt=data["prompt"],
                email_sender=data["email_sender"],
                content=data["content"],
                message_id = data["message_id"],
                response=data["response"],
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
            return jsonify({"error": "Message is required"}), 400

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
        if not email_content:
            return jsonify({"error": "emailContent is required"}), 400

        sanitized_content = email_content.replace("\t", "\\t").replace("\n", "\\n")
        cleaned_content = clean_json(email_content)
        email_data = json.loads(cleaned_content)
        in_reply_to = email_data.get("in_reply_to")
        if in_reply_to:
            # print("Email Reply")
            print("Email Reply")
            return jsonify({"error": "email is reply"})
        else:
            print("kosong")
            # Ekstrak dan bersihkan data penting
            from_raw = email_data.get("from", "")
            if "<" in from_raw and ">" in from_raw:
                from_name = from_raw.split("<")[0].strip()
                from_id = from_raw.split("<")[1].replace(">", "").strip()
            else:
                from_name = from_raw
                from_id = email_data.get("mail_from")

            # Parse tanggal dengan try-except fallback
            from datetime import datetime

            def parse_date(date_str, fallback_format="%Y-%m-%d %H:%M:%S"):
                try:
                    return datetime.strptime(date_str.strip(), fallback_format)
                except Exception:
                    return None

            # Buat objek model
            email = IncomingEmail(
                message_id=email_data.get("message_id"),
                from_id=from_id,
                from_name=from_name,
                subject=email_data.get("subject"),
                # rcpt_to=email_data.get("subject"),
                account=email_data.get("account"),
                tenant_code=email_data.get("tenant_code"),
                in_reply_to=email_data.get("in_reply_to"),
                plain_body=email_data.get("plain_body"),
                html_body=email_data.get("html_body"),
                attachment_quantity=email_data.get("attachment_quantity"),
                uid=email_data.get("uid"),
                path=email_data.get("path"),
                to=email_data.get("to"),
                timestamp=email_data.get("timestamp"),
                id_incoming_mail=email_data.get("id_incoming_mail"),
                try_attempt=email_data.get("try_attempt"),
                message_text=email_data.get("plain_body", ""),
                message_html=email_data.get("html_body", ""),
                date_middleware=parse_date(email_data.get("date_imap_reads"), "%Y-%m-%d %H: %M: %S"),
                date_origin=parse_date(email_data.get("timestamp")),
            )
            db.session.add(email)
            db.session.commit()

            try:
                email_data = json.loads(cleaned_content)
                message_id = email_data.get("message_id")
                # in_reply_to = email_data.get("from")
                cleaned_message_id = message_id.strip("<>")
                sender_name = email_data.get("from")
                email_sender = email_data.get("mail_from")
                subject = email_data.get("subject")
                plain_body = email_data.get("plain_body")
                html_body = email_data.get("html_body")

                prompt =f"""
                Ekstrak informasi berikut dari konten email berikut:
    
                \"\"\"{sanitized_content}\"\"\"
    
                Periksa apakah konten email memiliki semua informasi berikut menggunakan pendekatan **similarity matching**:
    
                ---
    
                ### **Instruksi Ekstraksi Data (Rule Baru):**
                Identifikasi dan ekstrak informasi berikut:
    
                1. **Jenis Laporan** (Gangguan/Permintaan)
                2. **Nama Layanan** (Nama layanan yang disebutkan dalam email)
                3. **No. Telp Pelapor** (Nomor telepon dari pelapor)
                4. **Nama Perangkat/Aplikasi** (Nama perangkat atau aplikasi yang dilaporkan)
                5. **URL Aplikasi** (URL aplikasi yang dilaporkan - **opsional**)
                6. **Uraian Permasalahan** (Penjelasan lengkap dan detail permasalahan atau kebutuhan, termasuk jumlah/no. workstation jika relevan)
    
                ---
    
                ### **Cara Menentukan "Uraian Permasalahan"**
                - "Uraian Permasalahan" adalah bagian dalam email yang menjelaskan **tujuan utama pengirim**.
                - Fokus pada **keluhan, permintaan, atau kebutuhan tindakan**.
                - Kata kunci umum: "minta", "tolong", "butuh", "kami ingin", "bisa dibantu", "terjadi masalah".
                - Jika tidak ditemukan, gunakan paragraf terakhir sebagai kandidat uraian.
    
                ---
    
                Jika ada informasi yang tidak ditemukan atau kosong, catat dalam daftar **missing_fields**, kecuali **URL Aplikasi** yang **boleh kosong**.
    
                ---
    
                ### **Format Jawaban:**
                Jika semua data ditemukan:
    
                ```json
                {{
                  "sender": {email_sender},
                  "status": "Lengkap",
                  "completed_fields": [
                    {{
                      "Id": 1,
                      "detail": "Jenis Laporan",
                      "value": "Permintaan"
                    }},
                    {{
                      "Id": 2,
                      "detail": "Nama Layanan",
                      "value": "Layanan Internet XYZ"
                    }},
                    {{
                      "Id": 3,
                      "detail": "No. Telp Pelapor",
                      "value": "081234567890"
                    }},
                    {{
                      "Id": 4,
                      "detail": "Nama Perangkat/Aplikasi",
                      "value": "Aplikasi e-Monitoring"
                    }},
                    {{
                      "Id": 5,
                      "detail": "URL Aplikasi",
                      "value": "http://app.emonitoring.com"
                    }},
                    {{
                      "Id": 6,
                      "detail": "Uraian Permasalahan",
                      "value": "Tolong bantu cek aplikasi e-Monitoring tidak bisa diakses pada 5 workstation sejak pukul 10 pagi."
                    }}
                  ]
                }}
    
        Jika ada data yang tidak ditemukan:
                {{
                      "sender": {email_sender},
                      "status": "Tidak Lengkap",
                      "missing_fields": [
                        {{
                          "Id": 4,
                          "detail": "Nama Perangkat/Aplikasi"
                        }},
                        {{
                          "Id": 6,
                          "detail": "Uraian Permasalahan"
                        }}
                      ],
                      "completed_fields": [
                        {{
                          "Id": 1,
                          "detail": "Jenis Laporan",
                          "value": "Gangguan"
                        }},
                        {{
                          "Id": 2,
                          "detail": "Nama Layanan",
                          "value": "Jaringan Kantor"
                        }},
                        {{
                          "Id": 3,
                          "detail": "No. Telp Pelapor",
                          "value": "085678901234"
                        }}
                      ]
                    }}"""
                # print(prompt)
                # Panggil OpenAI API dengan timeout
                response = openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system",
                         "content": "Kamu adalah asisten yang membantu mengidentifikasi informasi dalam email."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,
                    timeout=10  # Tambahkan timeout 10 detik
                )

                raw_response = response.choices[0].message.content.strip()
                # print(raw_response)
                # Bersihkan output JSON
                clean_json_str = re.sub(r"```json|```", "", raw_response).strip()
                response_data = [{
                    "prompt": '',
                    "email_sender": email_sender,
                    "message_id" : cleaned_message_id,
                    "content": plain_body,
                    "response": raw_response,
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

                # print(jsonify(sent_email))
                try:
                    ai_response = json.loads(clean_json_str)
                except json.JSONDecodeError as e:
                    logging.error(f"JSON Decode Error: {e}")
                    return jsonify({"error": "Invalid JSON response", "raw": clean_json_str}), 500

                status = ai_response["status"]
                if status == "Tidak Lengkap":
                    print(status)
                    sent_email = send_email("IOC", "threeatech.development@gmail.com", email_sender, "IOC Infomedia Nusantara",ai_response)
                elif status == "Lengkap":
                    print(status)
                    sent_api = send_email_to_api(message_id, sender_name, email_sender, subject, plain_body, html_body)
                               # send_email_to_api(message_id, sender, mail_from, subject, plain_body, html_body):
                    print(sent_api)
                return jsonify({"response": ai_response})

            except json.JSONDecodeError as e:
                print("Error parsing JSON:", e)

    except Exception as e:
        logging.error(f"Error in /email-checker: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/receive_data', methods=['POST'])
def receive_data():
    try:
        data = request.json  # Ambil data dari body JSON

        # Pastikan data memiliki format yang benar
        if not data or "auth_id" not in data or "data" not in data or "session_id" not in data:
            return jsonify({"error": "Invalid data format"}), 400

        # Simpan data ke dalam tabel ReceivedData
        received_entry = ReceivedData(
            auth_id=data["auth_id"],
            session_id=data["session_id"],
            request_id=0,
            category=data["data"]["category"],
            category_id=data["data"]["category_id"],
            # id_layanan=data["data"]["id_layanan"],
            detail_sub_category=data["data"]["detail_sub_category"],
            group_level=data["data"]["group_level"],
            impact=data["data"]["impact"],
            layanan=data["data"]["layanan"],
            nama_jenis_perangkat=data["data"]["nama_jenis_perangkat"],
            priority=data["data"]["priority"],
            remark=data["data"]["remark"],
            scope=data["data"]["scope"],
            sentiment=data["data"]["sentiment"],
            sub_category=data["data"]["sub_category"],
            subject=data["data"]["subject"],
            symptom=data["data"]["symptom"],
            type_incident=data["data"]["type_incident"],
            urgency=data["data"]["urgency"]
        )

        db.session.add(received_entry)
        db.session.commit()

        return jsonify({"message": "Data received and saved successfully", "received_id": received_entry.id}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/send_email', methods=['GET'])
def send_email_old():
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

#
# def send_email(from_name,from_address,to_address,subject,text,html):
#     try:
#         payload = {
#             "from": {
#                 "name": from_name,
#                 "address": from_address,
#             },
#             "to": [{"address": to_address}],
#             "subject": subject,
#             "text": text,
#             "html": html
#         }
#
#         # Set header dan parameter
#         headers = {"Content-Type": "application/json"}
#         # params = {"access_token": ACCESS_TOKEN}
#
#         # Kirim request ke API
#         response = requests.post(EMAIL_API_URL, json=payload, headers=headers)
#         print(response)
#         return response
#     except Exception as e:
#         logging.error(f"Error in /email-checker: {e}")
#         return jsonify({"error": str(e)}), 500

# Fungsi untuk mengirim email
def send_email(from_name, from_address, to_address, subject, json_data):
    try:
        missing_fields = json_data.get("missing_fields", [])
        completed_fields = json_data.get("completed_fields", [])
        all_fields = completed_fields + missing_fields

        html_content = render_template_string(
            html_template3,
            sender=json_data.get("sender", "Tidak diketahui"),
            status=json_data.get("status", "Tidak diketahui"),
            missing_fields=missing_fields,
            completed_fields=completed_fields,
            all_fields=all_fields
        )

        text_content = f"Pengirim: {json_data.get('sender', 'Tidak diketahui')}\nStatus: {json_data.get('status', 'Tidak diketahui')}\n\n"

        if missing_fields:
            text_content += "Data yang belum lengkap:\n"
            text_content += "\n".join([f"- {field['detail']}" for field in missing_fields])
            text_content += "\n\n"

        if completed_fields:
            text_content += "Data yang lengkap:\n"
            text_content += "\n".join([f"- {field['detail']}: {field['value']}" for field in completed_fields])

        payload = {
            "from": {"name": from_name, "address": from_address},
            "to": [{"address": to_address}],
            "subject": subject,
            "text": text_content,
            "html": html_content
        }

        response = requests.post(EMAIL_API_URL, json=payload, headers={"Content-Type": "application/json"})
        response_data = response.json()

        if "messageId" in response_data:
            message_id = response_data.get("messageId", "").strip("<>")
            send_at = datetime.fromisoformat(response_data["sendAt"].replace("Z", "+00:00"))

            email_log = EmailLog(
                response=response_data.get("response", "Unknown"),
                message_id=message_id,
                send_at=send_at,
                queue_id=response_data.get("queueId", "Unknown")
            )

            db.session.add(email_log)
            db.session.commit()
            logging.info(f"Email log saved: {message_id}")

        return response_data

    except Exception as e:
        db.session.add(email_log)
        db.session.commit()
        logging.error(f"Error in sending email: {str(e)}")
        return {"error": str(e)}

def save_email_response(response_data):
    try:
        if response_data.get("status") != 200:
            return {"error": "Invalid response from API"}

        email_data = response_data.get("data", {})

        # Buat objek EmailResponse
        email_response = EmailResponse(
            account=email_data.get("account"),
            message_id=email_data.get("message_id"),
            from_id=email_data.get("from_id"),
            from_name=email_data.get("from_name"),
            subject=email_data.get("subject"),
            message_text=email_data.get("message_text"),
            message_html=email_data.get("message_html"),
            date_middleware=datetime.fromisoformat(email_data.get("date_middleware").replace("Z", "")) if email_data.get("date_middleware") else None,
            date_origin=datetime.fromisoformat(email_data.get("date_origin").replace("Z", "")) if email_data.get("date_origin") else None,
        )

        # Simpan ke database
        db.session.add(email_response)
        db.session.commit()

        return jsonify({"message": "Email response saved successfully", "id": email_response.id})

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)})

def send_email_to_api(message_id,sender, mail_from,subject,plain_body,html_body):
    missing_fields = []
    if not message_id:
        missing_fields.append("message_id")
    if not sender:
        missing_fields.append("sender")
    if not mail_from:
        missing_fields.append("mail_from")
    if not subject:
        missing_fields.append("subject")
    if not plain_body:
        missing_fields.append("plain_body")
    if not html_body:
        missing_fields.append("html_body")

    # Jika ada field yang kosong, kembalikan error
    if missing_fields:
        return {"error": "Missing required fields", "missing_fields": missing_fields}
    else:
        # return response.json("{'status':'ok'}")
        headers = {
            "Content-Type": "application/json",
            "Cookie": "Path=/"
        }
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        payload = {
            "id": "AAAAAQAAAPw",
            "message_id": message_id,
            "rcpt_to": "omnixstaging@gmail.com <omnixstaging@gmail.com>",
            "account": "omnixstaging@gmail.com",
            "tenant_code": "onx_dev",
            "from": sender,
            "mail_from": mail_from,
            "in_reply_to": None,
            "references": None,
            "subject": subject,
            "date": current_time,
            "date_imap_reads": current_time,
            "cc": None,
            "plain_body": plain_body,
            "html_body": html_body,
            "textAsHtml": None,
            "type": None,
            "partId": None,
            "attachment_quantity": 0,
            "attachments": [],
            "info_seqno": None,
            "uid": 252,
            "path": "INBOX",
            "to": "omnixstaging@gmail.com <omnixstaging@gmail.com>",
            "timestamp": current_time,
            "bcc": None
        }
        # print(payload)
        try:
            response = requests.post(OMNIX_API_URL, headers=headers, json=payload)
            response.raise_for_status()  # Jika ada error HTTP, akan raise exception
            api_response = response.json()
            # print(api_response)
            save_email_response(api_response)
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e),"Response body": response.text}


if __name__ == '__main__':
    # Gantilah `0.0.0.0` dengan `127.0.0.1` untuk menghindari masalah akses di Windows
    app.run(host='0.0.0.0', port=6400, debug=True)