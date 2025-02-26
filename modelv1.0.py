import pandas as pd
from sklearn.preprocessing import LabelEncoder
import json
import os
from sklearn.model_selection import train_test_split
from datasets import load_dataset, Features, Value, ClassLabel
from transformers import AutoModelForSequenceClassification, AutoTokenizer, Trainer, TrainingArguments, AutoConfig, TrainerCallback
import numpy as np
import evaluate
import time

class CustomCallback(TrainerCallback):
    def __init__(self):
        self.start_time = None
    
    def on_train_begin(self, args, state, control, **kwargs):
        self.start_time = time.time()
        print("Training has started.")
    
    def on_step_end(self, args, state, control, **kwargs):
        if state.global_step % args.logging_steps == 0:
            elapsed_time = time.time() - self.start_time
            steps_per_second = state.global_step / elapsed_time
            remaining_steps = state.max_steps - state.global_step
            estimated_time_left = remaining_steps / steps_per_second if steps_per_second > 0 else 0
            print(f"Step: {state.global_step}/{state.max_steps}")
            print(f"Elapsed Time: {elapsed_time:.2f} seconds")
            print(f"Estimated Time Left: {estimated_time_left:.2f} seconds")
            if state.log_history and 'loss' in state.log_history[-1]:
                print(f"Training Loss: {state.log_history[-1]['loss']:.4f}")
    
    def on_evaluate(self, args, state, control, **kwargs):
        metrics = state.log_history[-1]
        print("Evaluation at step:", state.global_step)
        for key, value in metrics.items():
            if key.startswith('eval_'):
                print(f"{key}: {value:.4f}")

    def on_train_end(self, args, state, control, **kwargs):
        total_time = time.time() - self.start_time
        print("Training has ended.")
        print(f"Total Training Time: {total_time:.2f} seconds")

