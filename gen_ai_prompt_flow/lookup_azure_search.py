import logging
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from openai import AzureOpenAI
from promptflow.core import tool
from promptflow.connections import CognitiveSearchConnection, AzureOpenAIConnection

@tool
def retrieve(
    connection: CognitiveSearchConnection, 
    question: str,
    embedding_connection: AzureOpenAIConnection,
    index_name: str,
    embedding_deployment_name: str = "text-embedding-3-small", 
    top_k: int = 5,
    is_safe: bool = True
) -> dict:
    """
    BƯỚC 2: Tìm kiếm dữ liệu.
    """
    if not is_safe:
        return {
            "context": "",
            "question": question,
            "skipped": True,
        }

    try:
        client = AzureOpenAI(
            api_key=embedding_connection.api_key,
            api_version="2024-02-01",
            azure_endpoint=embedding_connection.api_base
        )
        query_vector = client.embeddings.create(model=embedding_deployment_name, input=question).data[0].embedding

        search_client = SearchClient(
            endpoint=connection.api_base, 
            index_name=index_name, 
            credential=AzureKeyCredential(connection.api_key)
        )
        results = search_client.search(
            search_text=question, 
            vector_queries=[VectorizedQuery(vector=query_vector, k_nearest_neighbors=50, fields="text_vector")], 
            query_type="semantic", 
            semantic_configuration_name=f"{index_name}-semantic-configuration", 
            top=top_k
        )
        chunks = []
        for r in results:
            score = r.get("@search.score", 0.0)
            source = r.get("metadata_storage_name", "")
            text = r.get("chunk", "")
            chunks.append(f"[Score: {score:.4f}] [Source: {source}]\n{text}")
        context = "\n\n---\n\n".join(chunks)
        
        return {
            "context": context,
            "question": question,
            "skipped": False,
        }
    except Exception as e:
        return {"context": f"Error: {str(e)}", "question": question, "skipped": False}
