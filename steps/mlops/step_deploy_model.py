from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from azure.ai.ml import MLClient
from azure.ai.ml.entities import (
    CodeConfiguration,
    DataCollector,
    DeploymentCollection,
    ManagedOnlineDeployment,
    ManagedOnlineEndpoint,
    OnlineRequestSettings,
)
from azure.identity import DefaultAzureCredential

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("mlops.deploy_model")


def resolve_environment_id(ml_client: MLClient, env_ref: str) -> str:
    ref = env_ref.removeprefix("azureml:")
    if "@" in ref:
        name, tag = ref.split("@", 1)
        if tag == "latest":
            env_obj = ml_client.environments.get(name=name, label="latest")
            return env_obj.id
        env_obj = ml_client.environments.get(name=name, version=tag)
        return env_obj.id
    env_obj = ml_client.environments.get(name=ref, label="latest")
    return env_obj.id


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint-name", required=True)
    parser.add_argument("--deployment-name", required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--model-version-file", required=True)
    parser.add_argument("--instance-type", default="Standard_DS1_v2")
    parser.add_argument("--instance-count", type=int, default=1)
    parser.add_argument("--inference-env", default="mlops-env@latest")
    parser.add_argument("--scoring-script", default="score.py")
    args = parser.parse_args()
    logger.info(
        "Starting model deployment. Endpoint %s, deployment %s, model %s, instance type %s, instances %d",
        args.endpoint_name,
        args.deployment_name,
        args.model_name,
        args.instance_type,
        args.instance_count,
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
    logger.info("ML client ready for workspace %s in resource group %s", workspace_name, resource_group)

    model_version = Path(args.model_version_file).read_text(encoding="utf-8").strip()
    environment_id = resolve_environment_id(ml_client, args.inference_env)
    model_ref = f"azureml:{args.model_name}:{model_version}"
    logger.info("Resolved model ref %s and environment %s", model_ref, environment_id)

    endpoint = ManagedOnlineEndpoint(name=args.endpoint_name, auth_mode="key")
    logger.info("Creating or updating endpoint %s", args.endpoint_name)
    ml_client.online_endpoints.begin_create_or_update(endpoint).result()

    dep = ManagedOnlineDeployment(
        name=args.deployment_name,
        endpoint_name=args.endpoint_name,
        model=model_ref,
        app_insights_enabled=True,
        instance_type=args.instance_type,
        instance_count=args.instance_count,
        request_settings=OnlineRequestSettings(
            request_timeout_ms=10000,
            max_concurrent_requests_per_instance=1,
        ),
        code_configuration=CodeConfiguration(
            code=str(Path("mlop_training_job").resolve()),
            scoring_script=args.scoring_script,
        ),
        environment_variables={
            "MODEL_DEPLOYMENT_NAME": args.deployment_name,
        },
        environment=environment_id,
        data_collector=DataCollector(
            collections={
                "model_inputs": DeploymentCollection(enabled="True"),
                "model_outputs": DeploymentCollection(enabled="True"),
            }
        ),
    )

    logger.info("Creating or updating deployment %s", args.deployment_name)
    ml_client.online_deployments.begin_create_or_update(dep).result()
    print(f"deployed: {args.endpoint_name}/{args.deployment_name} -> {model_ref}, env={environment_id}")
    logger.info("Step completed")


if __name__ == "__main__":
    main()
