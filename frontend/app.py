from __future__ import annotations

import requests
import gradio as gr

API_URL = "http://localhost:8000"


def chat_with_agent(message: str, session_id: str) -> tuple[str, str]:
    payload = {"session_id": session_id, "message": message}
    resp = requests.post(f"{API_URL}/chat", json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    citations = "\n".join(
        [
            f"- المصدر: {c['source']} | الصفحة: {c['page']}"
            for c in data.get("citations", [])
        ]
    )
    return data["answer"], citations


def upload_document(file) -> str:
    with open(file.name, "rb") as f:
        files = {"file": f}
        resp = requests.post(f"{API_URL}/uploads", files=files, timeout=60)
        resp.raise_for_status()
        return resp.json()["document_id"]


def analyze_contract(message: str, session_id: str, document_id: str) -> tuple[str, str, str]:
    payload = {"session_id": session_id, "message": message, "document_id": document_id}
    resp = requests.post(f"{API_URL}/agent/analyze", json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    plan = "\n".join([f"- {step}" for step in data.get("plan", [])])
    citations = "\n".join(
        [
            f"- المصدر: {c['source']} | الصفحة: {c['page']}"
            for c in data.get("citations", [])
        ]
    )
    notes = "\n".join([f"- {n}" for n in data.get("notes", [])])
    return data["answer"], plan, notes + ("\n" + citations if citations else "")


with gr.Blocks(title="LegalMind Agent") as demo:
    gr.Markdown("# مساعد قانوني ذكي للأنظمة التونسية")

    with gr.Tab("الدردشة القانونية"):
        session_id = gr.Textbox(label="معرف الجلسة", value="session-1")
        question = gr.Textbox(label="سؤالك القانوني")
        answer = gr.Textbox(label="الإجابة")
        sources = gr.Textbox(label="المصادر")
        ask_btn = gr.Button("اسأل")
        ask_btn.click(chat_with_agent, inputs=[question, session_id], outputs=[answer, sources])

    with gr.Tab("تحليل عقد"):
        session_id2 = gr.Textbox(label="معرف الجلسة", value="session-1")
        uploader = gr.File(label="تحميل عقد (PDF/DOCX)")
        document_id = gr.Textbox(label="معرف الوثيقة")
        upload_btn = gr.Button("رفع")
        upload_btn.click(upload_document, inputs=[uploader], outputs=[document_id])

        agent_query = gr.Textbox(label="ماذا تريد تحليله؟")
        agent_answer = gr.Textbox(label="النتيجة")
        agent_plan = gr.Textbox(label="خطة التحليل")
        agent_notes = gr.Textbox(label="ملاحظات ومصادر")
        run_btn = gr.Button("حلل")
        run_btn.click(
            analyze_contract,
            inputs=[agent_query, session_id2, document_id],
            outputs=[agent_answer, agent_plan, agent_notes],
        )


if __name__ == "__main__":
    demo.launch()
