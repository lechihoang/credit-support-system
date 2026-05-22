import logging
import os
import statistics
import time
from typing import Any

import requests
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("endpoint_benchmark.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

load_dotenv(override=True)

ML_URL = os.getenv("AZURE_ML_ENDPOINT_URL")
ML_KEY = os.getenv("AZURE_ML_ENDPOINT_KEY")
GENAI_URL = os.getenv("AZURE_FOUNDRY_ENDPOINT_URL")
GENAI_KEY = os.getenv("AZURE_FOUNDRY_ENDPOINT_KEY")

N_CALLS = 10
ML_QUESTIONS = [
    "How do I locate my card?",
    "I still have not received my new card, I ordered over a week ago.",
    "I ordered a card but it has not arrived. Help please!",
    "Is there a way to know when my card will arrive?",
    "My card has not arrived yet.",
    "When will I get my card?",
    "Do you know if there is a tracking number for the new card you sent me?",
    "i have not received my card",
    "still waiting on that card",
    "Is it normal to have to wait over a week for my new card?",
]
GENAI_QUESTIONS = [
    "How does express card issuance work, and what fees or timing should I know?",
    "I heard express card issuance guarantees delivery in 1 working day. Is that correct?",
    "What are the responsibilities between a primary cardholder and supplementary cardholders?",
    "Can a supplementary cardholder terminate the primary card if they disagree with the primary cardholder?",
    "What card transactions are allowed, including online and MOTO transactions?",
    "Can I use the card for illegal gambling if the merchant accepts card payment?",
    "How is credit-card interest calculated, and how is DreamCard treated differently?",
    "If I pay the full statement balance on time, are cash withdrawals interest-free too?",
    "What happens if I only pay part of my statement balance by the due date?",
    "What exact late payment fee amount will I be charged if I miss the minimum repayment?",
]


def percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    idx = (len(sorted_values) - 1) * p
    lo = int(idx)
    hi = min(lo + 1, len(sorted_values) - 1)
    frac = idx - lo
    return sorted_values[lo] * (1.0 - frac) + sorted_values[hi] * frac


def summarize_latencies(label: str, latencies: list[float], success_count: int, error_count: int) -> None:
    if not latencies:
        logger.info("%s summary: success=%d error=%d (no latency stats)", label, success_count, error_count)
        return
    vals = sorted(latencies)
    logger.info(
        "%s summary: success=%d error=%d avg=%.3fs p50=%.3fs p95=%.3fs min=%.3fs max=%.3fs",
        label,
        success_count,
        error_count,
        statistics.mean(vals),
        percentile(vals, 0.50),
        percentile(vals, 0.95),
        vals[0],
        vals[-1],
    )


def call_ml(question: str) -> dict[str, Any]:
    if not ML_URL or not ML_KEY:
        return {"error": "ML Endpoint configuration missing in .env", "duration": 0.0}
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {ML_KEY}"}
    payload = {"data": [{"text": question}]}

    start = time.time()
    try:
        response = requests.post(ML_URL, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return {"result": response.json(), "duration": time.time() - start}
    except Exception as e:
        return {"error": str(e), "duration": time.time() - start}


def call_genai(question: str) -> dict[str, Any]:
    if not GENAI_URL or not GENAI_KEY:
        return {"error": "GenAI Endpoint configuration missing in .env", "duration": 0.0}
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {GENAI_KEY}"}
    payload = {"question": question, "chat_history": []}

    start = time.time()
    try:
        response = requests.post(GENAI_URL, json=payload, headers=headers, timeout=90)
        response.raise_for_status()
        trace_id = response.headers.get("x-ms-client-request-id") or response.headers.get("x-ms-promptflow-run-id")
        return {"result": response.json(), "duration": time.time() - start, "trace_id": trace_id}
    except Exception as e:
        return {"error": str(e), "duration": time.time() - start}


def benchmark_ml_batch(questions: list[str]) -> None:
    latencies: list[float] = []
    success_count = 0
    error_count = 0

    logger.info("=== MLOps Benchmark: %d calls ===", len(questions))
    for idx, q in enumerate(questions, 1):
        res = call_ml(q)
        d = float(res.get("duration", 0.0))
        latencies.append(d)
        if "error" in res:
            error_count += 1
            logger.error("ML #%d failed (%.3fs): %s", idx, d, res["error"])
        else:
            success_count += 1
            pred = (res.get("result") or {}).get("predictions", ["N/A"])[0]
            logger.info("ML #%d ok (%.3fs): pred=%s", idx, d, pred)

    summarize_latencies("MLOps", latencies, success_count, error_count)


def benchmark_genai_batch(questions: list[str]) -> None:
    latencies: list[float] = []
    success_count = 0
    error_count = 0

    logger.info("=== GenAIOps Benchmark: %d calls ===", len(questions))
    for idx, q in enumerate(questions, 1):
        res = call_genai(q)
        d = float(res.get("duration", 0.0))
        latencies.append(d)
        if "error" in res:
            error_count += 1
            logger.error("GenAI #%d failed (%.3fs): %s", idx, d, res["error"])
        else:
            success_count += 1
            ans = ((res.get("result") or {}).get("answer") or "")
            logger.info("GenAI #%d ok (%.3fs): trace_id=%s answer=%s", idx, d, res.get("trace_id", "N/A"), ans[:120])

    summarize_latencies("GenAIOps", latencies, success_count, error_count)


def main() -> None:
    ml_questions = ML_QUESTIONS[:N_CALLS]
    genai_questions = GENAI_QUESTIONS[:N_CALLS]
    benchmark_ml_batch(ml_questions)
    benchmark_genai_batch(genai_questions)


if __name__ == "__main__":
    main()
