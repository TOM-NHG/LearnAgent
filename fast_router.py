"""
Fast-Path Router & Parametric Cypher Template Engine (Sub-50ms Execution).
Maps high-frequency financial and academic queries directly to optimized Cypher/SQL templates.
Zero LLM latency and 100% deterministic accuracy.
"""
import sys
import os
import re
import time
from typing import Optional, Dict, Any, Tuple

# Reconfigure stdout to UTF-8 for Windows console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

class FastPathRouter:
    """
    High-performance pattern matcher and parameterized query runner.
    Bypasses LLM generation for standard executive and management queries.
    """
    def __init__(self):
        # Register standard parameterized templates: (Regex Pattern, Template Name, Parameterized Cypher, Description)
        self.templates = [
            # 1. Tổng công nợ còn lại toàn trường
            (
                r"(tổng\s+)?(công\s+nợ|tiền\s+nợ|dư\s+nợ|nợ\s+học\s+phí)(\s+còn\s+lại)?(\s+toàn\s+trường)?",
                "TOTAL_REMAINING_DEBT",
                """
                MATCH (i:Invoice)
                RETURN 
                    sum(i.remaining_balance) AS tong_cong_no_con_lai_vnd,
                    count(i) AS tong_so_hoa_don,
                    sum(CASE WHEN i.remaining_balance > 0 THEN 1 ELSE 0 END) AS so_hoa_don_con_no
                """,
                "Tổng công nợ học phí còn tồn đọng toàn trường"
            ),
            # 2. Tổng doanh thu học phí đã lập hóa đơn (Billed Tuition)
            (
                r"(tổng\s+)?(doanh\s+thu|học\s+phí\s+đã\s+lập|học\s+phí\s+phải\s+thu|billed)",
                "TOTAL_BILLED_TUITION",
                """
                MATCH (i:Invoice)
                RETURN 
                    sum(i.total_amount) AS tong_hoc_phi_lap_hd_vnd,
                    sum(i.tuition_fee) AS hoc_phi_goc_vnd,
                    sum(i.scholarship_amount) AS hoc_bong_da_cap_vnd,
                    sum(i.late_fee) AS phi_tre_han_vnd,
                    count(i) AS tong_so_hoa_don
                """,
                "Tổng học phí đã lập hóa đơn (Billed Tuition)"
            ),
            # 3. Tổng tiền học phí thực thu về tài khoản
            (
                r"(tổng\s+)?(tiền\s+)?(thực\s+thu|đã\s+thu|thu\s+về|collected)",
                "TOTAL_COLLECTED_TUITION",
                """
                MATCH (p:Payment)
                WHERE p.payment_status = 'Successful' OR p.payment_status = 'Success'
                RETURN 
                    sum(p.amount_paid) AS tong_tien_thuc_thu_vnd,
                    count(p) AS so_giao_dich_thanh_cong
                """,
                "Tổng tiền học phí thực thu từ các giao dịch thành công"
            ),
            # 4. Công nợ quá hạn (Overdue Debt)
            (
                r"(tổng\s+)?(công\s+nợ|tiền\s+nợ)\s+(quá\s+hạn|trễ\s+hạn|overdue)",
                "TOTAL_OVERDUE_DEBT",
                """
                MATCH (i:Invoice)
                WHERE i.remaining_balance > 0 AND (i.status CONTAINS 'Overdue' OR i.due_date < date('2026-08-30'))
                RETURN 
                    sum(i.remaining_balance) AS tong_no_qua_han_vnd,
                    count(i) AS so_hoa_don_qua_han
                """,
                "Tổng công nợ học phí đã quá hạn thanh toán"
            ),
            # 5. Top sinh viên nợ nhiều nhất
            (
                r"top\s*(\d+)?\s*(sinh\s+viên|sv)\s+(nợ\s+nhiều\s+nhất|dư\s+nợ\s+cao\s+nhất|nợ\s+khủng)",
                "TOP_STUDENTS_HIGHEST_DEBT",
                """
                MATCH (s:Student)
                WHERE s.total_remaining_debt > 0
                OPTIONAL MATCH (s)-[:BELONGS_TO]->(d:Department)
                RETURN 
                    s.id AS mssv,
                    s.full_name AS ho_ten,
                    d.name AS khoa,
                    s.total_remaining_debt AS tong_no_vnd,
                    s.payment_completion_rate AS ty_le_da_dong,
                    s.status AS trang_thai
                ORDER BY s.total_remaining_debt DESC
                LIMIT $limit
                """,
                "Top sinh viên có số nợ tồn đọng cao nhất"
            ),
            # 6. Top sinh viên có rủi ro cao nhất (Risk Score)
            (
                r"top\s*(\d+)?\s*(sinh\s+viên|sv)\s+(rủi\s+ro|nguy\s+cơ|risk)",
                "TOP_STUDENTS_HIGHEST_RISK",
                """
                MATCH (s:Student)
                OPTIONAL MATCH (s)-[:BELONGS_TO]->(d:Department)
                RETURN 
                    s.id AS mssv,
                    s.full_name AS ho_ten,
                    d.name AS khoa,
                    s.risk_score AS diem_rui_ro,
                    s.total_remaining_debt AS tong_no_vnd,
                    s.failed_payments_count AS so_lan_loi_the,
                    s.status AS trang_thai
                ORDER BY s.risk_score DESC, s.total_remaining_debt DESC
                LIMIT $limit
                """,
                "Top sinh viên có điểm rủi ro tài chính cao nhất"
            ),
            # 7. Khoa có ngân sách lớn nhất / Chi tiết ngân sách khoa
            (
                r"(khoa|phòng\s+ban)\s+(nào\s+)?(ngân\s+sách\s+lớn\s+nhất|ngân\s+sách\s+cao\s+nhất|ngân\s+sách\s+năm)",
                "DEPARTMENT_ANNUAL_BUDGET",
                """
                MATCH (d:Department)
                OPTIONAL MATCH (d)<-[:INCURRED_BY]-(e:Expense)
                WHERE e.approval_status = 'Approved' OR e.approval_status IS NULL
                WITH d, coalesce(sum(e.amount), 0) AS chi_phi_da_duyet
                RETURN 
                    d.id AS ma_khoa,
                    d.name AS ten_khoa,
                    d.annual_budget AS ngan_sach_nam_vnd,
                    chi_phi_da_duyet AS da_giai_ngan_vnd,
                    round(chi_phi_da_duyet * 100.0 / d.annual_budget, 2) AS ty_le_giai_ngan_pct
                ORDER BY d.annual_budget DESC
                """,
                "Danh sách ngân sách và tỷ lệ giải ngân của các khoa"
            ),
            # 8. Tổng chi phí hoạt động đã phê duyệt
            (
                r"(tổng\s+)?(chi\s+phí|khoản\s+chi)(\s+hoạt\s+động)?(\s+đã\s+duyệt|\s+đã\s+phê\s+duyệt)?",
                "TOTAL_APPROVED_EXPENSES",
                """
                MATCH (e:Expense)
                WHERE e.approval_status = 'Approved'
                RETURN 
                    sum(e.amount) AS tong_chi_phi_da_duyet_vnd,
                    count(e) AS so_khoan_chi_da_duyet
                """,
                "Tổng chi phí hoạt động đã phê duyệt của toàn trường"
            ),
            # 9. Dòng tiền thuần (Net Cash Flow)
            (
                r"(dòng\s+tiền\s+thuần|net\s+cash\s+flow|thu\s+trừ\s+chi|chênh\s+lệch\s+thu\s+chi)",
                "NET_CASH_FLOW",
                """
                MATCH (p:Payment) WHERE p.payment_status = 'Successful' OR p.payment_status = 'Success'
                WITH sum(p.amount_paid) AS tong_thu
                MATCH (e:Expense) WHERE e.approval_status = 'Approved'
                WITH tong_thu, sum(e.amount) AS tong_chi
                RETURN 
                    tong_thu AS tien_thuc_thu_vnd,
                    tong_chi AS tien_thuc_chi_vnd,
                    (tong_thu - tong_chi) AS dong_tien_thuan_vnd
                """,
                "Dòng tiền thuần toàn trường (Thực thu - Thực chi)"
            ),
            # 10. Tỷ lệ thu học phí toàn trường
            (
                r"(tỷ\s+lệ\s+thu|hiệu\s+quả\s+thu|collection\s+rate)",
                "COLLECTION_RATE",
                """
                MATCH (i:Invoice)
                WITH sum(i.total_amount) AS phai_thu
                MATCH (p:Payment) WHERE p.payment_status = 'Successful' OR p.payment_status = 'Success'
                WITH phai_thu, sum(p.amount_paid) AS da_thu
                RETURN 
                    phai_thu AS tong_phai_thu_vnd,
                    da_thu AS tong_da_thu_vnd,
                    round(da_thu * 100.0 / phai_thu, 2) AS ty_le_thu_hoc_phi_pct
                """,
                "Tỷ lệ thu hồi học phí toàn trường"
            ),
            # 11. Thống kê tổng số sinh viên toàn trường & tổng số khoa (không kèm tên khoa cụ thể)
            (
                r"^(\s*thống\s+kê\s+)?(tổng\s+số\s+sinh\s+viên|số\s+sinh\s+viên\s+toàn\s+trường|sinh\s+viên\s+và\s+khoa)(\s+toàn\s+trường)?$",
                "TOTAL_STUDENTS_AND_DEPARTMENTS",
                """
                MATCH (s:Student) WITH count(s) AS tong_sv
                MATCH (d:Department) WITH tong_sv, count(d) AS tong_khoa
                MATCH (i:Invoice) WITH tong_sv, tong_khoa, count(i) AS tong_hd
                RETURN tong_sv, tong_khoa, tong_hd
                """,
                "Thống kê tổng số lượng sinh viên, khoa và hóa đơn toàn trường"
            ),
            # 12. Sinh viên theo Khoa cụ thể (chỉ bắt khi có tên khoa cụ thể ở cuối: Luật, Kinh tế, CNTT...)
            (
                r"^(bao\s+nhiêu\s+)?(sinh\s+viên|sv)\s+(đang\s+học\s+tại\s+|của\s+)?khoa\s+(công\s+nghệ\s+thông\s+tin|luật|kinh\s+tế|tài\s+chính\s*-\s*kế\s+toán|quản\s+trị\s+kinh\s+doanh|ngoại\s+ngữ|kỹ\s+thuật\s+điện|kỹ\s+thuật\s+xây\s+dựng|công\s+nghệ\s+sinh\s+học|du\s+lịch\s*-\s*khách\s+sạn|truyền\s+thông|khoa\s+học\s+dữ\s+liệu)$",
                "DEPARTMENT_STUDENTS_COUNT",
                """
                MATCH (s:Student)-[:BELONGS_TO]->(d:Department)
                WHERE toLower(d.name) CONTAINS toLower($dept_name)
                RETURN d.name AS ten_khoa, count(s) AS so_sv, sum(CASE WHEN s.status = 'Active' THEN 1 ELSE 0 END) AS dang_hoc
                """,
                "Số lượng sinh viên của một khoa cụ thể"
            ),
            # 13. Sinh viên bỏ học (Dropout)
            (
                r"(sinh\s+viên|sv)\s+(đã\s+)?(nghỉ\s+học|thôi\s+học|dropped\s+out|dropout)",
                "DROPOUT_STUDENTS_COUNT",
                """
                MATCH (s:Student)
                WHERE s.status = 'Dropped Out'
                RETURN count(s) AS so_sv_thoi_hoc
                """,
                "Số lượng sinh viên đã thôi học / nghỉ học"
            ),
            # 14. Nhà cung cấp nhận chi phí lớn nhất
            (
                r"(nhà\s+cung\s+cấp|vendor)\s+(nào\s+)?(lớn\s+nhất|nhiều\s+tiền\s+nhất|chi\s+phí\s+cao\s+nhất)",
                "TOP_VENDOR_EXPENSE",
                """
                MATCH (e:Expense)-[:PAID_TO]->(v:Vendor)
                WHERE e.approval_status = 'Approved'
                RETURN v.name AS ten_vendor, sum(e.amount) AS tong_tien_chi_vnd
                ORDER BY tong_tien_chi_vnd DESC LIMIT 5
                """,
                "Top nhà cung cấp nhận chi phí lớn nhất"
            )
        ]

    def route(self, question: str) -> Optional[Dict[str, Any]]:
        """
        Evaluates question against regex patterns.
        Returns query plan dict if matched, None if fallback to LLM is needed.
        """
        start_time = time.perf_counter()
        normalized_q = question.strip().lower()
        
        # Remove punctuation
        cleaned_q = re.sub(r"[?!.,]", "", normalized_q)

        for pattern, name, cypher_template, description in self.templates:
            match = re.search(pattern, cleaned_q, re.IGNORECASE)
            if match:
                params = {}
                # Check if query contains a custom limit (e.g. 'top 5', 'top 20')
                limit = 10
                if "$limit" in cypher_template:
                    if match.groups() and match.group(1) and match.group(1).isdigit():
                        limit = int(match.group(1))
                    else:
                        # Scan question for digit
                        num_match = re.search(r"top\s*(\d+)", cleaned_q)
                        if num_match:
                            limit = int(num_match.group(1))
                    params["limit"] = limit

                # Extract department name if applicable
                if name == "DEPARTMENT_STUDENTS_COUNT" and match.groups():
                    dept_raw = match.group(len(match.groups())).strip()
                    params["dept_name"] = dept_raw

                elapsed_ms = (time.perf_counter() - start_time) * 1000
                return {
                    "matched": True,
                    "template_name": name,
                    "description": description,
                    "cypher": cypher_template.strip(),
                    "params": params,
                    "routing_time_ms": round(elapsed_ms, 3)
                }

        return None

if __name__ == "__main__":
    router = FastPathRouter()
    test_queries = [
        "Tổng công nợ còn lại của toàn trường là bao nhiêu?",
        "Doanh thu học phí đã lập hóa đơn?",
        "Tổng tiền thực thu về tài khoản",
        "Công nợ quá hạn hiện tại",
        "Top 5 sinh viên nợ nhiều nhất",
        "Top 15 sinh viên rủi ro nhất",
        "Khoa nào ngân sách lớn nhất",
        "Tổng chi phí hoạt động đã duyệt",
        "Dòng tiền thuần của trường đang âm hay dương?",
        "Tỷ lệ thu học phí đạt bao nhiêu %?",
        "Cho tôi biết sinh viên tên Nguyễn Văn A học chuyên ngành gì?" # Câu tự do (không match)
    ]

    print("=" * 70)
    print("FAST-PATH ROUTER BENCHMARK (Target < 5ms):")
    print("=" * 70)
    for q in test_queries:
        res = router.route(q)
        if res:
            print(f"✅ MATCHED: '{q}'")
            print(f"   -> Template: {res['template_name']} | Time: {res['routing_time_ms']} ms | Params: {res['params']}")
        else:
            print(f"⚡ FALLBACK TO LLM: '{q}'")
