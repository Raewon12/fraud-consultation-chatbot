import os
import warnings
import pickle
import json
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
import re
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain_community.vectorstores.utils import filter_complex_metadata
from dotenv import load_dotenv

# 경고메세지 삭제
warnings.filterwarnings('ignore')
load_dotenv()

# openapi key 확인
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise ValueError('.env확인, key없음')

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size = 600,
    chunk_overlap = 100,
    length_function = len,

)


# =====================================================
# 1. 사기 사례 문서 로딩 (이미 구현됨)
# =====================================================
def load_fraud_cases_documents(path: str):
    """사기 사례 JSON 파일을 로드하여 Document 객체로 변환"""
    with open(path, 'r', encoding='utf-8') as f:
        cases = json.load(f)
    
    docs = []
    for case in cases:
        text = (
            f"사례번호: {case['case_id']}\n"
            f"연도: {case['year']}\n"
            f"플랫폼: {case['platform']}\n"
            f"상품: {case['item']}\n"
            f"피해금액: {case['amount_krw']:,}원\n"
            f"사기유형: {case['fraud_type']}\n"
            f"수법: {case['seller_method']}\n"
            f"태그: {', '.join(case['tags'])}\n"
        )

        # 실제 소송 경험이 있는 사례는 추가 텍스트 생성
        if "lawsuit_summary" in case:
            ls = case["lawsuit_summary"]
            text += f"\n실제 소송 경험:\n"
            text += f"법원: {ls.get('court', '')}\n"
            text += f"사건유형: {ls.get('case_type', '')}\n"
            text += f"결과: {ls.get('result', '')} — {ls.get('result_reason', '')}\n"
            text += f"소요기간: 약 {ls.get('duration_months', '?')}개월\n"
            if "parallel_proceedings" in ls:
                text += f"병행절차: {ls['parallel_proceedings']}\n"
            if "key_lessons" in ls:
                text += "핵심 교훈:\n"
                for lesson in ls["key_lessons"]:
                    text += f"- {lesson}\n"

        metadata = {
            "source": "fraud_cases",
            "filename": os.path.basename(path),
            "case_id": case.get("case_id"),
            "year": case.get("year"),
            "platform": case.get("platform"),
            "fraud_type": case.get("fraud_type"),
            "amount_krw": case.get("amount_krw"),
            "tags": ", ".join(case.get("tags", [])),  # 배열을 문자열로 변환
            "document_type": "fraud_case",
            "has_lawsuit_record": "lawsuit_summary" in case
        }

        docs.append(Document(page_content=text, metadata=metadata))

    return docs

