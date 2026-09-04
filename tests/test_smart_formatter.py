import pytest
from smart_formatter_agent import SmartAnswerFormatterAgent

@pytest.fixture
def agent():
    return SmartAnswerFormatterAgent()

def test_single_metric_kpi(agent):
    question = "Tổng học phí đã lập của toàn trường là bao nhiêu?"
    records = [{"tong_hoc_phi_da_lap": 15000000000}]
    output = agent.format(question, records)
    
    assert "Báo Cáo Chỉ Số" in output
    assert "15,000,000,000 VNĐ" in output
    assert "Tổng Học Phí Đã Lập" in output

def test_ranking_top_list(agent):
    question = "Top 3 sinh viên có dư nợ cao nhất?"
    records = [
        {"ho_ten": "Nguyễn Văn A", "tien_no": 25000000},
        {"ho_ten": "Trần Thị B", "tien_no": 18000000},
        {"ho_ten": "Lê Văn C", "tien_no": 12000000}
    ]
    output = agent.format(question, records)
    
    assert "Bảng Xếp Hạng" in output
    assert "🥇 **Nguyễn Văn A**" in output
    assert "25,000,000 VNĐ" in output
    assert "🥉 **Lê Văn C**" in output

def test_table_multi_records(agent):
    question = "Danh sách thống kê các khoa"
    records = [
        {"ten_khoa": "Khoa Luật", "so_sv": 120, "tong_no": 50000000},
        {"ten_khoa": "Khoa CNTT", "so_sv": 350, "tong_no": 20000000}
    ]
    output = agent.format(question, records)
    
    assert "Kết Quả Tra Cứu" in output
    assert "| Tên Khoa / Phòng Ban | Số Lượng Sinh Viên | Tổng Công Nợ (VNĐ) |" in output
    assert "| Khoa Luật | 120 | 50,000,000 VNĐ |" in output

def test_empty_result(agent):
    question = "Khoa Hàng Không có bao nhiêu sinh viên?"
    records = []
    output = agent.format(question, records)
    
    assert "Không tìm thấy dữ liệu phù hợp" in output
    assert "Khoa Hàng Không" in output
