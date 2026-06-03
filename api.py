"""
MODIFIED: 智扫通机器人智能客服 - FastAPI REST API 入口
提供 HTTP API 接口，与 Streamlit 前端互补

启动方式: uvicorn api:app --host 0.0.0.0 --port 8000
"""
import uuid
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent.react_agent import ReactAgent
from utils.database import (
    save_message,
    get_conversation_messages,
    create_conversation,
    list_conversations,
    get_conversation,
    delete_conversation,
)


# MODIFIED: 全局 Agent 实例（懒加载）
_agent: ReactAgent | None = None


def get_agent() -> ReactAgent:
    global _agent
    if _agent is None:
        _agent = ReactAgent()
    return _agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化
    get_agent()
    yield
    # 关闭时清理
    global _agent
    _agent = None


app = FastAPI(
    title="智扫通机器人智能客服 API",
    description="基于 LangChain ReAct Agent + RAG 的智能客服系统 REST API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 配置 - 允许 Streamlit 等前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- 请求/响应模型 ----------

class ChatRequest(BaseModel):
    """聊天请求"""
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    """聊天响应"""
    session_id: str
    reply: str


class HistoryResponse(BaseModel):
    """历史消息响应"""
    session_id: str
    messages: list[dict]


class ConversationItem(BaseModel):
    """会话列表项"""
    session_id: str
    title: str
    message_count: int
    created_at: str
    updated_at: str


# ---------- API 端点 ----------

@app.get("/")
def root():
    """API 健康检查"""
    return {
        "service": "智扫通机器人智能客服",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    发送消息并获取 AI 回复

    - 如果不传 session_id，会自动创建新会话
    - 回复使用流式模式，返回完整文本
    """
    session_id = request.session_id or str(uuid.uuid4())[:8]

    # 确保会话存在
    if not get_conversation(session_id):
        create_conversation(session_id, f"对话 {session_id}")

    # 保存用户消息
    save_message(session_id, "user", request.message)

    # 调用 Agent
    full_response = []
    for chunk in get_agent().execute_stream(request.message):
        if chunk:
            full_response.append(chunk)

    reply = "".join(full_response)

    # 保存 AI 回复
    save_message(session_id, "assistant", reply)

    return ChatResponse(session_id=session_id, reply=reply)


@app.get("/history/{session_id}", response_model=HistoryResponse)
def get_history(session_id: str):
    """获取指定会话的历史消息"""
    messages = get_conversation_messages(session_id)
    return HistoryResponse(session_id=session_id, messages=messages)


@app.get("/conversations", response_model=list[ConversationItem])
def list_all_conversations():
    """列出所有会话"""
    convs = list_conversations()
    return [
        ConversationItem(**c) for c in convs
    ]


@app.delete("/conversations/{session_id}")
def remove_conversation(session_id: str):
    """删除指定会话"""
    success = delete_conversation(session_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在")
    return {"message": f"会话 {session_id} 已删除"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