# =====================================================
# 2. 법률 정보 문서 로딩
# =====================================================
def load_legal_documents(path: str):
    """법률 정보 JSON 파일을 로드하여 Document 객체로 변환"""
    with open(path, 'r', encoding='utf-8') as f:
        legal_data = json.load(f)
    
    docs = []
    file_type = os.path.splitext(os.path.basename(path))[0]  # laws, procedures, 등
    
    if file_type == "laws" and "laws" in legal_data:
        # 법령별로 분리
        for law in legal_data["laws"]:
            text = f"""법령명: {law['law_name']}
조항: {law.get('article', '해당없음')}
내용: {law['content']}
처벌: {law.get('punishment', '관련법 참조')}
쉬운설명: {law.get('easy_explanation', law.get('easy_name', ''))}

"""
            if "실제_처벌수준" in law:
                text += "실제 처벌 수준:\n"
                for key, value in law["실제_처벌수준"].items():
                    if key != "note":
                        text += f"- {key}: {value}\n"
                if "note" in law["실제_처벌수준"]:
                    text += f"참고: {law['실제_처벌수준']['note']}\n"
            
            if "amounts" in law:
                text += "\n금액별 처벌:\n"
                for amount, punishment in law["amounts"].items():
                    text += f"- {amount}: {punishment}\n"
            
            if "coverage" in law:
                text += f"\n적용범위:\n"
                if "포함" in law["coverage"]:
                    text += f"포함: {', '.join(law['coverage']['포함'])}\n"
                if "제외" in law["coverage"]:
                    text += f"제외: {', '.join(law['coverage']['제외'])}\n"
                    
            if "requirements" in law:
                text += f"\n구성요건:\n"
                for req in law["requirements"]:
                    text += f"- {req}\n"
            
            if "note" in law:
                text += f"\n참고: {law['note']}\n"
                
            if "important_note" in law:
                text += f"\n중요: {law['important_note']}\n"
            
            text += f"\n출처: {law.get('source', '')}"
            
            metadata = {
                "source": "legal_info",
                "filename": os.path.basename(path),
                "document_type": "law",
                "law_name": law["law_name"],
                "article": law.get("article"),
                "file_type": file_type
            }
            
            docs.append(Document(page_content=text, metadata=metadata))
    
    elif file_type == "procedures" and "procedures" in legal_data:
        # 절차별로 분리
        for procedure in legal_data["procedures"]:
            text = f"""절차명: {procedure['name']}
설명: {procedure['description']}
"""
            if "steps" in procedure:
                text += f"\n단계:\n"
                for step in procedure["steps"]:
                    text += f"{step['step']}. {step['action']}\n"
                    if "details" in step:
                        if isinstance(step["details"], list):
                            for detail in step["details"]:
                                text += f"   - {detail}\n"
                        else:
                            text += f"   {step['details']}\n"
                    if "why" in step:
                        text += f"   (이유: {step['why']})\n"
                    text += "\n"
            
            metadata = {
                "source": "legal_info", 
                "filename": os.path.basename(path),
                "document_type": "procedure",
                "procedure_name": procedure["name"],
                "file_type": file_type
            }
            
            docs.append(Document(page_content=text, metadata=metadata))
            
    elif file_type == "civil_lawsuit_process":
        # 민사소송 루트: 섹션별로 분리
        base_metadata = {
            "source": "legal_info",
            "filename": os.path.basename(path),
            "file_type": file_type
        }

        # 1) 개요: 왜 민사소송인가
        why = legal_data.get("why_civil_lawsuit", {})
        text_overview = f"""민사소송 루트 - 개요

{legal_data.get('title', '')}
{legal_data.get('description', '')}

형사 고소의 한계:
"""
        for item in why.get("형사_고소의_한계", []):
            text_overview += f"- {item}\n"
        text_overview += "\n민사 소송의 장점:\n"
        for item in why.get("민사_소송의_장점", []):
            text_overview += f"- {item}\n"

        docs.append(Document(
            page_content=text_overview,
            metadata={**base_metadata, "document_type": "civil_lawsuit_overview"}
        ))

        # 2) 각 단계별로 분리
        process = legal_data.get("complete_process", {})
        for key in sorted(process.keys()):
            step = process[key]
            step_num = step.get("순서", key)
            action = step.get("action", "")

            text_step = f"민사소송 - {key}: {action}\n"
            if "where" in step:
                text_step += f"장소: {step['where']}\n"
            if "when" in step:
                text_step += f"시기: {step['when']}\n"
            if "duration" in step:
                text_step += f"소요시간: {step['duration']}\n"
            if "purpose" in step:
                text_step += f"목적: {step['purpose']}\n"
            if "what_happens" in step:
                text_step += f"진행: {step['what_happens']}\n"

            skip_keys = {"순서", "action", "where", "when", "duration", "purpose", "what_happens"}
            for field_key, field_val in step.items():
                if field_key in skip_keys:
                    continue
                if isinstance(field_val, str):
                    text_step += f"\n{field_key}: {field_val}\n"
                elif isinstance(field_val, list):
                    text_step += f"\n{field_key}:\n"
                    for item in field_val:
                        text_step += f"- {item}\n"
                elif isinstance(field_val, dict):
                    text_step += f"\n{field_key}:\n"
                    for k, v in field_val.items():
                        if isinstance(v, list):
                            text_step += f"  {k}:\n"
                            for item in v:
                                text_step += f"    - {item}\n"
                        elif isinstance(v, dict):
                            text_step += f"  {k}:\n"
                            for kk, vv in v.items():
                                text_step += f"    {kk}: {vv}\n"
                        else:
                            text_step += f"  {k}: {v}\n"

            docs.append(Document(
                page_content=text_step,
                metadata={**base_metadata, "document_type": "civil_lawsuit_step",
                           "step": str(step_num), "step_action": action}
            ))

        # 3) 형사 고소와 비교
        comparison = legal_data.get("형사_고소와_비교", {})
        if comparison:
            text_compare = "민사소송 vs 형사고소 비교\n\n"
            for route, details in comparison.items():
                if isinstance(details, dict):
                    text_compare += f"[{route}]\n"
                    for k, v in details.items():
                        text_compare += f"  {k}: {v}\n"
                    text_compare += "\n"
                else:
                    text_compare += f"추천: {details}\n"

            docs.append(Document(
                page_content=text_compare,
                metadata={**base_metadata, "document_type": "civil_vs_criminal_comparison"}
            ))

        # 4) 타임라인
        timeline = legal_data.get("전체_타임라인", {})
        if timeline:
            text_timeline = "민사소송 전체 타임라인\n\n"
            for day, action in timeline.items():
                text_timeline += f"{day}: {action}\n"

            docs.append(Document(
                page_content=text_timeline,
                metadata={**base_metadata, "document_type": "civil_lawsuit_timeline"}
            ))

        # 5) 비용 총정리
        cost = legal_data.get("비용_총정리", {})
        if cost:
            text_cost = "민사소송 비용 총정리\n\n"
            for k, v in cost.items():
                text_cost += f"{k}: {v}\n"

            docs.append(Document(
                page_content=text_cost,
                metadata={**base_metadata, "document_type": "civil_lawsuit_cost"}
            ))

        # 6) 주의사항
        warnings_list = legal_data.get("주의사항", [])
        if warnings_list:
            text_warnings = "민사소송 주의사항\n\n"
            for w in warnings_list:
                text_warnings += f"- {w}\n"

            docs.append(Document(
                page_content=text_warnings,
                metadata={**base_metadata, "document_type": "civil_lawsuit_warnings"}
            ))

    elif file_type == "prosecution_strategy":
        # 고소 전략: 섹션별로 분리
        base_metadata = {
            "source": "legal_info",
            "filename": os.path.basename(path),
            "file_type": file_type
        }

        # 1) 개요 & 전략 이유
        overview = legal_data.get("overview", {})
        why = legal_data.get("why_this_strategy", {})
        text_overview = f"""사기꾼 참교육 완전 가이드 - 개요

목적: {overview.get('목적', '')}
대상: {overview.get('대상', '')}
소요기간: {overview.get('소요기간', '')}
비용: {overview.get('비용', '')}
난이도: {overview.get('난이도', '')}
"""
        success = overview.get("성공률", {})
        if success:
            text_overview += f"성공률 - 처벌: {success.get('처벌', '')}, 환불: {success.get('환불', '')}\n"

        problems = why.get("일반_신고의_문제점", {})
        if problems:
            text_overview += "\n일반 신고의 문제점:\n"
            for k, v in problems.items():
                text_overview += f"- {k}: {v}\n"

        advantages = why.get("등기우편_고소장의_장점", {})
        if advantages:
            text_overview += "\n등기우편 고소장의 장점:\n"
            for k, v in advantages.items():
                text_overview += f"- {k}: {v}\n"

        docs.append(Document(
            page_content=text_overview,
            metadata={**base_metadata, "document_type": "prosecution_overview"}
        ))

        # 2) 각 단계별로 분리 (step_1 ~ step_9)
        process = legal_data.get("complete_process", {})
        for key in sorted(process.keys()):
            step = process[key]
            step_num = step.get("순서", key)
            action = step.get("action", step.get("choice", ""))

            text_step = f"""고소 전략 - {key}: {action}\n"""
            if "duration" in step:
                text_step += f"소요시간: {step['duration']}\n"
            if "when" in step:
                text_step += f"시기: {step['when']}\n"
            if "why" in step:
                text_step += f"이유: {step['why']}\n"
            if "cost" in step:
                text_step += f"비용: {step['cost']}\n"
            if "priority" in step:
                text_step += f"우선순위: {step['priority']}\n"
            if "choice" in step:
                text_step += f"선택: {step['choice']}\n"

            # 나머지 주요 필드들을 텍스트로 변환
            skip_keys = {"순서", "action", "choice", "duration", "when", "why", "cost", "priority"}
            for field_key, field_val in step.items():
                if field_key in skip_keys:
                    continue
                if isinstance(field_val, str):
                    text_step += f"\n{field_key}: {field_val}\n"
                elif isinstance(field_val, list):
                    text_step += f"\n{field_key}:\n"
                    for item in field_val:
                        text_step += f"- {item}\n"
                elif isinstance(field_val, dict):
                    text_step += f"\n{field_key}:\n"
                    for k, v in field_val.items():
                        if isinstance(v, list):
                            text_step += f"  {k}:\n"
                            for item in v:
                                text_step += f"    - {item}\n"
                        elif isinstance(v, dict):
                            text_step += f"  {k}:\n"
                            for kk, vv in v.items():
                                text_step += f"    {kk}: {vv}\n"
                        else:
                            text_step += f"  {k}: {v}\n"

            docs.append(Document(
                page_content=text_step,
                metadata={**base_metadata, "document_type": "prosecution_step",
                           "step": str(step_num), "step_action": action}
            ))

        # 3) 금액별 전략
        amount_strategies = legal_data.get("금액별_전략", {})
        for amount_range, strategy in amount_strategies.items():
            text_amount = f"""금액별 고소 전략: {amount_range}\n\n권장: {strategy.get('권장', '')}\n"""
            if "이유" in strategy:
                text_amount += f"이유:\n"
                for reason in strategy["이유"]:
                    text_amount += f"- {reason}\n"
            if "대안" in strategy:
                text_amount += f"대안:\n"
                for alt in strategy["대안"]:
                    text_amount += f"- {alt}\n"
            if "전략" in strategy:
                text_amount += f"전략: {strategy['전략']}\n"
            if "진행_방법" in strategy:
                text_amount += f"\n진행 방법:\n"
                for k, v in strategy["진행_방법"].items():
                    text_amount += f"  {k}: {v}\n"
            if "기대_효과" in strategy:
                text_amount += f"\n기대 효과:\n"
                for k, v in strategy["기대_효과"].items():
                    text_amount += f"  {k}: {v}\n"
            if "고려사항" in strategy:
                text_amount += f"\n고려사항:\n"
                for k, v in strategy["고려사항"].items():
                    text_amount += f"  {k}: {v}\n"

            docs.append(Document(
                page_content=text_amount,
                metadata={**base_metadata, "document_type": "prosecution_amount_strategy",
                           "amount_range": amount_range}
            ))

        # 4) 핵심 팁
        tips = legal_data.get("핵심_팁", {})
        if tips:
            text_tips = "고소 전략 - 핵심 팁\n\n"
            for tip_name, tip_data in tips.items():
                text_tips += f"[{tip_name}]\n"
                for k, v in tip_data.items():
                    text_tips += f"  {k}: {v}\n"
                text_tips += "\n"

            docs.append(Document(
                page_content=text_tips,
                metadata={**base_metadata, "document_type": "prosecution_tips"}
            ))

        # 5) 주의사항
        warnings = legal_data.get("주의사항", {})
        if warnings:
            text_warnings = "고소 전략 - 주의사항\n\n"
            for warn_name, warn_data in warnings.items():
                text_warnings += f"[{warn_name}]\n"
                for k, v in warn_data.items():
                    if isinstance(v, list):
                        text_warnings += f"  {k}:\n"
                        for item in v:
                            text_warnings += f"    - {item}\n"
                    else:
                        text_warnings += f"  {k}: {v}\n"
                text_warnings += "\n"

            docs.append(Document(
                page_content=text_warnings,
                metadata={**base_metadata, "document_type": "prosecution_warnings"}
            ))

        # 6) 실전 타임라인 예시
        timelines = legal_data.get("실전_타임라인_예시", {})
        for case_name, timeline in timelines.items():
            text_timeline = f"실전 타임라인: {case_name}\n\n"
            for day, action in timeline.items():
                text_timeline += f"{day}: {action}\n"

            docs.append(Document(
                page_content=text_timeline,
                metadata={**base_metadata, "document_type": "prosecution_timeline",
                           "case_name": case_name}
            ))
    
    return docs

