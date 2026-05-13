from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from azure.ai.ml import MLClient
from azure.ai.ml.entities import Model
from azure.identity import DefaultAzureCredential

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("genaiops.register_flow_model")


def get_env(name: str) -> str:
    v = os.getenv(name, "").strip()
    if not v:
        raise ValueError(f"Missing env var: {name}")
    return v


def normalize_model_name(model_name: str) -> str:
    name = model_name.strip()
    if name.startswith("azureml:"):
        name = name[len("azureml:") :]
    if not name:
        raise ValueError("model_name is empty")
    return name


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-name", default="credit-card-support-flow-model")
    parser.add_argument("--flow-path", default="gen_ai_prompt_flow")
    parser.add_argument("--version-out", default="")
    args = parser.parse_args()
    normalized_model_name = normalize_model_name(args.model_name)
    logger.info("Starting flow model registration. Model %s from %s", normalized_model_name, args.flow_path)

    ml_client = MLClient(
        credential=DefaultAzureCredential(),
        subscription_id=get_env("AZUREML_ARM_SUBSCRIPTION"),
        resource_group_name=get_env("AZUREML_ARM_RESOURCEGROUP"),
        workspace_name=get_env("AZUREML_ARM_WORKSPACE_NAME"),
    )

    model = Model(
        name=normalized_model_name,
        path=str(Path(args.flow_path).resolve()),
        description="Prompt Flow model for credit card support chatbot",
        properties={
            "azureml.promptflow.source_flow_id": "credit_card_support",
            "azureml.promptflow.mode": "chat",
            "azureml.promptflow.chat_input": "question",
            "azureml.promptflow.chat_output": "answer",
        },
    )
    logger.info("Registering model %s", normalized_model_name)
    out = ml_client.models.create_or_update(model)
    logger.info("Model registered: %s (version %s)", out.name, out.version)

    if args.version_out:
        version_out = Path(args.version_out)
        version_out.parent.mkdir(parents=True, exist_ok=True)
        version_out.write_text(str(out.version), encoding="utf-8")
        logger.info("Wrote model version to %s", version_out)
    logger.info("Step completed")


if __name__ == "__main__":
    main()
