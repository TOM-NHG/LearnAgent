# 🏛️ Agent of MRP: University Financial & Academic Knowledge Graph AI (Version 1.0)

> **Hệ thống Trí tuệ Nhân tạo & Đồ thị Tri thức Quản trị Tài chính - Đào tạo Đại học**  
> Vận hành 100% Offline bảo mật cao trên nền tảng **Neo4j Graph Database** + **Ollama Qwen 2.5 7B Local LLM**.

---

## 🌟 Tính Năng Nổi Bật (Version 1.0)

1. **Dữ liệu sạch & Feature Store:** Pipeline tự động khắc phục triệt để 1.086+ sự kiện lỗi dữ liệu, nén Parquet Snappy giảm ~60% dung lượng và tạo sẵn 2 bảng ML Feature Store (`ml_student_finance_features`, `ml_invoice_risk_features`).
2. **Đồ thị tri thức Neo4j quy mô lớn:** Mô hình hóa **12.929 Nodes** và **18.469 Relationships** đa chiều giữa Sinh viên, Hóa đơn, Giao dịch nộp tiền, Chi phí hoạt động, Khoa/Phòng ban và Nhà cung cấp.
3. **Trợ lý AI Đàm thoại Tiếng Việt:** Few-Shot Semantic Cypher QA Chain cho phép hỏi đáp tự nhiên, trích xuất chính xác số liệu tài chính mà không rò rỉ dữ liệu ra Internet.
4. **Bảo mật & Guardrails:** Cơ chế phân quyền Read-Only và bộ lọc tự động chặn các câu lệnh Cypher nguy hiểm (`DELETE`, `DROP`, `SET`, `REMOVE`).
5. **Giao diện & Dashboard:** Trực quan hóa toàn diện với **Executive Financial Dashboard** và **Interactive Web Chat UI** qua FastAPI Server.

---

## 🏗️ Kiến Trúc Hệ Thống

```
d:/NHG/AgentofMRP/
├── data/
│   ├── cleaned/                    # Dữ liệu sạch dạng Parquet & CSV
│   ├── ml_ready/                   # Feature Store phân tích rủi ro & ML training
│   ├── mrp_finance.db              # CSDL SQLite lưu trữ 12 công thức nghiệp vụ
│   └── data_quality_manifest.csv   # Nhật ký kiểm định chất lượng dữ liệu
├── reports/
│   ├── MRP_V1_PROJECT_REVIEW_AND_V2_ROADMAP_REPORT.md # Báo cáo tổng kết V1 & Lộ trình V2
│   ├── MRP_PROJECT_MILESTONE_AND_ARCHITECTURE_REPORT.md # Báo cáo kiến trúc hệ thống
│   ├── DATA_CLEANING_AND_ML_OPTIMIZATION_REPORT.md      # Báo cáo kỹ thuật làm sạch dữ liệu
│   ├── MRP_FINANCIAL_FORMULAS_AND_SQL_SPECIFICATION.md  # Cẩm nang 12 công thức SQL
│   ├── mrp_executive_dashboard.html                     # Bảng điều khiển tài chính tương tác
│   └── figures/                                         # Biểu đồ phân tích độ phân giải cao
├── scripts/
│   ├── run_data_remediation_pipeline.py # Pipeline làm sạch & Feature Store tự động
│   ├── execute_sql_formulas_and_export.py # Script tính toán 12 chỉ số tài chính
│   └── generate_erd_diagram.py          # Script vẽ sơ đồ ERD
├── agent.py                        # LangChain Tool Agent & Security Guardrails
├── graph_qa.py                     # Few-Shot Semantic Cypher Engine & Ollama LLM
├── load_data.py                    # Script nạp dữ liệu lô vào Neo4j
├── main.py                         # FastAPI Server & REST API endpoint
├── setup_guardrail_user.py         # Script phân quyền user Neo4j
├── chat.html                       # Giao diện Web Chat tương tác
└── .env.example                    # File mẫu cấu hình môi trường
```

---

## 🚀 Hướng Dẫn Cài Đặt & Chạy Hệ Thống

### 1. Cài đặt môi trường & Thư viện
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt # hoặc cài đặt fastapi uvicorn langchain langchain-neo4j langchain-community pandas pyarrow python-dotenv
```

### 2. Cấu hình file `.env`
Sao chép `.env.example` thành `.env` và điền thông tin kết nối Neo4j:
```ini
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen2.5:7b-instruct
```

### 3. Nạp dữ liệu vào Neo4j
```bash
python load_data.py
```

### 4. Khởi động AI REST API & Web Chat
```bash
python main.py
```
Truy cập trình duyệt:
* 💬 **Web Chat UI:** `http://127.0.0.1:8000`
* 📚 **Swagger API Docs:** `http://127.0.0.1:8000/docs`
* 📊 **Executive Dashboard:** Mở file `reports/mrp_executive_dashboard.html`

---

## 📜 Tài Liệu Báo Cáo Kỹ Thuật
Chi tiết xem tại thư mục [`reports/`](file:///d:/NHG/AgentofMRP/reports):
- [Báo Cáo Tổng Kết V1.0 & Lộ Trình V2.0](reports/MRP_V1_PROJECT_REVIEW_AND_V2_ROADMAP_REPORT.md)
- [Cẩm Nang 12 Công Thức SQL Nghiệp Vụ](reports/MRP_FINANCIAL_FORMULAS_AND_SQL_SPECIFICATION.md)
- [Báo Cáo Làm Sạch Dữ Liệu & ML Feature Store](reports/DATA_CLEANING_AND_ML_OPTIMIZATION_REPORT.md)
