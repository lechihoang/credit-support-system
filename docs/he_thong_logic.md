## 2.2. Thuật toán xử lý và Luồng Logic hệ thống

Hệ thống được thiết kế và vận hành hoàn toàn trên hệ sinh thái Azure AI (Cloud-native), đảm bảo tính nhất quán từ khâu phát triển đến triển khai thực tế. Kiến trúc bao gồm hai phân hệ cốt lõi: Phân loại ý định (MLOps) và Trợ lý RAG thông minh (GenAIOps).

### A. Phân hệ Phân loại Ý định (MLOps Flow)
Phân hệ này đảm nhận vai trò định tuyến các yêu cầu của khách hàng vào các nhóm nghiệp vụ cụ thể. Hệ thống hỗ trợ đa dạng cấp độ mô hình để tối ưu hóa giữa hiệu năng và chi phí:

1. **Các mô hình huấn luyện:**
   - **Baseline (Logistic Regression):** Sử dụng bộ trích xuất đặc trưng **TF-IDF** (với ngram_range=(1, 2)). Mô hình được tối ưu hóa bằng solver `lbfgs` và xử lý mất cân bằng dữ liệu bằng tham số `class_weight='balanced'`. Phù hợp cho các phản hồi nhanh (< 0.5s).
   - **Advanced (XGBoost):** Sử dụng thuật toán tăng cường độ dốc (Gradient Boosting) với mục tiêu `multi:softprob`. Kỹ thuật `tree_method='hist'` được áp dụng để tăng hiệu suất xử lý trên các đặc trưng thưa (sparse features) từ TF-IDF.
   - **Deep Learning (BERT):** Fine-tune mô hình ngôn ngữ lớn `bert-base-uncased` (Transformers). BERT giúp hệ thống hiểu ngữ cảnh sâu (Deep Context) và phân biệt các câu hỏi có từ ngữ tương tự nhưng ý định khác nhau.

2. **Quy trình MLOps (Inner Loop):**
   - **Tracking:** Mọi phiên bản huấn luyện đều được ghi nhật ký (Logging) qua **MLflow**, bao gồm: Accuracy, Recall, và F1-macro.
   - **Quality Gate:** Chỉ các mô hình đạt F1-score > 0.85 mới được đăng ký vào **Azure ML Model Catalog**.
   - **Deployment:** Triển khai dưới dạng **Managed Online Endpoints** với cơ chế **Blue-Green Deployment** để đảm bảo không gián đoạn dịch vụ khi cập nhật phiên bản mới.

3. **Kết quả & Metric:**
   - Thời gian xử lý trung bình: **~0.8s/request**.
   - Metric chính: **F1-macro score**, **Confusion Matrix** (để phát hiện các nhãn bị nhầm lẫn).

---

### B. Phân hệ Trợ lý Thông minh RAG (GenAIOps Flow)
Phân hệ này cung cấp khả năng trả lời câu hỏi tự động dựa trên tri thức từ tài liệu chính sách của ngân hàng.

1. **Kiến trúc RAG chi tiết:**
   - **BƯỚC 1: Content Safety:** Kiểm tra tính an toàn của câu hỏi đầu vào (Input Filter) để ngăn chặn các truy vấn độc hại hoặc vi phạm chính sách bảo mật.
   - **BƯỚC 2: Vector hóa (Embedding):** Sử dụng mô hình `text-embedding-3-small` để chuyển đổi văn bản sang vector 1536 chiều.
   - **BƯỚC 3: Truy vấn Hybrid Search (Azure AI Search):** Kết hợp đồng thời **Keyword Search** (tìm kiếm chính xác thuật ngữ) và **Vector Search** (tìm kiếm theo ý nghĩa).
   - **BƯỚC 4: Tái xếp hạng (Semantic Ranking):** Sử dụng lớp xếp hạng ngữ nghĩa của Azure AI Search để chọn lọc ra 5 đoạn văn bản (chunks) có giá trị nhất từ bộ dữ liệu "Điều khoản thẻ tín dụng Techcombank".
   - **BƯỚC 5: Prompt Orchestration (Prompt Flow):** 
     - Tích hợp ngữ cảnh (Context) vào mô hình **GPT-4o-mini**.
     - Hệ thống System Message được thiết kế để AI đóng vai một chuyên viên tư vấn tài chính chuyên nghiệp: "Trả lời chính xác, từ tốn và chỉ sử dụng thông tin từ tài liệu được cung cấp".

2. **Đánh giá chất lượng GenAI (Azure Evaluation):**
   Việc đánh giá không chỉ dựa trên độ chính xác mà còn qua 3 chỉ số chuyên sâu từ Azure AI Foundry:
   - **Groundedness (Tính xác thực):** Đảm bảo câu trả lời không có hiện tượng "ảo giác" (Hallucination), mọi thông tin phải có nguồn gốc từ tài liệu PDF (Mục tiêu > 4/5).
   - **Relevance (Độ phù hợp):** Đo lường mức độ sát thực của câu trả lời so với câu hỏi của khách hàng.
   - **Coherence (Sự mạch lạc):** Đánh giá cấu trúc câu trả lời có logic và dễ hiểu cho khách hàng hay không.

3. **Vận hành & Giám sát:**
   - Sử dụng **Managed Endpoints** cho phép scale-out linh hoạt theo lượng truy cập.
   - Giám sát luồng qua **Azure Tracing** và **Application Insights** để phát hiện lỗi trong quá trình RAG.

---

### C. So sánh và Tổng kết
Hệ thống kết hợp sức mạnh của **MLOps** (tốc độ cao, chi phí thấp cho các tác vụ phân loại lặp đi lặp lại) và **GenAIOps** (khả năng xử lý tri thức linh hoạt, cá nhân hóa phản hồi). Toàn bộ hạ tầng được quản lý tập trung trên Azure giúp tối ưu chi phí vận hành (Compute cost) và dễ dàng mở rộng trong tương lai.
