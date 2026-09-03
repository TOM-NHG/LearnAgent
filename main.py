"""
FastAPI Server for MRP Financial & Student AI Agent (Version 2.0).
Integrates:
1. Fast-Path Router (Sub-50ms deterministic query resolution).
2. Super Cypher Engine with Pruned Sub-Ontology and Self-Healing.
3. Fallback SQLite Data Service for zero-downtime offline querying when Neo4j is starting.
4. Interactive Web Chat & Dashboard integration.
"""
import os
import sys
import sqlite3
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any

# UTF-8 console output for Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PROJECT_ROOT = os.path.abspath("d:/NHG/AgentofMRP")
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from fast_router import FastPathRouter
from super_cypher_engine import SuperCypherEngine

app = FastAPI(
    title="MRP Financial Intelligence AI Agent API (Version 2.0)",
    description="Cognitive Knowledge Graph & Super Cypher Multi-Agent System.",
    version="2.0.0"
)

# Enable CORS for web dashboards and external apps
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

fast_router = FastPathRouter()

# Connect SQLite database as high-performance local fallback
SQLITE_DB_PATH = os.path.join(PROJECT_ROOT, "data", "mrp_finance.db")

def query_sqlite_fallback(template_name: str, params: dict) -> str:
    """Executes matching business formula against SQLite data warehouse."""
    if not os.path.exists(SQLITE_DB_PATH):
        return "Cơ sở dữ liệu SQLite chưa được khởi tạo."
    
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()

    try:
        if template_name == "TOTAL_REMAINING_DEBT":
            row = cursor.execute("""
                SELECT 
                    SUM(Remaining_Balance) AS tong_no,
                    COUNT(Invoice_ID) AS so_hd
                FROM fact_tuition_invoices;
            """).fetchone()
            tong_no = row[0] or 0
            return f"📊 **Tổng công nợ học phí còn tồn đọng toàn trường:** **{tong_no:,.0f} VNĐ** (trên {row[1]:,} hóa đơn)."

        elif template_name == "TOTAL_BILLED_TUITION":
            row = cursor.execute("""
                SELECT 
                    SUM(Tuition_Fee - Scholarship_Amount + Late_Fee),
                    SUM(Tuition_Fee),
                    SUM(Scholarship_Amount),
                    SUM(Late_Fee),
                    COUNT(Invoice_ID)
                FROM fact_tuition_invoices;
            """).fetchone()
            return f"📋 **Tổng học phí đã lập hóa đơn:** **{row[0]:,.0f} VNĐ** (Gốc: {row[1]:,.0f} đ, Học bổng miễn giảm: -{row[2]:,.0f} đ, Phí nộp muộn: +{row[3]:,.0f} đ, trên {row[4]:,} hóa đơn)."

        elif template_name == "TOTAL_COLLECTED_TUITION":
            row = cursor.execute("""
                SELECT COUNT(Payment_ID), SUM(Amount_Paid)
                FROM fact_payments
                WHERE Payment_Status = 'Successful';
            """).fetchone()
            return f"💰 **Tổng số tiền học phí thực thu về tài khoản:** **{row[1]:,.0f} VNĐ** (từ {row[0]:,} giao dịch thành công)."

        elif template_name == "TOTAL_OVERDUE_DEBT":
            row = cursor.execute("""
                SELECT SUM(Remaining_Balance), COUNT(Invoice_ID)
                FROM fact_tuition_invoices
                WHERE Remaining_Balance > 0 AND DATE('2026-08-30') > DATE(Due_Date);
            """).fetchone()
            return f"⚠️ **Tổng công nợ quá hạn (Overdue Debt):** **{row[0]:,.0f} VNĐ** (chiếm {row[1]:,} hóa đơn trễ hạn)."

        elif template_name == "TOP_STUDENTS_HIGHEST_DEBT":
            limit = params.get("limit", 5)
            rows = cursor.execute(f"""
                SELECT s.Student_ID, s.Full_Name, d.Department_Name, m.total_remaining_debt, m.payment_completion_rate
                FROM ml_student_features m
                JOIN dim_students s ON m.Student_ID = s.Student_ID
                JOIN dim_departments d ON s.Department_ID = d.Department_ID
                WHERE m.total_remaining_debt > 0
                ORDER BY m.total_remaining_debt DESC
                LIMIT {limit};
            """).fetchall()
            resp = f"🏆 **Top {limit} sinh viên có dư nợ cao nhất:**\n"
            for idx, r in enumerate(rows, 1):
                resp += f"{idx}. **{r[1]}** (MSSV: `{r[0]}`, Khoa: {r[2]}): nợ **{r[3]:,.0f} VNĐ** (Đã đóng: {r[4]*100:.1f}%)\n"
            return resp

        elif template_name == "TOP_STUDENTS_HIGHEST_RISK":
            limit = params.get("limit", 5)
            rows = cursor.execute(f"""
                SELECT s.Student_ID, s.Full_Name, d.Department_Name, m.risk_score, m.total_remaining_debt, s.Status
                FROM ml_student_features m
                JOIN dim_students s ON m.Student_ID = s.Student_ID
                JOIN dim_departments d ON s.Department_ID = d.Department_ID
                ORDER BY m.risk_score DESC, m.total_remaining_debt DESC
                LIMIT {limit};
            """).fetchall()
            resp = f"🚨 **Top {limit} sinh viên có điểm rủi ro tài chính cao nhất:**\n"
            for idx, r in enumerate(rows, 1):
                resp += f"{idx}. **{r[1]}** (MSSV: `{r[0]}`, Khoa: {r[2]}): Điểm rủi ro **{r[3]:.1f}/100** (Nợ: {r[4]:,.0f} VNĐ, Trạng thái: {r[5]})\n"
            return resp

        elif template_name == "DEPARTMENT_ANNUAL_BUDGET":
            rows = cursor.execute("""
                SELECT d.Department_Name, d.Annual_Budget
                FROM dim_departments d
                ORDER BY d.Annual_Budget DESC
                LIMIT 5;
            """).fetchall()
            resp = "🏛️ **Top 5 Khoa/Phòng ban có ngân sách năm lớn nhất:**\n"
            for idx, r in enumerate(rows, 1):
                resp += f"{idx}. **{r[0]}**: ngân sách **{r[1]:,.0f} VNĐ**\n"
            return resp

        elif template_name == "TOTAL_APPROVED_EXPENSES":
            row = cursor.execute("""
                SELECT COUNT(Expense_ID), SUM(Amount)
                FROM fact_expenses
                WHERE Approval_Status = 'Approved';
            """).fetchone()
            return f"🏢 **Tổng chi phí hoạt động đã phê duyệt:** **{row[1]:,.0f} VNĐ** (trên {row[0]:,} khoản chi hợp lệ)."

        elif template_name == "NET_CASH_FLOW":
            thu = cursor.execute("SELECT SUM(Amount_Paid) FROM fact_payments WHERE Payment_Status = 'Successful'").fetchone()[0] or 0
            chi = cursor.execute("SELECT SUM(Amount) FROM fact_expenses WHERE Approval_Status = 'Approved'").fetchone()[0] or 0
            dong_tien = thu - chi
            return f"📈 **Dòng tiền thuần toàn trường:** **{dong_tien:,.0f} VNĐ** (Tổng thực thu: {thu:,.0f} đ, Tổng thực chi: {chi:,.0f} đ)."

        elif template_name == "COLLECTION_RATE":
            thu = cursor.execute("SELECT SUM(Amount_Paid) FROM fact_payments WHERE Payment_Status = 'Successful'").fetchone()[0] or 0
            phai_thu = cursor.execute("SELECT SUM(Tuition_Fee - Scholarship_Amount + Late_Fee) FROM fact_tuition_invoices").fetchone()[0] or 1
            rate = (thu / phai_thu) * 100.0
            return f"🎯 **Tỷ lệ thu hồi học phí toàn trường:** đạt **{rate:.2f}%** ({thu:,.0f} đ / {phai_thu:,.0f} đ)."

        elif template_name == "TOTAL_STUDENTS_AND_DEPARTMENTS":
            sv_count = cursor.execute("SELECT COUNT(Student_ID) FROM dim_students;").fetchone()[0] or 0
            dept_count = cursor.execute("SELECT COUNT(Department_ID) FROM dim_departments;").fetchone()[0] or 0
            inv_count = cursor.execute("SELECT COUNT(Invoice_ID) FROM fact_tuition_invoices;").fetchone()[0] or 0
            return f"📊 **Thống kê toàn hệ thống:** Hiện có **{sv_count:,} sinh viên** đang theo học tại **{dept_count} Khoa/Phòng ban** với tổng cộng **{inv_count:,} hóa đơn học phí** đã phát hành."

        elif template_name == "IT_STUDENTS_COUNT":
            row = cursor.execute("""
                SELECT COUNT(s.Student_ID), SUM(CASE WHEN s.Status = 'Active' THEN 1 ELSE 0 END)
                FROM dim_students s
                JOIN dim_departments d ON s.Department_ID = d.Department_ID
                WHERE d.Department_Name LIKE '%Công nghệ thông tin%';
            """).fetchone()
            return f"💻 **Khoa Công nghệ thông tin:** Hiện có tổng cộng **{row[0]:,} sinh viên** (trong đó **{row[1]:,} sinh viên** đang theo học `Active`)."

        elif template_name == "DROPOUT_STUDENTS_COUNT":
            count = cursor.execute("SELECT COUNT(Student_ID) FROM dim_students WHERE Status = 'Dropped Out';").fetchone()[0] or 0
            total_sv = cursor.execute("SELECT COUNT(Student_ID) FROM dim_students;").fetchone()[0] or 1
            return f"🛑 **Số lượng sinh viên thôi học (Dropped Out):** Có **{count:,} sinh viên** đã nghỉ học (chiếm **{(count*100.0/total_sv):.2f}%** tổng số sinh viên toàn trường)."

        elif template_name == "TOP_VENDOR_EXPENSE":
            rows = cursor.execute("""
                SELECT Vendor_Name, SUM(Amount) AS Tong_Tien
                FROM fact_expenses
                WHERE Approval_Status = 'Approved'
                GROUP BY Vendor_Name
                ORDER BY Tong_Tien DESC
                LIMIT 5;
            """).fetchall()
            resp = "🏢 **Top 5 Nhà cung cấp (Vendors) nhận chi phí lớn nhất:**\n"
            for idx, r in enumerate(rows, 1):
                resp += f"{idx}. **{r[0]}**: được giải ngân **{r[1]:,.0f} VNĐ**\n"
            return resp

        return "Không có dữ liệu phù hợp."
    finally:
        conn.close()

