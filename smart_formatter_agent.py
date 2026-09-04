"""
Specialized Smart Answer Formatter Agent for MRP Graph Intelligence
Extracts question keywords and deterministically formats raw Neo4j records into
executive Markdown tables, KPI callout cards, and financial summaries in < 5ms.
Zero-LLM second-round inference prevents latency and hallucinations.
"""
import re
from typing import List, Dict, Any, Optional

class SmartAnswerFormatterAgent:
    """
    Dedicated Presentation Agent that bridges graph query records with natural language.
    Leverages user query keywords and schema heuristics to produce crisp, citable answers.
    """

    COLUMN_LABELS = {
        # Department
        "ten_khoa": "Tên Khoa / Phòng Ban",
        "d.name": "Tên Khoa",
        "ngan_sach": "Ngân Sách (VNĐ)",
        "annual_budget": "Ngân Sách Năm (VNĐ)",
        "da_chi": "Đã Chi Thực Tế (VNĐ)",
        "ty_le_giai_ngan_pct": "Tỷ Lệ Giải Ngân (%)",

        # Student
        "mssv": "Mã Sinh Viên",
        "s.id": "Mã Sinh Viên",
        "ho_ten": "Họ và Tên",
        "s.full_name": "Họ và Tên",
        "so_sv": "Số Lượng Sinh Viên",
        "so_sinh_vien": "Số Lượng Sinh Viên",
        "so_sinh_vien_bo_hoc": "Số SV Thôi Học",
        "diem_rui_ro": "Điểm Rủi Ro",
        "risk_score": "Điểm Rủi Ro",
        "ty_le_hoan_thanh": "Tỷ Lệ Đóng (%)",
        "payment_completion_rate": "Tỷ Lệ Đóng (%)",
        "tien_no": "Công Nợ Còn Lại (VNĐ)",
        "tong_no": "Tổng Công Nợ (VNĐ)",
        "tong_no_kho_doi": "Tổng Nợ Khó Đòi (VNĐ)",

        # Invoice & Finance
        "tong_hoc_phi_da_lap": "Tổng Học Phí Đã Lập (VNĐ)",
        "tong_thuc_thu": "Tổng Thực Thu (VNĐ)",
        "tong_cong_no": "Tổng Công Nợ Còn Lại (VNĐ)",
        "tong_so_tien": "Tổng Số Tiền (VNĐ)",
        "so_hoa_don": "Số Lượng Hóa Đơn",
        "so_hoa_don_qua_han": "Hóa Đơn Quá Hạn",
        "tong_no_qua_han": "Tổng Nợ Quá Hạn (VNĐ)",
        "tong_tien_phat": "Tiền Phạt Trễ Hạn (VNĐ)",
        "tong_tien_mien_giam": "Tổng Tiền Miễn Giảm (VNĐ)",
        "hoc_bong": "Học Bổng / Miễn Giảm (VNĐ)",

        # Payment
        "phuong_thuc": "Phương Thức Thanh Toán",
        "so_lan_thanh_toan": "Số Lượt Giao Dịch",
        "tong_tien_da_dong": "Tổng Tiền Đã Đóng (VNĐ)",

        # Vendor & Expenses
        "nha_cung_cap": "Nhà Cung Cấp",
        "tong_tien_nhan": "Tổng Chi Trả (VNĐ)",
        "loai_chi_phi": "Danh Mục Chi Phí",

        # Audit
        "ten_bang": "Bảng Dữ Liệu",
        "loai_loi": "Loại Lỗi Kiểm Toán",
        "so_luong_loi": "Số Lượng Lỗi"
    }

    CURRENCY_COLUMNS = {
        "ngan_sach", "annual_budget", "da_chi", "tien_no", "tong_no",
        "tong_no_kho_doi", "tong_hoc_phi_da_lap", "tong_thuc_thu",
        "tong_cong_no", "tong_so_tien", "tong_no_qua_han", "tong_tien_phat",
        "tong_tien_mien_giam", "hoc_bong", "tong_tien_da_dong", "tong_tien_nhan",
        "amount", "debt_amount", "tuition_fee", "remaining_balance"
    }

    PERCENT_COLUMNS = {
        "ty_le_giai_ngan_pct", "ty_le_hoan_thanh", "payment_completion_rate", "rate"
    }

    def __init__(self):
        self.name = "SmartAnswerFormatterAgent"

    def format(self, question: str, records: List[Dict[str, Any]], cypher_query: Optional[str] = None) -> str:
        """
        Main entry point for formatting graph query results.
        Returns a beautifully rendered Markdown response based on query keywords and data structure.
        """
        if not records:
            return self._format_empty_result(question, cypher_query)

        # 1. Inspect data shape
        row_count = len(records)
        first_row = records[0]
        keys = list(first_row.keys())

        # 2. Extract question keywords and detect intent
        intent = self._detect_intent(question, keys, row_count)

        # 3. Render appropriate format
        if intent == "SINGLE_METRIC":
            return self._format_single_metric(question, first_row)
        elif intent == "RANKING_LIST":
            return self._format_ranking_list(question, records, keys)
        else:
            return self._format_table(question, records, keys)

    def _detect_intent(self, question: str, keys: List[str], row_count: int) -> str:
        q_lower = question.lower()

        # If exactly 1 row and 1-3 aggregated numeric columns
        if row_count == 1 and len(keys) <= 3:
            numeric_or_stat = any(k.startswith(("tong_", "so_", "ty_le_")) or k in self.CURRENCY_COLUMNS for k in keys)
            if numeric_or_stat and not any(kw in q_lower for kw in ["danh sách", "bảng", "chi tiết"]):
                return "SINGLE_METRIC"

        # If question asks for Top / Rank
        if any(kw in q_lower for kw in ["top", "cao nhất", "nhiều nhất", "thấp nhất", "xếp hạng"]):
            if row_count <= 10:
                return "RANKING_LIST"

        return "TABLE"

    def _format_value(self, key: str, val: Any) -> str:
        if val is None:
            return "0"
        
        # Check percentage
        if key in self.PERCENT_COLUMNS or "pct" in key or "rate" in key:
            try:
                num = float(val)
                return f"{num:.1f}%"
            except (ValueError, TypeError):
                return str(val)

        # Check currency
        if key in self.CURRENCY_COLUMNS or any(curr in key for curr in ["tien", "budget", "no_", "chi", "thu"]):
            try:
                num = float(val)
                return f"{num:,.0f} VNĐ"
            except (ValueError, TypeError):
                return str(val)

        # Check numeric counts
        if isinstance(val, (int, float)):
            if isinstance(val, int) or val.is_integer():
                return f"{int(val):,}"
            return f"{val:,.2f}"

        return str(val)

    def _get_label(self, key: str) -> str:
        # Check dictionary exact match
        if key in self.COLUMN_LABELS:
            return self.COLUMN_LABELS[key]
        # Normalize snake_case or dotted alias
        normalized = key.split(".")[-1].replace("_", " ").title()
        return normalized

    def _format_single_metric(self, question: str, record: Dict[str, Any]) -> str:
        """Renders 1-row aggregated KPI cards with context from question."""
        metrics_lines = []
        for k, v in record.items():
            label = self._get_label(k)
            formatted_val = self._format_value(k, v)
            metrics_lines.append(f"• **{label}**: `{formatted_val}`")

        response = [
            f"📊 **Báo Cáo Chỉ Số:** *\"{question.strip()}\"*",
            "",
            "> 💡 **Kết quả tổng hợp từ Đồ thị Tri thức:**",
            ""
        ]
        response.extend(metrics_lines)
        return "\n".join(response)

    def _format_ranking_list(self, question: str, records: List[Dict[str, Any]], keys: List[str]) -> str:
        """Renders Top N items with ranking badges."""
        response = [
            f"🏆 **Bảng Xếp Hạng:** *\"{question.strip()}\"*",
            ""
        ]

        # Primary name key (first non-numeric string column)
        name_key = keys[0]
        val_keys = keys[1:]

        medals = ["🥇", "🥈", "🥉"]
        for idx, row in enumerate(records, 1):
            badge = medals[idx - 1] if idx <= 3 else f"`#{idx}`"
            primary_name = row.get(name_key, "N/A")

            details = []
            for vk in val_keys:
                label = self._get_label(vk)
                formatted_val = self._format_value(vk, row.get(vk))
                details.append(f"{label}: **{formatted_val}**")

            detail_str = " | ".join(details)
            response.append(f"{badge} **{primary_name}** ({detail_str})")

        return "\n".join(response)

    def _format_table(self, question: str, records: List[Dict[str, Any]], keys: List[str]) -> str:
        """Renders standard multi-row tabular Markdown."""
        headers = [self._get_label(k) for k in keys]
        separators = ["---"] * len(keys)

        lines = [
            f"📋 **Kết Quả Tra Cứu:** *\"{question.strip()}\"*",
            "",
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(separators) + " |"
        ]

        for row in records:
            row_vals = [self._format_value(k, row.get(k)) for k in keys]
            lines.append("| " + " | ".join(row_vals) + " |")

        lines.append(f"\n*(Tổng cộng: {len(records)} dòng kết quả)*")
        return "\n".join(lines)

    def _format_empty_result(self, question: str, cypher_query: Optional[str] = None) -> str:
        """Constructs a helpful, keyword-aware empty result advisory."""
        return (
            f"🔍 **Không tìm thấy dữ liệu phù hợp** cho câu hỏi:\n"
            f"> *\"{question.strip()}\"*\n\n"
            f"💡 **Gợi ý kiểm tra:**\n"
            f"- Kiểm tra lại tên riêng (tên Khoa, mã Sinh viên, năm học) xem có chính xác không.\n"
            f"- Thử nới lỏng điều kiện tìm kiếm hoặc hỏi thông tin tổng quan của toàn trường."
        )

# Singleton instance
smart_formatter = SmartAnswerFormatterAgent()
