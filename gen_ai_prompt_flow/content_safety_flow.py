from azure.ai.contentsafety import ContentSafetyClient
from azure.ai.contentsafety.models import AnalyzeTextOptions
from azure.core.credentials import AzureKeyCredential
from promptflow.core import tool
from promptflow.connections import AzureContentSafetyConnection

@tool
def check_safety(connection: AzureContentSafetyConnection, question: str) -> dict:
    """
    BƯỚC 1: Kiểm tra an toàn cho câu hỏi hiện tại.
    """
    client = ContentSafetyClient(
        endpoint=connection.endpoint,
        credential=AzureKeyCredential(connection.api_key),
    )
    response = client.analyze_text(AnalyzeTextOptions(text=question))

    is_safe = True
    block_reason = ""
    for category in response.categories_analysis:
        if category.severity > 0:
            is_safe = False
            block_reason = category.category
            break

    return {
        "is_safe": is_safe,
        "question": question,
        "block_message": f"This message is blocked due to safety policies (Block reason: {block_reason})" if not is_safe else "",
    }
