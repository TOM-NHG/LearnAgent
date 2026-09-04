"""
E2E Automated Test Suite for MRP Intelligence (Group 1 Evaluation)
Tests queries from Basic single-entity to Advanced multi-hop cross-table joins.
Evaluates Semantic Cache hits, Slim Prompt LLM execution, Smart Formatter rendering, and Latency.
"""
import sys
import time
import requests
import json

# Force UTF-8 stdout
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

SERVER_URL = "http://127.0.0.1:8000"

# Comprehensive test matrix: Basic -> Intermediate -> Advanced Multi-Hop
TEST_SCENARIOS = [
    {
        "id": "TC01",
        "level": "Cơ bản (Single Entity - Đếm)",
        "question": "Có bao nhiêu sinh viên khoa Luật?",
        "expected_keywords": ["Luật", "Sinh Viên"],
        "expect_records": True
    },
    {
        "id": "TC02",
        "level": "Cơ bản (Single Entity - Phân loại)",
        "question": "số sinh viên công nghệ thông tin",
        "expected_keywords": ["135", "Sinh Viên"],
        "expect_records": True
    },
    {
        "id": "TC03",
        "level": "Cơ bản (Finance - Thống kê tiền phạt)",
        "question": "Có bao nhiêu hóa đơn có tiền phạt trễ hạn?",
        "expected_keywords": ["731", "Tiền Phạt"],
        "expect_records": True
    },
    {
        "id": "TC04",
        "level": "Trung cấp (2 Thực thể: Invoice + Student - Học bổng)",
        "question": "Những sinh viên nào được miễn giảm học phí và số tiền là bao nhiêu?",
        "expected_keywords": ["Miễn Giảm", "VNĐ"],
        "expect_records": True
    },
    {
        "id": "TC05",
        "level": "Trung cấp (2 Thực thể: Student + Department - Nợ học phí)",
        "question": "Danh sách sinh viên nợ học phí của khoa Luật là ai và nợ bao nhiêu?",
        "expected_keywords": ["Luật", "VNĐ"],
        "expect_records": True
    },
    {
        "id": "TC06",
        "level": "Nâng cao (Xếp hạng Top N: Student + Department + Risk)",
        "question": "Top 5 sinh viên có điểm rủi ro cao nhất?",
        "expected_keywords": ["Bảng Xếp Hạng", "🥇", "Điểm Rủi Ro"],
        "expect_records": True
    },
    {
        "id": "TC07",
        "level": "Nâng cao (3 Bảng JOIN: Department + Student + Invoice)",
        "question": "Thống kê tổng học phí đã lập, thực thu và nợ còn lại của từng khoa?",
        "expected_keywords": ["Khoa", "Tổng Học Phí", "Thực Thu", "Công Nợ"],
        "expect_records": True
    },
    {
        "id": "TC08",
        "level": "Nâng cao (Ngân sách & Chi phí: Department + Expense + Giải ngân)",
        "question": "Khoa nào có ngân sách lớn nhất và chi phí đã chi là bao nhiêu?",
        "expected_keywords": ["Ngân Sách", "VNĐ"],
        "expect_records": True
    },
    {
        "id": "TC09",
        "level": "Biên / Edge Case (Khoa không tồn tại trong hệ thống)",
        "question": "Khoa Hàng Không Vũ Trụ có bao nhiêu sinh viên?",
        "expected_keywords": ["0"],
        "expect_records": False
    }
]

def run_e2e_suite():
    print("=" * 80)
    print("🧪 MRP INTELLIGENCE V3.0 — BỘ KIỂM THỬ TỰ ĐỘNG E2E (EVALUATION SUITE)")
    print(f"Target Server: {SERVER_URL}")
    print("=" * 80)

    # 1. Health check
    try:
        r_health = requests.get(f"{SERVER_URL}/health", timeout=5)
        print(f"✅ Server Health: {r_health.status_code} | Model status: {r_health.json().get('status')}")
    except Exception as e:
        print(f"❌ Server không phản hồi trên cổng 8000: {e}")
        print("💡 Hãy chạy '.\venv\Scripts\python.exe main.py' trên terminal trước khi test.")
        return

    results = []
    total_passed = 0

    for tc in TEST_SCENARIOS:
        print(f"\n[{tc['id']}] [{tc['level']}]")
        print(f"❓ Câu hỏi: \"{tc['question']}\"")
        
        t_start = time.perf_counter()
        try:
            res = requests.post(f"{SERVER_URL}/chat", json={"question": tc["question"]}, timeout=60)
            latency_ms = (time.perf_counter() - t_start) * 1000
            
            if res.status_code == 200:
                data = res.json()
                answer = data.get("answer", "")
                source = data.get("source", "")
                cypher = data.get("metadata", {}).get("cypher", "")
                total_ms = data.get("total_time_ms", latency_ms)
                cypher_ms = data.get("cypher_time_ms", 0)

                # Validate
                passed = True
                fail_reasons = []

                # Keyword verification
                for kw in tc["expected_keywords"]:
                    if kw.lower() not in answer.lower():
                        passed = False
                        fail_reasons.append(f"Thiếu keyword: '{kw}'")

                if passed:
                    total_passed += 1
                    status_icon = "✅ PASS"
                else:
                    status_icon = "⚠️ SOFT_FAIL"

                print(f"Status: {status_icon} | Nguồn: {source} | Độ trễ: {total_ms:.1f} ms (Cypher: {cypher_ms} ms)")
                print(f"Cypher: {cypher}")
                print(f"Trích xuất câu trả lời:\n{answer[:200]}...")
                if fail_reasons:
                    print(f"Lưu ý: {', '.join(fail_reasons)}")

                results.append({
                    "id": tc["id"],
                    "level": tc["level"],
                    "question": tc["question"],
                    "passed": passed,
                    "source": source,
                    "total_ms": total_ms,
                    "cypher_ms": cypher_ms,
                    "cypher": cypher
                })
            else:
                print(f"❌ Lỗi HTTP {res.status_code}: {res.text}")
                results.append({"id": tc["id"], "passed": False, "total_ms": 0, "source": "HTTP_ERROR"})
        except Exception as e:
            print(f"❌ Timeout / Connection Error: {e}")
            results.append({"id": tc["id"], "passed": False, "total_ms": 0, "source": "TIMEOUT"})

    # Print Summary Table
    print("\n" + "=" * 80)
    print("📊 BẢNG TỔNG KẾT ĐÁNH GIÁ HIỆU SUẤT NHÓM 1 (E2E TEST REPORT)")
    print("=" * 80)
    print(f"{'ID':<6} | {'Cấp Độ':<28} | {'Kết Quả':<10} | {'Nguồn':<20} | {'Độ Trễ (ms)'}")
    print("-" * 80)
    for r in results:
        res_str = "PASS" if r["passed"] else "FAIL"
        ms_str = f"{r.get('total_ms', 0):,.1f} ms"
        print(f"{r['id']:<6} | {r.get('level', 'N/A')[:28]:<28} | {res_str:<10} | {r.get('source', '')[:20]:<20} | {ms_str}")

    print("-" * 80)
    print(f"🏆 Tỷ lệ vượt qua: {total_passed}/{len(TEST_SCENARIOS)} ({total_passed/len(TEST_SCENARIOS)*100:.1f}%)")
    print("=" * 80)

if __name__ == "__main__":
    run_e2e_suite()
