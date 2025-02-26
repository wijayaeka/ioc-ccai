from flask import Flask, request, jsonify
import openai
import json
import re
import logging
from model_service import classifier  # Import service model

app = Flask(__name__)

# Konfigurasi Logging
logging.basicConfig(level=logging.INFO)

# Konfigurasi OpenAI Client
openai_client = openai.AzureOpenAI(
    api_key="xxxx",
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


if __name__ == '__main__':
    # Gantilah `0.0.0.0` dengan `127.0.0.1` untuk menghindari masalah akses di Windows
    app.run(host='0.0.0.0', port=2000, debug=True)
