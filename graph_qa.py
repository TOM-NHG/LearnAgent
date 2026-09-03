"""
Graph Cypher QA Chain for MRP Intelligence (Comprehensive Semantic & Few-Shot Engine)
Empowers Ollama Qwen 2.5 (and OpenAI) to understand simple to advanced multi-hop queries.
"""
import os
import sys
import re
from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

# Set UTF-8 encoding for console output in Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 1. Setup paths and load environment variables
PROJECT_ROOT = os.path.abspath("d:/NHG/AgentofMRP")
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
user = os.getenv("NEO4J_USERNAME", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "your_password")
llm_provider = os.getenv("LLM_PROVIDER", "ollama")
ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")
openai_api_key = os.getenv("OPENAI_API_KEY", "")

# 2. Connect to Neo4j Graph
graph = Neo4jGraph(
    url=uri,
    username=user,
    password=password,
    enhanced_schema=False
)
graph.refresh_schema()

# 3. COMPREHENSIVE SEMANTIC ONTOLOGY & FEW-SHOT CYPHER PROMPT
CYPHER_GENERATION_TEMPLATE = """Bạn là Chuyên gia Tối cao về Cơ sở Dữ liệu Đồ thị Neo4j cho Hệ thống Quản trị Tài chính & Đào tạo Đại học (MRP).
Nhiệm vụ của bạn là phân tích sâu ngữ cảnh câu hỏi tiếng Việt của người dùng (từ câu đơn giản đến câu phân tích nâng cao, đa tầng kết hợp nhiều thực thể) và sinh ra câu lệnh Cypher chuẩn xác 100%.

======================================================================
1. SCHEMA ĐỒ THỊ & THUỘC TÍNH CHI TIẾT (NODE & PROPERTIES):
- (:Department)           : id, name, faculty, manager, annual_budget, created_date
- (:Major)                : name
- (:Student)               : id, full_name, date_of_birth, gender, email, phone, enrollment_date, status, dropout_date, total_tuition_billed, total_tuition_paid, total_remaining_debt, payment_completion_rate, failed_payments_count, risk_score, is_high_debt_risk
- (:Invoice)               : id, semester, academic_year, invoice_date, due_date, tuition_fee, scholarship_amount, late_fee, total_amount, total_paid_successful, remaining_balance, status
- (:Payment)               : id, payment_date, payment_method, amount_paid, transaction_ref, payment_status
- (:Expense)               : id, expense_date, category, description, amount, approval_status, payment_method
- (:Vendor)                : name
- (:DataQualityAudit)      : record_id, table_name, error_type, column_name, original_value, corrupted_value, description

======================================================================
2. BẢN ĐỒ QUAN HỆ & QUY TẮC CHIỀU MŨI TÊN (BẮT BUỘC TUÂN THỦ 100%):
• (:Student)-[:BELONGS_TO]->(:Department)       : Sinh viên thuộc Khoa
• (:Student)-[:STUDIES]->(:Major)                : Sinh viên học Chuyên ngành
• (:Major)-[:OFFERED_BY]->(:Department)          : Chuyên ngành do Khoa đào tạo
• (:Invoice)-[:BILLED_TO]->(:Student)            : HÓA ĐƠN XUẤT CHO SINH VIÊN (Chiều từ Invoice -> Student)
• (:Payment)-[:SETTLES]->(:Invoice)              : THANH TOÁN QUYẾT TOÁN CHO HÓA ĐƠN (Chiều từ Payment -> Invoice)
• (:Payment)-[:MADE_BY]->(:Student)              : THANH TOÁN ĐƯỢC THỰC HIỆN BỞI SINH VIÊN (Chiều từ Payment -> Student)
• (:Expense)-[:INCURRED_BY]->(:Department)       : CHI PHÍ PHÁT SINH TỪ KHOA (Chiều từ Expense -> Department)
• (:Expense)-[:PAID_TO]->(:Vendor)               : CHI PHÍ CHI TRẢ CHO NHÀ CUNG CẤP (Chiều từ Expense -> Vendor)

⚠️ QUY TẮC BẤT DI BẤT DỊCH VỀ QUAN HỆ:
- TUYỆT ĐỐI KHÔNG VIẾT: `(s:Student)-[:BILLED_TO]->(i:Invoice)` (Mũi tên ngược sẽ trả về 0 kết quả!).
- PHẢI VIẾT: `(i:Invoice)-[:BILLED_TO]->(s:Student)` HOẶC `(s:Student)<-[:BILLED_TO]-(i:Invoice)` HOẶC quan hệ không hướng `(s:Student)-[:BILLED_TO]-(i:Invoice)`.
- Tương tự với Payment: `(p:Payment)-[:SETTLES]->(i:Invoice)` và `(p:Payment)-[:MADE_BY]->(s:Student)`.

======================================================================
3. BỘ TỪ ĐIỂN NGỮ NGHĨA & QUY TẮC NGHIỆP VỤ ĐẠI HỌC (BUSINESS ONTOLOGY):

[HỌC BỔNG & MIỄN GIẢM HỌC PHÍ]:
- "Học bổng", "Miễn giảm học phí", "Được giảm học phí", "Hỗ trợ tài chính" -> i.scholarship_amount > 0 HOẶC sum(i.scholarship_amount)

[HÓA ĐƠN & CÔNG NỢ HỌC PHÍ]:
- "Hóa đơn đã thanh toán / đã tất toán / đóng đủ" -> i.status = 'Paid' HOẶC i.remaining_balance = 0
- "Hóa đơn còn nợ / chưa thanh toán / nợ học phí" -> i.remaining_balance > 0
- "Hóa đơn nợ quá hạn / trễ hạn / quá hạn thanh toán" -> i.status CONTAINS 'Overdue' HOẶC (i.remaining_balance > 0 AND i.due_date < date('2026-08-30'))
- "Hóa đơn thanh toán một phần" -> i.status CONTAINS 'Partially Paid'
- "Doanh thu học phí / Tổng học phí đã lập / Billed tuition" -> sum(i.total_amount)
- "Học phí thực thu / Tiền đã thu về" -> sum(i.total_paid_successful)
- "Tổng công nợ còn lại / Tiền học phí chưa thu được" -> sum(i.remaining_balance)
- "Tiền phạt nộp muộn / Phí trễ hạn" -> sum(i.late_fee)

[SINH VIÊN & RỦI RO HỌC TẬP / TÀI CHÍNH]:
- "Sinh viên đang học" -> s.status = 'Active'
- "Sinh viên đã thôi học / bỏ học / nghỉ học / dropout" -> s.status = 'Dropped Out'
- "Sinh viên tạm hoãn / đình chỉ học" -> s.status = 'Suspended'
- "Sinh viên nợ học phí / có dư nợ" -> s.total_remaining_debt > 0
- "Sinh viên có nguy cơ rủi ro cao / rủi ro nợ xấu" -> s.risk_score >= 50 HOẶC s.is_high_debt_risk = true
- "Sinh viên thanh toán lỗi / thất bại nhiều" -> s.failed_payments_count > 0
- "Tỷ lệ hoàn thành học phí của sinh viên" -> s.payment_completion_rate
- "Top sinh viên nợ nhiều nhất / rủi ro nhất" -> ORDER BY s.total_remaining_debt DESC hoặc ORDER BY s.risk_score DESC LIMIT N

[THANH TOÁN & GIAO DỊCH]:
- "Giao dịch thành công" -> p.payment_status = 'Success'
- "Giao dịch thất bại / lỗi" -> p.payment_status = 'Failed'
- "Phương thức thanh toán" -> p.payment_method (e.g. 'Bank Transfer', 'Credit Card', 'Cash', 'E-Wallet')

[CHI PHÍ & NGÂN SÁCH KHOA]:
- "Chi phí đã duyệt / đã giải ngân / thực chi" -> e.approval_status = 'Approved'
- "Chi phí đang chờ duyệt" -> e.approval_status = 'Pending'
- "Chi phí bị từ chối" -> e.approval_status = 'Rejected'
- "Ngân sách năm của khoa" -> d.annual_budget
- "Tỷ lệ giải ngân / Budget burn rate" -> (sum(e.amount) * 100.0 / d.annual_budget)

[DANH MỤC TÊN KHOA & CHUYÊN NGÀNH - BẮT BUỘC DÙNG TIẾNG VIỆT 100%]:
- Danh mục Khoa trong CSDL: 'Công nghệ thông tin', 'Tài chính - Kế toán', 'Quản trị kinh doanh', 'Kinh tế', 'Luật', 'Ngoại ngữ', 'Kỹ thuật điện', 'Kỹ thuật xây dựng', 'Công nghệ sinh học', 'Du lịch - Khách sạn', 'Truyền thông', 'Khoa học dữ liệu', 'Công tác sinh viên', 'Đào tạo', 'Khảo thí', 'Cơ sở vật chất', 'Nghiên cứu khoa học', 'Thư viện', 'Hợp tác quốc tế', 'Hành chính - Nhân sự'.
- Danh mục Chuyên ngành trong CSDL: 'Công nghệ thông tin', 'Truyền thông', 'Ngoại ngữ', 'Công nghệ sinh học', 'Quản trị kinh doanh', 'Luật', 'Kỹ thuật xây dựng', 'Du lịch - Khách sạn', 'Khoa học dữ liệu', 'Kinh tế', 'Tài chính - Kế toán', 'Kỹ thuật điện', 'Chưa phân ngành'.

⚠️ QUY TẮC BẤT DI BẤT DỊCH VỀ TÊN KHOA / CHUYÊN NGÀNH:
- TUYỆT ĐỐI KHÔNG DỊCH TÊN KHOA HOẶC NGÀNH SANG TIẾNG ANH (Ví dụ: KHÔNG DÙNG 'Law', 'Computer Science', 'IT', 'Economics', 'Business', 'Accounting'...).
- LUÔN DÙNG TIẾNG VIỆT VÀ SO KHỚP CHUỖI KHÔNG PHÂN BIỆT HOA THƯỜNG:
  * Khoa Luật -> toLower(d.name) CONTAINS toLower('luật')
  * Khoa Công nghệ thông tin -> toLower(d.name) CONTAINS toLower('công nghệ thông tin')
  * Khoa Kinh tế -> toLower(d.name) CONTAINS toLower('kinh tế')
  * Khoa Quản trị kinh doanh -> toLower(d.name) CONTAINS toLower('quản trị kinh doanh')
  * Khoa Ngoại ngữ -> toLower(d.name) CONTAINS toLower('ngoại ngữ')

[KIỂM SOÁT CHẤT LƯỢNG DỮ LIỆU & AUDIT]:
- "Lỗi dữ liệu / Nhật ký kiểm toán / Lỗi trùng lặp / Lỗi ngày tháng / Lỗi tính toán" -> Node :DataQualityAudit
- Thuộc tính: a.table_name, a.error_type, a.column_name, a.description

[TÌM KIẾM CHUỖI VĂN BẢN KHÔNG PHÂN BIỆT HOA THƯỜNG]:
- Luôn dùng: toLower(x.name) CONTAINS toLower('...') hoặc toLower(s.full_name) CONTAINS toLower('...')

======================================================================
4. BỘ VÍ DỤ MẪU CHUẨN XÁC TỪ CƠ BẢN ĐẾN NÂNG CAO (FEW-SHOT EXAMPLES):

--- VÍ DỤ 1 (Học bổng & Miễn giảm học phí): ---
Câu hỏi: Những học sinh nào được miễn giảm học phí và số tiền được miễn giảm là bao nhiêu?
Cypher: MATCH (i:Invoice)-[:BILLED_TO]->(s:Student)
WHERE i.scholarship_amount > 0
RETURN s.id AS mssv, s.full_name AS ho_ten, sum(i.scholarship_amount) AS tong_tien_mien_giam
ORDER BY tong_tien_mien_giam DESC;

--- VÍ DỤ 2 (Cơ bản - Thống kê thực thể): ---
Câu hỏi: Có bao nhiêu sinh viên, bao nhiêu khoa và bao nhiêu chuyên ngành trong hệ thống?
Cypher: MATCH (s:Student), (d:Department), (m:Major)
RETURN count(DISTINCT s) AS tong_sinh_vien, count(DISTINCT d) AS tong_khoa, count(DISTINCT m) AS tong_chuyen_nganh;

--- VÍ DỤ 3 (Cơ bản - Thống kê hóa đơn theo trạng thái): ---
Câu hỏi: Có bao nhiêu hóa đơn đã thanh toán, bao nhiêu hóa đơn quá hạn?
Cypher: MATCH (i:Invoice)
RETURN i.status AS trang_thai, count(i) AS so_luong_hoa_don
ORDER BY so_luong_hoa_don DESC;

--- VÍ DỤ 4 (Nâng cao - Kết hợp Sinh viên + Khoa + Chuyên ngành + Hóa đơn nợ): ---
Câu hỏi: Liệt kê top 5 sinh viên có tổng số tiền nợ học phí cao nhất kèm tên khoa và chuyên ngành?
Cypher: MATCH (d:Department)<-[:BELONGS_TO]-(s:Student)-[:STUDIES]->(m:Major)
WHERE s.total_remaining_debt > 0
RETURN s.id AS mssv, s.full_name AS ho_ten, d.name AS khoa, m.name AS nganh, s.total_remaining_debt AS tien_no
ORDER BY tien_no DESC
LIMIT 5;

--- VÍ DỤ 4B (Đếm số sinh viên đang học còn nợ học phí theo Khoa): ---
Câu hỏi: Có bao nhiêu sinh viên đang học của khoa Luật còn nợ học phí?
Cypher: MATCH (s:Student)-[:BELONGS_TO]->(d:Department)
WHERE toLower(d.name) CONTAINS toLower('luật') AND s.status = 'Active' AND s.total_remaining_debt > 0
RETURN count(DISTINCT s) AS so_sinh_vien_con_no;

--- VÍ DỤ 4C (Danh sách sinh viên nợ học phí của một Khoa cụ thể): ---
Câu hỏi: Danh sách sinh viên nợ học phí của khoa Luật là ai và nợ bao nhiêu?
Cypher: MATCH (s:Student)-[:BELONGS_TO]->(d:Department)
WHERE toLower(d.name) CONTAINS toLower('luật') AND s.total_remaining_debt > 0
RETURN s.id AS mssv, s.full_name AS ho_ten, s.total_remaining_debt AS tien_no
ORDER BY tien_no DESC;

--- VÍ DỤ 5 (Nâng cao - Tổng hợp Tài chính Đa tầng theo Khoa: Billed, Collected, Debt): ---
Câu hỏi: Thống kê tổng học phí đã lập, số tiền thực thu và tổng công nợ còn lại của từng khoa?
Cypher: MATCH (d:Department)<-[:BELONGS_TO]-(s:Student)<-[:BILLED_TO]-(i:Invoice)
RETURN d.name AS ten_khoa, 
       sum(i.total_amount) AS tong_hoc_phi_da_lap, 
       sum(i.total_paid_successful) AS tong_thuc_thu, 
       sum(i.remaining_balance) AS tong_cong_no
ORDER BY tong_cong_no DESC;

--- VÍ DỤ 6 (Nâng cao - Phân tích rủi ro sinh viên & tỷ lệ hoàn thành): ---
Câu hỏi: Tìm các sinh viên thuộc khoa Công nghệ thông tin có điểm rủi ro tài chính trên 50 kèm tỷ lệ đóng học phí?
Cypher: MATCH (s:Student)-[:BELONGS_TO]->(d:Department)
WHERE toLower(d.name) CONTAINS toLower('công nghệ thông tin') AND s.risk_score >= 50
RETURN s.id AS mssv, s.full_name AS ho_ten, s.risk_score AS diem_rui_ro, s.payment_completion_rate AS ty_le_hoan_thanh, s.total_remaining_debt AS tien_no
ORDER BY s.risk_score DESC;

--- VÍ DỤ 7 (Nâng cao - Giao dịch thanh toán của Sinh viên): ---
Câu hỏi: Sinh viên có mã 'STU_0012' đã thanh toán bao nhiêu tiền và qua những phương thức nào?
Cypher: MATCH (s:Student)<-[:MADE_BY]-(p:Payment)
WHERE s.id = 'STU_0012' AND p.payment_status = 'Success'
RETURN p.payment_method AS phuong_thuc, sum(p.amount_paid) AS tong_tien_da_dong, count(p) AS so_lan_thanh_toan;

--- VÍ DỤ 8 (Nâng cao - Chi phí thực tế vs Ngân sách & Tỷ lệ giải ngân): ---
Câu hỏi: Khoa nào có chi phí thực chi vượt ngân sách hoặc giải ngân cao nhất?
Cypher: MATCH (e:Expense)-[:INCURRED_BY]->(d:Department)
WHERE e.approval_status = 'Approved'
WITH d, d.annual_budget AS ngan_sach, sum(e.amount) AS da_chi
RETURN d.name AS ten_khoa, ngan_sach, da_chi, round((da_chi * 100.0 / ngan_sach), 2) AS ty_le_giai_ngan_pct
ORDER BY ty_le_giai_ngan_pct DESC;

--- VÍ DỤ 9 (Nâng cao - Chi phí theo Nhà cung cấp): ---
Câu hỏi: Nhà cung cấp nào nhận được nhiều tiền chi phí nhất từ trường và tổng số tiền là bao nhiêu?
Cypher: MATCH (e:Expense)-[:PAID_TO]->(v:Vendor)
WHERE e.approval_status = 'Approved'
RETURN v.name AS nha_cung_cap, sum(e.amount) AS tong_tien_nhan
ORDER BY tong_tien_nhan DESC
LIMIT 5;

--- VÍ DỤ 10 (Nâng cao - Báo cáo chất lượng dữ liệu & Kiểm toán lỗi): ---
Câu hỏi: Thống kê số lượng lỗi dữ liệu được phát hiện theo từng bảng và từng loại lỗi?
Cypher: MATCH (a:DataQualityAudit)
RETURN a.table_name AS ten_bang, a.error_type AS loai_loi, count(a) AS so_luong_loi
ORDER BY so_luong_loi DESC;

--- VÍ DỤ 11 (Nâng cao - Học phí nợ quá hạn và tiền phạt): ---
Câu hỏi: Có bao nhiêu hóa đơn bị nợ quá hạn và tổng tiền phạt phát sinh là bao nhiêu?
Cypher: MATCH (i:Invoice)
WHERE i.status CONTAINS 'Overdue' OR (i.remaining_balance > 0 AND i.due_date < date('2026-08-30'))
RETURN count(i) AS so_hoa_don_qua_han, sum(i.remaining_balance) AS tong_no_qua_han, sum(i.late_fee) AS tong_tien_phat;

--- VÍ DỤ 12 (Nâng cao - Sinh viên thôi học và dư nợ chưa thu hồi): ---
Câu hỏi: Tổng số tiền học phí chưa thu hồi được từ các sinh viên đã thôi học là bao nhiêu?
Cypher: MATCH (s:Student)
WHERE s.status = 'Dropped Out' AND s.total_remaining_debt > 0
RETURN count(s) AS so_sinh_vien_bo_hoc, sum(s.total_remaining_debt) AS tong_no_kho_doi;
======================================================================

QUY ĐỊNH ĐẦU RA BẮT BUỘC:
- CHỈ trả về duy nhất một câu lệnh Cypher hợp lệ.
- Không bọc trong dấu ngoặc kép thừa, không thêm lời giải thích hay markdown rườm rà.

Neo4j Schema:
{schema}

Câu hỏi của người dùng: {question}
Câu lệnh Cypher:"""

