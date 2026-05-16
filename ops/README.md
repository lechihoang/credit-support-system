# Ops Runbook

## 1) Prerequisites (chung)

```bash
az login
az account set --subscription "<SUBSCRIPTION_ID>"
```

Bắt buộc có sẵn:
- Resource Group
- Azure ML Workspace
- Compute cluster dùng chung (ví dụ: `compute-cluster`)

Gợi ý kiểm tra nhanh:

```bash
az ml workspace show -g "<RESOURCE_GROUP>" -n "<WORKSPACE_NAME>"
az ml compute show -g "<RESOURCE_GROUP>" -w "<WORKSPACE_NAME>" -n "compute-cluster"
```

## 2) Tạo môi trường trước khi chạy pipeline

MLOps/DataOps env:

```bash
az ml environment create -f ops/environments/aml-mlops-env.yml
```

GenAIOps env:

```bash
az ml environment create -f ops/environments/aml-genaiops-env.yml
```

## 3) Runbook theo pipeline

- Tổng quan: `ops/pipeline/README.md`
- DataOps: `ops/pipeline/dataops/README.md`
- MLOps: `ops/pipeline/mlops/README.md`
- GenAIOps: `ops/pipeline/genaiops/README.md`
