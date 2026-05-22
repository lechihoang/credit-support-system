tạo resource group
tạo azure ml workspace
az configure --defaults group="credit-system-312" workspace="credit-system-312"

tạo env
az ml environment create -f ops/environments/aml-mlops-env.yml
az ml environment create -f ops/environments/aml-genaiops-env.yml

chạy pipeline mlop
az ml job create -f ops/pipeline/mlops/mlops_pipeline.yml

GENAIOP

tạo azure foundry, ai search, content safety, lấy các giá trị liên quan cho vào env

source .env

az ml job create \
    -f ops/pipeline/genaiops/genaiops_setup_pipeline.yml \
    --set inputs.aoai_endpoint="$AZURE_OPENAI_ENDPOINT" \
          inputs.aoai_resource_id="$AZURE_OPENAI_RESOURCE_ID" \
          inputs.aoai_api_key="${AZURE_OPENAI_API_KEY:-}" \
          inputs.search_endpoint="$AZURE_SEARCH_ENDPOINT" \
          inputs.search_api_key="$AZURE_SEARCH_API_KEY" \
          inputs.content_safety_endpoint="$AZURE_CONTENT_SAFETY_ENDPOINT" \
          inputs.content_safety_key="$AZURE_CONTENT_SAFETY_KEY" \
          inputs.storage_connection_string="$AZURE_STORAGE_CONNECTION_STRING"

az ml job create \
  -f ops/pipeline/genaiops/genaiops_promptflow_deploy_pipeline.yml