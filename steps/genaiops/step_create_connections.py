from __future__ import annotations

import argparse
import logging
import os

from azure.ai.ml import MLClient
from azure.ai.ml.entities import (
    AzureAISearchConnection,
    AzureContentSafetyConnection,
    AzureOpenAIConnection,
)
from azure.identity import DefaultAzureCredential

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("genaiops.create_connections")

def get_env(name: str, required: bool = True, default: str = "") -> str:
    v = os.getenv(name, default).strip()
    if required and not v:
        raise ValueError(f"Missing required env var: {name}")
    return v

def ml_client() -> MLClient:
    return MLClient(
        credential=DefaultAzureCredential(),
        subscription_id=get_env("AZUREML_ARM_SUBSCRIPTION"),
        resource_group_name=get_env("AZUREML_ARM_RESOURCEGROUP"),
        workspace_name=get_env("AZUREML_ARM_WORKSPACE_NAME"),
    )

def aoai_endpoint() -> str:
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()
    if not endpoint:
        raise ValueError("Missing required env var: AZURE_OPENAI_ENDPOINT")
    return endpoint

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--aoai-conn-name", default="conn-aoai-chat")
    parser.add_argument("--embed-conn-name", default="conn-aoai-embed")
    parser.add_argument("--search-conn-name", default="conn-ai-search")
    parser.add_argument("--safety-conn-name", default="conn-content-safety")
    parser.add_argument("--aoai-endpoint", default="")
    parser.add_argument("--aoai-resource-id", default="")
    parser.add_argument("--aoai-api-key", default="")
    parser.add_argument("--search-endpoint", default="")
    parser.add_argument("--search-api-key", default="")
    parser.add_argument("--content-safety-endpoint", default="")
    parser.add_argument("--content-safety-key", default="")
    args = parser.parse_args()
    logger.info("Starting connection setup")

    client = ml_client()

    aoai_endpoint_value = args.aoai_endpoint.strip() or aoai_endpoint()
    aoai_resource_id = args.aoai_resource_id.strip() or get_env("AZURE_OPENAI_RESOURCE_ID", required=False, default="")
    aoai_api_key = args.aoai_api_key.strip() or get_env("AZURE_OPENAI_API_KEY", required=False, default="")
    aoai_api_version = get_env("AZURE_OPENAI_API_VERSION", required=False, default="2024-10-21")

    search_endpoint = args.search_endpoint.strip() or get_env("AZURE_SEARCH_ENDPOINT")
    search_api_key = args.search_api_key.strip() or get_env("AZURE_SEARCH_API_KEY")

    safety_endpoint = args.content_safety_endpoint.strip() or get_env("AZURE_CONTENT_SAFETY_ENDPOINT")
    safety_api_key = args.content_safety_key.strip() or get_env("AZURE_CONTENT_SAFETY_KEY")

    logger.info("Creating or updating connection %s", args.aoai_conn_name)
    chat_conn = AzureOpenAIConnection(
        name=args.aoai_conn_name,
        azure_endpoint=aoai_endpoint_value,
        resource_id=aoai_resource_id or None,
        api_key=aoai_api_key or None,
        api_version=aoai_api_version,
    )
    client.connections.create_or_update(chat_conn)

    logger.info("Creating or updating connection %s", args.embed_conn_name)
    embed_conn = AzureOpenAIConnection(
        name=args.embed_conn_name,
        azure_endpoint=aoai_endpoint_value,
        resource_id=aoai_resource_id or None,
        api_key=aoai_api_key or None,
        api_version=aoai_api_version,
    )
    client.connections.create_or_update(embed_conn)

    logger.info("Creating or updating connection %s", args.search_conn_name)
    search_conn = AzureAISearchConnection(
        name=args.search_conn_name,
        endpoint=search_endpoint,
        api_key=search_api_key,
    )
    client.connections.create_or_update(search_conn)

    logger.info("Creating or updating connection %s", args.safety_conn_name)
    safety_conn = AzureContentSafetyConnection(
        name=args.safety_conn_name,
        endpoint=safety_endpoint,
        api_key=safety_api_key,
    )
    client.connections.create_or_update(safety_conn)

    logger.info("Connection ready: %s", args.aoai_conn_name)
    logger.info("Connection ready: %s", args.embed_conn_name)
    logger.info("Connection ready: %s", args.search_conn_name)
    logger.info("Connection ready: %s", args.safety_conn_name)
    logger.info("Step completed")

if __name__ == "__main__":
    main()
