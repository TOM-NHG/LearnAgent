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

# 3. SLIM & COMPACT CYPHER PROMPT (~350 TOKENS - 10X FASTER ON CPU)
CYPHER_GENERATION_TEMPLATE = """Bạn là Chuyên gia Neo4j viết Cypher cho Quản trị Đại học.
Chỉ trả về DUY NHẤT một câu lệnh Cypher hợp lệ. Không markdown, không giải thích.

SCHEMA & CHIỀU QUAN HỆ BẮT BUỘC:
• (:Department) {{id, name, annual_budget}}
• (:Student) {{id, full_name, status, total_remaining_debt, payment_completion_rate, risk_score}}
• (:Invoice) {{id, total_amount, scholarship_amount, late_fee, total_paid_successful, remaining_balance, status}}
• (:Payment) {{id, payment_method, amount_paid, payment_status}}
• (:Expense) {{id, amount, approval_status}}
• (:Vendor) {{name}}

MŨI TÊN CHUẨN:
- (:Student)-[:BELONGS_TO]->(:Department)
- (:Invoice)-[:BILLED_TO]->(:Student)
- (:Payment)-[:SETTLES]->(:Invoice)
- (:Payment)-[:MADE_BY]->(:Student)
- (:Expense)-[:INCURRED_BY]->(:Department)
- (:Expense)-[:PAID_TO]->(:Vendor)

QUY TẮC SO KHỚP CHUỖI TIẾNG VIỆT:
- Luôn dùng: toLower(d.name) CONTAINS toLower('tên_khoa')
- Học bổng / Miễn giảm: i.scholarship_amount > 0
- Nợ học phí: s.total_remaining_debt > 0 hoặc i.remaining_balance > 0
- Sinh viên đang học: s.status = 'Active'

Câu hỏi: {question}
Cypher:"""

CYPHER_PROMPT = PromptTemplate(
    input_variables=["question"],
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


def execute_graph_query_raw(question: str) -> dict:
    """
    Thực hiện truy vấn Graph tối ưu V3.0:
    1. Kiểm tra Dynamic Semantic Cypher Cache (< 1ms).
    2. Nếu miss cache, gọi LLM với Prompt siêu tinh gọn (~350 tokens thay vì 4000).
    3. Hiệu chỉnh Cypher bằng MRPCypherCorrector.
    4. Thực thi trực tiếp trên Neo4j để lấy danh sách bản ghi thô (records).
    5. Lưu vào Cypher Cache cho các câu hỏi sau.
    """
    import time
    from langchain_core.output_parsers import StrOutputParser
    from cypher_cache import cypher_cache
    
    # 0. Check Semantic Cache first
    t_start = time.perf_counter()
    cached_cypher = cypher_cache.get(question)
    
    if cached_cypher:
        t_exec_start = time.perf_counter()
        records = graph.query(cached_cypher)
        exec_time_ms = (time.perf_counter() - t_exec_start) * 1000
        total_gen_ms = (time.perf_counter() - t_start) * 1000
        return {
            "cypher": cached_cypher,
            "records": records,
            "gen_time_ms": round(total_gen_ms, 2),
            "exec_time_ms": round(exec_time_ms, 2),
            "cached": True
        }

    # 1. Pipeline sinh Cypher qua LLM (Prompt Slimming)
    llm = get_llm()
    corrector_schema = [
        Schema(el["start"], el["type"], el["end"])
        for el in graph.get_structured_schema.get("relationships", [])
    ]
    custom_corrector = MRPCypherCorrector(corrector_schema)
    
    cypher_chain = CYPHER_PROMPT | llm | StrOutputParser()
    
    raw_cypher = cypher_chain.invoke({
        "question": question
    })
    gen_time_ms = (time.perf_counter() - t_start) * 1000
    
    # Làm sạch markdown nếu LLM sinh ```cypher ... ```
    cleaned_cypher = raw_cypher.replace("```cypher", "").replace("```", "").strip()
    
    # 2. Hiệu chỉnh Cypher theo ontology
    final_cypher = custom_corrector(cleaned_cypher)
    
    # 3. Thực thi trực tiếp trên Neo4j
    t_exec_start = time.perf_counter()
    records = graph.query(final_cypher)
    exec_time_ms = (time.perf_counter() - t_exec_start) * 1000
    
    # 4. Save into cache
    if records:
        cypher_cache.put(question, final_cypher)
    
    return {
        "cypher": final_cypher,
        "records": records,
        "gen_time_ms": round(gen_time_ms, 2),
        "exec_time_ms": round(exec_time_ms, 2),
        "cached": False
    }

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

