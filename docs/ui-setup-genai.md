# UI Setup — GenAIOps (Chatbot RAG) - Hướng dẫn Toàn diện (Full Version)

Tài liệu này hướng dẫn thiết lập hệ thống RAG từ A-Z, tuân thủ mọi yêu cầu của Bài tập 14, sử dụng Streamlit local để thực hiện vòng lặp Human-in-the-loop.

## 1. Deploy Model (Azure AI Foundry)
1.  **gpt-4o-mini**: Vào Model Catalog -> Deploy bản **Standard** (Pay-as-you-go). Đặt tên là `gpt-4o`. Hạ TPM xuống **5k** để an toàn.
2.  **text-embedding-3-small**: Deploy bản Standard. Đặt tên là `text-embedding-3-small`.

## 2. Thiết lập Search & DataOps (Yêu cầu 2)
1.  **Azure AI Search**: Tạo tài nguyên gói **Standard S1** (để có Semantic Ranker) tại vùng East US.
2.  **Upload PDF**: Tải file `techcombank_tc_2025.pdf` lên một Container trong **Azure Blob Storage**.
3.  **Wizard Indexing**: Trong AI Foundry, dùng Wizard **"Import and vectorize data"**:
    - Source: Trỏ về file PDF trong Blob.
    - Embedding: Chọn model `text-embedding-3-small`.
    - Index name: `techcombank-terms`.
    - Azure sẽ tự động Chunking và Vectorization.

## 3. Cấu hình Content Safety (Yêu cầu 3.B.2)
1.  Tạo tài nguyên **Azure AI Content Safety (F0)** trên Portal.
2.  Trong AI Foundry, tạo **Connection** tới tài nguyên này.
3.  Trong Prompt Flow, cấu hình node `content_safety` sử dụng Connection trên để lọc các câu hỏi nhạy cảm/độc hại.

## 4. Orchestration với Prompt Flow (Yêu cầu 3.A.2)
1.  **Import**: Tải thư mục `genai/deployment/` lên Prompt Flow trong AI Foundry.
2.  **Config**: Nối các node Input -> Content Safety -> Search -> Prompt -> LLM -> Output.
3.  **Prompt Engineering**: Chỉnh sửa file `chat.jinja2` để AI trả lời chuyên nghiệp và bám sát tài liệu ngân hàng.

## 5. Evaluation - Đánh giá chất lượng (Yêu cầu 5)
1.  Vào tab **Evaluation** trong Prompt Flow.
2.  Chạy đánh giá tự động các chỉ số: **Groundedness, Relevance, Coherence**.
3.  Đảm bảo điểm **Groundedness > 4/5**. Nếu thấp hơn, phải quay lại bước 4 để sửa Prompt.

## 6. Deployment - Managed Online Endpoint (Yêu cầu 3.B.1)
1.  Nhấn nút **Deploy** trong Prompt Flow để tạo **Managed Online Endpoint**.
2.  Lấy **Scoring URI** và **Primary Key** để điền vào file `.env`.
3.  **Lưu ý**: Endpoint này tốn phí máy ảo (~$5/ngày), cần xóa ngay sau khi demo.

## 7. Human-in-the-loop (HITL) với Feedback API (Yêu cầu 3.B.2)
Sử dụng **Built-in Feedback API** của Prompt Flow để thu thập phản hồi chuyên nghiệp và tự động liên kết với Traces.

1.  **Lấy Trace ID**: Khi gọi Endpoint để lấy câu trả lời (`/score`), hãy trích xuất **`x-ms-client-request-id`** (hoặc `traceparent`) từ response header. Đây là ID duy nhất để định danh lượt truy vấn.
2.  **Gửi Feedback qua API**: Khi người dùng nhấn Like/Dislike trên UI (Streamlit), gửi một yêu cầu `POST` tới endpoint `/feedback`:
    - **URL**: `https://<your-endpoint>.inference.ml.azure.com/feedback`
    - **Payload**:
      ```json
      {
        "trace_id": "<ID_vừa_lấy>",
        "payload": {
          "rating": "thumbs_up",
          "comment": "Câu trả lời chính xác",
          "metadata": { "user_id": "test_user" }
        }
      }
      ```
3.  **Vòng lặp (The Loop)**: 
    - Xem phản hồi trực tiếp trong tab **Monitoring** hoặc dùng KQL trong **Application Insights** để lọc các câu bị "thumbs_down".
    - Điều chỉnh Prompt trong `chat.jinja2` dựa trên góp ý của người dùng.
    - Chạy lại Evaluation để xác nhận cải thiện.

## 8. Monitoring - Giám sát hệ thống (Yêu cầu 3.B.2)
1.  Vào tab **Monitoring** của Project trong AI Foundry.
2.  Theo dõi biểu đồ về độ an toàn nội dung (Content Safety) và chất lượng câu trả lời từ dữ liệu thực tế.

## 9. Báo cáo Chi phí (Yêu cầu 5)
1.  Sử dụng dữ liệu từ file `reports/cost_comparison.md`.
2.  So sánh: MLOps (XGBoost) tập trung vào hiệu năng/chi phí thấp, GenAIOps (GPT) tập trung vào trải nghiệm người dùng/tri thức.

---

### ⚠️ QUY TẮC BẢO VỆ TÀI KHOẢN (Student & PAYG):
1.  **Xóa Endpoint** (Mục 6) ngay sau khi quay phim/demo xong.
2.  **Xóa Azure AI Search S1** (Mục 2) sau khi hoàn thành bài tập.
3.  Các tài nguyên khác (OpenAI, Content Safety, App Insights) có thể giữ lại vì không dùng không tốn phí.
