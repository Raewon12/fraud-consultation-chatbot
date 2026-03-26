import os
import json
import warnings
from dotenv import load_dotenv

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from pydantic import SecretStr
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.messages import HumanMessage, AIMessage
from sentence_transformers import CrossEncoder

warnings.filterwarnings("ignore")
load_dotenv()

_api_key_str = os.getenv("OPENAI_API_KEY")
api_key = SecretStr(_api_key_str) if _api_key_str else None

# =====================================================
# 의도 분류 (상담 vs 서식작성)
# =====================================================
def classify_intent(question: str) -> str:
    """사용자 질문의 의도를 분류: 'form_writing' or 'counseling'"""
    q = question.lower()
    form_types = ["고소장", "고발장", "내용증명", "소장", "신청서", "진정서", "제출명령"]
    action_words = ["작성", "써줘", "써 줘", "만들어", "양식", "서식", "초안", "draft"]

    has_form_type = any(kw in q for kw in form_types)
    has_action = any(kw in q for kw in action_words)

    if has_form_type and has_action:
        return "form_writing"
    return "counseling"


def classify_form_type(question: str) -> str:
    """서식 종류를 세분화하여 분류"""
    q = question.lower()
    if any(kw in q for kw in ["금융거래정보", "계좌추적", "계좌 조회", "예금주"]):
        return "financial_info"
    if any(kw in q for kw in ["사실조회", "신원확인", "전화번호 조회", "통신사 조회"]):
        return "fact_inquiry"
    if any(kw in q for kw in ["내용증명", "통고", "최고"]):
        return "certified_mail"
    if any(kw in q for kw in ["소장", "민사", "손해배상"]):
        return "civil"
    if any(kw in q for kw in ["고소장", "고발장", "형사", "고소"]):
        return "accusation"
    return "unknown"


if not api_key:
    raise ValueError("OPENAI_API_KEY 없음! .env 확인해줘")

# =====================================================
# 1단계: 벡터 저장소 로드
# =====================================================
def load_vectorstore(persist_directory: str = "chroma_db"):
    """
    기존에 생성된 벡터 저장소를 로드합니다.
    
    Args:
        persist_directory: 벡터 DB가 저장된 폴더 경로
        
    Returns:
        Chroma: 로드된 벡터 저장소 객체
    """
    print(f"벡터 저장소 로드 중: {persist_directory}")
    
    # OpenAI 임베딩 초기화 (청킹할 때와 동일한 모델 사용)
    embeddings = OpenAIEmbeddings(
        api_key=api_key,
        model="text-embedding-3-small"
    )
    
    # Chroma 벡터 저장소 로드
    vectorstore = Chroma(
        persist_directory=persist_directory,
        embedding_function=embeddings
    )
    
    print("✅ 벡터 저장소 로드 완료!")
    return vectorstore

# =====================================================
# 2단계: 검색기(Retriever) 설정  
# =====================================================
def setup_retriever(vectorstore, k: int = 5, fetch_k: int = 15):
    """
    벡터 저장소로부터 검색기를 설정합니다.
    넓게 fetch_k개를 가져온 후 reranking으로 k개를 선별합니다.
    """
    print(f"검색기 설정 중 (초기 검색: {fetch_k}개 → reranking 후: {k}개)")

    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": fetch_k}  # 넓게 가져옴
    )

    print("✅ 검색기 설정 완료!")
    return retriever


