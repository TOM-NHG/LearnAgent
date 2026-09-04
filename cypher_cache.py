"""
Dynamic Semantic Cypher Cache for MRP Intelligence
Caches validated Cypher queries and extracts parameters (e.g. department names, limits, years).
Bypasses LLM inference for recurring or parameterized questions in < 2ms.
"""
import re
import time
from typing import Optional, Dict, Any, List

class SemanticCypherCache:
    """
    In-memory semantic cache with parameterized template matching.
    """
    def __init__(self):
        # Exact and normalized question cache
        self.exact_cache: Dict[str, str] = {}
        
        # Parameterized templates: (Pattern, Parameterized Cypher)
        self.templates = [
            # 1. Đếm sinh viên theo khoa: "có bao nhiêu sinh viên khoa luật", "sinh viên khoa CNTT"
            (
                r"(?:bao\s+nhiêu\s+)?(?:sinh\s+viên|sv)\s+(?:của\s+|thuộc\s+|đang\s+học\s+tại\s+)?khoa\s+([a-zA-Z\s\u00C0-\u1EF9\-]+)",
                """MATCH (s:Student)-[:BELONGS_TO]->(d:Department)
WHERE toLower(d.name) CONTAINS toLower('{dept}')
RETURN d.name AS ten_khoa, count(DISTINCT s) AS so_sinh_vien, sum(CASE WHEN s.status = 'Active' THEN 1 ELSE 0 END) AS dang_hoc"""
            ),
            # 2. Sinh viên nợ học phí theo khoa: "danh sách sinh viên nợ khoa luật", "sinh viên nợ học phí khoa kinh tế"
            (
                r"(?:danh\s+sách\s+)?(?:sinh\s+viên|sv)\s+(?:còn\s+)?(?:nợ|dư\s+nợ)\s+(?:học\s+phí\s+)?(?:của\s+)?khoa\s+([a-zA-Z\s\u00C0-\u1EF9\-]+)",
                """MATCH (s:Student)-[:BELONGS_TO]->(d:Department)
WHERE toLower(d.name) CONTAINS toLower('{dept}') AND s.total_remaining_debt > 0
RETURN s.id AS mssv, s.full_name AS ho_ten, s.total_remaining_debt AS tien_no, s.payment_completion_rate AS ty_le_hoan_thanh
ORDER BY tien_no DESC"""
            ),
            # 3. Thống kê tài chính từng khoa: "tổng học phí, thực thu và nợ của từng khoa"
            (
                r"(?:thống\s+kê\s+)?(?:tổng\s+)?(?:học\s+phí|thu\s+chi|công\s+nợ|thực\s+thu).*(?:từng\s+khoa|các\s+khoa)",
                """MATCH (d:Department)<-[:BELONGS_TO]-(s:Student)<-[:BILLED_TO]-(i:Invoice)
RETURN d.name AS ten_khoa, 
       sum(i.total_amount) AS tong_hoc_phi_da_lap, 
       sum(i.total_paid_successful) AS tong_thuc_thu, 
       sum(i.remaining_balance) AS tong_cong_no
ORDER BY tong_cong_no DESC"""
            ),
            # 4. Top N sinh viên nợ cao nhất
            (
                r"top\s*(\d+)?\s*(?:sinh\s+viên|sv)\s+(?:có\s+)?(?:dư\s+nợ|nợ\s+học\s+phí|nợ\s+cao\s+nhất|nợ\s+nhiều\s+nhất)",
                """MATCH (d:Department)<-[:BELONGS_TO]-(s:Student)
WHERE s.total_remaining_debt > 0
RETURN s.id AS mssv, s.full_name AS ho_ten, d.name AS ten_khoa, s.total_remaining_debt AS tien_no, s.risk_score AS diem_rui_ro
ORDER BY tien_no DESC
LIMIT {limit}"""
            ),
            # 5. Top N sinh viên rủi ro cao nhất
            (
                r"top\s*(\d+)?\s*(?:sinh\s+viên|sv)\s+(?:có\s+)?(?:điểm\s+)?(?:rủi\s+ro|nguy\s+cơ|risk)",
                """MATCH (d:Department)<-[:BELONGS_TO]-(s:Student)
RETURN s.id AS mssv, s.full_name AS ho_ten, d.name AS ten_khoa, s.risk_score AS diem_rui_ro, s.total_remaining_debt AS tien_no, s.payment_completion_rate AS ty_le_hoan_thanh
ORDER BY diem_rui_ro DESC
LIMIT {limit}"""
            ),
            # 6. Ngân sách khoa lớn nhất / chi phí giải ngân
            (
                r"(?:khoa|phòng\s+ban)\s+(?:nào\s+)?(?:ngân\s+sách\s+lớn\s+nhất|ngân\s+sách\s+cao\s+nhất|chi\s+phí\s+nhiều\s+nhất)",
                """MATCH (d:Department)
OPTIONAL MATCH (d)<-[:INCURRED_BY]-(e:Expense)
WHERE e.approval_status = 'Approved' OR e.approval_status IS NULL
WITH d, d.annual_budget AS ngan_sach, coalesce(sum(e.amount), 0) AS da_chi
RETURN d.name AS ten_khoa, ngan_sach, da_chi, round((da_chi * 100.0 / ngan_sach), 2) AS ty_le_giai_ngan_pct
ORDER BY ngan_sach DESC"""
            ),
            # 7. Học sinh được miễn giảm học phí / học bổng
            (
                r"(?:những\s+)?(?:sinh\s+viên|học\s+sinh|sv)\s+(?:nào\s+)?(?:được\s+)?(?:miễn\s+giảm|giảm\s+học\s+phí|học\s+bổng)",
                """MATCH (i:Invoice)-[:BILLED_TO]->(s:Student)
WHERE i.scholarship_amount > 0
RETURN s.id AS mssv, s.full_name AS ho_ten, sum(i.scholarship_amount) AS tong_tien_mien_giam
ORDER BY tong_tien_mien_giam DESC"""
            ),
            # 8. Tổng quan toàn trường (Sinh viên, Khoa, Hóa đơn)
            (
                r"(?:thống\s+kê\s+)?(?:tổng\s+quan|số\s+lượng\s+sinh\s+viên\s+và\s+khoa|bao\s+nhiêu\s+sinh\s+viên\s+toàn\s+trường)",
                """MATCH (s:Student) WITH count(s) AS tong_sv
MATCH (d:Department) WITH tong_sv, count(d) AS tong_khoa
MATCH (i:Invoice) WITH tong_sv, tong_khoa, count(i) AS tong_hd
RETURN tong_sv, tong_khoa, tong_hd"""
            ),
            # 9. Hóa đơn nợ quá hạn và tiền phạt trễ hạn
            (
                r"(?:bao\s+nhiêu\s+)?(?:hóa\s+đơn|hd)\s+.*(?:tiền\s+phạt|trễ\s+hạn|nộp\s+muộn|phạt)",
                """MATCH (i:Invoice)
WHERE i.late_fee > 0
RETURN count(DISTINCT i) AS so_hoa_don_bi_phat, sum(i.late_fee) AS tong_tien_phat, sum(i.remaining_balance) AS tong_no_con_lai"""
            )
        ]

    def normalize(self, text: str) -> str:
        return re.sub(r"[?!.,]", "", text.strip().lower())

    def get(self, question: str) -> Optional[str]:
        """Returns cached or template-rendered Cypher in < 1ms."""
        norm_q = self.normalize(question)

        # 1. Exact match hit
        if norm_q in self.exact_cache:
            return self.exact_cache[norm_q]

        # 2. Parameterized template hit
        for pattern, cypher_tmpl in self.templates:
            match = re.search(pattern, norm_q, re.IGNORECASE)
            if match:
                groups = match.groups()
                # Determine limit
                limit_val = 5
                limit_search = re.search(r"top\s*(\d+)", norm_q)
                if limit_search:
                    limit_val = int(limit_search.group(1))

                # Determine dept
                dept_val = ""
                if "{dept}" in cypher_tmpl and groups:
                    dept_val = groups[0].strip()

                rendered = cypher_tmpl.format(dept=dept_val, limit=limit_val)
                # Store in exact cache for next time
                self.exact_cache[norm_q] = rendered
                return rendered

        return None

    def put(self, question: str, cypher: str):
        """Saves a successfully executed Cypher query into cache."""
        norm_q = self.normalize(question)
        self.exact_cache[norm_q] = cypher.strip()

# Singleton cache instance
cypher_cache = SemanticCypherCache()
