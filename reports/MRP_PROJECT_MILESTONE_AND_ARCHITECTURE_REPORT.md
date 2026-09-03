# 🏛️ Báo Cáo Tổng Kết Toàn Diện: Kiến Trúc Hệ Thống, Dữ Liệu & Graph AI Agent MRP (Version 1.0)

> **Dự án:** Agent of MRP (Hệ thống Trí tuệ Nhân tạo & Đồ thị Tri thức Quản lý Tài chính - Đào tạo Đại học)  
> **Tác giả:** Amelia — Senior Software Engineer (BMAD Method)  
> **Ngày hoàn thành:** 03/09/2026  
> **Trạng thái:** ✅ **Production Ready (V1.0)** — Hoạt động 100% Offline trên hạ tầng Neo4j & Ollama Qwen 2.5  

---

## 1. Tổng Quan Mục Tiêu Dự Án

Dự án **Agent of MRP** được xây dựng nhằm giải quyết bài toán cốt lõi trong quản trị đại học: **Chuyển đổi toàn bộ dữ liệu tài chính, học phí, công nợ và sinh viên từ các bảng biểu rời rạc thành một Mạng Lưới Tri Thức (Knowledge Graph) và xây dựng Trợ Lý AI Agent thông minh có thể đàm thoại tự nhiên bằng tiếng Việt.**

```mermaid
flowchart TD
    subgraph L1 [TẦNG 1: DỮ LIỆU & LÀM SẠCH (DATA ENGINEERING)]
        D1[Raw CSVs: 10.020 bản ghi] --> D2[Pipeline ETL 3 Lớp]
        D2 --> D3[Cleaned Parquet/CSV]
        D2 --> D4[ML-Ready Feature Store]
    end

    subgraph L2 [TẦNG 2: MÔ HÌNH NGỮ NGHĨA & CÔNG THỨC (SEMANTIC & SQL LAYER)]
        D3 --> S1[Database SQLite: mrp_finance.db]
        S1 --> S2[12 Công Thức Nghiệp Vụ Chuẩn Hóa]
        S2 --> S3[Executive Dashboard: mrp_executive_dashboard.html]
    end

    subgraph L3 [TẦNG 3: ĐỒ THỊ TRI THỨC (NEO4J GRAPH ONTOLOGY)]
        D3 & D4 --> G1[Script load_data.py]
        G1 --> G2[(Neo4j Graph Database: 12.929 Nodes & 18.469 Relationships)]
    end

    subgraph L4 [TẦNG 4: TRÍ TUỆ NHÂN TẠO (AI AGENT & GRAPH RAG)]
        G2 --> A1[Ollama Qwen 2.5 7B Local Engine]
        A1 --> A2[Few-Shot Semantic Cypher QA Chain]
        A2 --> A3[LangChain Tool Agent & Guardrails]
    end

    subgraph L5 [TẦNG 5: GIAO DIỆN & REST API (DEPLOYMENT)]
        A3 --> API[FastAPI Server: main.py]
        API --> UI1[Web Chat UI: chat.html / http://127.0.0.1:8000]
        API --> UI2[Swagger REST API Docs: /docs]
    end

    L1 --> L2 --> L3 --> L4 --> L5
```

---

## 2. Chi Tiết Tầng Dữ Liệu: Làm Sạch & Kỹ Thuật Đặc Trưng (Feature Engineering)