# =====================================================
# 3. 응급 가이드 문서 로딩  
# =====================================================
def load_emergency_guide_documents(path: str):
    """응급 가이드 JSON 파일을 로드하여 Document 객체로 변환"""
    with open(path, 'r', encoding='utf-8') as f:
        guide_data = json.load(f)
    
    docs = []
    file_type = os.path.splitext(os.path.basename(path))[0]
    
    if file_type == "immediate_actions" and "immediate_actions" in guide_data:
        # 각 액션별로 분리
        for action in guide_data["immediate_actions"]:
            text = f"""단계 {action['step']}: {action['action']}

이유: {action.get('why', '')}
시간제한: {action.get('time_limit', '')}
"""
            if "details" in action:
                text += f"\n세부사항:\n"
                if isinstance(action["details"], list):
                    for detail in action["details"]:
                        text += f"- {detail}\n"
                else:
                    text += f"{action['details']}\n"
            
            if "warning" in action:
                text += f"\n⚠️ 주의: {action['warning']}\n"
            
            if "note" in action:
                text += f"\n📝 참고: {action['note']}\n"
                
            if "detailed_guide" in action:
                text += f"\n상세가이드: {action['detailed_guide']}\n"
            
            metadata = {
                "source": "emergency_guide",
                "filename": os.path.basename(path),
                "document_type": "immediate_action",
                "step": action["step"],
                "action": action["action"],
                "file_type": file_type
            }
            
            docs.append(Document(page_content=text, metadata=metadata))
    
    elif file_type == "evidence_checklist" and "evidence_types" in guide_data:
        # 증거 유형별로 분리
        for evidence_type in guide_data["evidence_types"]:
            text = f"""증거 유형: {evidence_type['category']}
중요도: {evidence_type['importance']}

항목들:
"""
            for item in evidence_type["items"]:
                text += f"\n• {item['item']}\n"
                text += f"  설명: {item['description']}\n"
                if "how_to_get" in item:
                    text += f"  수집방법: {item['how_to_get']}\n"
                if "priority" in item:
                    text += f"  우선순위: {item['priority']}\n"
            
            metadata = {
                "source": "emergency_guide",
                "filename": os.path.basename(path),
                "document_type": "evidence_checklist", 
                "category": evidence_type["category"],
                "importance": evidence_type["importance"],
                "file_type": file_type
            }
            
            docs.append(Document(page_content=text, metadata=metadata))
    
    elif file_type == "account_freeze":
        # 계좌 지급정지: 섹션별로 분리

        # 1) 중요 경고 & 현실 체크
        warning = guide_data.get("important_warning", {})
        reality = guide_data.get("reality_check", {})
        text_warning = f"""계좌 지급정지 - 중요 경고

{warning.get('critical', '')}
현실: {', '.join(warning.get('reality', []))}
법적 근거: {warning.get('legal_basis', '')}

흔한 오해: {reality.get('common_myth', '')}
진실: {reality.get('truth', '')}
실제 효과: {reality.get('what_actually_stops', '')}
"""
        docs.append(Document(
            page_content=text_warning,
            metadata={"source": "emergency_guide", "filename": os.path.basename(path),
                       "document_type": "account_freeze_warning", "file_type": file_type}
        ))

        # 2) 신청 방법 (step_1: 전화 신청)
        how_to = guide_data.get("how_to_apply", {})
        step1 = how_to.get("step_1", {})
        text_step1 = f"""계좌 지급정지 - 신청 방법 (전화)

행동: {step1.get('action', '')}
"""
        for contact in step1.get("contacts", []):
            text_step1 += f"\n연락처: {contact.get('name', '')} ({contact.get('phone', '')})"
            if "available" in contact:
                text_step1 += f" - {contact['available']}"
            if "what_to_say" in contact:
                text_step1 += f"\n  말할 내용: {contact['what_to_say']}"
            if "협조_은행" in contact:
                text_step1 += f"\n  협조 은행: {', '.join(contact['협조_은행'])}"
            if "거절_가능" in contact:
                text_step1 += f"\n  거절 가능: {contact['거절_가능']}"

        text_step1 += f"\n\n준비물: {', '.join(step1.get('required_info', []))}"

        realistic = how_to.get("realistic_expectation", {})
        if realistic:
            text_step1 += f"\n\n성공률: {realistic.get('success_rate', '')}"
            text_step1 += f"\n협조 은행: {', '.join(realistic.get('cooperating_banks', []))}"
            text_step1 += f"\n대부분 은행: {realistic.get('most_banks', '')}"

        docs.append(Document(
            page_content=text_step1,
            metadata={"source": "emergency_guide", "filename": os.path.basename(path),
                       "document_type": "account_freeze_how_to", "file_type": file_type}
        ))

        # 3) 은행 방문 (step_3)
        step3 = how_to.get("step_3", {})
        if step3:
            text_step3 = f"""계좌 지급정지 - 은행 방문 서류 제출

행동: {step3.get('action', '')}
기한: {step3.get('when', '')}
장소: {step3.get('where', '')}
필요 서류: {', '.join(step3.get('documents', []))}
"""
            docs.append(Document(
                page_content=text_step3,
                metadata={"source": "emergency_guide", "filename": os.path.basename(path),
                           "document_type": "account_freeze_documents", "file_type": file_type}
            ))

        # 4) 환불 가능성
        refund = guide_data.get("refund_possibility", {})
        if refund:
            refund_reality = refund.get("현실", {})
            text_refund = f"""계좌 지급정지 - 환불 가능성

조건: {refund.get('조건', '')}
절차: {' → '.join(refund.get('절차', []))}
중고거래 현실: {refund_reality.get('중고거래', '')}
환불 가능성: {refund_reality.get('환불_가능성', '')}
여러 피해자: {refund.get('multiple_victims', '')}
"""
            docs.append(Document(
                page_content=text_refund,
                metadata={"source": "emergency_guide", "filename": os.path.basename(path),
                           "document_type": "account_freeze_refund", "file_type": file_type}
            ))

        # 5) 주의사항
        warnings_list = guide_data.get("warnings", [])
        if warnings_list:
            text_warnings = "계좌 지급정지 - 주의사항\n\n"
            for w in warnings_list:
                text_warnings += f"- {w}\n"
            docs.append(Document(
                page_content=text_warnings,
                metadata={"source": "emergency_guide", "filename": os.path.basename(path),
                           "document_type": "account_freeze_warnings", "file_type": file_type}
            ))

    elif file_type == "report_contacts":
        # 신고 연락처: 각 연락처별로 분리
        for contact in guide_data.get("emergency_contacts", []):
            text = f"""긴급 신고 연락처: {contact['name']}

전화번호: {contact.get('phone', '')}
용도: {contact.get('what', '')}
시기: {contact.get('when', '')}
"""
            if "online" in contact:
                text += f"온라인: {contact['online']}\n"
            if "note" in contact:
                text += f"참고: {contact['note']}\n"

            docs.append(Document(
                page_content=text,
                metadata={"source": "emergency_guide", "filename": os.path.basename(path),
                           "document_type": "emergency_contact", "contact_name": contact["name"],
                           "file_type": file_type}
            ))

    else:
        # 기타 응급 가이드 파일들은 전체를 하나의 문서로
        text = f"""제목: {guide_data.get('title', '')}
우선순위: {guide_data.get('priority', '')}
사용시기: {guide_data.get('when_to_use', '')}

내용: {json.dumps(guide_data, ensure_ascii=False, indent=2)}
"""

        metadata = {
            "source": "emergency_guide",
            "filename": os.path.basename(path),
            "document_type": file_type,
            "file_type": file_type
        }

        docs.append(Document(page_content=text, metadata=metadata))
    
    return docs

