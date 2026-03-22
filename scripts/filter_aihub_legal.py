import json, os, shutil
from pathlib import Path

BASE = '/Users/raewon/Desktop/프로젝트파일/창업동아리프로젝트/aihub_raw'
OUT = '/Users/raewon/Desktop/프로젝트파일/창업동아리프로젝트/data/aihub_legal'

# Clean previous output
if os.path.exists(OUT):
    shutil.rmtree(OUT)

# ============================================================
# 1단계: "사기" false positive 처리
# ============================================================
SAGI_FALSE_POSITIVES = [
    '조사기간', '공사기간', '투자기간', '검사기간', '심사기간', '감사기간',
    '인사기록', '감사기록', '조사기록', '조사기일', '검사기일', '심사기일',
    '기사기', '사기업', '사기관', '사기록', '사기능', '사기재',
    '증거조사기', '변론조사기', '현장조사기', '사실조사기',
    '인사기밀', '봉사기', '봉사기관', '역사기', '역사기록',
    '공사기', '투사기', '조사기구', '감사기구',
]

def has_real_sagi(text):
    if '사기' not in text:
        return False
    cleaned = text
    for fp in SAGI_FALSE_POSITIVES:
        cleaned = cleaned.replace(fp, '___')
    return '사기' in cleaned

# ============================================================
# 2단계: 키워드 정의
# ============================================================

# 강한 사기 키워드 — 이것만 있으면 무조건 포함
STRONG_FRAUD_KW = [
    '사기죄', '편취', '기망', '사기행위', '사기범', '사기피해',
    '사취', '보이스피싱', '피싱', '사기미수',
]

# 중고거래/온라인 거래 맥락 키워드
TRADE_CONTEXT_KW = [
    '중고', '직거래', '온라인거래', '인터넷거래', '택배거래',
    '당근마켓', '번개장터', '중고나라', '카카오페이',
    '선입금', '송금', '계좌이체', '물품대금', '거래대금',
    '물품인도', '허위매물', '가품',
]

# 법적 조치 키워드 (사기 맥락과 함께 쓰일 때만 유효)
LEGAL_ACTION_KW = [
    '환불', '반환청구', '대금반환', '대금청구', '계약금반환',
    '손해배상', '부당이득', '채무불이행',
    '계약해제', '계약해지', '계약취소',
    '지급명령', '소액심판', '소액사건',
]

# 사기 맥락 확인용
FRAUD_CONTEXT_KW = [
    '사기', '피해', '기망', '편취', '속', '허위', '거짓',
    '피해자', '가해자', '피의자', '피고소인',
]

# ============================================================
# 4단계: 제외 필터 (강화)
# ============================================================
EXCLUDE_TOPICS = [
    # 가사
    '이혼', '양육비', '상속', '유언', '친권', '위자료청구',
    # 부동산/임대차
    '전세금', '임대차', '보증금반환', '명도청구', '건물인도',
    '부동산', '토지', '건축', '착공', '준공', '재건축', '재개발',
    '공유물분할', '등기이전',
    # 노동
    '임금체불', '퇴직금', '해고', '산업재해', '근로계약',
    # 교통/의료
    '교통사고', '음주운전', '의료사고', '의료과실',
    # 지식재산
    '특허', '상표', '저작권', '디자인등록',
    # 형사 (사기 외)
    '성폭력', '성희롱', '폭행', '상해', '살인', '강도', '절도',
    '마약', '도박', '명예훼손',
    # 기타
    '축산물', '식품위생', '환경', '행정처분취소',
]

# ============================================================
# 텍스트 추출
# ============================================================
def extract_text(data):
    texts = []
    title = data['document'].get('title') or ''
    texts.append(title)
    for field in ['purpose', 'use_case', 'main_category', 'sub_category', 'detail_category']:
        v = data['document'].get(field) or ''
        texts.append(v)
    for sub in data['document'].get('sub_documents', []):
        for content in sub.get('contents', []):
            t = content.get('text') or ''
            texts.append(t)
    return ' '.join(texts)

def get_doc_type(fname):
    """파일명에서 문서 유형 추출 (민사소장_0003.json -> 민사소장)"""
    return fname.rsplit('_', 1)[0]

