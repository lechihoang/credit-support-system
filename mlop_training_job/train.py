#!/usr/bin/env python3
"""Train intent classifier (TF-IDF + XGBoost/Logistic Regression) for Azure ML."""

import argparse
import json
import logging
import shutil
import time
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import mlflow
import mlflow.pyfunc
import mltable
import pandas as pd
import xgboost as xgb
from mlflow.models.signature import infer_signature
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    recall_score,
)
from sklearn.preprocessing import LabelEncoder


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
TEXT_COL = "text"
LABEL_COL = "simplified"


def read_df(path: str) -> pd.DataFrame:
    p = Path(path)
    if p.is_dir():
        parquet_file = p / "data.parquet"
        if parquet_file.exists():
            logger.info("Found %s, reading directly as Parquet...", parquet_file)
            return pd.read_parquet(parquet_file)
    logger.info("Loading MLTable from: %s", path)
    return mltable.load(path).to_pandas_dataframe()


def _ensure_empty_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for item in path.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()


def load_data(train_path: str, test_path: str, text_col: str, label_col: str):
    train_df = read_df(train_path)
    test_df = read_df(test_path)

    X_train = train_df[text_col].astype(str).tolist()
    X_test = test_df[text_col].astype(str).tolist()
    y_train_raw = train_df[label_col].astype(str).tolist()
    y_test_raw = test_df[label_col].astype(str).tolist()

    label_encoder = LabelEncoder()
    y_train = label_encoder.fit_transform(y_train_raw)
    y_test = label_encoder.transform(y_test_raw)

    return X_train, X_test, y_train, y_test, label_encoder


def build_model(model_name: str, num_classes: int):
    if model_name == "lr":
        return LogisticRegression(
            C=1.0,
            max_iter=1000,
            class_weight="balanced",
            random_state=42,
            solver="lbfgs",
        )

    return xgb.XGBClassifier(
        max_depth=6,
        learning_rate=0.1,
        n_estimators=200,
        objective="multi:softprob",
        num_class=num_classes,
        eval_metric="mlogloss",
        random_state=42,
        tree_method="hist",
    )


class TextClassifierPyfunc(mlflow.pyfunc.PythonModel):
    def load_context(self, context):
        self.vectorizer = joblib.load(context.artifacts["vectorizer"])
        self.model = joblib.load(context.artifacts["model"])
        self.label_encoder = joblib.load(context.artifacts["label_encoder"])

    def predict(self, context, model_input: pd.DataFrame):
        texts = model_input["text"].astype(str).tolist()
        feats = self.vectorizer.transform(texts)
        preds = self.model.predict(feats)
        return self.label_encoder.inverse_transform(preds)


def save_mlflow_model(model, vectorizer, label_encoder, example_text: str, model_output_dir: Path) -> Path:
    artifacts_dir = model_output_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    model_path = artifacts_dir / "model.pkl"
    vectorizer_path = artifacts_dir / "vectorizer.pkl"
    label_encoder_path = artifacts_dir / "label_encoder.pkl"
    model_config_path = artifacts_dir / "model_config.json"

    joblib.dump(model, model_path)
    joblib.dump(vectorizer, vectorizer_path)
    joblib.dump(label_encoder, label_encoder_path)
    model_config_path.write_text(json.dumps({"model_type": "sklearn_xgb"}), encoding="utf-8")

    example_df = pd.DataFrame({"text": [example_text]})
    example_pred = label_encoder.inverse_transform(model.predict(vectorizer.transform([example_text])))
    signature = infer_signature(example_df, example_pred)

    mlflow_dir = model_output_dir / "mlflow_model"
    # mlflow.save_model requires an empty target folder.
    _ensure_empty_dir(mlflow_dir)
    mlflow.pyfunc.save_model(
        path=str(mlflow_dir),
        python_model=TextClassifierPyfunc(),
        artifacts={
            "model": str(model_path),
            "vectorizer": str(vectorizer_path),
            "label_encoder": str(label_encoder_path),
            "model_config": str(model_config_path),
        },
        input_example=example_df,
        signature=signature,
    )
    return mlflow_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train intent classifier")
    parser.add_argument("--train-path", type=str, required=True)
    parser.add_argument("--test-path", type=str, required=True)
    parser.add_argument("--model", type=str, default="xgb", choices=["xgb", "lr"])
    parser.add_argument("--min-f1-gate", type=float, default=0.85)
    parser.add_argument("--model-output-dir", type=str, default="outputs/model")
    return parser.parse_args()


def main() -> None:
    train_start = time.perf_counter()
    args = parse_args()

    X_train, X_test, y_train, y_test, label_encoder = load_data(
        train_path=args.train_path,
        test_path=args.test_path,
        text_col=TEXT_COL,
        label_col=LABEL_COL,
    )
    num_classes = len(label_encoder.classes_)

    vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2), min_df=2)
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)

    model = build_model(args.model, num_classes)
    model.fit(X_train_vec, y_train)
    train_time_seconds = round(time.perf_counter() - train_start, 3)

    y_pred_train = model.predict(X_train_vec)
    y_pred = model.predict(X_test_vec)

    train_acc = accuracy_score(y_train, y_pred_train)
    train_recall = recall_score(y_train, y_pred_train, average="macro")
    train_f1_macro = f1_score(y_train, y_pred_train, average="macro")
    test_acc = accuracy_score(y_test, y_pred)
    test_recall = recall_score(y_test, y_pred, average="macro")
    test_f1_macro = f1_score(y_test, y_pred, average="macro")
    report_text = classification_report(y_test, y_pred, target_names=label_encoder.classes_, zero_division=0)

    mlflow.log_metrics(
        {
            "train_accuracy": float(train_acc),
            "train_recall": float(train_recall),
            "train_f1_macro": float(train_f1_macro),
            "train_time_seconds": float(train_time_seconds),
            "test_accuracy": float(test_acc),
            "test_recall": float(test_recall),
            "test_f1_macro": float(test_f1_macro),
        }
    )

    cm = confusion_matrix(y_test, y_pred)
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=label_encoder.classes_)
    fig, ax = plt.subplots(figsize=(10, 8))
    disp.plot(ax=ax, cmap="Blues", colorbar=True, xticks_rotation="vertical")
    ax.set_title(f"Confusion Matrix - {args.model}")
    fig.tight_layout()
    mlflow.log_figure(fig, "confusion_matrix.png")
    plt.close(fig)
    logger.info("Confusion matrix labels: %s", list(label_encoder.classes_))
    logger.info("Confusion matrix values: %s", cm.tolist())

    model_output_dir = Path(args.model_output_dir)
    model_output_dir.mkdir(parents=True, exist_ok=True)
    example_text = X_test[0] if X_test else X_train[0]
    mlflow_model_dir = save_mlflow_model(model, vectorizer, label_encoder, example_text, model_output_dir)

    logger.info("Training job completed successfully.")
    logger.info("Training Time (seconds): %.3f", train_time_seconds)
    logger.info("Test Accuracy: %.4f", test_acc)
    logger.info("Test F1 Macro: %.4f", test_f1_macro)
    logger.info("Classification Report:\n%s", report_text)
    logger.info("MLflow model saved at: %s", mlflow_model_dir)

    if float(test_f1_macro) < float(args.min_f1_gate):
        raise RuntimeError(
            f"Quality gate failed: test_f1_macro={test_f1_macro:.4f} < min_f1_gate={args.min_f1_gate:.4f}"
        )
    logger.info("Quality gate passed: test_f1_macro >= %.4f", args.min_f1_gate)


if __name__ == "__main__":
    main()