# =====================================================
# 4. FAQ 문서 로딩
# =====================================================
def load_faq_documents(path: str):
    """FAQ JSON 파일을 로드하여 Document 객체로 변환"""
    with open(path, 'r', encoding='utf-8') as f:
        faq_data = json.load(f)

    docs = []
    for entry in faq_data:
        faq = entry.get("자주_묻는_질문", {})
        for key, qa in faq.items():
            text = f"""자주 묻는 질문: {qa['질문']}

답변: {qa['답변']}
"""
            metadata = {
                "source": "faq",
                "filename": os.path.basename(path),
                "document_type": "faq",
                "question_id": key
            }
            docs.append(Document(page_content=text, metadata=metadata))

    return docs

# =====================================================
# 5. 실무 지식 문서 로딩
# =====================================================
def load_practical_insights(path: str):
    """실제 소송기록에서 추출한 실무 지식 JSON을 Document로 변환"""
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    docs = []
    for insight in data.get("practical_insights", []):
        text = f"""실무 지식: {insight['title']}
카테고리: {insight['category']}

{insight['content']}

실무 팁: {insight['practical_tip']}

관련 검색어: {', '.join(insight.get('related_keywords', []))}
"""
        metadata = {
            "source": "practical_insights",
            "filename": os.path.basename(path),
            "document_type": "practical_insight",
            "insight_id": insight["insight_id"],
            "category": insight["category"],
        }
        docs.append(Document(page_content=text, metadata=metadata))
    return docs


