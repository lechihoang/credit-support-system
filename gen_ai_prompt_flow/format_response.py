from promptflow.core import tool

@tool
def format_response(safety_output: dict, llm_output: str) -> str:
    """
    BƯỚC CUỐI: Định dạng kết quả trả về cho người dùng.
    """
    if not safety_output.get("is_safe", True):
        return safety_output.get("block_message", "This message is blocked due to safety policies.")
    
    return llm_output if llm_output else "No response generated."
