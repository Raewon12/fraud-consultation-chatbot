"""
AI Hub 법률 서식 데이터 전처리 스크립트
- 텍스트 블록 합치기
- 플레이스홀더 정리
- 문서 유형별 구조화된 JSON으로 저장
"""
import json, os, re
from pathlib import Path

INPUT_DIR = '/Users/raewon/Desktop/프로젝트파일/창업동아리프로젝트/data/aihub_legal'
OUTPUT_PATH = '/Users/raewon/Desktop/프로젝트파일/창업동아리프로젝트/data/aihub_legal_processed.json'

# ============================================================
# 플레이스홀더 매핑: (@성명1) → [성명], (@금액) → [금액] 등
# ============================================================
PLACEHOLDER_MAP = {
    '성명': '[성명]', '주소': '[주소]', '전화번호': '[전화번호]',
    '금액': '[금액]', '날짜': '[날짜]', '계좌번호': '[계좌번호]',
    '은행': '[은행]', '은행명': '[은행]', '사건번호': '[사건번호]',
    '식별번호': '[식별번호]', '고유번호': '[고유번호]',
    '생년월일': '[생년월일]', '회사명': '[회사명]', '기관': '[기관]',
    '이메일': '[이메일]', '우편번호': '[우편번호]', '직업': '[직업]',
    '직위': '[직위]', '직책': '[직책]', '나이': '[나이]',
    '비율': '[비율]', '숫자': '[숫자]', '수수료': '[수수료]',
    '물건': '[물건]', '상품': '[상품]', '제품': '[제품]',
    '국가명': '[국가명]', '지역': '[지역]', '지역명': '[지역]',
    '장소': '[장소]', '병원': '[병원]', '웹사이트': '[웹사이트]',
    '사업': '[사업]', '상표': '[상표]', '시간': '[시간]',
    '수량': '[수량]', '판결번호': '[판결번호]', '계약': '[계약]',
}

# 내용이 있는 플레이스홀더 (그대로 남기되 괄호 정리)
CONTENT_PLACEHOLDERS = [
    '구체적 사실관계', '구체적사실관계', '구체적 사실', '구체적사실',
    '구채적사실', '구체적인 사실관계', '구체적 사실 금액',
    '사실 관계', '사실관계',
    '법리 검토', '법리검토', '법리 적용', '법리적용', '관련법리',
    '적용법조', '관련판례',
    '피해 사실', '피해사실', '피해 상황', '피해상황',
    '처벌 촉구', '처벌촉구', '처분촉구', '수사 촉구', '수사특별요청',
    '요구사항', '요청사항', '발송요지', '발송용지',
    '입증 자료', '입증자료', '입증내역', '첨부 자료', '첨부자료',
    '참고자료', '상표입증자료',
    '관련 사건', '관련사건', '괸련사건', '사건명',
    '당사자 지위', '당사자지위',
    '청구취지', '주장 사실',
    '배상액 산정', '방안', '정보내용', '행정기관',
    '관할', '업무', '연구',
]


def clean_placeholder(text):
    """플레이스홀더를 정리된 형태로 변환"""
    # (@성명1), (@주소2) 등 → [성명], [주소]
    def replace_match(m):
        inner = m.group(1).strip()
        # 숫자 제거: 성명1 → 성명, 주소2 → 주소
        base = re.sub(r'\s*\d+$', '', inner).strip()

        # 매핑된 플레이스홀더
        if base in PLACEHOLDER_MAP:
            return PLACEHOLDER_MAP[base]

        # 내용 플레이스홀더 → [해당 내용] 으로
        for cp in CONTENT_PLACEHOLDERS:
            if base == cp:
                return f'[{base}]'

        # 매핑 안 된 것도 [원문] 형태로
        return f'[{base}]'

    result = re.sub(r'\(@([^)]+)\)', replace_match, text)
    return result


def extract_and_clean(data):
    """JSON에서 텍스트 추출 + 플레이스홀더 정리 + 합치기"""
    doc = data.get('document', {})

    # sub_documents에서 텍스트 추출 (sort_order 기준 정렬)
    subs = doc.get('sub_documents', [])
    subs_sorted = sorted(subs, key=lambda x: (x.get('sort_order') or 0))

    text_parts = []
    for sub in subs_sorted:
        for content in sub.get('contents', []):
            t = content.get('text', '')
            if t and t.strip():
                cleaned = clean_placeholder(t.strip())
                text_parts.append(cleaned)

    full_text = '\n'.join(text_parts)

    # 연속 빈 줄 정리
    full_text = re.sub(r'\n{3,}', '\n\n', full_text)
    # 연속 공백 정리
    full_text = re.sub(r'[ \t]{3,}', ' ', full_text)

    return full_text


def get_doc_type_label(fname):
    """파일명에서 문서 유형 한글 라벨 추출"""
    base = fname.rsplit('_', 1)[0]
    type_map = {
        '형사고소장': '형사고소장',
        '형사고발장': '형사고발장',
        '민사소장': '민사소장',
        '내용증명': '내용증명',
        '진정서': '진정서',
        '신청서': '신청서',
        '청구서': '청구서',
        '보정서': '보정서',
        '신고서': '신고서',
        '행정소송소장': '행정소송소장',
        '행정심판청구서': '행정심판청구서',
    }
    return type_map.get(base, base)