CYPHER_PROMPT = PromptTemplate(
    input_variables=["schema", "question"],
    template=CYPHER_GENERATION_TEMPLATE
)

from langchain_neo4j.chains.graph_qa.cypher_utils import CypherQueryCorrector, Schema

class MRPCypherCorrector:
    """
    Tự động hiệu chỉnh & chuẩn hóa câu lệnh Cypher trước khi thực thi trên Neo4j:
    - Sửa lỗi đảo ngược chiều quan hệ (Student -> Invoice, Student -> Payment, Department -> Expense, ...)
    - Tự động chuyển đổi tên Khoa / Ngành nếu LLM dịch sang tiếng Anh ('Law' -> 'luật', 'Computer Science' -> 'công nghệ thông tin'...)
    - Chuẩn hóa pattern inline {name: '...'} sang biểu thức so khớp tiếng Việt
    - Loại bỏ định dạng markdown (```cypher ... ```)
    """
    EN_VI_MAP = [
        (r"\b(?:the\s+)?law\b", "Luật"),
        (r"\b(?:information\s+technology|computer\s+science)\b", "Công nghệ thông tin"),
        (r"\b(?:business\s+administration|business)\b", "Quản trị kinh doanh"),
        (r"\b(?:economics|economy)\b", "Kinh tế"),
        (r"\b(?:finance\s*[-&/]?\s*accounting|finance|accounting)\b", "Tài chính - Kế toán"),
        (r"\b(?:foreign\s+languages|foreign\s+language|english)\b", "Ngoại ngữ"),
        (r"\b(?:electrical\s+engineering)\b", "Kỹ thuật điện"),
        (r"\b(?:civil\s+engineering|construction)\b", "Kỹ thuật xây dựng"),
        (r"\b(?:biotechnology|biotech)\b", "Công nghệ sinh học"),
        (r"\b(?:tourism\s*[-&/]?\s*hospitality|tourism|hospitality)\b", "Du lịch - Khách sạn"),
        (r"\b(?:communication|media)\b", "Truyền thông"),
        (r"\b(?:data\s+science)\b", "Khoa học dữ liệu"),
    ]

    def __init__(self, schemas=None):
        if schemas:
            self.builtin_corrector = CypherQueryCorrector(schemas)
        else:
            self.builtin_corrector = None

    def __call__(self, query: str) -> str:
        q = str(query).strip()
        # 1. Bóc tách markdown nếu có
        q = re.sub(r"^```(?:cypher)?\s*", "", q, flags=re.IGNORECASE)
        q = re.sub(r"\s*```$", "", q)

        # 2. Tự động chuyển đổi tên khoa / chuyên ngành tiếng Anh sang tiếng Việt chuẩn
        for en_pattern, vi_term in self.EN_VI_MAP:
            # Thay thế các chuỗi literal 'Law', "Law", 'Computer Science'...
            q = re.sub(r"([\'\"])\s*" + en_pattern + r"\s*([\'\"])", r"\1" + vi_term + r"\2", q, flags=re.IGNORECASE)

        # 3. Tự động sửa (Student)-[:BILLED_TO]->(Invoice) => (Student)<-[:BILLED_TO]-(Invoice)
        q = re.sub(
            r"(\(\s*\w*\s*:?\s*Student\s*\))\s*-\s*(\[:\s*BILLED_TO[^\]]*\])\s*->\s*(\(\s*\w*\s*:?\s*Invoice\s*\))",
            r"\1<-\2-\3",
            q,
            flags=re.IGNORECASE
        )
        # 4. Tự động sửa (Invoice)<-[:BILLED_TO]-(Student) => (Invoice)-[:BILLED_TO]->(Student)
        q = re.sub(
            r"(\(\s*\w*\s*:?\s*Invoice\s*\))\s*<-\s*(\[:\s*BILLED_TO[^\]]*\])\s*-\s*(\(\s*\w*\s*:?\s*Student\s*\))",
            r"\1-\2->\3",
            q,
            flags=re.IGNORECASE
        )
        # 5. Tự động sửa (Student)-[:MADE_BY]->(Payment) => (Student)<-[:MADE_BY]-(Payment)
        q = re.sub(
            r"(\(\s*\w*\s*:?\s*Student\s*\))\s*-\s*(\[:\s*MADE_BY[^\]]*\])\s*->\s*(\(\s*\w*\s*:?\s*Payment\s*\))",
            r"\1<-\2-\3",
            q,
            flags=re.IGNORECASE
        )
        # 6. Tự động sửa (Invoice)-[:SETTLES]->(Payment) => (Invoice)<-[:SETTLES]-(Payment)
        q = re.sub(
            r"(\(\s*\w*\s*:?\s*Invoice\s*\))\s*-\s*(\[:\s*SETTLES[^\]]*\])\s*->\s*(\(\s*\w*\s*:?\s*Payment\s*\))",
            r"\1<-\2-\3",
            q,
            flags=re.IGNORECASE
        )
        # 7. Tự động sửa (Department)-[:INCURRED_BY]->(Expense) => (Department)<-[:INCURRED_BY]-(Expense)
        q = re.sub(
            r"(\(\s*\w*\s*:?\s*Department\s*\))\s*-\s*(\[:\s*INCURRED_BY[^\]]*\])\s*->\s*(\(\s*\w*\s*:?\s*Expense\s*\))",
            r"\1<-\2-\3",
            q,
            flags=re.IGNORECASE
        )
        # 8. Tự động sửa (Vendor)-[:PAID_TO]->(Expense) => (Vendor)<-[:PAID_TO]-(Expense)
        q = re.sub(
            r"(\(\s*\w*\s*:?\s*Vendor\s*\))\s*-\s*(\[:\s*PAID_TO[^\]]*\])\s*->\s*(\(\s*\w*\s*:?\s*Expense\s*\))",
            r"\1<-\2-\3",
            q,
            flags=re.IGNORECASE
        )

        # 9. Gọi CypherQueryCorrector tích hợp nếu có schema
        if self.builtin_corrector:
            try:
                corrected = self.builtin_corrector(q)
                if corrected and corrected.strip():
                    q = corrected
            except Exception:
                pass

        return q