# =====================================================
# 6. 법률 서식 템플릿 문서 로딩
# =====================================================
def load_template_documents(path: str):
    """법률 서식 템플릿 텍스트 파일을 로드하여 Document 객체로 변환"""
    docs = []
    
    if path.endswith('.txt'):
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 긴 템플릿은 의미있는 섹션별로 분할
        template_name = os.path.splitext(os.path.basename(path))[0]
        
        if len(content) > 1000:  # 긴 템플릿의 경우 분할
            chunks = text_splitter.split_text(content)
            for i, chunk in enumerate(chunks):
                metadata = {
                    "source": "legal_templates",
                    "filename": os.path.basename(path),
                    "document_type": "template",
                    "template_name": template_name,
                    "chunk_number": i + 1,
                    "total_chunks": len(chunks)
                }
                docs.append(Document(page_content=chunk, metadata=metadata))
        else:
            # 짧은 템플릿은 통째로
            metadata = {
                "source": "legal_templates",
                "filename": os.path.basename(path),
                "document_type": "template", 
                "template_name": template_name
            }
            docs.append(Document(page_content=content, metadata=metadata))
    
    return docs

# =====================================================
# 7. 전체 데이터 로딩 및 처리 파이프라인
# =====================================================
def load_all_documents(data_dir: str = "data"):
    """모든 데이터를 로드하여 Document 객체 리스트로 반환"""
    all_docs = []
    
    print("데이터 로딩 시작...")
    
    # 1. 사기 사례 로딩
    fraud_cases_path = os.path.join(data_dir, "fraud_cases", "cases.json")
    if os.path.exists(fraud_cases_path):
        print(f"사기 사례 로딩: {fraud_cases_path}")
        all_docs.extend(load_fraud_cases_documents(fraud_cases_path))
    
    # 2. 법률 정보 로딩
    legal_files = ["laws.json", "procedures.json", "prosecution_strategy.json", "civil_lawsuit_process.json"]
    for legal_file in legal_files:
        legal_path = os.path.join(data_dir, "legal_info", legal_file)
        if os.path.exists(legal_path):
            print(f"법률 정보 로딩: {legal_path}")
            all_docs.extend(load_legal_documents(legal_path))
    
    # 3. 응급 가이드 로딩
    emergency_dir = os.path.join(data_dir, "emergency_guide")
    if os.path.exists(emergency_dir):
        for filename in os.listdir(emergency_dir):
            if filename.endswith('.json'):
                emergency_path = os.path.join(emergency_dir, filename)
                print(f"응급 가이드 로딩: {emergency_path}")
                all_docs.extend(load_emergency_guide_documents(emergency_path))
    
    # 4. FAQ 로딩
    faq_dir = os.path.join(data_dir, "fraq")
    if os.path.exists(faq_dir):
        for filename in os.listdir(faq_dir):
            if filename.endswith('.json'):
                faq_path = os.path.join(faq_dir, filename)
                print(f"FAQ 로딩: {faq_path}")
                all_docs.extend(load_faq_documents(faq_path))

    # 5. 실무 지식 로딩
    insights_path = os.path.join(data_dir, "legal_info", "practical_insights.json")
    if os.path.exists(insights_path):
        print(f"실무 지식 로딩: {insights_path}")
        all_docs.extend(load_practical_insights(insights_path))

    # 6. 법률 서식 템플릿 로딩
    templates_dir = os.path.join(data_dir, "legal_info", "templates")
    if os.path.exists(templates_dir):
        for filename in os.listdir(templates_dir):
            if filename.endswith('.txt'):
                template_path = os.path.join(templates_dir, filename)
                print(f"템플릿 로딩: {template_path}")
                all_docs.extend(load_template_documents(template_path))

    print(f"\n총 {len(all_docs)}개의 문서 청크가 생성되었습니다!")
    return all_docs

