import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from rag import FraudRAGAssistant

# 세션별 어시스턴트 저장 (간단한 인메모리 방식)
sessions: dict[str, FraudRAGAssistant] = {}

# 공유 리소스 (벡터 저장소, reranker 등은 한 번만 로드)
assistant_template: FraudRAGAssistant | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """서버 시작 시 RAG 시스템 초기화"""
    global assistant_template
    print("🚀 RAG 시스템 초기화 중...")
    assistant_template = FraudRAGAssistant()
    print("✅ 서버 준비 완료!")
    yield
    print("👋 서버 종료")


app = FastAPI(title="겟백 API", lifespan=lifespan)

# CORS 설정 (프론트엔드에서 접근 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


def get_or_create_session(session_id: str) -> FraudRAGAssistant:
    """세션별 어시스턴트 반환 (없으면 새로 생성, 무거운 리소스는 공유)"""
    if session_id not in sessions:
        # 새 세션은 공유 리소스를 재사용하되, 대화 기록만 독립
        a = FraudRAGAssistant.__new__(FraudRAGAssistant)
        a.counseling_store = assistant_template.counseling_store
        a.counseling_retriever = assistant_template.counseling_retriever
        a.reranker = assistant_template.reranker
        a.final_k = assistant_template.final_k
        a.templates = assistant_template.templates
        a.counseling_prompt = assistant_template.counseling_prompt
        a.form_prompt = assistant_template.form_prompt
        a.llm = assistant_template.llm
        a.counseling_chain = assistant_template.counseling_chain
        a.form_chain = assistant_template.form_chain
        a.chat_history = []
        a.max_history = 10
        a.last_intent = None
        a.last_form_type = None
        sessions[session_id] = a
    return sessions[session_id]


# =====================================================
# REST API (일반 응답)
# =====================================================
@app.post("/api/chat")
async def chat(req: ChatRequest):
    """일반 REST 방식 — 답변을 한 번에 반환"""
    assistant = get_or_create_session(req.session_id)
    answer = await asyncio.to_thread(assistant.ask, req.message)
    return {"answer": answer, "session_id": req.session_id}


# =====================================================
# SSE API (스트리밍 응답)
# =====================================================
@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    """SSE 방식 — 답변을 글자 단위로 스트리밍"""
    assistant = get_or_create_session(req.session_id)

    async def generate():
        # RAG 답변 생성 (동기 함수이므로 스레드에서 실행)
        answer = await asyncio.to_thread(assistant.ask, req.message)

        # 글자 단위로 스트리밍
        for char in answer:
            yield {"data": json.dumps({"token": char}, ensure_ascii=False)}
            await asyncio.sleep(0.02)  # 타이핑 느낌

        # 스트리밍 종료 신호
        yield {"data": json.dumps({"done": True}, ensure_ascii=False)}

    return EventSourceResponse(generate())


# =====================================================
# 세션 관리
# =====================================================
@app.post("/api/chat/reset")
async def reset_chat(req: ChatRequest):
    """대화 기록 초기화"""
    if req.session_id in sessions:
        sessions[req.session_id].clear_history()
    return {"status": "ok", "session_id": req.session_id}


@app.get("/api/health")
async def health():
    """서버 상태 확인"""
    return {"status": "ok", "model": "gpt-4o-mini"}
