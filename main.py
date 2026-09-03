"""
FastAPI Server for MRP Financial & Student AI Agent
Exposes REST API endpoints for chatting with the Graph AI Agent.
Supports local Ollama (Free & Offline) and OpenAI.
"""
import os
import sys
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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

app = FastAPI(
    title="MRP Financial Intelligence AI Agent API",
    description="REST API interface powered by FastAPI, LangChain, Ollama Qwen 2.5, and Neo4j Knowledge Graph.",
    version="1.0.0"
)

# Enable CORS for web dashboards and external apps
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = "default_session"

class ChatResponse(BaseModel):
    question: str
    answer: str
    status: str = "success"
    metadata: Optional[Dict[str, Any]] = None

from fastapi.responses import FileResponse

@app.get("/")
def read_root():
    chat_html_path = os.path.join(PROJECT_ROOT, "chat.html")
    if os.path.exists(chat_html_path):
        return FileResponse(chat_html_path)
    return {
        "service": "MRP Financial & Student AI Agent API",
        "status": "Online",
        "provider": os.getenv("LLM_PROVIDER", "ollama"),
        "model": os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct"),
        "endpoints": {
            "chat": "POST /chat",
            "health": "GET /health",
            "docs": "GET /docs"
        }
    }

@app.get("/chat-ui")
def get_chat_ui():
    return FileResponse(os.path.join(PROJECT_ROOT, "chat.html"))

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "neo4j_uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        "llm_provider": os.getenv("LLM_PROVIDER", "ollama"),
        "model": os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")
    }

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="Câu hỏi không được để trống.")

    try:
        from graph_qa import get_graph_qa_chain
        qa_chain = get_graph_qa_chain()
        res = qa_chain.invoke({"query": req.question})
        answer = res.get("result", "Không thể tạo câu trả lời.")
        
        # Extract intermediate cypher query if available
        cypher_used = [step["query"] for step in res.get("intermediate_steps", []) if "query" in step]

        return ChatResponse(
            question=req.question,
            answer=answer,
            status="success",
            metadata={"cypher": cypher_used[0] if cypher_used else None}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xử lý câu hỏi: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print("Starting FastAPI server on http://127.0.0.1:8000 ...")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
