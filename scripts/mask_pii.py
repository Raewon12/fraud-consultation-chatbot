"""
소송기록 PDF에서 텍스트 추출 후 개인정보 마스킹.
마스킹된 텍스트만 출력하여 안전하게 활용할 수 있도록 함.

사용법:
    python scripts/mask_pii.py <pdf파일경로> [--output <출력경로>] [--names 이름1,이름2,...]

예시:
    python scripts/mask_pii.py docs/lawsuit/record.pdf
    python scripts/mask_pii.py docs/lawsuit/record.pdf --names 홍길동,김철수
    python scripts/mask_pii.py docs/lawsuit/record.pdf --output docs/lawsuit/record_masked.txt
"""

import re
import sys
import argparse
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    print("pdfplumber가 필요합니다: pip install pdfplumber")
    sys.exit(1)


def extract_text_from_pdf(pdf_path: str) -> str:
    """PDF에서 전체 텍스트 추출."""
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(f"--- 페이지 {i} ---\n{page_text}")
    return "\n\n".join(text_parts)


def mask_names(text: str, names: list[str]) -> str:
    """지정된 실명을 마스킹 처리."""
    masked = text
    for name in names:
        name = name.strip()
        if name:
            masked = masked.replace(name, '[실명]')
    return masked


def mask_case_numbers(text: str) -> str:
    """사건번호의 구체적 숫자를 일반화."""
    # 2025가소311273 → 2025가소XXXXXX
    masked = re.sub(
        r'(\d{4}[가-힣]{1,3})\d{4,8}',
        r'\1XXXXXX',
        text
    )
    return masked


def mask_pii(text: str, names: list[str] | None = None) -> str:
    """개인정보를 마스킹 처리."""
    masked = text

    # 지정된 실명 마스킹 (가장 먼저 처리)
    if names:
        masked = mask_names(masked, names)

    # 사건번호 일반화
    masked = mask_case_numbers(masked)

    # 주민등록번호: 123456-1234567
    masked = re.sub(
        r'\d{6}\s*[-–]\s*[1-4]\d{6}',
        '[주민등록번호]',
        masked
    )

    # 전화번호: 010-1234-5678, 02-123-4567 등
    masked = re.sub(
        r'(0\d{1,2})[-.\s]?(\d{3,4})[-.\s]?(\d{4})',
        '[전화번호]',
        masked
    )

    # 계좌번호: 숫자-숫자-숫자 (10자리 이상)
    masked = re.sub(
        r'\d{2,6}[-]\d{2,6}[-]\d{2,6}(?:[-]\d{1,6})?',
        lambda m: '[계좌번호]' if sum(c.isdigit() for c in m.group()) >= 10 else m.group(),
        masked
    )

    # 이메일
    masked = re.sub(
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        '[이메일]',
        masked
    )

    # 주소: 도로명 주소 패턴 (OO시/도 OO구/군 ... 숫자)
    masked = re.sub(
        r'(?:서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)'
        r'(?:특별시|광역시|특별자치시|도|특별자치도)?'
        r'\s*\S+(?:시|군|구)\s*\S+(?:로|길|동|읍|면)\s*[\d\-]+(?:\s*\S+)?',
        '[주소]',
        masked
    )

    # 카드번호: 4자리-4자리-4자리-4자리
    masked = re.sub(
        r'\d{4}[-\s]\d{4}[-\s]\d{4}[-\s]\d{4}',
        '[카드번호]',
        masked
    )

    # 사업자등록번호: 123-45-67890
    masked = re.sub(
        r'\d{3}-\d{2}-\d{5}',
        '[사업자등록번호]',
        masked
    )

    # 여권번호: M12345678
    masked = re.sub(
        r'[A-Z]\d{8}',
        '[여권번호]',
        masked
    )

    return masked


def main():
    parser = argparse.ArgumentParser(description='소송기록 PDF 개인정보 마스킹')
    parser.add_argument('pdf_path', help='PDF 파일 경로')
    parser.add_argument('--output', '-o', help='출력 파일 경로 (미지정 시 자동 생성)')
    parser.add_argument('--names', '-n', help='마스킹할 실명 목록 (쉼표 구분)', default='')
    args = parser.parse_args()

    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"파일을 찾을 수 없습니다: {pdf_path}")
        sys.exit(1)

    # 텍스트 추출
    print(f"PDF 텍스트 추출 중: {pdf_path}")
    raw_text = extract_text_from_pdf(str(pdf_path))

    if not raw_text.strip():
        print("텍스트를 추출할 수 없습니다. 스캔 PDF일 수 있습니다.")
        print("스캔 PDF는 OCR 처리가 필요합니다 (pytesseract 등).")
        sys.exit(1)

    # 마스킹
    names = [n for n in args.names.split(',') if n.strip()] if args.names else None
    masked_text = mask_pii(raw_text, names=names)

    # 마스킹 통계
    pii_types = ['실명', '주민등록번호', '전화번호', '계좌번호', '이메일', '주소', '카드번호', '사업자등록번호', '여권번호']
    print("\n마스킹 결과:")
    for pii_type in pii_types:
        count = masked_text.count(f'[{pii_type}]')
        if count > 0:
            print(f"  [{pii_type}] × {count}건")

    # 출력
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = pdf_path.with_name(f"{pdf_path.stem}_masked.txt")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(masked_text, encoding='utf-8')
    print(f"\n마스킹 완료: {output_path}")


if __name__ == '__main__':
    main()