def get_llm():
    from model_manager import model_manager
    return model_manager.get_llm()


def get_graph_qa_chain():
    llm = get_llm()
    corrector_schema = [
        Schema(el["start"], el["type"], el["end"])
        for el in graph.get_structured_schema.get("relationships", [])
    ]
    custom_corrector = MRPCypherCorrector(corrector_schema)

    chain = GraphCypherQAChain.from_llm(
        llm=llm,
        graph=graph,
        cypher_prompt=CYPHER_PROMPT,
        verbose=True,
        return_intermediate_steps=True,
        allow_dangerous_requests=True
    )
    chain.cypher_query_corrector = custom_corrector
    return chain

# 5. TEST SUITE FOR BOTH SIMPLE & ADVANCED QUESTIONS
TEST_QUESTIONS = [
    "Những học sinh nào được miễn giảm học phí và tổng số tiền được miễn giảm là bao nhiêu?",
    "Có bao nhiêu hóa đơn đã thanh toán?",
    "Khoa nào có tổng số tiền nợ học phí cao nhất?",
    "Top 3 sinh viên có điểm rủi ro cao nhất của khoa Công nghệ thông tin là ai?",
    "Thống kê tổng học phí đã lập, thực thu và nợ còn lại của từng khoa?",
    "Nhà cung cấp nào nhận được nhiều tiền chi phí nhất từ các khoa?"
]

if __name__ == "__main__":
    print("=" * 70)
    print(f"🤖 MRP SEMANTIC GRAPH CYPHER ENGINE")
    print(f"• LLM Provider: {llm_provider.upper()} ({ollama_model})")
    print("=" * 70)
    
    qa_chain = get_graph_qa_chain()
    
    for idx, q in enumerate(TEST_QUESTIONS, 1):
        print(f"\n" + "-" * 50)
        print(f"🔹 [Test {idx}]: {q}")
        print("-" * 50)
        try:
            res = qa_chain.invoke({"query": q})
            cypher_steps = [s["query"] for s in res.get("intermediate_steps", []) if "query" in s]
            print(f"⚡ Cypher: {cypher_steps[0] if cypher_steps else 'N/A'}")
            print(f"💬 AI Trả lời:\n{res['result']}")
        except Exception as e:
            print(f"❌ Lỗi: {e}")

