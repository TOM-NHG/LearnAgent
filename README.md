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

## 🧪 Hướng Dẫn Chạy & Kiểm Thử Hệ Thống (Test Runner)

### 1. Chạy bộ kiểm thử tự động (Automated Test Suite)
Để kiểm tra tính toàn vẹn của Ontology, SHACL Shapes, Fast-Path Router và FastAPI Server:
```bash
venv\Scripts\python test_v2_suite.py
```
> **Kết quả kỳ vọng:** `ALL 5 TEST CASES PASSED SUCCESSFULLY (100% GREEN)!`

### 2. Khởi động máy chủ API & Giao diện Web Chat V2.0
```bash
venv\Scripts\python main.py
```
Truy cập trình duyệt:
* 💬 **Web Chat UI:** `http://127.0.0.1:8000` hoặc `http://127.0.0.1:8000/chat-ui`
* 📚 **Tài liệu Swagger REST API:** `http://127.0.0.1:8000/docs`
* 📊 **Executive Financial Dashboard:** Mở file `reports/mrp_executive_dashboard.html`

### 3. Thử nghiệm các câu hỏi mẫu trên Web Chat hoặc API
| Nhóm Câu Hỏi | Câu Hỏi Mẫu | Thời Gian Phản Hồi | Nguồn Xử Lý |
|---|---|:---:|:---:|
| **Công nợ toàn trường** | *"Tổng công nợ còn lại của trường là bao nhiêu?"* | **< 0.05 giây** | `FAST_PATH_TEMPLATE` |
| **Doanh thu học phí** | *"Doanh thu học phí đã lập hóa đơn"* | **< 0.05 giây** | `FAST_PATH_TEMPLATE` |
| **Tiền thực thu** | *"Tổng tiền thực thu về tài khoản"* | **< 0.05 giây** | `FAST_PATH_TEMPLATE` |
| **Top sinh viên nợ** | *"Top 5 sinh viên nợ nhiều nhất"* | **< 0.05 giây** | `FAST_PATH_TEMPLATE` |
| **Điểm rủi ro sinh viên**| *"Top 5 sinh viên có rủi ro cao nhất"* | **< 0.05 giây** | `FAST_PATH_TEMPLATE` |
| **Ngân sách các khoa** | *"Khoa nào có ngân sách lớn nhất"* | **< 0.05 giây** | `FAST_PATH_TEMPLATE` |
| **Dòng tiền thuần** | *"Dòng tiền thuần của trường đang âm hay dương?"*| **< 0.05 giây** | `FAST_PATH_TEMPLATE` |
| **Tỷ lệ thu học phí** | *"Tỷ lệ thu học phí đạt bao nhiêu %?"* | **< 0.05 giây** | `FAST_PATH_TEMPLATE` |

---

## 📜 Tài Liệu Thiết Kế & Báo Cáo
- 📑 [Business Requirements Document (BRD V2.0)](reports/MRP_V2_BUSINESS_REQUIREMENTS_DOCUMENT_BRD.md)
- 🏛️ [Báo Cáo Nghiệm Thu V1.0 & Lộ Trình Nâng Cấp V2.0](reports/MRP_V1_PROJECT_REVIEW_AND_V2_ROADMAP_REPORT.md)
- 📊 [Cẩm Nang 12 Công Thức Tài Chính & SQL Specification](reports/MRP_FINANCIAL_FORMULAS_AND_SQL_SPECIFICATION.md)
- 🛠️ [Báo Cáo Kỹ Thuật Làm Sạch Dữ Liệu & Feature Store](reports/DATA_CLEANING_AND_ML_OPTIMIZATION_REPORT.md)
