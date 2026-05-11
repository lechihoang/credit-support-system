from __future__ import annotations

import logging
import os

from azure.ai.ml import MLClient
from azure.ai.ml.constants import AssetTypes
from azure.ai.ml.entities import Data
from azure.identity import DefaultAzureCredential

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("dataops.register_assets")

def main() -> None:
    subscription_id = os.environ["AZUREML_ARM_SUBSCRIPTION"].strip()
    resource_group = os.environ["AZUREML_ARM_RESOURCEGROUP"].strip()
    workspace_name = os.environ["AZUREML_ARM_WORKSPACE_NAME"].strip()

    credential = DefaultAzureCredential()
    ml_client = MLClient(
        credential=credential,
        subscription_id=subscription_id,
        resource_group_name=resource_group,
        workspace_name=workspace_name,
    )
    logger.info("ML client ready for workspace %s in resource group %s", workspace_name, resource_group)

    train_asset = Data(
        name="train_data",
        path="azureml://datastores/workspaceblobstore/paths/data/mlops/processed/train_data_mltable",
        type=AssetTypes.MLTABLE,
        description="Training dataset mapped to simplified labels",
    )
    test_asset = Data(
        name="test_data",
        path="azureml://datastores/workspaceblobstore/paths/data/mlops/processed/test_data_mltable",
        type=AssetTypes.MLTABLE,
        description="Test dataset mapped to simplified labels",
    )
    rag_asset = Data(
        name="rag_pdf",
        path="azureml://datastores/workspaceblobstore/paths/data/genaiops/raw/rag_source.pdf",
        type=AssetTypes.URI_FILE,
        description="RAG source PDF",
    )

    logger.info("Registering asset %s", train_asset.name)
    tr = ml_client.data.create_or_update(train_asset)
    logger.info("Registered asset %s (version %s)", tr.name, tr.version)
    logger.info("Registering asset %s", test_asset.name)
    te = ml_client.data.create_or_update(test_asset)
    logger.info("Registered asset %s (version %s)", te.name, te.version)
    logger.info("Registering asset %s", rag_asset.name)
    rg = ml_client.data.create_or_update(rag_asset)
    logger.info("Registered asset %s (version %s)", rg.name, rg.version)
    logger.info("Step completed")


if __name__ == "__main__":
    main()
