---
name: wrap-up
description: 오늘 작업 내용을 정리하고 커밋 후 push
disable-model-invocation: true
---

# 오늘 작업 마무리

다음 순서로 진행하세요:

1. `git log --since="today" --oneline`과 `git diff`로 오늘 변경사항 확인
2. 커밋 안 된 변경사항이 있으면 먼저 커밋
3. 오늘 한 작업을 `docs/logs/YYYY-MM-DD.md` 파일로 정리
   - 한 일 (변경된 파일, 추가된 기능, 수정 사항)
   - 내일 할 일 또는 남은 작업 (있으면)
   - 메모 (대화 중 나온 중요한 결정이나 아이디어)
4. 로그 파일 포함하여 커밋
5. push

작업 로그는 한국어로 간결하게 작성하세요.
