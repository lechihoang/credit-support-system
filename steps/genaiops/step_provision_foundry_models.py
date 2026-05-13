from __future__ import annotations

import argparse
import logging
import os
from urllib.parse import urlparse

from azure.identity import DefaultAzureCredential
from azure.core.exceptions import ResourceNotFoundError
from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("genaiops.provision_models")


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def get_env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def account_from_endpoint(endpoint: str) -> str:
    parsed = urlparse(endpoint)
    host = parsed.netloc or ""
    if not host or not host.endswith(".openai.azure.com"):
        raise ValueError("AZURE_OPENAI_ENDPOINT must be like https://<account>.openai.azure.com/")
    return host.split(".", 1)[0]


def ensure_deployment(
    client: CognitiveServicesManagementClient,
    resource_group: str,
    account_name: str,
    deployment_name: str,
    model_name: str,
    model_version: str,
) -> None:
    try:
        client.deployments.get(resource_group, account_name, deployment_name)
        logger.info("Deployment already exists: %s", deployment_name)
        logger.info("Deployment already available: %s", deployment_name)
        return
    except ResourceNotFoundError:
        pass

    logger.info("Creating deployment %s for model %s (version %s)", deployment_name, model_name, model_version)
    poller = client.deployments.begin_create_or_update(
        resource_group_name=resource_group,
        account_name=account_name,
        deployment_name=deployment_name,
        deployment={
            "sku": {"name": "GlobalStandard", "capacity": 50},
            "properties": {"model": {"format": "OpenAI", "name": model_name, "version": model_version}},
        },
    )
    poller.result()
    logger.info("Deployment created: %s", deployment_name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chat-deployment-name", default="gpt-4o-mini")
    parser.add_argument("--embedding-deployment-name", default="text-embedding-3-small")
    parser.add_argument("--chat-model-name", default="gpt-4o-mini")
    parser.add_argument("--embedding-model-name", default="text-embedding-3-small")
    parser.add_argument("--aoai-endpoint", default="")
    args = parser.parse_args()
    logger.info("Starting model provisioning")

    chat_model_version = "2024-07-18"
    embedding_model_version = "1"

    subscription_id = required("AZUREML_ARM_SUBSCRIPTION")
    resource_group = required("AZUREML_ARM_RESOURCEGROUP")
    aoai_endpoint = args.aoai_endpoint.strip() or required("AZURE_OPENAI_ENDPOINT")
    account_name = account_from_endpoint(aoai_endpoint)


    credential = DefaultAzureCredential()
    client = CognitiveServicesManagementClient(credential, subscription_id)

    ensure_deployment(client, resource_group, account_name, args.chat_deployment_name, args.chat_model_name, chat_model_version)
    ensure_deployment(client, resource_group, account_name, args.embedding_deployment_name, args.embedding_model_name, embedding_model_version)
    logger.info("Step completed")


if __name__ == "__main__":
    main()
