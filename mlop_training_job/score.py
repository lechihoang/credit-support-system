import json
import logging
import os
from pathlib import Path

import joblib
import pandas as pd
from azureml.ai.monitoring import Collector

model = None
vectorizer = None
label_encoder = None
inputs_collector = None
outputs_collector = None
model_name = None
deployment_name = None


def find_file(root, name):
    matches = list(Path(root).rglob(name))
    if not matches:
        raise FileNotFoundError(f"Cannot find {name} under {root}")
    return matches[0]


def init():
    global model, vectorizer, label_encoder, inputs_collector, outputs_collector, model_name, deployment_name

    model_dir = os.getenv("AZUREML_MODEL_DIR")
    if not model_dir:
        raise RuntimeError("AZUREML_MODEL_DIR is not set")

    # Lấy tên model từ biến môi trường hoặc từ folder name
    model_name = os.environ.get("AZUREML_MODEL_NAME", Path(model_dir).name)
    deployment_name = os.environ.get("MODEL_DEPLOYMENT_NAME", "unknown")

    model = joblib.load(find_file(model_dir, "model.pkl"))
    vectorizer = joblib.load(find_file(model_dir, "vectorizer.pkl"))
    label_encoder = joblib.load(find_file(model_dir, "label_encoder.pkl"))
    
    # Sử dụng tên dành riêng 'model_inputs' và 'model_outputs' chuẩn SDK v2
    inputs_collector = Collector(name='model_inputs')
    outputs_collector = Collector(name='model_outputs')
    
    logging.info(f"Model {model_name} and Data Collectors loaded successfully.")


def run(raw_data):
    try:
        payload = json.loads(raw_data)
        input_list = payload["data"]
        
        # 1. Thu thập Input và lấy context
        input_df = pd.DataFrame(input_list)
        context = inputs_collector.collect(input_df)

        # 2. Dự báo
        texts = [row["text"] for row in input_list]
        features = vectorizer.transform(texts)
        predictions = model.predict(features)
        labels = label_encoder.inverse_transform(predictions).tolist()

        # 3. Thu thập Output kèm context để mapping
        output_df = pd.DataFrame({"predictions": labels})
        outputs_collector.collect(output_df, context)

        return {
            "predictions": labels,
            "deployment": deployment_name,
        }
    except Exception as error:
        logging.exception("Scoring failed")
        return {"error": str(error)}
