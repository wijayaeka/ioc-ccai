import json
import os
from pathlib import Path
from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline
import torch

class TextClassifier:
    def __init__(self, model_name="captainrobotfly/ccai_coi", mapping_file="label_mapping.json", hf_api_key="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"):
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

    def predict(self, text):
        """Melakukan klasifikasi teks dan mengembalikan label dengan deskripsi."""
        res = self.pipeline(text)[0]
        label = res["label"]  # Misalnya "LABEL_7"
        confidence = res["score"]

        # Konversi label "LABEL_X" → "X"
        label_id = label.replace("LABEL_", "")

        # Ambil deskripsi dari mapping
        label_info = self.mapping.get(label_id, {
            "label_value": label_id,
            "label_description": "Deskripsi tidak tersedia"
        })

        return {
            "category_id": label_info["label_value"],
            "label_description": label_info["label_description"],
            "confidence": confidence
        }

# Contoh penggunaan dengan API Key
classifier = TextClassifier()