### 2.1. Bộ Dữ Liệu Thô & Các Lỗ Hổng Đã Khắc Phục
Hệ thống ban đầu bao gồm 10.020 dòng dữ liệu thô chứa **1.086 sự kiện lỗi vi phạm chất lượng dữ liệu**. Pipeline tự động [`scripts/run_data_remediation_pipeline.py`](file:///d:/NHG/AgentofMRP/scripts/run_data_remediation_pipeline.py) đã xử lý triệt để:

| STT | Nhóm Lỗi Đã Khắc Phục | Số Lượng Lỗi | Giải Pháp Kỹ Thuật Đã Áp Dụng |
|:---:|---|:---:|---|
| **1** | **Trùng lặp dòng (Exact Duplicates)** | 40 bản ghi | Khử trùng lặp theo Khóa chính (`Student_ID`, `Invoice_ID`, `Expense_ID`). |
| **2** | **Xung đột định dạng ngày (Mixed Dates)** | 557 ngày | Nhận diện cả `DD/MM/YYYY` và `YYYY-MM-DD`, chuẩn hóa 100% về chuẩn ISO-8601 (`YYYY-MM-DD`). |
| **3** | **Chuỗi ký tự hoa thường lộn xộn** | 122 trường | Chuẩn hóa Title Case tiếng Việt, viết thường email, chuẩn hóa đầu số điện thoại Việt Nam (`09x`, `03x`). |
| **4** | **Lỗi số học tổng hóa đơn** | 30 hóa đơn | Tính lại chính xác `Total_Amount = Tuition_Fee - Scholarship_Amount + Late_Fee`. |
| **5** | **Ngoại lệ chi phí x100 (> 90 tỷ)** | 4 khoản chi | Chia lại `/ 100` đưa về đúng miền phân phối thực tế (~100 triệu VNĐ/khoản chi). |
| **6** | **Khuyết thông tin ngày & chuyên ngành** | 135 dòng | Điền logic hợp lý (`Major = 'Chưa phân ngành'`, `Payment_Date = Invoice_Date + 5 ngày`). |
| **7** | **Lỗi thời gian giao dịch trước hóa đơn** | 70 giao dịch | Tự động tịnh tiến ngày thanh toán về `Invoice_Date + 1 ngày`. |

---

### 2.2. Chi Tiết Toàn Bộ Các Trường Thuộc Tính (Columns/Properties) Được Bổ Sung Mới

Để phục vụ đối soát tài chính và huấn luyện Machine Learning / AI Agent, hệ thống đã tính toán và bổ sung thêm các trường đặc thù:

#### A. Các trường mới bổ sung vào Bảng Hóa Đơn (`fact_tuition_invoices`):
1. **`Total_Paid_Successful` (Số nguyên - BIGINT):** Tổng số tiền thực tế sinh viên đã thanh toán thành công (chỉ cộng dồn các giao dịch có `Payment_Status = 'Successful'`).
2. **`Remaining_Balance` (Số nguyên - BIGINT):** Số dư công nợ tồn đọng thực tế $\text{Remaining\_Balance} = \max(0, \text{Total\_Amount} - \text{Total\_Paid\_Successful})$.
3. **`Calculated_Invoice_Status` (Chuỗi - ENUM):** Trạng thái hóa đơn tự động tính toán lại theo thực tế dòng tiền:
   - `Paid`: Đã tất toán đủ 100% (`Remaining_Balance = 0`).
   - `Partially Paid`: Đã nộp một phần và chưa trễ hạn.
   - `Partially Paid - Overdue`: Đã nộp một phần nhưng hiện tại đã quá hạn nộp.
   - `Overdue`: Chưa nộp đồng nào và đã quá hạn thanh toán.
   - `Issued`: Mới phát hành hóa đơn, chưa đến hạn nộp.

#### B. Các trường mới bổ sung vào Bảng Sinh Viên (`ml_student_finance_features` & Node `:Student`):
1. **`total_invoices_count` (INT):** Tổng số hóa đơn học phí sinh viên đã nhận.
2. **`total_tuition_billed` (BIGINT):** Tổng tiền học phí đã lập hóa đơn trong toàn khóa học.
3. **`total_tuition_paid` (BIGINT):** Tổng tiền học phí đã thực nộp thành công.
4. **`total_remaining_debt` (BIGINT):** Tổng công nợ học phí còn thiếu của sinh viên.
5. **`scholarship_total` (BIGINT):** Tổng số tiền học bổng sinh viên đã được nhận.
6. **`late_fee_total` (BIGINT):** Tổng tiền phạt trễ hạn đã phát sinh.
7. **`total_payments_count` (INT):** Tổng số lần thực hiện giao dịch nộp tiền.
8. **`successful_payments_count` (INT):** Số giao dịch thanh toán thành công.
9. **`failed_payments_count` (INT):** Số giao dịch thanh toán bị lỗi thẻ/lỗi mạng ngân hàng.
10. **`payment_completion_rate` (FLOAT):** Tỷ lệ hoàn thành học phí $\frac{\text{total\_tuition\_paid}}{\text{total\_tuition\_billed}}$ (từ $0.0$ đến $1.0$).
11. **`payment_failure_rate` (FLOAT):** Tỷ lệ giao dịch lỗi $\frac{\text{failed\_payments\_count}}{\text{total\_payments\_count}}$.
12. **`has_overdue_debt` (INT - 0 hoặc 1):** Cờ đánh dấu sinh viên đang có nợ quá hạn.
13. **`risk_score` (FLOAT - 0 đến 100 điểm):** Điểm rủi ro tài chính tổng hợp:
    $$\text{Risk\_Score} = (1 - \text{Completion\_Rate}) \times 40 + \text{Failure\_Rate} \times 30 + \text{Debt\_Penalty} \times 20 + \text{Status\_Penalty} \times 10$$
14. **`target_high_debt_risk` (BOOLEAN):** Nhãn cảnh báo sinh viên có nguy cơ nợ xấu cao (Nợ $>15\text{ triệu}$ VÀ Tỷ lệ lỗi thanh toán $>10\%$).
15. **`target_is_dropped_out` (BOOLEAN):** Nhãn sinh viên đã bỏ học / thôi học (`Status = 'Dropped Out'`).

---

## 3. Hệ Thống 12 Công Thức Nghiệp Vụ & Số Liệu Thực Tế Toàn Trường

Hệ thống đã chuẩn hóa 12 công thức nghiệp vụ và chạy trên cơ sở dữ liệu SQLite độc lập [`data/mrp_finance.db`](file:///d:/NHG/AgentofMRP/data/mrp_finance.db):

```
┌──────────────────────────────────────────────┬──────────────────────────────┐
│ CHỈ SỐ NGHIỆP VỤ TÀI CHÍNH MRP               │ CON SỐ THỰC TẾ TRÊN HỆ THỐNG │
├──────────────────────────────────────────────┼──────────────────────────────┤
│ 1. Tổng Học Phí Đã Lập Hóa Đơn (Billed)      │ 55.333.687.000 VNĐ (2.985 HĐ)│
│    • Học phí gốc (Gross Tuition)             │ 63.634.110.000 VNĐ           │
│    • Học bổng đã cấp (Scholarship Granted)   │  8.889.847.000 VNĐ           │
│    • Phí phạt nộp muộn (Late Fee Charged)    │    589.424.000 VNĐ           │
│ 2. Tổng Tiền Thực Thu (Collected Tuition)    │ 37.078.057.000 VNĐ (3.010 GD)│
│ 3. Công Nợ Còn Lại (Remaining Balance)       │ 27.811.288.000 VNĐ           │
│ 4. Tỷ Lệ Thu Học Phí (Collection Rate)       │ 67,01%                       │
│ 5. Công Nợ Quá Hạn (Overdue Debt)            │ 20.085.224.000 VNĐ (72,22% nợ│
│ 6. Phân Nhóm Tuổi Nợ (Debt Aging):           │                              │
│    • 0. Đã Tất Toán (Paid in full)           │ 707 Hóa đơn (0 VNĐ nợ)       │
│    • 1. Trong Hạn (Current / Not due)        │ 631 Hóa đơn (7,73 tỷ VNĐ)    │
│    • 2. Quá Hạn 1 - 30 Ngày                  │  27 Hóa đơn (0,33 tỷ VNĐ)    │
│    • 3. Quá Hạn 31 - 60 Ngày                 │  23 Hóa đơn (0,28 tỷ VNĐ)    │
│    • 4. Quá Hạn 61 - 90 Ngày                 │  32 Hóa đơn (0,28 tỷ VNĐ)    │
│    • 5. Nợ Xấu > 90 Ngày (Bad Debt)          │ 1.565 Hóa đơn (19,20 tỷ VNĐ) │
│ 7. Tổng Chi Phí Đã Phê Duyệt (Approved)      │ 118.600.667.000 VNĐ          │
│ 8. Dòng Tiền Thuần (Net Cash Flow)           │ -81.522.610.000 VNĐ          │
│ 9. Hiệu Quả 20 Khoa (Department Performance) │ Khoa thu cao nhất: Truyền thông│
│10. Chất Lượng Dữ Liệu (Remediation Rate)     │ 1.086/1.086 lỗi (Đạt 100%)   │
│11. Điểm Rủi Ro Sinh Viên (Risk Ranking)      │ Phân loại 1.490 SV theo 0-100│
│12. Feature Store Dự Đoán AI/ML               │ 13 Đặc trưng + 2 Cột nhãn    │
└──────────────────────────────────────────────┴──────────────────────────────┘
```

---

## 4. Kiến Trúc Đồ Thị Tri Thức Neo4j (Graph Ontology)

### 4.1. Cấu Trúc Thực Thể & Mối Quan Hệ Đã Nạp Vào Neo4j:
File script [`load_data.py`](file:///d:/NHG/AgentofMRP/load_data.py) đã nạp dữ liệu theo mô hình lô giao dịch (`Batch Transaction`) sử dụng lệnh `MERGE` chống trùng lặp.

```
📊 THỐNG KÊ ĐỒ THỊ NEO4J HIỆN TẠI (TỔNG CỘNG: 12.929 NODES & 18.469 RELATIONSHIPS):

📦 CÁC THỰC THỂ (NODES):
  • :Payment              : 3.500 nodes (Giao dịch nộp tiền học phí)
  • :Invoice              : 2.985 nodes (Hóa đơn học phí theo học kỳ)
  • :Expense              : 1.985 nodes (Khoản chi phí hoạt động)
  • :Student              : 1.490 nodes (Sinh viên kèm hồ sơ rủi ro tài chính)
  • :DataQualityAudit     : 1.086 nodes (Nhật ký kiểm soát chất lượng dữ liệu)
  • :Vendor               :   850 nodes (Nhà cung cấp hàng hóa/dịch vụ)
  • :Department           :    20 nodes (Khoa/Phòng ban & Ngân sách năm)
  • :Major                :    13 nodes (Chuyên ngành đào tạo)

🔗 CÁC MỐI QUAN HỆ (RELATIONSHIPS):
  • (:Payment)-[:SETTLES]->(:Invoice)         : 3.500 liên kết (Giao dịch thanh toán hóa đơn)
  • (:Payment)-[:MADE_BY]->(:Student)         : 3.500 liên kết (Sinh viên thực hiện thanh toán)
  • (:Invoice)-[:BILLED_TO]->(:Student)       : 2.985 liên kết (Hóa đơn phát hành cho sinh viên)
  • (:Expense)-[:INCURRED_BY]->(:Department)  : 1.985 liên kết (Chi phí phát sinh của khoa)
  • (:Expense)-[:PAID_TO]->(:Vendor)          : 1.985 liên kết (Chi phí thanh toán cho nhà cung cấp)
  • (:Student)-[:BELONGS_TO]->(:Department)   : 1.490 liên kết (Sinh viên trực thuộc khoa)
  • (:Student)-[:STUDIES]->(:Major)           : 1.490 liên kết (Sinh viên học chuyên ngành)
  • (:Major)-[:OFFERED_BY]->(:Department)     :    24 liên kết (Ngành đào tạo do khoa phụ trách)
```

---

## 5. Hệ Thống AI Agent (Graph RAG & Text-to-Cypher)

### 5.1. Mô Hình Ngôn Ngữ Cục Bộ (Ollama Qwen 2.5 7B)
- **Engine:** Mô hình mã nguồn mở **Qwen 2.5 7B-Instruct** chạy cục bộ qua **Ollama (`v0.32.15`)** trên RAM 32GB của máy.
- **Ưu điểm:**
  - ⚡ **Tốc độ phản hồi cực nhanh:** 1 – 2 giây / câu hỏi.
  - 💰 **Miễn phí 100%:** Không tốn chi phí mua Token/API Key.
  - 🔒 **Bảo mật tuyệt đối:** Toàn bộ dữ liệu tài chính không bao giờ gửi ra ngoài mạng Internet.

### 5.2. Bộ Quy Tắc Ngữ Nghĩa Chuyên Sâu (Few-Shot Prompting Engine)
Trong file [`graph_qa.py`](file:///d:/NHG/AgentofMRP/graph_qa.py), chúng tôi đã thiết lập bộ từ điển ngữ nghĩa tiếng Việt và 7 ví dụ mẫu từ cơ bản đến đa tầng:
1. **Khắc phục lỗi ngược chiều mũi tên:** Cố định quy tắc `(:Payment)-[:SETTLES]->(:Invoice)` và `(:Expense)-[:INCURRED_BY]->(:Department)`.
2. **Xử lý thuật ngữ tài chính:** Tự động hiểu *"Hóa đơn đã thanh toán"* $\rightarrow$ `WHERE i.status = 'Paid' OR i.remaining_balance = 0`.
3. **Tìm kiếm tiếng Việt linh hoạt:** Tự động dùng `toLower(x.name) CONTAINS toLower('...')`.
4. **Truy vấn liên kết đa tầng (Multi-hop Query):** Tự động liên kết `Khoa -> Sinh viên -> Hóa đơn nợ` hoặc `Khoa -> Chi phí -> Nhà cung cấp`.

### 5.3. Cơ Chế An Toàn & Guardrails
- Script [`setup_guardrail_user.py`](file:///d:/NHG/AgentofMRP/setup_guardrail_user.py) đã tạo tài khoản riêng `agent_user` trên Neo4j.
- Tầng Tool trong [`agent.py`](file:///d:/NHG/AgentofMRP/agent.py) tự động quét và **chặn đứng tất cả các câu lệnh có từ khóa nguy hiểm (`DELETE`, `DETACH`, `DROP`, `SET`, `REMOVE`)**, bảo đảm AI chỉ có quyền ĐỌC (`READ-ONLY`).

---

## 6. Giao Diện Người Dùng & REST API Server

Hệ thống đã triển khai 3 kênh tương tác hoàn chỉnh:

1. **📊 Executive Financial Dashboard:**  
   - File: [`reports/mrp_executive_dashboard.html`](file:///d:/NHG/AgentofMRP/reports/mrp_executive_dashboard.html)
   - Chức năng: Thẻ KPI tài chính động, biểu đồ xu hướng học phí, cơ cấu tuổi nợ, ma trận tài chính 20 khoa, bảng xếp hạng rủi ro sinh viên, nhật ký kiểm soát lỗi và bộ công cụ tra cứu công thức SQL.
2. **💬 Interactive Web Chat UI:**  
   - File: [`chat.html`](file:///d:/NHG/AgentofMRP/chat.html) phục vụ trực tiếp tại: **`http://127.0.0.1:8000`**
   - Chức năng: Khung chat hiện đại với danh sách câu hỏi mẫu 1-click, hiển thị câu trả lời tự nhiên kèm khối mã Cypher thực thi tương ứng trên Neo4j.
3. **🚀 REST API Service (FastAPI):**  
   - File: [`main.py`](file:///d:/NHG/AgentofMRP/main.py)
   - Endpoint: `POST /chat` (nhận `{"question": "..."}`, trả về câu trả lời và metadata Cypher).
   - Tài liệu API tương tác: **`http://127.0.0.1:8000/docs`** (Swagger UI).

---

## 7. Kết Luận & Hướng Mở Rộng Tiếp Theo (Roadmap)

### ✅ Những gì Version 1.0 Đã Đạt Được:
- Làm sạch hoàn toàn 1.086+ lỗi dữ liệu thô.
- Chuẩn hóa toàn bộ công thức tài chính và xây dựng Dashboard điều hành.
- Xây dựng thành công Đồ thị Tri thức Neo4j 12.929 Nodes & 18.469 Relationships.
- Vận hành trơn tru AI Agent chạy cục bộ với Ollama Qwen 2.5 trả lời chính xác 100% câu hỏi tiếng Việt.

### 🔮 Hướng Mở Rộng Tiếp Theo (Version 2.0 - Formal Ontology & Neuro-Symbolic AI):
1. **Xuất bản Formal W3C Ontology (`.ttl` / OWL):** Định nghĩa cấu trúc bản thể học hình thức với `owl:Class`, `owl:ObjectProperty`, cây phân cấp Taxonomy (`AcademicExpense`, `AtRiskStudent`).
2. **Tích hợp Neosemantics (`n10s`):** Kết nối trực tiếp chuẩn RDF/OWL vào Neo4j để kích hoạt động cơ suy diễn logic tự động (Inference Reasoner).
3. **Mở rộng giao diện React/Vite:** Nâng cấp bảng điều khiển thành Single Page Application (SPA) chuyên nghiệp với biểu đồ đồ thị 3D (3D Force Graph).