def create_vector_store(docs, persist_directory: str = "chroma_db"):
    """Document 리스트로부터 Chroma 벡터 저장소 생성"""
    print("벡터 저장소 생성 중...")
    
    # 복잡한 메타데이터 필터링
    filtered_docs = filter_complex_metadata(docs)
    
    # OpenAI 임베딩 초기화
    embeddings = OpenAIEmbeddings(
        openai_api_key=api_key,
        model="text-embedding-3-small"
    )
    
    # Chroma 벡터 저장소 생성
    vectorstore = Chroma.from_documents(
        documents=filtered_docs,
        embedding=embeddings,
        persist_directory=persist_directory
    )
    
    print(f"벡터 저장소가 '{persist_directory}'에 저장되었습니다!")
    return vectorstore

def load_vector_store(persist_directory: str = "chroma_db"):
    """기존 벡터 저장소 로드"""
    print("기존 벡터 저장소 로드 중...")
    
    embeddings = OpenAIEmbeddings(
        openai_api_key=api_key,
        model="text-embedding-3-small" 
    )
    
    vectorstore = Chroma(
        persist_directory=persist_directory,
        embedding_function=embeddings
    )
    
    print("벡터 저장소 로드 완료!")
    return vectorstore

def main():
    """메인 실행 함수 — 상담용 벡터 저장소 생성"""
    try:
        # 모든 문서 로딩
        documents = load_all_documents()

        print(f"\n상담용 문서: {len(documents)}개")

        # 문서 타입별 통계
        doc_types = {}
        for doc in documents:
            doc_type = doc.metadata.get('document_type', 'unknown')
            doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
        print("\n문서 타입별 통계:")
        for doc_type, count in sorted(doc_types.items(), key=lambda x: -x[1]):
            print(f"  - {doc_type}: {count}개")

        # 벡터 저장소 생성 (상담용만)
        vs = create_vector_store(documents, "chroma_db_counseling")

        print("\n청킹 및 벡터화 완료!")
        print("상담용: chroma_db_counseling/")

        return vs

    except Exception as e:
        print(f"오류 발생: {e}")
        return None

if __name__ == "__main__":
    main()        