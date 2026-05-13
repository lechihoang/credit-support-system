from __future__ import annotations

import argparse
import logging
import os
import re
from pathlib import PurePosixPath
import requests

from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient, SearchIndexerClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes.models import (
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SearchIndexer,
    SearchIndexerDataContainer,
    SearchIndexerDataSourceConnection,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
)
from azure.core.exceptions import ResourceNotFoundError

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("genaiops.search_index")


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def parse_azureml_datastore_uri(uri: str) -> tuple[str, str]:
    full = re.match(
        r"^azureml://subscriptions/[^/]+/resourcegroups/[^/]+/workspaces/[^/]+/datastores/([^/]+)/paths/(.+)$",
        uri,
        re.IGNORECASE,
    )
    if full:
        return full.group(1), full.group(2).strip("/")

    raise ValueError(f"Unsupported data asset path format: {uri}")


def resolve_blob_location(ml_client: MLClient, asset_name: str, asset_version: str) -> tuple[str, str]:
    asset = ml_client.data.get(name=asset_name, version=asset_version)
    datastore_name, blob_path = parse_azureml_datastore_uri(str(asset.path))
    datastore = ml_client.datastores.get(datastore_name)
    container_name = getattr(datastore, "container_name", None)
    if not container_name:
        raise ValueError(f"Datastore {datastore_name} does not expose container_name")
    p = PurePosixPath(blob_path)
    prefix = str(p.parent) if p.suffix else str(p)
    return container_name, "" if prefix == "." else prefix

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index-name", default="rag-index")
    parser.add_argument("--data-source-name", default="rag-datasource")
    parser.add_argument("--indexer-name", default="rag-indexer")
    parser.add_argument("--rag-asset-name", default="rag_pdf")
    parser.add_argument("--rag-asset-version", default="latest")
    parser.add_argument("--search-endpoint", default="")
    parser.add_argument("--search-api-key", default="")
    parser.add_argument("--storage-connection-string", default="")
    parser.add_argument("--aoai-endpoint", default="")
    parser.add_argument("--aoai-api-key", default="")
    parser.add_argument("--embedding-deployment-name", default="text-embedding-3-small")
    args = parser.parse_args()
    logger.info("Starting search index build. Index %s, asset %s@%s", args.index_name, args.rag_asset_name, args.rag_asset_version)

    credential = DefaultAzureCredential()
    ml_client = MLClient(
        credential=credential,
        subscription_id=required("AZUREML_ARM_SUBSCRIPTION"),
        resource_group_name=required("AZUREML_ARM_RESOURCEGROUP"),
        workspace_name=required("AZUREML_ARM_WORKSPACE_NAME"),
    )

    endpoint = args.search_endpoint.strip() or required("AZURE_SEARCH_ENDPOINT")
    aoai_endpoint = args.aoai_endpoint.strip() or required("AZURE_OPENAI_ENDPOINT")
    aoai_api_key = args.aoai_api_key.strip() or required("AZURE_OPENAI_API_KEY")

    asset_version = args.rag_asset_version
    if asset_version == "latest":
        latest = ml_client.data.get(name=args.rag_asset_name, label="latest")
        asset_version = latest.version

    blob_container, blob_prefix = resolve_blob_location(ml_client, args.rag_asset_name, asset_version)
    storage_connection_string = args.storage_connection_string.strip() or required("AZURE_STORAGE_CONNECTION_STRING")
    logger.info("Resolved blob container %s with prefix %s", blob_container, blob_prefix)
    logger.info("Using storage connection string for data source authentication")

    search_api_key = args.search_api_key.strip() or required("AZURE_SEARCH_API_KEY")
    search_credential = AzureKeyCredential(search_api_key)
    logger.info("Using AzureKeyCredential for Azure AI Search")

    index_client = SearchIndexClient(endpoint=endpoint, credential=search_credential)
    indexer_client = SearchIndexerClient(endpoint=endpoint, credential=search_credential)

    try:
        index_client.get_index(args.index_name)
        doc_count = SearchClient(
            endpoint=endpoint,
            index_name=args.index_name,
            credential=search_credential,
        ).get_document_count()
        if doc_count > 0:
            logger.info("Index already exists and has %s documents, skip rebuild: %s", doc_count, args.index_name)
            logger.info("Step completed")
            return
        logger.info("Index exists but empty (%s docs), continue rebuild: %s", doc_count, args.index_name)
    except ResourceNotFoundError:
        logger.info("Index not found, proceeding to create: %s", args.index_name)

    logger.info("Creating or updating index %s", args.index_name)
    index = SearchIndex(
        name=args.index_name,
        fields=[
            SearchField(
                name="id",
                type=SearchFieldDataType.String,
                key=True,
                searchable=True,
                analyzer_name="keyword",
                filterable=True,
            ),
            SearchField(name="parent_id", type=SearchFieldDataType.String, filterable=True),
            SearchField(name="chunk", type=SearchFieldDataType.String, searchable=True),
            SearchField(name="content", type=SearchFieldDataType.String, searchable=True),
            SearchField(name="metadata_storage_path", type=SearchFieldDataType.String, searchable=False, filterable=True),
            SearchField(name="metadata_storage_name", type=SearchFieldDataType.String, searchable=True, filterable=True),
            SearchField(
                name="text_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=1536,
                vector_search_profile_name="vector-profile-1",
            ),
        ],
        semantic_search=SemanticSearch(
            configurations=[
                SemanticConfiguration(
                    name=f"{args.index_name}-semantic-configuration",
                    prioritized_fields=SemanticPrioritizedFields(
                        content_fields=[SemanticField(field_name="chunk")],
                        keywords_fields=[SemanticField(field_name="metadata_storage_name")],
                    ),
                )
            ]
        ),
        vector_search=VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="hnsw-1")],
            profiles=[VectorSearchProfile(name="vector-profile-1", algorithm_configuration_name="hnsw-1")],
        )
    )
    index_client.create_or_update_index(index)

    logger.info("Creating or updating data source %s", args.data_source_name)
    data_source = SearchIndexerDataSourceConnection(
        name=args.data_source_name,
        type="azureblob",
        connection_string=storage_connection_string,
        container=SearchIndexerDataContainer(name=blob_container, query=blob_prefix),
    )
    indexer_client.create_or_update_data_source_connection(data_source)

    skillset_name = f"{args.indexer_name}-skillset"
    logger.info("Creating or updating skillset %s via REST", skillset_name)
    skillset_url = f"{endpoint.rstrip('/')}/skillsets/{skillset_name}?api-version=2024-07-01"
    skillset_payload = {
        "name": skillset_name,
        "skills": [
            {
                "@odata.type": "#Microsoft.Skills.Text.SplitSkill",
                "name": "split-text",
                "description": "Split long content into chunks before embeddings",
                "context": "/document",
                "textSplitMode": "pages",
                "maximumPageLength": 5000,
                "maximumPagesToTake": 0,
                "inputs": [{"name": "text", "source": "/document/content"}],
                "outputs": [{"name": "textItems", "targetName": "pages"}],
            },
            {
                "@odata.type": "#Microsoft.Skills.Text.AzureOpenAIEmbeddingSkill",
                "name": "aoai-embed",
                "context": "/document/pages/*",
                "resourceUri": aoai_endpoint,
                "apiKey": aoai_api_key,
                "deploymentId": args.embedding_deployment_name,
                "modelName": args.embedding_deployment_name,
                "dimensions": 1536,
                "inputs": [{"name": "text", "source": "/document/pages/*"}],
                "outputs": [{"name": "embedding", "targetName": "text_vector"}],
            }
        ],
        "indexProjections": {
            "selectors": [
                {
                    "targetIndexName": args.index_name,
                    "parentKeyFieldName": "parent_id",
                    "sourceContext": "/document/pages/*",
                    "mappings": [
                        {"name": "chunk", "source": "/document/pages/*"},
                        {"name": "text_vector", "source": "/document/pages/*/text_vector"},
                        {"name": "metadata_storage_path", "source": "/document/metadata_storage_path"},
                        {"name": "metadata_storage_name", "source": "/document/metadata_storage_name"},
                    ],
                }
            ],
            "parameters": {"projectionMode": "skipIndexingParentDocuments"},
        },
    }
    resp = requests.put(
        skillset_url,
        headers={"Content-Type": "application/json", "api-key": search_api_key},
        json=skillset_payload,
        timeout=60,
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Failed to create/update skillset: {resp.status_code} {resp.text}")

    logger.info("Creating or updating indexer %s", args.indexer_name)
    indexer = SearchIndexer(
        name=args.indexer_name,
        data_source_name=args.data_source_name,
        target_index_name=args.index_name,
        skillset_name=skillset_name,
        parameters={
            "configuration": {
                "indexedFileNameExtensions": ".pdf",
                "dataToExtract": "contentAndMetadata",
                "imageAction": "none",
                "parsingMode": "default",
            }
        },
    )
    indexer_client.create_or_update_indexer(indexer)

    logger.info("Running indexer %s", args.indexer_name)
    indexer_client.run_indexer(args.indexer_name)

    logger.info("Search index ready")
    logger.info("Index name: %s", args.index_name)
    logger.info("RAG asset: %s (version %s)", args.rag_asset_name, asset_version)
    logger.info("Blob container: %s", blob_container)
    logger.info("Blob prefix: %s", blob_prefix)
    logger.info("Step completed")


if __name__ == "__main__":
    main()
