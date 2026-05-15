from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from azure.ai.ml import MLClient
from azure.ai.ml.constants import AssetTypes
from azure.ai.ml.entities import Model
from azure.identity import DefaultAzureCredential

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("mlops.register_model")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--version-out", required=True)
    args = parser.parse_args()
    logger.info("Starting model registration. Model %s from %s", args.model_name, args.model_dir)

    subscription_id = os.environ["AZUREML_ARM_SUBSCRIPTION"].strip()
    resource_group = os.environ["AZUREML_ARM_RESOURCEGROUP"].strip()
    workspace_name = os.environ["AZUREML_ARM_WORKSPACE_NAME"].strip()

    ml_client = MLClient(
        credential=DefaultAzureCredential(),
        subscription_id=subscription_id,
        resource_group_name=resource_group,
        workspace_name=workspace_name,
    )
    logger.info("ML client ready for workspace %s in resource group %s", workspace_name, resource_group)

    model_dir = Path(args.model_dir)
    mlflow_subdir = model_dir / "mlflow_model"
    model_path = mlflow_subdir if mlflow_subdir.exists() else model_dir

    model = Model(
        path=str(model_path),
        name=args.model_name,
        type=AssetTypes.MLFLOW_MODEL,
        description=f"Registered from pipeline step for {args.model_name}",
    )
    logger.info("Registering model %s from %s", args.model_name, model_path)
    created = ml_client.models.create_or_update(model)
    logger.info("Model registered: %s (version %s)", created.name, created.version)

    out = Path(args.version_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(str(created.version), encoding="utf-8")
    logger.info("Wrote version file to %s", out)

    print(f"registered: {created.name}:{created.version}")
    logger.info("Step completed")


if __name__ == "__main__":
    main()
