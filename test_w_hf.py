import json
from pathlib import Path
from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline
import torch

class TextClassifier:
    def __init__(self, text: str, model_name="captainrobotfly/ccai_coi", mapping_file="label_mapping.json"):
        self.text = text
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Device set to use {self.device}")

        # Load model
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name).to(self.device)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)

        # Load label mapping dari file JSON
        self.mapping = self.load_mapping(mapping_file)

        # Pipeline klasifikasi
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
        return {}  # Kembalikan mapping kosong jika file tidak ditemukan atau rusak

    def predict(self):
        """Melakukan klasifikasi teks dengan label mapping dari JSON."""
        res = self.pipeline(self.text)[0]
        label = res["label"]  # Contoh: "LABEL_7"
        confidence = res["score"]

        # Hapus "LABEL_" agar cocok dengan JSON (ubah ke angka sebagai string)
        label_id = label.replace("LABEL_", "")

        # Pastikan label ada di mapping
        label_info = self.mapping.get(label_id, {
            "label_value": label_id,
            "label_description": "Deskripsi tidak tersedia"
        })

        return {
            "category_id": label_info["label_value"],
            "label_description": label_info["label_description"],
            "confidence": confidence
        }

# Contoh penggunaan
text_input = "Mohon dibantu kendala suara putus-putus layanan CC Bank ICBC di semua seat."
classifier = TextClassifier(text_input)
hasil_prediksi = classifier.predict()
print(hasil_prediksi)