class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = "default_session"

class ChatResponse(BaseModel):
    question: str
    answer: str
    status: str = "success"
    source: str = "FAST_PATH"
    routing_time_ms: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

@app.get("/")
def read_root():
    chat_html_path = os.path.join(PROJECT_ROOT, "chat.html")
    if os.path.exists(chat_html_path):
        return FileResponse(chat_html_path)
    return {
        "service": "MRP Financial & Academic Intelligence AI Agent API",
        "version": "2.0.0",
        "status": "Online",
        "fast_path_ready": True
    }

@app.get("/chat-ui")
def get_chat_ui():
    return FileResponse(os.path.join(PROJECT_ROOT, "chat.html"))

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "version": "2.0.0",
        "fast_path_templates": len(fast_router.templates),
        "sqlite_db": os.path.exists(SQLITE_DB_PATH)
    }

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="Câu hỏi không được để trống.")

    # 1. Fast-Path Router (Sub-5ms Execution)
    routed = fast_router.route(req.question)
    if routed:
        answer_text = query_sqlite_fallback(routed["template_name"], routed["params"])
        return ChatResponse(
            question=req.question,
            answer=answer_text,
            status="success",
            source="FAST_PATH_TEMPLATE",
            routing_time_ms=routed["routing_time_ms"],
            metadata={"template": routed["template_name"], "cypher": routed["cypher"]}
        )

    # 2. Fallback to Neo4j Graph Cypher QA Chain if running
    try:
        from graph_qa import get_graph_qa_chain
        qa_chain = get_graph_qa_chain()
        res = qa_chain.invoke({"query": req.question})
        answer = res.get("result", "Không thể tạo câu trả lời.")
        cypher_used = [step["query"] for step in res.get("intermediate_steps", []) if "query" in step]

        return ChatResponse(
            question=req.question,
            answer=answer,
            status="success",
            source="GRAPH_CYPHER_LLM",
            metadata={"cypher": cypher_used[0] if cypher_used else None}
        )
    except Exception as e:
        # Graceful response explaining offline state
        return ChatResponse(
            question=req.question,
            answer=f"Câu hỏi của bạn cần phân tích đồ thị tự do. Lưu ý: dịch vụ Neo4j/Ollama đang ở trạng thái bảo trì hoặc chưa bật ({str(e)}). Vui lòng hỏi các chỉ số quản trị tài chính (công nợ, học phí, top sinh viên, ngân sách) để nhận phản hồi Fast-Path tức thì.",
            status="degraded_fallback",
            source="FALLBACK_ADVISOR"
        )

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting MRP Intelligence Server V2.0 on http://127.0.0.1:8000 ...")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
