from __future__ import annotations

import argparse
import logging
from pathlib import Path

from azure.ai.ml import MLClient
from azure.ai.ml.entities import BuildContext, Environment, ManagedOnlineDeployment, ManagedOnlineEndpoint, OnlineRequestSettings
from azure.identity import DefaultAzureCredential

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("genaiops.deploy_flow_endpoint")


def get_env(name: str) -> str:
    import os

    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing env var: {name}")
    return value


def normalize_model_reference(model_name: str) -> str:
    name = model_name.strip()
    if not name:
        raise ValueError("model_name is empty")
    if name.startswith("azureml:"):
        name = name[len("azureml:") :]
    if "@" in name or ":" in name:
        return f"azureml:{name}"
    return f"azureml:{name}@latest"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint-name", default="genaiops-flow-endpoint")
    parser.add_argument("--deployment-name", default="blue")
    parser.add_argument("--model-name", default="credit-card-support-flow-model")
    parser.add_argument("--model-version-file", default="")
    parser.add_argument("--instance-type", default="Standard_DS1_v2")
    parser.add_argument("--instance-count", type=int, default=1)
    args = parser.parse_args()

    logger.info(
        "Starting flow endpoint deployment. Endpoint %s, deployment %s, model %s",
        args.endpoint_name,
        args.deployment_name,
        args.model_name,
    )

    subscription_id = get_env("AZUREML_ARM_SUBSCRIPTION")
    resource_group = get_env("AZUREML_ARM_RESOURCEGROUP")
    workspace_name = get_env("AZUREML_ARM_WORKSPACE_NAME")

    ml_client = MLClient(
        credential=DefaultAzureCredential(),
        subscription_id=subscription_id,
        resource_group_name=resource_group,
        workspace_name=workspace_name,
    )

    logger.info("Creating or updating endpoint %s", args.endpoint_name)
    endpoint = ManagedOnlineEndpoint(name=args.endpoint_name, auth_mode="key")
    ml_client.online_endpoints.begin_create_or_update(endpoint).result()

    model_ref = normalize_model_reference(args.model_name)
    if args.model_version_file:
        model_version = Path(args.model_version_file).read_text(encoding="utf-8").strip()
        if not model_version:
            raise ValueError("model_version_file is empty")
        base_name = args.model_name.strip().removeprefix("azureml:").split("@", 1)[0].split(":", 1)[0]
        model_ref = f"azureml:{base_name}:{model_version}"

    prt_override = (
        f"deployment.subscription_id={subscription_id},"
        f"deployment.resource_group={resource_group},"
        f"deployment.workspace_name={workspace_name},"
        f"deployment.endpoint_name={args.endpoint_name},"
        f"deployment.deployment_name={args.deployment_name}"
    )

    flow_dir = Path("gen_ai_prompt_flow").resolve()
    pf_environment = Environment(
        build=BuildContext(
            path=str(flow_dir),
            dockerfile_path="Dockerfile.promptflow",
        ),
        inference_config={
            "liveness_route": {"path": "/health", "port": 8080},
            "readiness_route": {"path": "/health", "port": 8080},
            "scoring_route": {"path": "/score", "port": 8080},
        },
    )
    logger.info("Resolved model ref %s and promptflow runtime environment", model_ref)

    dep = ManagedOnlineDeployment(
        name=args.deployment_name,
        endpoint_name=args.endpoint_name,
        model=model_ref,
        environment=pf_environment,
        app_insights_enabled=True,
        instance_type=args.instance_type,
        instance_count=args.instance_count,
        request_settings=OnlineRequestSettings(request_timeout_ms=120000, max_concurrent_requests_per_instance=2),
        environment_variables={
            "PRT_CONFIG_OVERRIDE": prt_override,
            "content_safety": "conn-content-safety",
            "connection": "conn-ai-search",
            "embedding_connection": "conn-aoai-embed",
        },
    )

    logger.info("Creating or updating deployment %s", args.deployment_name)
    ml_client.online_deployments.begin_create_or_update(dep).result()

    ep = ml_client.online_endpoints.get(args.endpoint_name)
    ep.traffic = {args.deployment_name: 100}
    logger.info("Updating endpoint traffic to %s", ep.traffic)
    ml_client.online_endpoints.begin_create_or_update(ep).result()

    logger.info("Deployment completed for %s/%s", args.endpoint_name, args.deployment_name)
    logger.info("Step completed")


if __name__ == "__main__":
    main()
