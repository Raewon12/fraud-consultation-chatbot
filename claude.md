이 프로젝트는 한국어 사기 상담 RAG 챗봇입니다. 모든 사용자 대면 콘텐츠와 데이터는 별도 지정이 없는 한 한국어로 작성합니다.

## 프로젝트 개요

- 한국어 중고거래 사기 피해 상담 RAG 챗봇 (Python 기반)
- 민사/형사 두 가지 법적 루트를 구분하여 상담

## 핵심 파일

- `chunking.py` — 데이터 로딩, 청킹, Chroma 벡터 저장소 생성
- `rag.py` — RAG 체인, 멀티턴 대화, Cross-Encoder reranking
- `data/` — 사기 사례, 법률 정보, 응급 가이드, AI Hub 법률 서식
- `scripts/` — AI Hub 데이터 필터링/전처리 스크립트

## 기술 스택

- Python 3.x, LangChain, ChromaDB, OpenAI API
- 임베딩: `text-embedding-3-small`
- LLM: `gpt-4o-mini` (temperature=0.1)
- Reranker: `cross-encoder/ms-marco-MiniLM-L-6-v2`

## 코드 규칙

- 수정 후 반드시 `python -c 'import app'`로 검증
- 새 패키지 추가 시 `requirements.txt` 업데이트
- `.env` 파일은 git에 올리지 않음 (API 키 포함)
- 데이터 파일(JSON)은 UTF-8 인코딩, 한국어

## 커뮤니케이션

- '부족하다', '빈약하다' 등은 구현 문제가 아닌 전체 방향/주제에 대한 고민으로 먼저 해석할 것
- 답변은 한국어로, 간결하게
