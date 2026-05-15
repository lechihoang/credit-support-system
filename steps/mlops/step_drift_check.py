from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import mltable
import pandas as pd
from evidently.metric_preset import DataDriftPreset
from evidently.report import Report

TEXT_COL = "text"
CLOUD_EVENT_TYPE = "azureml.inference.model_inputs"
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("mlops.drift_check")


def read_reference_df(path: str) -> pd.DataFrame:
    root = Path(path)
    parquet_file = root / "data.parquet"
    if root.is_dir() and parquet_file.exists():
        return pd.read_parquet(parquet_file)
    return mltable.load(path).to_pandas_dataframe()


def parse_model_input_line(line: str) -> list[dict]:
    event = json.loads(line)
    if not isinstance(event, dict):
        return []

    event_type = str(event.get("eventType") or event.get("type") or "")
    if event_type and event_type != CLOUD_EVENT_TYPE:
        return []

    payload = event.get("data")
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        return [payload]

    # Some collector exports may already be flattened.
    if isinstance(event.get(TEXT_COL), str):
        return [{TEXT_COL: event.get(TEXT_COL)}]
    return []


def iter_collector_jsonl_files(root_path: Path) -> list[Path]:
    if root_path.is_file():
        if root_path.suffix.lower() != ".jsonl":
            raise RuntimeError(f"Expected .jsonl collector file, got: {root_path}")
        return [root_path]
    if root_path.is_dir():
        return sorted(root_path.rglob("*.jsonl"))
    raise FileNotFoundError(f"Collector path not found: {root_path}")


def read_collector_inputs(root: str) -> pd.DataFrame:
    root_path = Path(root)

    rows: list[dict] = []
    for jsonl_path in iter_collector_jsonl_files(root_path):
        with jsonl_path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rows.extend(parse_model_input_line(line))

    if not rows:
        raise RuntimeError(f"No model_inputs records found under: {root}")

    cur_df = pd.DataFrame(rows)
    if TEXT_COL not in cur_df.columns:
        raise RuntimeError(f"Collected inputs do not contain '{TEXT_COL}' column")
    return cur_df


def build_eval_frame(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({"text_length": df[TEXT_COL].astype(str).str.len()})


def run_drift(reference_eval: pd.DataFrame, current_eval: pd.DataFrame) -> dict:
    report = Report(metrics=[DataDriftPreset()])
    report.run(reference_data=reference_eval, current_data=current_eval)
    return report.as_dict()


def summarize(report_dict: dict, threshold: float, reference_rows: int, current_rows: int, collector_root: str) -> dict:
    metrics = report_dict.get("metrics", [])
    metric_result = metrics[0].get("result", {}) if isinstance(metrics, list) and metrics else {}

    dataset_drift = metric_result.get("dataset_drift")
    drift_share = float(metric_result.get("share_of_drifted_columns") or 0.0)
    drift_cols = metric_result.get("number_of_drifted_columns")
    is_drift = bool(dataset_drift) if dataset_drift is not None else drift_share >= threshold

    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "reference_rows": int(reference_rows),
        "current_rows": int(current_rows),
        "metrics": {
            "dataset_drift": bool(dataset_drift) if dataset_drift is not None else None,
            "share_of_drifted_columns": drift_share,
            "n_drifted_columns": int(drift_cols) if drift_cols is not None else None,
            "threshold": float(threshold),
        },
        "is_drift": bool(is_drift),
        "collector_root": collector_root,
        "evidently_report": report_dict,
    }


def print_summary(summary: dict, report_path: Path) -> None:
    status = "DETECTED" if summary["is_drift"] else "NOT DETECTED"
    metrics = summary["metrics"]
    print("=== DRIFT CHECK SUMMARY ===")
    print(f"Status: {status}")
    print(
        "Decision rule: Drift detected when "
        f"share_of_drifted_columns >= {metrics['threshold']:.4f}"
    )
    print(f"Dataset drift flag: {metrics['dataset_drift']}")
    print(
        "Share of drifted columns: "
        f"{metrics['share_of_drifted_columns']:.4f} (Threshold: {metrics['threshold']:.4f})"
    )
    print(f"Number of drifted columns: {metrics['n_drifted_columns']}")
    print(f"Number of reference rows: {summary['reference_rows']}")
    print(f"Number of current rows: {summary['current_rows']}")
    top = summary.get("top_drift_feature")
    if top:
        print(
            "Top drifted feature: "
            f"{top['name']} (score={top['score']:.4f}, test={top['test']})"
        )
    else:
        print("Top drifted feature: N/A")
    print(f"Collector root: {summary['collector_root']}")
    print(f"Report path: {report_path}")
    print("===========================")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", required=True, help="Reference MLTable path (train data)")
    parser.add_argument("--current-inputs-root", required=True, help="Collector root folder")
    parser.add_argument("--threshold", type=float, default=0.2)
    parser.add_argument("--report-out", required=True)
    args = parser.parse_args()
    logger.info("Starting drift check. Reference %s, collector root %s, threshold %.4f", args.reference, args.current_inputs_root, args.threshold)

    reference_df = read_reference_df(args.reference)
    current_df = read_collector_inputs(args.current_inputs_root)
    logger.info("Loaded reference rows %d and current rows %d", len(reference_df), len(current_df))

    if TEXT_COL not in reference_df.columns:
        raise RuntimeError(f"Reference data does not contain '{TEXT_COL}' column")

    report_dict = run_drift(build_eval_frame(reference_df), build_eval_frame(current_df))
    drift_by_columns = (
        report_dict.get("metrics", [{}])[1]
        .get("result", {})
        .get("drift_by_columns", {})
        if len(report_dict.get("metrics", [])) > 1
        else {}
    )
    top_drift_feature = None
    if drift_by_columns:
        best_name = None
        best_score = float("-inf")
        best_test = ""
        for col_name, col_val in drift_by_columns.items():
            score = float(col_val.get("drift_score") or 0.0)
            if score > best_score:
                best_score = score
                best_name = col_name
                best_test = str(col_val.get("stattest_name") or "")
        if best_name is not None:
            top_drift_feature = {"name": best_name, "score": best_score, "test": best_test}

    summary = summarize(
        report_dict=report_dict,
        threshold=args.threshold,
        reference_rows=len(reference_df),
        current_rows=len(current_df),
        collector_root=args.current_inputs_root,
    )
    summary["top_drift_feature"] = top_drift_feature

    out = Path(args.report_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Report written to %s", out)

    print_summary(summary, out)
    logger.info("Step completed")


if __name__ == "__main__":
    main()
