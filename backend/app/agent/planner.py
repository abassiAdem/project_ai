from __future__ import annotations

from typing import List

from backend.app.embeddings.grok import chat_completion
from backend.app.models.schemas import AgentResponse, SourceCitation
from backend.app.agent.tools.legal_rag import legal_search_tool
from backend.app.agent.tools.contract_analyzer import analyze_contract


def _plan_steps(user_query: str) -> List[str]:
    system = (
        "انت مخطط مهام لمساعد قانوني. "
        "اعط خطة قصيرة من 3-5 خطوات باللغة العربية دون تفاصيل تنفيذية."
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_query},
    ]
    text = chat_completion(messages, temperature=0.1)
    steps = [line.strip("- ") for line in text.splitlines() if line.strip()]
    return steps[:5]


def run_agent(message: str, history: List[dict], document_id: str | None) -> AgentResponse:
    plan = _plan_steps(message)

    notes = []
    citations: List[SourceCitation] = []

    contract_result = None
    if document_id:
        contract_result = analyze_contract(document_id)
        notes.extend(contract_result["notes"])

    rag_answer, rag_citations = legal_search_tool(message)
    citations.extend(rag_citations)

    synthesis_prompt = (
        "انت مساعد قانوني. ادمج نتائج تحليل العقد والبحث القانوني. "
        "قدّم توصيات عملية، واذكر المخاطر او البنود المهمة. "
        "اطلب معلومات ناقصة عند الحاجة."
    )

    messages = [{"role": "system", "content": synthesis_prompt}]
    if history:
        messages.extend(history[-6:])

    user_payload = "\n\n".join(
        [
            f"سؤال المستخدم:\n{message}",
            f"نتائج البحث القانوني:\n{rag_answer}",
            f"نتائج تحليل العقد:\n{contract_result['summary'] if contract_result else 'لا يوجد عقد مرفق.'}",
        ]
    )
    messages.append({"role": "user", "content": user_payload})
    final_answer = chat_completion(messages)

    return AgentResponse(plan=plan, answer=final_answer, citations=citations, notes=notes)
