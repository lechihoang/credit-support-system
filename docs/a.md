- tạo resource group group ml-techcombank
- vào azure machine learning -> tạo workspace ml-techcombank
<!-- - vào azure ml studio -> compute -> new đặt tên là tên ml-techcombank -->
- vào azure ml studio -> data asset -> new tên ml techcomabank, kiểu mltable -> bấm skip data validation ở 4 ml table section
- vào azure ml studio -> environment -> custom environment -> new tên ml-techcombank, ở phần 2, dùng mlops/azure_training_conda.yml
- vào azure ml studio -> job -> all jobs -> create job
- upload folder ui_training_min
- thêm input train_data, test_data (chọn data asset đã tạo)
- command:
	- python train.py --model xgb --train-path ${{inputs.train_data}} --test-path ${{inputs.test_data}}
- environment dùng custom environment đã tạo, submit và chạy
- sau khi chạy xong: vào job -> outputs, register model bằng UI
- sau đó vào endpoint -> create, thêm tạm một model, sau đó sẽ có job deploy docker image, sau đó thì add deployment, thêm model 2, sau đó update traffic, bật package model, thu thập data, Standard_F2s_v2, 3 instance,
đợi 2 model deploy xong thì update traffic
- job -> schedule để sửa, sau đó dùng drift_job.py, 
python drift_job.py \
  --ref ${{inputs.ref_data}} \
  --prod ${{inputs.prod_data}} \
  --text-col text \
  --out-dir outputs
trỏ, ref_data tới data train, prod_data tới data input của model


Phần genaiop

- tạo service mới ở azure foundry
- vào model catalog, deploy llama-70b và text_embedding-3_small
  1. Vào Azure Portal (portal.azure.com).
   2. Tìm đến Resource Group chứa cái AI Foundry này.
   3. Chọn mục Access Control (IAM).
   4. Nhấn + Add -> Add role assignment.
   5. Chọn role Azure AI Developer.
   6. Chọn tên tài khoản của bạn và nhấn Save.
- sau đó tạo azure ai search (bản free), vào foundry-> management cent->kết nối với ai search
- vào azure ai search -> import data -> blob(chọn RAG)-> kết nối foundry (chọn cái deploy embedding)
- tạo azure content safety
- vào tracing, tạo application insight
- vào prompt flow, upload file