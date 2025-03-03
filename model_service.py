import json
import os
from pathlib import Path
from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline
import torch
import openai
import time
import os
from dotenv import load_dotenv
load_dotenv()



AI_KEY = os.getenv("AI_KEY")
GROQ_KEY = os.getenv("GROQ_KEY")


# Konfigurasi Azure OpenAI
client_openai = openai.AzureOpenAI(
    azure_endpoint="https://your-azure-openai-instance.openai.azure.com/",  # Ganti dengan endpoint Azure kamu
    api_key=f"{AI_KEY}",  # Ganti dengan API Key kamu
    api_version="2023-12-01-preview"  # Sesuaikan dengan versi API yang digunakan
)
DEPLOYMENT_NAME = "gpt-4"


# # Konfigurasi Groq API
# client = openai.OpenAI(
#     api_key="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",  # Ganti dengan API Key Groq kamu
#     base_url="https://api.groq.com/v1"  # Endpoint Groq API
# )
from groq import Groq

client = Groq(
    api_key=f"{GROQ_KEY}",
)
class TextClassifier:
    def __init__(self, model_name="captainrobotfly/ioc_v2", mapping_file="mapping.json", hf_api_key="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"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Device set to use {self.device}")

        # Gunakan API key dari parameter atau environment variable
        self.hf_api_key = hf_api_key or os.getenv("HF_API_KEY")

        # Load model & tokenizer dengan API Key
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_name, token=self.hf_api_key
        ).to(self.device)

        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name, token=self.hf_api_key
        )

        # Load label mapping
        self.mapping = self.load_mapping(mapping_file)

        # Setup pipeline
        self.pipeline = pipeline(
            "text-classification",
            model=self.model,
            tokenizer=self.tokenizer,
            device=0 if self.device == "cuda" else -1
        )

    def analyze_text_azure(text):
        """Menganalisis sentimen dan memberikan kesimpulan serta saran perbaikan menggunakan Azure OpenAI."""

        prompt = f"""
        Saya ingin menganalisis teks berikut:

        "{text}"

        1. Tentukan sentimen teks ini sebagai "Positive", "Negative", atau "Neutral".
        2. Berikan kesimpulan singkat berdasarkan teks ini.
        3. Berikan saran untuk perbaikan atau penyampaian yang lebih baik.

        Jawab dalam format JSON seperti ini:
        {{
            "sentiment": "Positive/Negative/Neutral",
            "conclusion": "Kesimpulan singkat...",
            "suggestion": "Saran perbaikan..."
        }}
        """

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Anda adalah asisten yang membantu analisis teks."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5
        )

        result = response.choices[0].message.content.strip()

        return eval(result)  # Mengonversi JSON string menjadi dictionary

    def analyze_text_groq(text, max_retries=3):
        """Menganalisis sentimen dengan Groq API dan menangani timeout."""

        prompt = f"""
        Saya ingin menganalisis teks berikut:

        "{text}"

        1. Tentukan sentimen teks ini sebagai "Positive", "Negative", atau "Neutral".
        2. Berikan kesimpulan singkat berdasarkan teks ini.
        3. Berikan saran untuk perbaikan atau penyampaian yang lebih baik dengan penjelasan yang singkat, padat, dan jelas.

        Jawab dalam format JSON seperti ini:
        {{
            "sentiment": "Positive/Negative/Neutral",
            "conclusion": "Kesimpulan singkat...",
            "suggestion": "Saran perbaikan..."
        }}
        """

        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model='qwen-2.5-32b',
                    messages=[
                        {"role": "system", "content": "Anda adalah asisten yang membantu analisis teks."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0
                )

                result = response.choices[0].message.content.strip()
                return eval(result)  # Konversi JSON string ke dictionary

            except openai.OpenAIError as e:
                print(f"⚠️ Error: {e}, mencoba ulang ({attempt + 1}/{max_retries})...")
                time.sleep(2 ** attempt)  # Exponential backoff (1s, 2s, 4s, ...)

        return {"sentiment": "Unknown", "conclusion": "Gagal mendapatkan respons", "suggestion": "Coba lagi nanti"}

    # 🔹 Contoh Penggunaan
    # text = "Mohn dibantu di: IP: 172.28.152.157 Kendala: headset tidak ada suaranya, sudah dicoba testcall dan kendala sama (nama Agentnya: Ersyanita)"

    # result = analyze_text_groq(text)
    def load_mapping(self, mapping_file):
        """Memuat mapping label dari file JSON."""
        path = Path(mapping_file)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    mapping = json.load(f)
                    print("Label mapping loaded successfully.")
                    return mapping
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {e}")
        print("Warning: Label mapping not found or invalid. Using default labels.")
        return {}  # Mapping kosong jika file tidak ada atau rusak

    def parse_label_description(description):
        """Mengubah string label_description menjadi dictionary berdasarkan urutan elemen."""
        parts = description.split("|")

        # Definisikan struktur data sesuai urutan elemen dalam stringlabel_
        keys = [
            "Category", "Layanan", "SubCategory", "TypeIncident", "Scope",
            "Priority", "CategoryId", "", "SubCategory", "GroupLevel", "Dampak",
            "IncidentLevel", "ServiceDeskLevel"
        ]

        # Buat dictionary dari hasil split, abaikan jika key kosong
        description_dict = {keys[i]: parts[i] for i in range(min(len(parts), len(keys))) if keys[i]}

        return description_dict

    def safe_get(arr, index, default=""):
        return arr[index] if index < len(arr) else default

    def predict(self, text):
        """Melakukan klasifikasi teks dan mengembalikan label dengan deskripsi sebagai objek."""
        res = self.pipeline(text)[0]
        label = res["label"]
        confidence = res["score"]

        # Konversi label "LABEL_X" → "X"
        label_id = label.replace("LABEL_", "")

        # Ambil deskripsi dari mapping
        label_info = self.mapping.get(label_id, {
            "label_value": label_id,
            "label_description": "Deskripsi tidak tersedia"
        })

        label_description = label_info["label_description"];
        values = label_description.split('|');

        # for index, value in enumerate(values):
        #     print(f"Index {index}: {value}")

        # label_info2 ['result'] = TextClassifier.analyze_text_groq(text)
        # Buat dictionary dengan key yang sesuai
        ai_resp =  TextClassifier.analyze_text_groq(text);
        ai_resp['sentiment'];
        label_info2 = {
            "Layanan": TextClassifier.safe_get(values, 1),
            "Subject": TextClassifier.safe_get(values, 7),
            "TypeIncident": TextClassifier.safe_get(values, 2),
            "CategoryID": TextClassifier.safe_get(values, 0),
            "Category": TextClassifier.safe_get(values, 3),
            "SubCategory": TextClassifier.safe_get(values, 4),  # Diganti ke index 6 agar tidak duplikat
            "DetailSubCategory": TextClassifier.safe_get(values, 5),  # Diganti ke index 7 agar tidak duplikat
            "Scope": TextClassifier.safe_get(values, 6),
            "NamaJenisPerangkat": TextClassifier.safe_get(values, 8),
            "Urgency": TextClassifier.safe_get(values, 11),
            "Impact": TextClassifier.safe_get(values, 9),
            "Priority": TextClassifier.safe_get(values, 10),  # Menggunakan index 9 agar sesuai
            "Symptom": TextClassifier.safe_get(values, 7),
            "Sentiment":  ai_resp['sentiment'],
            "Remark": ai_resp['conclusion'],
            "GroupLevel": TextClassifier.safe_get(values, 12),
        }
        return {
            "category_id": label_info["label_value"],
            "label_description": label_info2,  # Sekarang objek
            "confidence": confidence
        }


# Contoh penggunaan dengan API Key
classifier = TextClassifier()
