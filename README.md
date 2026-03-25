# 중고거래 사기 피해 상담 RAG 챗봇

중고거래 사기 피해자를 위한 AI 상담 시스템. 사기 사례, 법률 정보, 응급 대응 가이드, 법률 서식 등을 기반으로 RAG 파이프라인을 구성하여 민사/형사 두 가지 법적 루트에 맞는 실질적인 상담을 제공한다.

## 프로젝트 구조

```
├── chunking.py              # 데이터 로딩 + 청킹 + 벡터 저장소 생성
├── rag.py                   # RAG 체인 + 멀티턴 대화 상담 인터페이스
├── requirements.txt
├── .env                     # OpenAI API 키 (git 미추적)
│
├── data/
│   ├── fraud_cases/
│   │   └── cases.json                  # 사기 사례 10건
│   ├── legal_info/
│   │   ├── laws.json                   # 관련 법령 (형법 347조, 특경법 등)
│   │   ├── procedures.json             # 고소·고발·소액심판 절차
│   │   ├── prosecution_strategy.json   # 고소 전략 가이드
│   │   ├── civil_lawsuit_process.json  # 민사소송 프로세스
│   │   └── templates/                  # 고소장·고발장·등기우편 서식
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
└── chroma_db/                          # 생성된 Chroma 벡터 저장소 (git 미추적)
```

## RAG 파이프라인

```
사용자 질문
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

### 주요 설정

| 항목 | 값 |
|------|-----|
| 임베딩 | OpenAI `text-embedding-3-small` |
| 벡터 저장소 | Chroma (로컬) |
| 초기 검색 | similarity search, fetch_k=15 |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| 최종 문서 수 | top_k=5 |
| LLM | `gpt-4o-mini`, temperature=0.1 |
| 대화 기록 | 최대 10턴 유지 |

## 청킹 전략

문서 유형에 따라 구조 기반 청킹을 우선 적용하고, 긴 문서에만 텍스트 분할기를 사용한다.

| 문서 유형 | 청킹 방식 |
|----------|----------|
| 사기 사례, 법령, 절차, FAQ, 연락처 | JSON 구조 그대로 1건 = 1 Document |
| 민사소송, 고소 전략, 계좌정지 | 섹션별 분리 |
| 법률 서식, AI Hub 서식 | 1000자 초과 시 RecursiveCharacterTextSplitter (chunk_size=600, overlap=100) |

총 약 600~700개 Document 청크가 벡터화된다.

## 실행 방법

```bash
# 의존성 설치
pip install -r requirements.txt

# .env 파일에 API 키 설정
OPENAI_API_KEY=sk-...

# 데이터 청킹 및 벡터 저장소 생성
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
