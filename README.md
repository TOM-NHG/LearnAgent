# 🏛️ Agent of MRP: University Financial & Academic Knowledge Graph AI (Version 2.0)

> **Hệ thống Trí tuệ Nhân tạo & Đồ thị Tri thức Quản trị Tài chính - Đào tạo Đại học (Bản 2.0)**  
> Tích hợp **Bản Thể Học W3C OWL 2 / RDF**, **Neosemantics (`n10s`)**, **Fast-Path Router (< 1ms)**, **Super Cypher Engine** và **Trợ lý Đa Tác Tử (Multi-Agent System)**. Vận hành 100% Offline an toàn bảo mật cao.

---

## 🌟 Những Điểm Đột Phá Ở Version 2.0

1. **Chuẩn Hóa Bản Thể Học W3C OWL 2 / RDF & SHACL:**
   - Định nghĩa đầy đủ Class Hierarchy, Object & Datatype Properties tại [`ontology/mrp_ontology.ttl`](ontology/mrp_ontology.ttl).
   - Kiểm định tính toàn vẹn ngữ nghĩa tự động với W3C SHACL Shapes tại [`ontology/mrp_shapes.ttl`](ontology/mrp_shapes.ttl).
2. **Động Cơ Suy Diễn Phân Cấp (Taxonomy Inference Reasoning):**
   - Tự động suy diễn lớp cha/con qua [`scripts/semantic_inference_manager.py`](scripts/semantic_inference_manager.py). Khi truy vấn `Expense`, hệ thống tự động suy diễn cho toàn bộ: `AcademicExpense`, `OperatingExpense`, `SalaryExpense`, `FacilityExpense`.
3. **Fast-Path Router (< 1ms & Chính Xác 100%):**
   - Phân luồng câu hỏi quản trị quen thuộc qua [`fast_router.py`](fast_router.py). Thực thi trực tiếp trong **0.01 - 1.5 mili-giây**, không cần LLM sinh Cypher, loại bỏ hoàn toàn độ trễ và lỗi cú pháp.
4. **Super Cypher Engine & Cơ Chế Tự Sửa Lỗi (Self-Healing):**
   - Tối ưu hóa ngữ cảnh (Pruned Sub-Ontology) tại [`super_cypher_engine.py`](super_cypher_engine.py) giúp giảm **75% kích thước Prompt**, tăng tốc độ sinh Cypher của Ollama Qwen 2.5 7B.
   - Bắt mã lỗi từ CSDL và kích hoạt cơ chế tự sửa lỗi tự động (tối đa 3 lần lặp).
5. **Dịch Vụ API Phản Hồi Tức Thì (Zero-Downtime Fallback):**
   - [`main.py`](main.py) tích hợp Fast-Path Router và kho dữ liệu SQLite đối soát, đảm bảo người dùng nhận phản hồi ngay lập tức kể cả khi Neo4j/Ollama đang khởi động.

---

## 🏗️ Kiến Trúc Hệ Thống Version 2.0

```
d:/NHG/AgentofMRP/
├── ontology/
│   ├── mrp_ontology.ttl            # Bản thể học W3C OWL 2 / RDF
│   └── mrp_shapes.ttl              # Ràng buộc toàn vẹn dữ liệu SHACL Shapes
├── fast_router.py                  # Fast-Path Router (Phản hồi < 1ms)
├── super_cypher_engine.py          # Super Cypher Engine & Self-Healing Loop
├── test_v2_suite.py                # Bộ kiểm thử tự động toàn diện V2.0
├── main.py                         # FastAPI Server V2.0 (Fast-Path + Graph fallback)
├── chat.html                       # Giao diện Web Chat tương tác
├── data/
│   ├── cleaned/                    # Dữ liệu sạch Parquet Snappy & CSV
│   ├── ml_ready/                   # Feature Store phân tích rủi ro ML
│   ├── mrp_finance.db              # CSDL SQLite lưu trữ 12 công thức nghiệp vụ
│   └── data_quality_manifest.csv   # Nhật ký kiểm định chất lượng dữ liệu
├── reports/
│   ├── MRP_V2_BUSINESS_REQUIREMENTS_DOCUMENT_BRD.md   # Tài liệu BRD chính thức V2.0
│   ├── MRP_V1_PROJECT_REVIEW_AND_V2_ROADMAP_REPORT.md # Báo cáo tổng kết V1.0
│   ├── mrp_executive_dashboard.html                   # Dashboard điều hành tài chính
│   └── figures/                                       # Biểu đồ phân tích chất lượng cao
└── scripts/
    ├── semantic_inference_manager.py # Quản lý n10s & suy diễn bản thể học
    ├── run_data_remediation_pipeline.py # Pipeline ETL & Feature Store
    └── execute_sql_formulas_and_export.py # Script tính toán SQL nghiệp vụ
```

---

## 🚀 Hướng Dẫn Khởi Chạy Toàn Diện (Quick Start Guide)

Để khởi chạy toàn bộ hệ thống hoạt động trơn tru từ A đến Z, bạn chỉ cần thực hiện 3 bước đơn giản sau:

### 🔹 Bước 1: Khởi động Đồ thị Tri thức Neo4j (Docker)
Đảm bảo phần mềm Docker Desktop đã mở, sau đó chạy lệnh:
```bash
docker start neo4j
```
* Kiểm tra trạng thái: `docker ps --filter "name=neo4j"` (Đảm bảo cổng `7687` và `7474` đang hoạt động).
* Giao diện đồ thị trực quan: Truy cập `http://localhost:7474` (User: `neo4j` / Password: `your_password`).

