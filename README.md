# 중고거래 사기 피해 상담 RAG 챗봇

중고거래 사기 피해자를 위한 AI 상담 시스템. 사기 사례, 법률 정보, 응급 대응 가이드, 법률 서식 등을 기반으로 RAG 파이프라인을 구성하여 민사/형사 두 가지 법적 루트에 맞는 실질적인 상담을 제공한다.

## 프로젝트 구조

```
├── chunking.py              # 데이터 로딩 + 청킹 + 벡터 저장소 2개 생성
├── rag.py                   # 의도 분류 + RAG 체인 + 멀티턴 대화 상담
├── requirements.txt
├── .env                     # OpenAI API 키 (git 미추적)
│
├── data/
│   ├── fraud_cases/
│   │   └── cases.json                  # 사기 사례 10건
│   ├── legal_info/
│   │   ├── laws.json                   # 관련 법령 (형법 347조 개정 반영, 특경법 등)
│   │   ├── procedures.json             # 경찰 신고 방법 비교 가이드
│   │   ├── prosecution_strategy.json   # 형사고소 전략 (등기우편 고소장 절차)
│   │   ├── civil_lawsuit_process.json  # 민사소송 절차 (소장~강제집행)
│   │   └── templates/                  # 등기우편 고소장 템플릿
│   ├── emergency_guide/
│   │   ├── immediate_actions.json      # 사기 직후 즉시 행동
│   │   ├── evidence_checklist.json     # 증거 수집 체크리스트
│   │   ├── account_freeze.json         # 계좌 지급정지 안내
│   │   └── report_contacts.json        # 긴급 신고 연락처
│   ├── fraq/
│   │   └── question.json               # FAQ
│   └── aihub_legal_processed.json      # AI Hub 법률 서식 (전처리 완료)
│
├── scripts/
│   ├── filter_aihub_legal.py           # AI Hub 원본 데이터 필터링
│   └── preprocess_aihub_legal.py       # AI Hub 데이터 전처리
│
├── chroma_db_counseling/               # 상담용 벡터 저장소 (git 미추적)
└── chroma_db_form/                     # 서식작성용 벡터 저장소 (git 미추적)
```

## RAG 파이프라인

```
사용자 질문
  ↓
의도 분류 (counseling / form_writing)
  ↓
┌─────────────────────┬──────────────────────┐
│   상담 모드          │   서식작성 모드        │
│   (일반 상담 질문)    │   ("고소장 써줘" 등)   │
│   chroma_db_counseling│  chroma_db_form      │
│   상담 프롬프트       │   서식작성 프롬프트     │
└─────────────────────┴──────────────────────┘
  ↓
쿼리 재작성 (대화 맥락 반영, 대명사·생략 표현 해소)
  ↓
벡터 검색 (similarity, 15개 후보)
  ↓
Cross-Encoder Reranking (5개 선별)
  ↓
컨텍스트 구성 + 프롬프트 조립
  ↓
LLM 답변 생성 (gpt-4o-mini)
```

### 의도 분류 (라우팅)

| 질문 예시 | 의도 | 사용 DB |
|----------|------|---------|
| "사기당했어요 어떻게 해야 하나요?" | counseling | 상담용 (73개) |
| "고소장 작성해줘" | form_writing | 서식작성용 (792개) |
| "고소장 접수하면 어떻게 되나요?" | counseling | 상담용 |

서식 타입 키워드 (고소장, 내용증명 등) + 작성 액션 (써줘, 작성 등) 둘 다 있어야 서식작성 모드로 라우팅.

### 주요 설정

| 항목 | 값 |
|------|-----|
| 임베딩 | OpenAI `text-embedding-3-small` |
| 벡터 저장소 | Chroma (로컬, 상담/서식 2개) |
| 초기 검색 | similarity search, fetch_k=15 |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| 최종 문서 수 | top_k=5 |
| LLM | `gpt-4o-mini`, temperature=0.1 |
| 대화 기록 | 최대 10턴 유지 |

## 청킹 전략

문서 유형에 따라 구조 기반 청킹을 우선 적용하고, 긴 문서에만 텍스트 분할기를 사용한다.

| 문서 유형 | 청킹 방식 | 저장소 |
|----------|----------|--------|
| 사기 사례, 법령, 절차, FAQ, 연락처 | JSON 구조 그대로 1건 = 1 Document | 상담용 |
| 민사소송, 고소 전략, 계좌정지 | 섹션별 분리 | 상담용 |
| 고소장 템플릿 | 1000자 초과 시 텍스트 분할 (chunk_size=600) | 상담용 |
| AI Hub 법률 서식 | 1000자 초과 시 텍스트 분할 (chunk_size=600) | 서식작성용 |

상담용 약 71개 + 서식작성용 약 792개 = 총 약 863개 Document 청크.

## 실행 방법

```bash
# 의존성 설치
pip install -r requirements.txt

# .env 파일에 API 키 설정
OPENAI_API_KEY=sk-...

# 데이터 청킹 및 벡터 저장소 생성 (상담용 + 서식작성용 2개)
python chunking.py

# 상담 시스템 실행
python rag.py
```

## 기술 스택

- Python 3.x
- LangChain (Core, OpenAI, Chroma, Community)
- OpenAI API (임베딩 + 채팅)
- ChromaDB
- sentence-transformers (Cross-Encoder Reranking)
