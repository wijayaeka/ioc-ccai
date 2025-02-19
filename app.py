import json
from pathlib import Path
from flask import Flask, request, jsonify
from transformers import pipeline,AutoModelForSequenceClassification, AutoTokenizer, TextClassificationPipeline
import os
import openai
import json
import re

app = Flask(__name__)


# Konfigurasi Azure OpenAI
# Konfigurasi Azure OpenAI Client
openai_client = openai.AzureOpenAI(
    api_key="b98cbbc0f92946588a1f164c728a4e14",
    azure_endpoint="https://openai-ai-gpt.openai.azure.com/",
    api_version="2024-08-01-preview"
)

# AZURE_OPENAI_ENDPOINT = "https://openai-ai-gpt.openai.azure.com/"
# AZURE_OPENAI_API_KEY = "b98cbbc0f92946588a1f164c728a4e14"
# AZURE_OPENAI_API_DEPLOYMENT_NAME = "gpt-4o"
# AZURE_OPENAI_API_VERSION = "2024-08-01-preview"
#
# openai.api_type = "azure"
# openai.api_base = AZURE_OPENAI_ENDPOINT
# openai.api_key = AZURE_OPENAI_API_KEY
# openai.api_version = AZURE_OPENAI_API_VERSION


class PredictorTextClassification:
    def __init__(self, model_dir="results/model1/hasilmodel"):
        self.path = self.get_latest_checkpoint(model_dir)  # Ambil checkpoint terbaru
        self.mapping_class = json.loads(Path("results/model1/mapping.json").read_text())

        # Load model & tokenizer sekali saja saat startup
        self.model = AutoModelForSequenceClassification.from_pretrained(self.path, ignore_mismatched_sizes=True)
        self.tokenizer = AutoTokenizer.from_pretrained(self.path)
        self.pipe = TextClassificationPipeline(model=self.model, tokenizer=self.tokenizer, top_k=1)

    def get_latest_checkpoint(self, model_dir: str) -> str:
        """Mencari checkpoint terbaru berdasarkan angka terbesar."""
        model_path = Path(model_dir)
        checkpoints = sorted(
            [p for p in model_path.iterdir() if p.is_dir() and "checkpoint-" in p.name],
            key=lambda x: int(x.name.split("-")[-1]),
            reverse=True
        )
        return str(checkpoints[0]) if checkpoints else model_dir  # Jika tidak ada checkpoint, gunakan direktori utama

    def predict(self, text: str):
        print(text)
        res = self.pipe(text)[0][0]
        result = self.mapping_class[str(res['label'])]
        result['confidence'] = res['score']

        detail = result["label_description"].split(" | ")
        if len(detail) == 5:
            result = {
                "category_id": result['label_value'],
                "mainCategory": detail[0],
                "category": detail[1],
                "subCategory": detail[2],
                "detailSubCategory": detail[3],
                "detailSubCategory2": detail[4],
                "confidence": res['score']
            }
        print(result);
        return result


# Load model saat startup
predictor = PredictorTextClassification()


@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json()
        text = data.get("text")
        if not text:
            return jsonify({"error": "Text is required"}), 400

        result = predictor.predict(text)
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/email-checker", methods=["POST"])
def email_checker():
    email_content = request.form.get("emailContent") or request.data.decode("utf-8")

    if not email_content:
        return jsonify({"error": "emailContent is required"}), 400

    sanitized_content = email_content.replace("\t", "\\t").replace("\n", "\\n")

    prompt = f"""
Ekstrak informasi berikut dari konten email berikut:
\"\"\"{sanitized_content}\"\"\"

Periksa apakah email memiliki semua informasi wajib berikut:
1. Jenis Laporan (Permintaan/Gangguan/Informasi)
2. Nama Layanan Request
3. Lokasi Layanan Request
4. Nama Manager Layanan yang Request
5. Nama 
6. Email 
7. Nomor Telepon
8. Deskripsi Request
Jika ada data yang hilang, berikan daftar field yang tidak ditemukan dengan.
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
Jawab missing_fields hanya dengan nomor nya saja.
Jawab completed_fields dengan informasi dari data yang ditemukan.
"""

    try:
        # response = openai.ChatCompletion.create(
        #     engine=AZURE_OPENAI_API_DEPLOYMENT_NAME,
        #     messages=[{"role": "system", "content": "Kamu adalah asisten yang membantu mengidentifikasi informasi dalam email."},
        #               {"role": "user", "content": prompt}],
        #     temperature=0
        # )
        #
        # ai_response = response["choices"][0]["message"]["content"].strip()
        #
        # # Bersihkan output JSON agar bisa di-parse dengan benar
        # ai_response = ai_response.replace("```json", "").replace("```", "").strip()
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Kamu adalah asisten yang membantu mengidentifikasi informasi dalam email."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )

        # Cetak respons
        #  resp = (response.choices[0].message.content)

        # 1. Hapus ```json dan ``` dari teks
        clean_json_str = re.sub(r"```json|```", "", response.choices[0].message.content).strip()

        # 2. Parsing JSON string ke dictionary
        ai_response = json.loads(clean_json_str)

        return jsonify({"response": ai_response})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=2000, debug=True)
