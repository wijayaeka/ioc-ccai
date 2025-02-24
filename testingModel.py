import json
from pathlib import Path
from transformers import AutoModelForSequenceClassification, AutoTokenizer, TextClassificationPipeline, pipeline


class PredictorTextClassification:
    def __init__(self, text: str, model_dir="results/model2/model_ioc"):
        self.text = text
        self.path = self.get_latest_checkpoint(model_dir)  # Ambil checkpoint terbaru
        self.mapping_class = json.loads(Path("results/model2/mapping.json").read_text())

    def get_latest_checkpoint(self, model_dir: str) -> str:
        """Mencari checkpoint terbaru berdasarkan angka terbesar."""
        model_path = Path(model_dir)
        checkpoints = sorted(
            [p for p in model_path.iterdir() if p.is_dir() and "checkpoint-" in p.name],
            key=lambda x: int(x.name.split("-")[-1]),
            reverse=True
        )
        return str(checkpoints[0]) if checkpoints else model_dir  # Jika tidak ada checkpoint, gunakan direktori utama

    def __call__(self):
        return self.predict(self.text)

    def predict(self, text: str):
        # model = AutoModelForSequenceClassification.from_pretrained(self.path, ignore_mismatched_sizes=True)
        # tokenizer = AutoTokenizer.from_pretrained(self.path)
        model = AutoModelForSequenceClassification.from_pretrained(self.path, ignore_mismatched_sizes=True).to("cuda")
        tokenizer = AutoTokenizer.from_pretrained(self.path)

        pipe = TextClassificationPipeline(model=model, tokenizer=tokenizer, top_k=1, device=0)
        print(next(model.parameters()).device)

        res = pipe(text)[0][0]

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
            }

        return result


predictor = PredictorTextClassification("Mohon bantuannya rekan untuk pengecekan pada MicroSIP karena call banyak yang terputus (10.1.1.167:9999 local) dan (sip1.onx.co.id:9999). inet disini terpantau aman")
hasil_prediksi = predictor()
print(hasil_prediksi)