class ProcessData():
    def __init__(self, service_credential_id: int, df: pd.DataFrame):
        self.service_credential_id = service_credential_id
        self.df = df
        self.location = f"results/model{service_credential_id}"

    def __call__(self):
        print("Data started to be processed")
        self.preprocessing()
        self.training()
        print("Data successfully processed")

    def preprocessing(self):
        print("Preprocessing started")
        df = self.df

        # delete missing value
        df.dropna(inplace=True)

        # delete duplicate
        df.drop_duplicates(inplace=True)
        df.drop_duplicates(subset=['text'], inplace=True, keep=False)

        # delete data if length of text is less than 5 words
        df = df[df['text'].str.split().str.len() >= 5]

        # lowercase
        df['text'] = df['text'].str.lower()

        # create label and mapping
        df['label'] = df['label_value']
        mapping = {}
        if df['label'].dtype != 'int64':
            le = LabelEncoder()
            df['label'] = le.fit_transform(df['label'])
            classes = le.classes_
            for i in range(len(classes)):
                mapping[i] = {
                    'label_value': classes[i],
                    'label_description': df['label_description'][df['label_value'] == classes[i]].iloc[0]
                }
        else:
            classes = [int(i) for i in df['label'].unique()]
            for i in classes:
                mapping[i] = {
                    'label_value': i,
                    'label_description': df['label_description'][df['label'] == i].iloc[0]
                }

        # save data mapping and label
        if not os.path.exists("results"):
            os.makedirs("results")
        if not os.path.exists(self.location):
            os.makedirs(self.location)
        with open(self.location + "/mapping.json", "w") as file:
            file.write(json.dumps(mapping))
        with open(self.location + "/label.txt", "w") as file:
            for item in df['label'].unique():
                file.write(str(item) + "\n")
        
        # split data into train and tes
        df = df[['text', 'label']]
        # Cek distribusi label sebelum split
        print("Distribusi label sebelum split:")
        print(df['label'].value_counts())

        # Hapus label yang kurang dari 2 sampel
        df = df[df.groupby('label')['label'].transform('count') > 1]

        # Cek kembali distribusi setelah filter
        print("Distribusi label setelah filter:")
        print(df['label'].value_counts())

        train_df, test_df = train_test_split(
            df,
            test_size=0.2,
            stratify=df['label'],
            random_state=self.service_credential_id
        )
        train_df.to_csv(self.location + '/train.csv', index=False, encoding='utf-8')
        test_df.to_csv(self.location + '/test.csv', index=False, encoding='utf-8')
        print("Preprocessing completed")

    def training(self):
        print("Training function started")
        with open(self.location + "/label.txt", "r") as f:
            label = [l.strip() for l in f.readlines()]

        feat = Features({"text": Value('string'),  "label": ClassLabel(names=label)})

        data_file = {
            "train": self.location + "/train.csv",
            "test": self.location + "/test.csv"
        }

        dataset = load_dataset("csv", data_files=data_file, features=feat)

        pretrained = r"C:\Users\MSI SHOP ID\.cache\huggingface\hub\models--cahya--bert-base-indonesian-1.5G\snapshots\a4400ab68607dea3f7f1522f9fed74909980bd77"

        tokenizer = AutoTokenizer.from_pretrained(pretrained)

        cfg = AutoConfig.from_pretrained(
            pretrained_model_name_or_path=pretrained,
            id2label={i: l for i, l in enumerate(label)},
            label2id={l: i for i, l in enumerate(label)},
            finetuning_task="single_label_classification",
            max_position_embeddings=4096,
        )

        model = AutoModelForSequenceClassification.from_pretrained(
            pretrained,
            config=cfg,
            ignore_mismatched_sizes=True,
        )

        def tokenize_function(examples):
            return tokenizer(examples["text"], max_length=1024, padding="max_length", truncation=True, return_tensors="pt")


        tokenized_datasets = dataset.map(tokenize_function, batched=True)

        num_label = dataset["train"].features["label"].num_classes

        # def compute_metrics(eval_pred):
        #     prec = evaluate.load("precision")
        #     rec = evaluate.load("recall")
        #     acc = evaluate.load("accuracy")
        #
        #     logits, labels = eval_pred
        #     predictions = np.argmax(logits, axis=-1)
        #     return {
        #         "precision": prec.compute(predictions=predictions, references=labels, average="weighted")['precision'],
        #         "recall": rec.compute(predictions=predictions, references=labels, average="weighted")['recall'],
        #         "accuracy": acc.compute(predictions=predictions, references=labels)['accuracy'],
        #     }
        def compute_metrics(eval_pred):
            prec = evaluate.load("precision")
            rec = evaluate.load("recall")
            acc = evaluate.load("accuracy")

            logits, labels = eval_pred
            predictions = np.argmax(logits, axis=-1)

            precision_score = prec.compute(predictions=predictions, references=labels, average="weighted")['precision']
            recall_score = rec.compute(predictions=predictions, references=labels, average="weighted")['recall']
            accuracy_score = acc.compute(predictions=predictions, references=labels)['accuracy']

            # Tangani jika nilai float, untuk menghindari error AttributeError: 'float' object has no attribute 'size'
            if isinstance(precision_score, float):
                precision_score = float(precision_score)

            if isinstance(recall_score, float):
                recall_score = float(recall_score)

            if isinstance(accuracy_score, float):
                accuracy_score = float(accuracy_score)

            return {
                "precision": precision_score,
                "recall": recall_score,
                "accuracy": accuracy_score,
            }

        model.resize_token_embeddings(len(tokenizer))

        training_args = TrainingArguments(
            output_dir=self.location+"/model_new",
            overwrite_output_dir=True,
            do_train=True,
            do_eval=True,
            logging_first_step=True,
            logging_steps=1000,
            logging_strategy="steps",
            evaluation_strategy="steps",
            eval_steps=1000,
            num_train_epochs=2,
            no_cuda=False,
            per_device_train_batch_size=4,
            per_device_eval_batch_size=4,
            save_strategy="steps",
            save_steps=1000,
        )

        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=tokenized_datasets["train"],
            eval_dataset=tokenized_datasets["test"],
            compute_metrics=compute_metrics,
            tokenizer=tokenizer,
            callbacks=[CustomCallback()]  # Add callbacks here
        )

        trainer.train()

        evaluate.load("precision")
        evaluate.load("recall")
        evaluate.load("accuracy")
        eval_result = trainer.evaluate()
        print(eval_result)

        trainer.save_model(self.location + "/model_new")
        print("Training completed")


file_url = 'data_baru_ioc.xlsx'
df = pd.read_excel(file_url)

service_credential_id = 3

processData = ProcessData(service_credential_id, df)
processData()