# ============================================================
# 선별 로직
# ============================================================
def is_relevant(text, fname, folder_name):
    doc_type = get_doc_type(fname)

    # --- 제외 필터 (강화: 1개만 걸려도 제외, 단 강한 사기 키워드 있으면 유지) ---
    has_strong = any(kw in text for kw in STRONG_FRAUD_KW)
    has_exclude = any(kw in text for kw in EXCLUDE_TOPICS)

    if has_exclude and not has_strong and not has_real_sagi(text):
        return False

    # --- 강한 사기 키워드: 무조건 포함 ---
    if has_strong:
        return True

    # --- "사기" 단어가 실제 fraud 의미로 등장 ---
    if has_real_sagi(text):
        return True

    # --- 문서 유형별 전략 ---

    # 형사고소장/고발장: 사기 키워드 없으면 제외 (명예훼손 등 걸러냄)
    if doc_type in ('형사고소장', '형사고발장'):
        return False  # 이미 위에서 사기 키워드로 체크했으므로 여기 오면 무관한 문서

    # 내용증명: 거래 맥락 + 법적 조치가 함께 있어야
    if folder_name == 'TS_내용증명_기타_내용증명':
        has_trade = any(kw in text for kw in TRADE_CONTEXT_KW)
        has_legal = any(kw in text for kw in LEGAL_ACTION_KW)
        has_fraud_ctx = any(kw in text for kw in FRAUD_CONTEXT_KW)
        return has_trade or (has_legal and has_fraud_ctx)

    # 민사소장: 거래 관련 + 사기/피해 맥락이 있어야
    if doc_type == '민사소장':
        has_trade = any(kw in text for kw in TRADE_CONTEXT_KW)
        has_fraud_ctx = any(kw in text for kw in FRAUD_CONTEXT_KW)
        has_legal = any(kw in text for kw in LEGAL_ACTION_KW)
        return has_trade and (has_fraud_ctx or has_legal)

    # 진정서: 사기/피해 맥락 필요
    if doc_type == '진정서':
        has_fraud_ctx = any(kw in text for kw in FRAUD_CONTEXT_KW)
        return has_fraud_ctx

    # 신청서/청구서/보정서: 거래 맥락 + 사기/피해 맥락 둘 다 필요
    if folder_name == 'TS_소의진행_신청_청구관련문서':
        has_trade = any(kw in text for kw in TRADE_CONTEXT_KW)
        has_fraud_ctx = any(kw in text for kw in FRAUD_CONTEXT_KW)
        has_legal = any(kw in text for kw in LEGAL_ACTION_KW)
        return (has_trade and has_fraud_ctx) or (has_legal and has_fraud_ctx and has_trade)

    # 민원행정: 사기 신고만
    if folder_name == 'TS_민원행정_요청_신고관련문서':
        return False  # 강한 키워드/사기 키워드 없으면 제외

    # 행정소송/행정심판: 제외
    if doc_type in ('행정소송소장', '행정심판청구서'):
        return False

    return False

# ============================================================
# 실행
# ============================================================
os.makedirs(OUT, exist_ok=True)

stats = {}
type_stats = {}  # 문서 유형별 통계
total_all = 0
total_selected = 0

for folder_name in sorted(os.listdir(BASE)):
    folder_path = os.path.join(BASE, folder_name)
    if not os.path.isdir(folder_path):
        continue

    files = [f for f in os.listdir(folder_path) if f.endswith('.json')]
    folder_count = len(files)
    selected = 0

    out_folder = os.path.join(OUT, folder_name)
    os.makedirs(out_folder, exist_ok=True)

    for fname in files:
        fpath = os.path.join(folder_path, fname)
        doc_type = get_doc_type(fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            text = extract_text(data)
            if is_relevant(text, fname, folder_name):
                shutil.copy2(fpath, os.path.join(out_folder, fname))
                selected += 1
                type_stats[doc_type] = type_stats.get(doc_type, 0) + 1
        except Exception as e:
            print(f"Error: {fpath}: {e}")

    stats[folder_name] = (selected, folder_count)
    total_all += folder_count
    total_selected += selected

    if selected == 0:
        os.rmdir(out_folder)

print("\n========== 필터링 결과 요약 ==========\n")
for folder_name, (sel, total) in sorted(stats.items()):
    pct = (sel/total*100) if total > 0 else 0
    print(f"  {folder_name}: {sel}/{total} ({pct:.1f}%)")

print(f"\n  전체: {total_selected}/{total_all} ({total_selected/total_all*100:.1f}%)")

print("\n---------- 문서 유형별 선별 수 ----------\n")
for doc_type, count in sorted(type_stats.items(), key=lambda x: -x[1]):
    print(f"  {doc_type}: {count}개")

print(f"\n  저장 위치: {OUT}")