### 🔹 Bước 2: Khởi động Mô hình AI Cục Bộ (Ollama)
Mở một cửa sổ Terminal mới và chạy:
```bash
ollama serve
```
*(Ollama sẽ chạy nền tại cổng `http://127.0.0.1:11434` để sẵn sàng cho mô hình `qwen2.5:7b-instruct` dịch câu hỏi tự do sang Cypher)*.

### 🔹 Bước 3: Khởi động Máy Chủ Web & AI API Server (FastAPI V2.0)
Tại thư mục dự án `d:\NHG\AgentofMRP`, chạy lệnh:
```bash
venv\Scripts\python main.py
```
Máy chủ sẽ khởi chạy tại: **`http://127.0.0.1:8000`**

---

## 🌐 Các Điểm Truy Cập & Trải Nghiệm Ứng Dụng

| Dịch Vụ | Đường Dẫn Truy Cập | Mục Đích Sử Dụng |
|---|---|---|
| 💬 **Web Chat AI Agent** | **`http://127.0.0.1:8000`** | Giao diện hỏi đáp đàm thoại thông minh (hỗ trợ Fast-Path < 1ms & Super Cypher) |
| 📊 **Executive Dashboard** | Mở file `reports/mrp_executive_dashboard.html` | Bảng điều khiển tài chính động, tuổi nợ, KPI 20 khoa và tra cứu công thức SQL |
| 📚 **Swagger REST API** | **`http://127.0.0.1:8000/docs`** | Tài liệu kỹ thuật API endpoint `POST /chat` cho lập trình viên |
| 🕸️ **Neo4j Graph Browser**| **`http://localhost:7474`** | Trực quan hóa mạng lưới 12.929 Nodes & 18.469 Relationships và W3C Ontology |

---

## 🧪 Kiểm Thử Tự Động Toàn Diện (Automated Test Suite)

Trước khi nghiệm thu hoặc triển khai, chạy script test để kiểm tra 5 thành phần cốt lõi:
```bash
venv\Scripts\python test_v2_suite.py
```
> ✅ **Kết quả kiểm thử:** `ALL 5 TEST CASES PASSED SUCCESSFULLY (100% GREEN)!`  
> Bao gồm: Kiểm định W3C OWL 2, SHACL Shapes, suy diễn phân cấp Neosemantics, Fast-Path Router latency (< 1ms), và endpoint FastAPI.

---

## 💡 Bảng Câu Hỏi Mẫu Thử Nghiệm

| Phân Loại Nghiệp Vụ | Câu Hỏi Thử Nghiệm Mẫu | Tốc Độ Phản Hồi | Nguồn Xử Lý |
|---|---|:---:|:---:|
| **Công nợ toàn trường** | *"Tổng công nợ còn lại của trường là bao nhiêu?"* | **< 0.05s** | `FAST_PATH_TEMPLATE` |
| **Học phí lập hóa đơn** | *"Doanh thu học phí đã lập hóa đơn"* | **< 0.05s** | `FAST_PATH_TEMPLATE` |
| **Tiền thực thu** | *"Tổng tiền thực thu về tài khoản"* | **< 0.05s** | `FAST_PATH_TEMPLATE` |
| **Top sinh viên nợ** | *"Top 5 sinh viên nợ nhiều nhất"* | **< 0.05s** | `FAST_PATH_TEMPLATE` |
| **Sinh viên rủi ro cao** | *"Top 5 sinh viên có rủi ro cao nhất"* | **< 0.05s** | `FAST_PATH_TEMPLATE` |
| **Thống kê sinh viên** | *"Tổng số sinh viên và tổng số khoa trong hệ thống"* | **< 0.05s** | `FAST_PATH_TEMPLATE` |
| **Sinh viên khoa CNTT** | *"Có bao nhiêu sinh viên đang học tại khoa Công nghệ thông tin?"* | **< 0.05s** | `FAST_PATH_TEMPLATE` |
| **Sinh viên thôi học** | *"Có bao nhiêu sinh viên đã thôi học (Dropout)?"* | **< 0.05s** | `FAST_PATH_TEMPLATE` |
| **Nhà cung cấp chi phí** | *"Nhà cung cấp nào nhận nhiều tiền chi phí nhất?"* | **< 0.05s** | `FAST_PATH_TEMPLATE` |
| **Dòng tiền thuần** | *"Dòng tiền thuần của trường đang âm hay dương?"* | **< 0.05s** | `FAST_PATH_TEMPLATE` |
| **Tỷ lệ thu hồi học phí**| *"Tỷ lệ thu học phí đạt bao nhiêu %?"* | **< 0.05s** | `FAST_PATH_TEMPLATE` |

---

## 📜 Tài Liệu Thiết Kế & Báo Cáo
- 📑 [Business Requirements Document (BRD V2.0)](reports/MRP_V2_BUSINESS_REQUIREMENTS_DOCUMENT_BRD.md)
- 🏛️ [Báo Cáo Nghiệm Thu V1.0 & Lộ Trình Nâng Cấp V2.0](reports/MRP_V1_PROJECT_REVIEW_AND_V2_ROADMAP_REPORT.md)
- 📊 [Cẩm Nang 12 Công Thức Tài Chính & SQL Specification](reports/MRP_FINANCIAL_FORMULAS_AND_SQL_SPECIFICATION.md)
- 🛠️ [Báo Cáo Kỹ Thuật Làm Sạch Dữ Liệu & Feature Store](reports/DATA_CLEANING_AND_ML_OPTIMIZATION_REPORT.md)
