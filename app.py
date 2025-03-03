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

from dotenv import load_dotenv
load_dotenv()



AI_KEY = os.getenv("AI_KEY")
GROQ_KEY = os.getenv("GROQ_KEY")

app = Flask(__name__)

# Konfigurasi Logging
logging.basicConfig(level=logging.INFO)

# Konfigurasi OpenAI Client
openai_client = openai.AzureOpenAI(
    api_key=f"{AI_KEY}",
    azure_endpoint="https://openai-ai-gpt.openai.azure.com/",
    api_version="2024-08-01-preview"
)


@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json()
        text = data.get("text")
        if not text:
            return jsonify({"error": "Text is required"}), 400

        result = classifier.predict(text)
        return jsonify(result)

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

        prompt = f"""
        Ekstrak informasi berikut dari konten email berikut:
        \"\"\"{sanitized_content}\"\"\".

        Periksa apakah email memiliki semua informasi wajib berikut:
        1. Jenis Laporan (Permintaan/Gangguan/Informasi)
        2. Nama Layanan Request
        3. Lokasi Layanan Request
        4. Nama Manager Layanan yang Request
        5. Nama 
        6. Email 
        7. Nomor Telepon
        8. Deskripsi Request

        Jika ada data yang hilang, berikan daftar field yang tidak ditemukan.
        Jika semua data lengkap, kembalikan JSON berikut:
        {{
          "status": "Lengkap",
          "missing_fields": [],
          "completed_fields": {{"6. Nama": "Dodo"}}
        }}
        Jika ada data yang tidak ditemukan, kembalikan dalam format JSON seperti ini:
        {{
          "status": "Tidak Lengkap",
          "missing_fields": ["1", "2"],
          "completed_fields": {{"5. Nama": "Dodo"}}
        }}

        Jangan berikan kata-kata lain, cukup hanya JSON-nya saja.
        """

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

        # Bersihkan output JSON
        clean_json_str = re.sub(r"```json|```", "", raw_response).strip()

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
if __name__ == '__main__':
    # Gantilah `0.0.0.0` dengan `127.0.0.1` untuk menghindari masalah akses di Windows
    app.run(host='0.0.0.0', port=6400, debug=True)