def setup_reranker(model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
    """Cross-Encoder reranker를 초기화합니다."""
    print(f"Reranker 초기화 중: {model_name}")
    reranker = CrossEncoder(model_name)
    print("✅ Reranker 초기화 완료!")
    return reranker


def rerank_documents(reranker, query: str, docs, top_k: int = 5):
    """검색된 문서들을 cross-encoder로 reranking하여 상위 top_k개를 반환합니다."""
    if not docs:
        return docs

    # (query, document) 쌍 생성
    pairs = [(query, doc.page_content) for doc in docs]

    # cross-encoder로 relevance score 계산
    scores = reranker.predict(pairs)

    # score 기준 정렬 후 상위 top_k개 선택
    scored_docs = sorted(zip(scores, docs), key=lambda x: x[0], reverse=True)
    reranked = [doc for _, doc in scored_docs[:top_k]]

    return reranked

# =====================================================
# 3단계: 프롬프트 템플릿 작성
# =====================================================
def create_prompt_template():
    """
    RAG용 프롬프트 템플릿을 생성합니다.
    대화 기록(chat_history)을 포함하여 멀티턴 대화를 지원합니다.
    """
    print("프롬프트 템플릿 생성 중...")

    prompt = ChatPromptTemplate.from_messages([
        ("system", """당신은 중고거래 사기 피해 전문 상담사입니다.
주어진 컨텍스트와 이전 대화 내용을 바탕으로 사용자의 질문에 정확하고 실용적인 답변을 제공하세요.

**핵심 원칙: 두 가지 법적 루트를 구분하세요**
사기 피해 대처에는 두 가지 루트가 있습니다. 사용자의 목적에 맞는 루트를 안내하세요:

1. 민사소송 루트 (돈 돌려받기가 목적)
   - 법원에 소장 제출 (피고: 성명불상)
   - 사실조회신청서로 사기꾼 신원 특정
   - 판결 → 강제집행으로 환불

2. 형사고소 루트 (사기꾼 처벌이 목적)
   - 경찰서에 고소장 제출 (등기우편 추천)
   - 경찰 수사로 사기꾼 특정
   - 기소 → 벌금/징역 처벌

사용자가 아직 어떤 루트를 원하는지 모르면, "돈을 돌려받고 싶으신 건지, 사기꾼을 처벌하고 싶으신 건지" 먼저 물어보세요.
둘 다 원하면 병행 가능하다고 안내하세요.

**답변 지침:**
1. 구체적이고 실행 가능한 조치를 제시하세요
2. 시급한 경우 우선순위를 명확히 하세요 (증거 수집이 항상 최우선)
3. 비용, 기간, 절차를 물으면 반드시 민사/형사 어떤 루트인지 구분하여 답변하세요
4. 금액별로 현실적인 조언을 하세요 (10만원 이하는 효율이 낮지만 가능하다고 안내)
5. 컨텍스트에 없는 내용은 "제공된 정보로는 확인이 어렵습니다"라고 하세요
6. 이전 대화에서 언급된 내용을 참고하여 일관성 있게 답변하세요
7. 반드시 컨텍스트에 있는 정보만 사용하세요. 컨텍스트에 없는 법률, 절차, 비용을 추측하여 답변하지 마세요.
8. 계좌 지급정지는 중고거래 사기에서 실효성이 매우 낮습니다 (의무 대상 아님, 성공률 5~10%). 적극 추천하지 말고, 사용자가 직접 물어볼 때만 현실적 기대치와 함께 안내하세요.

**참고 컨텍스트:**
{context}"""),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{question}")
    ])

    print("✅ 프롬프트 템플릿 생성 완료!")
    return prompt


def create_form_writing_prompt():
    """서식 작성 보조용 프롬프트 템플릿을 생성합니다. (템플릿 기반)"""
    print("서식작성 프롬프트 템플릿 생성 중...")

    prompt = ChatPromptTemplate.from_messages([
        ("system", """당신은 법률 서식 작성을 도와주는 전문 어시스턴트입니다.
아래 JSON 템플릿의 구조에 따라 법률 서식 초안을 작성해 주세요.

**작성 원칙:**
1. 각 section의 template_text를 그대로 사용하되, [placeholder] 부분만 사용자가 제공한 정보로 교체하세요
2. 사용자가 제공한 날짜, 금액, 이름 등을 절대 임의로 변경하지 마세요
3. 아직 제공되지 않은 required 필드가 있으면 사용자에게 물어보세요 (서식을 먼저 생성하지 말고 필요한 정보부터 요청)
4. 모든 정보가 제공되었으면 완성된 서식을 출력하세요
5. 템플릿의 notes에 있는 안내사항을 서식 끝에 포함하세요
6. submit_info의 제출 방법도 안내하세요
7. "이 초안은 참고용이며, 중요한 경우 법률 전문가 검토를 권장합니다" 문구를 반드시 포함하세요

**이전 대화에서 사용자가 이미 제공한 정보(이름, 금액, 계좌, 사건 경위 등)가 있으면 다시 묻지 말고 바로 활용하세요.**

**참고 템플릿:**
{context}"""),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{question}")
    ])

    print("✅ 서식작성 프롬프트 템플릿 생성 완료!")
    return prompt

# =====================================================
# 4단계: LLM 체인 구성
# =====================================================
def format_docs(docs):
    """검색된 문서들을 읽기 쉬운 컨텍스트 형태로 포맷"""
    formatted = []
    for i, doc in enumerate(docs, 1):
        doc_type = doc.metadata.get('document_type', '정보')
        content = doc.page_content.strip()
        formatted.append(f"[{i}] ({doc_type})\n{content}\n")
    return "\n".join(formatted)


def create_llm():
    """LLM 모델을 초기화합니다."""
    print("LLM 모델 초기화 중...")
    llm = ChatOpenAI(
        api_key=api_key,
        model="gpt-4o-mini",
        temperature=0.1
    )
    print("✅ LLM 초기화 완료!")
    return llm

# =====================================================
# 5단계: 인터페이스 함수
# =====================================================
class FraudRAGAssistant:
    """중고거래 사기 상담 RAG 어시스턴트 (멀티턴 대화 지원)"""

    def __init__(self, counseling_path: str = "chroma_db_counseling",
                 templates_dir: str = "data/legal_info/templates",
                 max_history: int = 10, final_k: int = 5, fetch_k: int = 15):
        """
        RAG 어시스턴트 초기화 (상담용 벡터 저장소 + 서식 템플릿)
        """
        print("=== 중고거래 사기 상담 RAG 시스템 초기화 ===")

        # 상담용 벡터 저장소
        self.counseling_store = load_vectorstore(counseling_path)
        self.counseling_retriever = setup_retriever(self.counseling_store, k=final_k, fetch_k=fetch_k)

        self.reranker = setup_reranker()
        self.final_k = final_k

        # 서식 템플릿 로드 (JSON 파일)
        self.templates = self._load_form_templates(templates_dir)

        # 프롬프트/체인
        self.counseling_prompt = create_prompt_template()
        self.form_prompt = create_form_writing_prompt()
        self.llm = create_llm()
        self.counseling_chain = self.counseling_prompt | self.llm | StrOutputParser()
        self.form_chain = self.form_prompt | self.llm | StrOutputParser()

        # 대화 기록 저장
        self.chat_history = []
        self.max_history = max_history
        self.last_intent = None
        self.last_form_type = None  # 서식 종류도 기억

        print("🎉 RAG 시스템 초기화 완료!\n")

    def _load_form_templates(self, templates_dir: str) -> dict:
        """서식 JSON 템플릿들을 로드합니다."""
        print("서식 템플릿 로드 중...")
        templates = {}
        mapping = {
            "civil_complaint.json": "civil",
            "criminal_accusation.json": "accusation",
            "certified_content.json": "certified_mail",
            "fact_inquiry.json": "fact_inquiry",
            "financial_info_order.json": "financial_info",
        }
        for filename, key in mapping.items():
            path = os.path.join(templates_dir, filename)
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    templates[key] = json.load(f)
                print(f"  ✅ {filename} 로드 완료")
        print(f"✅ 서식 템플릿 {len(templates)}개 로드 완료!")
        return templates

    def _build_search_query(self, question: str) -> str:
        """
        대화 맥락을 반영하여 검색 쿼리를 생성합니다.
        "그거 어떻게 해?", "더 자세히" 같은 대명사/생략 표현을
        이전 대화를 참고하여 구체적인 검색어로 변환합니다.
        """
        if not self.chat_history:
            return question

        # 최근 대화 2턴만 참고하여 검색 쿼리 보강
        recent = self.chat_history[-4:]  # 최근 2턴 (Q+A 2쌍)
        history_text = ""
        for msg in recent:
            if isinstance(msg, HumanMessage):
                history_text += f"사용자: {msg.content}\n"
            elif isinstance(msg, AIMessage):
                # 답변은 앞부분만 (검색 쿼리 보강용이니 전체 불필요)
                history_text += f"상담사: {msg.content[:200]}\n"

        # LLM으로 검색 쿼리 재작성
        rewrite_prompt = ChatPromptTemplate.from_template(
            """아래 대화 맥락을 참고하여, 사용자의 마지막 질문을 벡터 검색에 적합한 독립적인 질문으로 바꿔주세요.
대명사("그거", "아까 그 방법")나 생략된 표현을 구체적으로 풀어서 작성하세요.
재작성한 질문만 출력하세요.

대화 맥락:
{history}

마지막 질문: {question}

재작성된 질문:"""
        )
        rewrite_chain = rewrite_prompt | self.llm | StrOutputParser()
        rewritten = rewrite_chain.invoke({"history": history_text, "question": question})
        return rewritten.strip()

    def ask(self, question: str) -> str:
        """
        질문에 대한 답변을 생성합니다. (의도 분류 → 라우팅 → 답변)
        """
        print(f"💬 질문: {question}")

        try:
            # 1. 의도 분류 (이전 턴이 form_writing이면 후속 질문도 유지)
            intent = classify_intent(question)
            if intent == "counseling" and self.last_intent == "form_writing":
                intent = "form_writing"
                print(f"📌 의도 분류: {intent} (이전 턴 유지)")
            else:
                print(f"📌 의도 분류: {intent}")

            if intent == "form_writing":
                answer = self._handle_form_writing(question)
            else:
                answer = self._handle_counseling(question)

            # 대화 기록에 추가
            self.chat_history.append(HumanMessage(content=question))
            self.chat_history.append(AIMessage(content=answer))
            self.last_intent = intent

            if len(self.chat_history) > self.max_history * 2:
                self.chat_history = self.chat_history[-self.max_history * 2:]

            print("✅ 답변 생성 완료!\n")
            return answer

        except Exception as e:
            error_msg = f"답변 생성 중 오류 발생: {e}"
            print(f"❌ {error_msg}")
            return error_msg

    def _handle_counseling(self, question: str) -> str:
        """상담 질문 처리 (벡터 검색 + reranking)"""
        search_query = self._build_search_query(question)
        docs = self.counseling_retriever.invoke(search_query)
        docs = rerank_documents(self.reranker, search_query, docs, top_k=self.final_k)
        context = format_docs(docs)

        return self.counseling_chain.invoke({
            "context": context,
            "chat_history": self.chat_history,
            "question": question
        })

    def _handle_form_writing(self, question: str) -> str:
        """서식작성 질문 처리 (템플릿 기반)"""
        # 서식 종류 판별 (이전 턴 유지 또는 새로 판별)
        form_type = classify_form_type(question)
        if form_type == "unknown" and self.last_form_type:
            form_type = self.last_form_type
            print(f"📋 서식 종류: {form_type} (이전 턴 유지)")
        else:
            print(f"📋 서식 종류: {form_type}")

        # 서식 종류를 모르면 선택지 제시
        if form_type == "unknown":
            self.last_form_type = None
            return ("어떤 서식을 작성하시겠어요?\n\n"
                    "1. **민사소장** — 돈을 돌려받기 위한 소송 서류\n"
                    "2. **형사고소장** — 사기꾼 처벌을 위한 고소 서류\n"
                    "3. **내용증명** — 환불 요구를 공식 통보하는 서류\n"
                    "4. **사실조회신청서** — 통신사에 전화번호 명의자 조회\n"
                    "5. **금융거래정보제출명령신청서** — 은행에 계좌 예금주 조회\n\n"
                    "원하시는 서식을 말씀해주세요.")

        template = self.templates.get(form_type)
        if not template:
            return "해당 서식 템플릿을 찾을 수 없습니다."

        self.last_form_type = form_type
        context = json.dumps(template, ensure_ascii=False, indent=2)

        return self.form_chain.invoke({
            "context": context,
            "chat_history": self.chat_history,
            "question": question
        })

    def clear_history(self):
        """대화 기록을 초기화합니다."""
        self.chat_history = []
        self.last_intent = None
        self.last_form_type = None
        print("🗑️ 대화 기록이 초기화되었습니다.")

    def search_documents(self, query: str, k: int = 3, intent: str = None):
        """질문과 관련된 문서들을 검색합니다. (디버깅/확인용, 상담용만)"""
        if intent is None:
            intent = classify_intent(query)

        if intent == "form_writing":
            form_type = classify_form_type(query)
            template = self.templates.get(form_type)
            if template:
                print(f"📋 서식 템플릿: {template['template_name']}")
            else:
                print("📋 서식 종류를 특정할 수 없습니다.")
            return []

        print(f"🔍 문서 검색 ({intent}): {query}")
        docs = self.counseling_retriever.invoke(query)

        print(f"📄 검색된 문서 {len(docs)}개:")
        for i, doc in enumerate(docs, 1):
            doc_type = doc.metadata.get('document_type', '정보')
            print(f"  {i}. ({doc_type}) {doc.page_content[:100]}...")

        return docs

# =====================================================
# 메인 실행 함수
# =====================================================
def main():
    """RAG 시스템 테스트 및 대화형 인터페이스"""
    
    try:
        # RAG 어시스턴트 초기화
        assistant = FraudRAGAssistant()
        
        # 테스트 질문들
        test_questions = [
            "중고거래에서 사기를 당했어요. 지금 당장 뭘 해야 하나요?",
            "사기죄 처벌은 어떻게 되나요?",
            "증거로 뭘 모아야 하나요?"
        ]
        
        print("=== 테스트 질문들 ===")
        for i, question in enumerate(test_questions, 1):
            print(f"\n--- 테스트 {i} ---")
            answer = assistant.ask(question)
            print(f"📝 답변:\n{answer}\n")
            print("-" * 50)
        
        # 대화형 모드
        print("\n=== 대화형 모드 시작 ===")
        print("질문을 입력하세요. ('quit' 입력시 종료, '초기화' 입력시 대화 초기화)")
        print("여러 줄 입력: 빈 줄(Enter 두 번)로 전송\n")

        while True:
            lines = []
            first_line = input("💭 질문: ").strip()
            if first_line:
                lines.append(first_line)
            # 추가 줄 입력 (빈 줄이면 전송)
            while True:
                line = input("  ... : ").strip()
                if not line:
                    break
                lines.append(line)
            question = " ".join(lines)

            if question.lower() in ['quit', 'exit', '종료']:
                print("👋 상담을 종료합니다.")
                break

            if question in ['초기화', 'clear', 'reset']:
                assistant.clear_history()
                continue

            if not question:
                print("❓ 질문을 입력해주세요.")
                continue

            answer = assistant.ask(question)
            print(f"\n🤖 답변:\n{answer}")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    main()