def get_category(folder_name):
    """폴더명에서 카테고리 추출"""
    if '내용증명' in folder_name:
        return '내용증명'
    elif '소의개시' in folder_name:
        return '소의개시'
    elif '소의진행' in folder_name:
        return '소의진행'
    elif '민원행정' in folder_name:
        return '민원행정'
    return '기타'


# ============================================================
# 2차 필터링: 전처리 후 내용 기반으로 무관한 문서 제거
# ============================================================

# 무관한 주제 키워드
IRRELEVANT_TOPICS = [
    # 가사
    '이혼', '양육비', '양육권', '상속', '유언', '친권', '위자료', '혼인취소',
    '혼인무효', '입양', '친생자',
    # 부동산/임대차
    '전세금', '임대차', '명도청구', '건물인도', '부동산', '토지', '건축',
    '재건축', '재개발', '등기이전', '소유권이전',
    # 노동
    '임금체불', '퇴직금', '해고', '산업재해', '근로계약', '부당해고',
    # 교통/의료
    '교통사고', '음주운전', '의료사고', '의료과실', '의료법',
    # 병무
    '병무청', '입영', '전문연구요원', '산업기능요원',
    # 형사 (사기 외)
    '성폭력', '성희롱', '폭행', '상해', '살인', '강도', '절도',
    '마약', '도박', '명예훼손', '모욕죄',
    # 지식재산
    '특허', '저작권', '디자인등록',
    # 세금/행정
    '조세', '세무', '관세', '행정처분취소',
]

# 사기/거래 관련 키워드 (이게 있으면 관련 문서)
FRAUD_RELEVANT_KW = [
    '사기', '편취', '기망', '사취', '횡령', '배임',
    '피싱', '보이스피싱',
    '물품대금', '매매대금', '거래대금', '대금반환', '대금청구',
    '환불', '반환청구', '계약금반환',
    '손해배상', '부당이득', '채무불이행',
    '계약해제', '계약해지', '계약취소',
    '배상명령', '지급명령',
]


def is_relevant_for_fraud(text, doc_type):
    """전처리된 텍스트가 중고거래 사기 상담에 관련있는지 판단"""

    # 문서 유형 자체가 무관한 경우
    if doc_type in ('행정소송소장', '행정심판청구서', '신고서', '보정서', '청구서'):
        return False

    # 사기 관련 키워드가 있으면 일단 관련 있음
    has_fraud_kw = any(kw in text for kw in FRAUD_RELEVANT_KW)

    # 무관한 주제 키워드 체크
    found_irrelevant = [kw for kw in IRRELEVANT_TOPICS if kw in text]

    # 무관한 주제가 있고, 사기 관련 키워드가 없으면 제외
    if found_irrelevant and not has_fraud_kw:
        return False

    # 무관한 주제가 2개 이상이면 사기 키워드가 있어도 제외 (주제가 다른 문서)
    if len(found_irrelevant) >= 2:
        return False

    # 사기 관련 키워드가 없는 문서도 제외
    if not has_fraud_kw:
        return False

    return True


# ============================================================
# 실행
# ============================================================
processed = []
stats = {}
excluded_stats = {}

for folder_name in sorted(os.listdir(INPUT_DIR)):
    folder_path = os.path.join(INPUT_DIR, folder_name)
    if not os.path.isdir(folder_path):
        continue

    files = sorted([f for f in os.listdir(folder_path) if f.endswith('.json')])
    category = get_category(folder_name)

    for fname in files:
        fpath = os.path.join(folder_path, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            full_text = extract_and_clean(data)

            # 너무 짧은 문서 제외 (50자 미만)
            if len(full_text.strip()) < 50:
                continue

            doc_type = get_doc_type_label(fname)

            # ======== 2차 필터링: 중고거래 사기와 무관한 문서 제거 ========
            if not is_relevant_for_fraud(full_text, doc_type):
                excluded_stats[doc_type] = excluded_stats.get(doc_type, 0) + 1
                continue

            entry = {
                'id': fname.replace('.json', ''),
                'doc_type': doc_type,
                'category': category,
                'text': full_text,
            }
            processed.append(entry)

            stats[doc_type] = stats.get(doc_type, 0) + 1

        except Exception as e:
            print(f"Error: {fpath}: {e}")

# 저장
with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(processed, f, ensure_ascii=False, indent=2)

print(f"\n========== 전처리 결과 ==========\n")
print(f"  총 {len(processed)}개 문서 전처리 완료\n")
for doc_type, count in sorted(stats.items(), key=lambda x: -x[1]):
    print(f"  {doc_type}: {count}개")
print(f"\n  저장: {OUTPUT_PATH}")

print(f"\n---------- 제외된 문서 ----------\n")
for doc_type, count in sorted(excluded_stats.items(), key=lambda x: -x[1]):
    print(f"  {doc_type}: {count}개 제외")
