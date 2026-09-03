"""
AI Agent for MRP Financial & Student Intelligence
Wraps GraphCypherQAChain and direct Cypher tools with AgentExecutor.
Supports local Ollama Qwen 2.5 and OpenAI.
"""
import os
import sys
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import create_tool_calling_agent, AgentExecutor
from graph_qa import get_graph_qa_chain, get_llm, graph

# UTF-8 console output for Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PROJECT_ROOT = os.path.abspath("d:/NHG/AgentofMRP")
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# -------------------------------------------------------------
# 1. DEFINE TOOLS
# -------------------------------------------------------------
@tool
def query_mrp_knowledge_graph(question: str) -> str:
    """
    Truy vấn cơ sở dữ liệu đồ thị Neo4j của trường đại học (MRP) bằng ngôn ngữ tự nhiên.
    Sử dụng tool này để tra cứu thông tin chi tiết về:
    - Danh sách và ngân sách của các Khoa/Phòng ban (:Department).
    - Thông tin sinh viên, chuyên ngành, trạng thái học tập (:Student, :Major).
    - Hóa đơn học phí, học bổng, phí trễ hạn, công nợ còn lại (:Invoice).
    - Các giao dịch nộp tiền học phí (:Payment).
    - Các khoản chi phí hoạt động và nhà cung cấp (:Expense, :Vendor).
    - Lịch sử kiểm soát chất lượng dữ liệu (:DataQualityAudit).
    """
    try:
        qa_chain = get_graph_qa_chain()
        result = qa_chain.invoke({"query": question})
        return result.get("result", "Không tìm thấy thông tin phù hợp.")
    except Exception as e:
        return f"Lỗi truy vấn đồ thị: {str(e)}"

@tool
def execute_direct_cypher_readonly(cypher_query: str) -> str:
    """
    Thực thi trực tiếp câu lệnh Cypher chỉ đọc (READ-ONLY) trên cơ sở dữ liệu Neo4j.
    Chỉ dùng khi cần lấy dữ liệu dạng bảng/danh sách cụ thể với các lệnh MATCH, RETURN.
    Tuyệt đối không chạy các lệnh DELETE, CREATE, SET, DROP.
    """
    forbidden_keywords = ["delete", "detach", "create", "set", "drop", "merge", "remove"]
    query_lower = cypher_query.lower()
    for kw in forbidden_keywords:
        if f" {kw} " in f" {query_lower} ":
            return f"Từ chối thực thi: Lệnh Cypher chứa từ khóa bị cấm '{kw}' để bảo đảm an toàn dữ liệu."
    
    try:
        res = graph.query(cypher_query)
        return str(res[:20]) # Giới hạn 20 dòng để tránh quá tải context
    except Exception as e:
        return f"Lỗi chạy Cypher: {str(e)}"

tools = [query_mrp_knowledge_graph, execute_direct_cypher_readonly]

# -------------------------------------------------------------
# 2. CREATE AGENT
# -------------------------------------------------------------
AGENT_SYSTEM_PROMPT = """Bạn là Trợ lý AI Chuyên gia Quản trị Tài chính & Đào tạo Đại học (MRP AI Agent).
Bạn có quyền truy cập vào Đồ thị Tri thức Neo4j (Knowledge Graph) chứa toàn bộ dữ liệu về:
- Sinh viên, chuyên ngành đào tạo, tình trạng học tập, rủi ro nợ xấu.
- Doanh thu học phí, công nợ còn lại, giao dịch thanh toán.
- Ngân sách và chi phí hoạt động của 20 khoa/phòng ban.

Hướng dẫn trả lời:
1. Luôn sử dụng tool `query_mrp_knowledge_graph` hoặc `execute_direct_cypher_readonly` để lấy số liệu thực tế chính xác trước khi trả lời.
2. Trả lời bằng tiếng Việt lịch sự, rõ ràng, có cấu trúc gạch đầu dòng, format số tiền bằng VNĐ (hoặc tỷ đồng) dễ đọc.
3. Khi phát hiện các dấu hiệu bất thường (như nợ xấu quá hạn cao, chi phí vượt ngân sách, sinh viên có nguy cơ bỏ học), hãy đưa ra nhận xét và khuyến nghị mang tính xây dựng cho nhà quản lý.
"""

def get_mrp_agent_executor():
    llm = get_llm()

    prompt = ChatPromptTemplate.from_messages([
        ("system", AGENT_SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    return agent_executor

if __name__ == "__main__":
    print("=" * 70)
    print("🤖 MRP AI AGENT RUNNER (Chạy với Ollama Qwen 2.5 / Neo4j)")
    print("=" * 70)
    
    try:
        executor = get_mrp_agent_executor()
        test_query = "Khoa nào có ngân sách năm lớn nhất và số tiền là bao nhiêu?"
        print(f"\nUser: {test_query}\n")
        response = executor.invoke({"input": test_query})
        print(f"\nAgent: {response['output']}")
    except Exception as e:
        print(f"❌ Lỗi Agent: {e}")
