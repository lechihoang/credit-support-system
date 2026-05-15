# MLOps Runbook

## 1) Pipeline chính

- `ops/pipeline/mlops/mlops_pipeline.yml`

## 2) Pipeline làm gì

- train `lr` -> register model
- train `xgb` -> register model
- deploy `logistic-regression` + `xgboost` vào endpoint `ml-endpoint`
- shift traffic (50/50)

## 3) Chạy pipeline chính

```bash
az ml job create -f ops/pipeline/mlops/mlops_pipeline.yml
```

## 4) Drift monitoring

Manual drift job:

```bash
az ml job create -f ops/pipeline/mlops/drift_schedule.yml
```

Schedule drift job:

```bash
az ml schedule create -f ops/pipeline/mlops/drift_schedule_trigger.yml
```
