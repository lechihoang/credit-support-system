• # 1) Login
  az login

  # 2) Chọn subscription (nếu có nhiều subscription)
  az account set --subscription "<SUBSCRIPTION_ID_OR_NAME>"

  # 3) Cài extension ML nếu chưa có
  az extension add -n ml -y

  # 4) Set mặc định workspace + resource group cho CLI
  az configure --defaults group="<RESOURCE_GROUP>" workspace="<WORKSPACE_NAME>"
  az configure --defaults group="credit-system-312" workspace="credit-system-312"
  

• # 1) Login + set workspace mặc định
  az login
  az account set --subscription "<SUBSCRIPTION_ID>"
  az configure --defaults group="<RESOURCE_GROUP>" workspace="<WORKSPACE_NAME>"
set -a
  # 2) (Khuyến nghị) nạp biến từ .env
  source .env
  # cần có ít nhất:
  # AZURE_SUBSCRIPTION_ID, AZURE_RESOURCE_GROUP, AZURE_ML_WORKSPACE, AML_MLOPS_COMPUTE_NAME

  # 3) Register/update unified env (pipeline dùng @latest)
  az ml environment create -f ops/environments/dataops-train-env.yml

  # 4) Chạy DataOps pipeline trên cùng 1 compute cluster
az ml job create -f /Users/abc/Documents/IS2/ops/pipeline/dataops/dataops_pipeline.yml


  dùng User-assigned Managed Identity cho compute cluster

  az ml job create -f /Users/abc/Documents/IS2/ops/pipeline/mlops/mlops_pipeline.yml



   1. Cognitive Services OpenAI Contributor -> compute MI
  2. Search Service Contributor -> compute MI
  3. Search Index Data Contributor -> compute MI
  4. Storage Blob Data Reader -> search MI
mới:  cấp contributor, Storage Account Contributor
genai, endpoint: Azure Machine Learning Workspace Connection Secrets Reader


set -a
source /Users/abc/Documents/IS2/.env
set +a

AZURE_STORAGE_ACCOUNT_RESOURCE_ID="/subscriptions/$AZ_SUBSCRIPTION_ID/resourceGroups/$AZ_RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT_NAME"


  az ml job create \
    -f /Users/abc/Documents/IS2/ops/pipeline/genaiops/genaiops_setup_pipeline.yml \
    --set inputs.aoai_endpoint="$AZURE_OPENAI_ENDPOINT" \
          inputs.aoai_resource_id="$AZURE_OPENAI_RESOURCE_ID" \
          inputs.aoai_api_key="${AZURE_OPENAI_API_KEY:-}" \
          inputs.search_endpoint="$AZURE_SEARCH_ENDPOINT" \
          inputs.search_api_key="$AZURE_SEARCH_API_KEY" \
          inputs.content_safety_endpoint="$AZURE_CONTENT_SAFETY_ENDPOINT" \
          inputs.content_safety_key="$AZURE_CONTENT_SAFETY_KEY" \
          inputs.storage_connection_string="$AZURE_STORAGE_CONNECTION_STRING"

