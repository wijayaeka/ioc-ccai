import json
import os
from pathlib import Path
from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline
import openai
import time
from dotenv import load_dotenv
import re

load_dotenv()

# Konfigurasi API Keys
AI_KEY = os.getenv("AI_KEY")
GROQ_KEY = os.getenv("GROQ_KEY")

# Konfigurasi OpenAI Azure
client_openai = openai.AzureOpenAI(
    azure_endpoint="https://openai-ai-gpt.openai.azure.com/",  # Ganti dengan endpoint Azure kamu
    api_key=f"{AI_KEY}",
    api_version="2024-08-01-preview",
)

# Konfigurasi Groq
from groq import Groq

client = Groq(api_key=f"{GROQ_KEY}")


class TextClassifier:
    def __init__(self, model_name="captainrobotfly/ioc_v2", mapping_file="mapping.json",
                 hf_api_key="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"):
        self.device = "cpu"
        print(f"Device set to use {self.device}")

        # Load model & tokenizer dengan API Key
        self.hf_api_key = hf_api_key or os.getenv("HF_API_KEY")
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

    @staticmethod
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

        response = client_openai.chat.completions.create(
            model="gpt-4o",  # Pastikan sesuai dengan deployment di Azure
            messages=[
                {"role": "system", "content": "Anda adalah asisten yang membantu analisis teks."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5
        )

        # print(response.choices[0].message.content) # Mengembalikan teks hasil respons

        # result = response.choices[0].message.content.strip()
        # return json.loads(result)  # Mengubah JSON string ke dictionary
        result = response.choices[0].message.content.strip()
        result = re.sub(r"^```json|^```|```$", "", result, flags=re.MULTILINE).strip()
        # print(result)
        # Coba parsing JSON
        try:
            parsed_result = json.loads(result)  # Mengubah JSON string ke dictionary
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            parsed_result = {"error": "Response is not a valid JSON", "content": result}

        return parsed_result

    @staticmethod
    def analyze_text_groq(text, max_retries=3):
        """Menganalisis sentimen dengan Groq API dan menangani timeout."""
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
                return json.loads(result)  # Mengubah JSON string ke dictionary

            except openai.OpenAIError as e:
                print(f"⚠️ Error: {e}, mencoba ulang ({attempt + 1}/{max_retries})...")
                time.sleep(2 ** attempt)  # Exponential backoff (1s, 2s, 4s, ...)

        return {"sentiment": "Unknown", "conclusion": "Gagal mendapatkan respons", "suggestion": "Coba lagi nanti"}

    def load_mapping(self, mapping_file):
        """Memuat mapping label dari file JSON."""
        path = Path(mapping_file)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {e}")
        return {}  # Mapping kosong jika file tidak ada atau rusak

    @staticmethod
    def safe_get(arr, index, default=""):
        """Mengambil elemen dari list dengan indeks yang aman."""
        return arr[index] if index < len(arr) else default

    def predict(self, text):
        """Melakukan klasifikasi teks dan mengembalikan label dengan deskripsi sebagai objek."""
        res = self.pipeline(text)[0]
        label = res["label"]
        confidence = res["score"]
        # print(confidence)
        # Konversi label "LABEL_X" → "X"
        label_id = label.replace("LABEL_", "")

        # Ambil deskripsi dari mapping
        label_info = self.mapping.get(label_id, {
            "label_value": label_id,
            "label_description": "Deskripsi tidak tersedia"
        })

        label_description = label_info["label_description"]
        values = label_description.split('|')
        # print(f"Predicted label: {label}")
        # print(f"Label description: {label_description}")
        # print(f"Extracted values: {values}")
        # print(f"Layanan: {TextClassifier.safe_get(values, 1)}")  # Cek apakah benar mengambil Garuda EC

        # Dapatkan analisis sentimen
        ai_resp = self.analyze_text_azure(text)
        # print(ai_resp)

        label_info2 = {
            # "Layanan": self.safe_get(values, 1),
            # "Subject": self.safe_get(values, 7),
            # "TypeIncident": self.safe_get(values, 2),
            # "CategoryID": self.safe_get(values, 0),
            # "Category": self.safe_get(values, 3),
            # "SubCategory": self.safe_get(values, 4),
            # "DetailSubCategory": self.safe_get(values, 5),
            # "Scope": self.safe_get(values, 6),
            # "NamaJenisPerangkat": self.safe_get(values, 8),
            # "Urgency": self.safe_get(values, 11),
            # "Impact": self.safe_get(values, 9),
            # "Priority": self.safe_get(values, 10),
            # "Symptom": self.safe_get(values, 7),
            # "Sentiment": ai_resp['sentiment'],
            # "Remark": ai_resp['conclusion'],
            # "GroupLevel": self.safe_get(values, 12),
            "category": self.safe_get(values, 3),
            "category_id": self.safe_get(values, 0),
            "detail_sub_category": self.safe_get(values, 5),
            "group_level": self.safe_get(values, 12),
            "impact": self.safe_get(values, 9),
            "layanan": self.safe_get(values, 1),
            "nama_jenis_perangkat": self.safe_get(values, 8),
            "priority": self.safe_get(values, 10),
            "remark": ai_resp['conclusion'],
            "scope":  self.safe_get(values, 6),
            "sentiment":  ai_resp['sentiment'],
            "sub_category": self.safe_get(values, 4),
            "subject":  self.safe_get(values, 7),
            "symptom": self.safe_get(values, 7),
            "type_incident": self.safe_get(values, 2),
            "urgency":  self.safe_get(values, 11),
        }

        return {"data": label_info2}


# Contoh penggunaan
classifier = TextClassifier()
