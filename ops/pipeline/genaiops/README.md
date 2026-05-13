# GenAIOps Runbook

## 1) Dịch vụ cần tạo trước

Bắt buộc:
- Azure ML Workspace
- Azure ML Compute Cluster (`compute-cluster`)
- Azure OpenAI resource (hoặc Foundry resource có OpenAI deployment)
- Azure AI Search service

Khuyến nghị:
- Application Insights (nếu cần telemetry/feedback về sau)

## 2) Trạng thái deploy model (Foundry pay-as-you-go vs hiện tại)

Hiện tại pipeline **không** deploy model catalog kiểu pay-as-you-go (serverless) của Foundry.

Step `steps/genaiops/step_provision_foundry_models.py` đang gọi `CognitiveServicesManagementClient.deployments.begin_create_or_update` với:
- `properties.model.format = OpenAI`
- `sku = Standard`

Nghĩa là pipeline đang dùng Azure OpenAI deployment trong account hiện có (ví dụ deployment name `gpt-4o-mini`, `text-embedding-3-small`), không phải endpoint serverless model catalog PAYG.

## 3) Environment variables cần có

```bash
# Azure ML workspace runtime vars trong job container (bắt buộc)
export AZUREML_ARM_SUBSCRIPTION="<SUBSCRIPTION_ID>"
export AZUREML_ARM_RESOURCEGROUP="<RESOURCE_GROUP>"
export AZUREML_ARM_WORKSPACE_NAME="<WORKSPACE_NAME>"

# Azure OpenAI (bắt buộc cho provision_models)
export AZURE_OPENAI_ENDPOINT="https://<AOAI_ACCOUNT_NAME>.openai.azure.com/"

# Azure AI Search (bắt buộc cho build_search_index)
export AZURE_SEARCH_ENDPOINT="https://<SEARCH_NAME>.search.windows.net"
# Optional: nếu storage account của datastore nằm khác resource group workspace
export AZURE_STORAGE_ACCOUNT_RESOURCE_ID="/subscriptions/<SUB_ID>/resourceGroups/<RG>/providers/Microsoft.Storage/storageAccounts/<STORAGE_ACCOUNT>"

```

Ghi chú quan trọng:
- Endpoint chuẩn là `https://<account>.openai.azure.com/` (ví dụ `https://credit-74172.openai.azure.com/`).
- `AZURE_OPENAI_API_VERSION` là tùy chọn (mặc định `2024-10-21`).
- Model versions được pin trong code: `gpt-4o-mini=2024-07-18`, `text-embedding-3-small=1`.
- `AZUREML_ARM_*` là biến runtime của Azure ML job; nếu chạy local thì tự export trước khi chạy script.

## 4) Register environment

```bash
az ml environment create \
  -f ops/environments/aml-genaiops-env.yml
```

## 5) Chạy pipeline setup

File:
- `ops/pipeline/genaiops/genaiops_setup_pipeline.yml`
- Components:
  - `ops/pipeline/genaiops/components/provision_models.yml`
  - `ops/pipeline/genaiops/components/build_search_index.yml`

Pipeline làm:
- validate/create model deployments
- build Search index `rag-index` từ data asset `rag_pdf@latest`

Run:
```bash
az ml job create \
  -f ops/pipeline/genaiops/genaiops_setup_pipeline.yml \
  --set inputs.aoai_endpoint="$AZURE_OPENAI_ENDPOINT" \
        inputs.search_endpoint="$AZURE_SEARCH_ENDPOINT" \
        inputs.storage_account_resource_id="${AZURE_STORAGE_ACCOUNT_RESOURCE_ID:-}"
```

## 6) Chạy pipeline promptflow

File:
- `ops/pipeline/genaiops/genaiops_promptflow_deploy_pipeline.yml`
- Components:
  - `ops/pipeline/genaiops/components/register_flow_model.yml`
  - `ops/pipeline/genaiops/components/deploy_flow.yml`

Pipeline làm:
- publish flow lên Prompt Flow workspace (display name mặc định `credit-support-chatbot`)
- register flow model
- deploy online endpoint `genaiops-flow-endpoint` (deployment `blue`, `Standard_DS1_v2`)

Run:
```bash
az ml job create \
  -f ops/pipeline/genaiops/genaiops_promptflow_deploy_pipeline.yml 
```

## 7) Flow binding

`gen_ai_prompt_flow/flow.dag.yaml` đang bind:
- `conn-content-safety`
- `conn-ai-search`
- `conn-aoai-embed`
- `conn-aoai-chat`
