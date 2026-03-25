---
name: test-rag
description: RAG 시스템 전체 테스트 실행 및 결과 리포트 생성
---

# RAG 시스템 테스트

다음 순서로 RAG 시스템을 테스트하세요:

## 0. 사전 확인

1. `.env` 파일에 `OPENAI_API_KEY`가 있는지 확인
2. `chroma_db/` 디렉토리가 존재하는지 확인
   - 없으면 사용자에게 `python chunking.py`를 먼저 실행하라고 안내하고 중단

## 1. 벡터 저장소 상태 점검

Python 코드를 실행하여 다음을 확인:
- 벡터 저장소의 총 문서(chunk) 수
- document_type별 문서 수 분포

```python
from chunking import *
from rag import *
vs = load_vectorstore()
collection = vs._collection
print(f"총 문서 수: {collection.count()}")
# metadata에서 document_type 분포 확인
results = collection.get(include=["metadatas"])
from collections import Counter
types = Counter(m.get('document_type', '없음') for m in results['metadatas'])
for t, c in types.most_common():
    print(f"  {t}: {c}개")
```

## 2. 테스트 질문 실행

아래 테스트 질문들을 `FraudRAGAssistant`로 실행하세요. 각 질문마다:
- 답변 내용
- 응답 시간 (time 모듈 사용)
- 검색된 문서의 document_type 목록

```python
import time
from rag import FraudRAGAssistant

assistant = FraudRAGAssistant()

test_cases = [
    {
        "id": "민사루트",
        "question": "중고거래에서 50만원 사기당했는데 돈 돌려받고 싶어요. 어떻게 해야 하나요?",
    },
    {
        "id": "형사루트",
        "question": "사기꾼을 처벌하고 싶어요. 고소는 어떻게 하나요?",
    },
    {
        "id": "증거수집",
        "question": "사기 증거로 뭘 모아야 하나요? 카톡 대화만으로 충분한가요?",
    },
    {
        "id": "멀티턴",
        "question": "그거 비용은 얼마나 드나요?",
        "depends_on": "민사루트 질문 이후 연속으로 실행 (대화 기록 유지)",
    },
    {
        "id": "엣지케이스",
        "question": "3만원짜리 소액인데 고소할 가치가 있나요?",
    },
]
```

각 질문 실행 시 시간을 측정하고, `search_documents()`로 검색된 문서도 확인하세요.

## 3. 검색 품질 점검

각 질문에 대해 `search_documents()`를 별도로 호출하여:
- 검색된 문서 수가 0이면 ⚠️ 경고
- 검색된 문서의 document_type이 질문 주제와 관련 있는지 확인
- reranking 전후 문서 순서 변화가 있는지 확인 (rerank_documents 직접 호출)

## 4. 결과 리포트 생성

`docs/test-results/YYYY-MM-DD.md` 파일로 결과를 정리:

```markdown
# RAG 테스트 결과 — YYYY-MM-DD

## 벡터 저장소 상태
- 총 문서 수: N개
- document_type 분포: ...

## 테스트 결과

### 1. 민사루트
- **질문**: ...
- **응답 시간**: X.Xs
- **검색 문서**: document_type 목록
- **답변 요약**: (답변 첫 2~3문장)
- **판정**: ✅ 정상 / ⚠️ 문제있음

(각 테스트 케이스 반복)

## 요약
- 총 N개 테스트 중 N개 통과
- 평균 응답 시간: X.Xs
- 발견된 문제: (있으면 기술)
```

## 판정 기준

- ✅ 정상: 답변이 질문 주제에 맞고, 검색 문서가 1개 이상이며, 민사/형사 루트를 적절히 구분
- ⚠️ 주의: 답변은 생성되었으나 검색 문서가 주제와 무관하거나, 루트 구분이 불명확
- ❌ 실패: 검색 결과 0개, 에러 발생, 또는 답변이 "정보가 없습니다" 류

모든 출력과 리포트는 한국어로 작성하세요.
