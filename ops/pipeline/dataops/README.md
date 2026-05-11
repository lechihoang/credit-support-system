# DataOps Runbook

## 1) Pipeline

- `ops/pipeline/dataops/dataops_pipeline.yml`

## 2) Pipeline làm gì

- `fetch_data`: tải train/test CSV + PDF RAG vào blob raw
- `process_data`: map label + tạo MLTable parquet vào blob processed
- `register_assets`: đăng ký data assets `train_data`, `test_data`, `rag_pdf`

## 3) Chạy

```bash
az ml job create -f ops/pipeline/dataops/dataops_pipeline.yml
```
