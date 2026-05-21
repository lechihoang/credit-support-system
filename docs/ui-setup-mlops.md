# UI Setup — MLOps (Intent Classification)

Hướng dẫn setup bằng giao diện (UI) trong Azure Portal + Azure ML Studio. Hạn chế dùng code; chỉ tải file và bấm theo bước.

## 1. Tạo workspace

1. Azure Portal → Create a resource → Azure Machine Learning.
2. Tạo Resource Group (neu chua co).
3. Tạo Workspace (vi du: ml-techcombank) va cho den khi trang thai Succeeded.
4. Mo Azure ML Studio (Launch studio).

## 2. Tao compute cluster

1. Azure ML Studio → Compute → Compute clusters → New.
2. Chon instance type (vi du: Standard_F2s_v2) va min/max nodes phu hop.
3. Create va doi trang thai Running/Idle.

## 3. Tao data assets

Nguon du lieu da co trong repo:
- data/processed/ml/banking77_train_mapped.csv
- data/processed/ml/banking77_test_mapped.csv

Cach tao:
1. Azure ML Studio → Data → Create → Data asset.
2. Upload hai file CSV tren (dat ten: banking77_train_mapped, banking77_test_mapped).
3. Kiem tra schema: cot text va label.

## 4. Tao environment (UI)

**Khuyen dung environment co san (curated) cho XGBoost/LR**
1. Azure ML Studio → Environments → Curated.
2. Chon environment: `AzureML-sklearn-1.5-ubuntu20.04-py38-cpu` (hoac tuong duong).

**Bat buoc dung custom env cho BERT**
1. Azure ML Studio → Environments → Create.
2. Upload file `mlop_training_job/train_env.yml`.
3. Chon loai: `Conda requirement file`.
4. Luu ten environment (vi du: `intent-bert-env`).

## 5. Chay training job (UI)

1. Azure ML Studio → Jobs → Create job → Command.
2. Input code: upload thu muc `mlop_training_job/`.
3. Inputs:
   - train_data: chon data asset `banking77_train_mapped`
   - test_data: chon data asset `banking77_test_mapped`
3. Chon environment:
   - Cho XGBoost/LR: Dung curated environment o buoc 4.
   - Cho BERT: Dung custom environment `intent-bert-env` vua tao.
4. Chon compute cluster:
   - **Luu y:** BERT nen dung GPU (dong NC) de toc do nhanh hon. Neu dung CPU (dong F/D), hay giam `epochs` xuong 1.
5. Command:
   - **XGBoost:** `python train.py --model xgb --train-path ${{inputs.train_data}} --test-path ${{inputs.test_data}}`
   - **BERT:** `python train.py --model bert --train-path ${{inputs.train_data}} --test-path ${{inputs.test_data}} --epochs 2 --batch-size 16`
7. Submit va doi job hoan thanh.

Ket qua ky vong:
- F1-macro > 0.85
- Log metrics trong MLflow (tab Metrics cua job)

## 6. Register model (UI)

1. Mo job vua chay → Outputs + logs.
2. Chon output folder `outputs/model` (co file `MLmodel`) → Register model.
3. Chon model type: MLflow.
4. Dat ten model: banking77-xgb-tfidf (hoac ten tuong tu).
5. Kiem tra model o tab Models.

## 7. Tao Managed Online Endpoint (UI)

1. Azure ML Studio → Endpoints → Online endpoints → Create.
2. Dat ten endpoint: banking77-intent-endpoint.
3. Chon Auth mode: Key.
4. Create.

## 8. Tao deployment blue (UI)

1. Mo endpoint → Deployments → Add.
2. Chon model vua register (MLflow).
3. Chon deploy type: Deploy MLflow model.
4. Chon environment (curated hoac custom neu can).
5. Chon instance type (Standard_F2s_v2) va instance count.
6. Bat Data collection (model inputs + outputs).
7. Dat ten deployment: blue.
8. Create va doi trang thai Succeeded.

## 9. Tao deployment green (staging)

1. Lam giong buoc 8, dat ten deployment: green.
2. De traffic green = 0%, blue = 100%.

## 10. Monitor drift (UI)

1. Azure ML Studio → Monitoring → Create.
2. Chon endpoint + deployment.
3. Chon reference dataset: banking77_train_mapped.
4. Chon target column (neu co): `simplified`.
5. Chon feature columns (input): `text` (hoac cac cot input khac neu co).
6. Bat cac signal:
   - Input data drift.
   - Prediction drift (neu endpoint log duoc prediction).
   - Data quality (tuy chon).
7. Chon monitoring window (vi du: 7d) va threshold canh bao.
8. Dat schedule (vi du: daily 03:15 UTC) va Create.
9. Trigger ngay: mo schedule vua tao → chon Run now/Trigger.

## 11. Lay endpoint key va gan vao API

1. Endpoint → Keys & Endpoint.
2. Copy scoring URI va primary key.
3. Cap nhat .env:
   - AZURE_ML_ENDPOINT_URL
   - AZURE_ML_ENDPOINT_KEY

## 12. Kiem tra tich hop FastAPI

1. Azure ML Studio → Endpoints → Test (UI) voi sample JSON.
2. API local su dung URL + key tu .env.

## Luu y dat chat luong

- Gate MLOps: F1-macro > 0.85 (kiem tra trong job metrics).
- Neu F1 chua dat, thu:
  - Doi model (xgb va tfidf),
  - Can bang du lieu (neu can),
  - Thu cross-validation.
