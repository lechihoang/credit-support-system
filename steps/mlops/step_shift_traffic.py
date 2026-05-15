from __future__ import annotations

import argparse
import logging
import os

from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("mlops.shift_traffic")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint-name", required=True)
    parser.add_argument("--lr-deployment", default="lr")
    parser.add_argument("--xgb-deployment", default="xgb")
    parser.add_argument("--lr-traffic", type=int, default=10)
    parser.add_argument("--xgb-traffic", type=int, default=90)
    args = parser.parse_args()

    if args.lr_traffic < 0 or args.xgb_traffic < 0 or (args.lr_traffic + args.xgb_traffic) != 100:
        raise ValueError("traffic split must be non-negative and sum to 100")

    logger.info(
        "Starting traffic shift. Endpoint %s, %s=%d%%, %s=%d%%",
        args.endpoint_name,
        args.lr_deployment,
        args.lr_traffic,
        args.xgb_deployment,
        args.xgb_traffic,
    )

    subscription_id = os.environ["AZUREML_ARM_SUBSCRIPTION"].strip()
    resource_group = os.environ["AZUREML_ARM_RESOURCEGROUP"].strip()
    workspace_name = os.environ["AZUREML_ARM_WORKSPACE_NAME"].strip()

    ml_client = MLClient(
        credential=DefaultAzureCredential(),
        subscription_id=subscription_id,
        resource_group_name=resource_group,
        workspace_name=workspace_name,
    )

    ep = ml_client.online_endpoints.get(args.endpoint_name)
    ep.traffic = {
        args.lr_deployment: args.lr_traffic,
        args.xgb_deployment: args.xgb_traffic,
    }
    logger.info("Updating endpoint traffic to %s", ep.traffic)
    ml_client.online_endpoints.begin_create_or_update(ep).result()
    print(f"traffic updated: {ep.traffic}")
    logger.info("Step completed")


if __name__ == "__main__":
    main()
