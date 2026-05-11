from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path
from urllib.request import urlretrieve

BANKING77_TRAIN_URL = "https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/master/banking_data/train.csv"
BANKING77_TEST_URL = "https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/master/banking_data/test.csv"
RAG_PDF_URL = "https://techcombank.com/content/dam/techcombank/public-site/documents/terms-and-conditions-for-issuance-and-use-of-credit-card-at-techcombank-22102025.pdf"
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("dataops.fetch")


def download(url: str, out: Path) -> None:
    logger.info("Downloading %s to %s", url, out)
    out.parent.mkdir(parents=True, exist_ok=True)
    urlretrieve(url, out)


def main() -> None:
    t0 = time.perf_counter()
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-mlops", required=True)
    parser.add_argument("--raw-genaiops", required=True)
    args = parser.parse_args()

    raw_mlops = Path(args.raw_mlops)
    raw_genai = Path(args.raw_genaiops)
    logger.info("Starting data fetch. Raw MLOps at %s, raw GenAIOps at %s", raw_mlops, raw_genai)

    download(BANKING77_TRAIN_URL, raw_mlops / "train_raw.csv")
    download(BANKING77_TEST_URL, raw_mlops / "test_raw.csv")
    download(RAG_PDF_URL, raw_genai / "rag_source.pdf")
    logger.info("Fetch data completed in %.3f seconds", time.perf_counter() - t0)


if __name__ == "__main__":
    main()
