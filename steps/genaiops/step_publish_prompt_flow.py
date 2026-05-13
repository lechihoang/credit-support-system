from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from azure.identity import DefaultAzureCredential
from promptflow.azure import PFClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("genaiops.publish_prompt_flow")


def get_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing env var: {name}")
    return value


def resolve_credential():
    return DefaultAzureCredential()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--flow-path", default="gen_ai_prompt_flow")
    parser.add_argument("--flow-display-name", default="credit-support-chatbot")
    args = parser.parse_args()

    flow_path = Path(args.flow_path).resolve()
    if not flow_path.exists():
        raise FileNotFoundError(f"Flow path not found: {flow_path}")

    logger.info("Publishing flow to Prompt Flow workspace. path=%s display_name=%s", flow_path, args.flow_display_name)

    client = PFClient(
        credential=resolve_credential(),
        subscription_id=get_env("AZUREML_ARM_SUBSCRIPTION"),
        resource_group_name=get_env("AZUREML_ARM_RESOURCEGROUP"),
        workspace_name=get_env("AZUREML_ARM_WORKSPACE_NAME"),
    )

    kwargs = {
        "flow": str(flow_path),
        "display_name": args.flow_display_name,
    }
    flow = client.flows.create_or_update(**kwargs)

    logger.info("Prompt Flow published. name=%s display_name=%s type=%s", getattr(flow, "name", ""), getattr(flow, "display_name", ""), getattr(flow, "type", ""))
    logger.info("Step completed")


if __name__ == "__main__":
    main()
