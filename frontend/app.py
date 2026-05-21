from __future__ import annotations

import os
import uuid
import requests
import gradio as gr

API_URL = "http://localhost:8000"


def _format_citations(citations: list[dict]) -> str:
    if not citations:
        return ""
    rows = [f"- المصدر: {c['source']} | الصفحة: {c['page']}" for c in citations]
    return "\n".join(rows)


def _append_sections(answer: str, extra_sections: list[tuple[str, str]]) -> str:
    sections = [answer.strip()]
    for title, content in extra_sections:
        if content:
            sections.append(f"\n\n**{title}**\n{content}")
    return "".join(sections)


def _new_session_id() -> str:
    return f"session-{uuid.uuid4().hex[:8]}"


def init_state() -> dict:
    session_id = _new_session_id()
    return {
        "sessions": [session_id],
        "histories": {session_id: []},
        "documents": {},
        "document_names": {},
    }


def create_session(state: dict) -> tuple[dict, gr.Dropdown, list, str]:
    session_id = _new_session_id()
    state["sessions"].append(session_id)
    state["histories"][session_id] = []
    return (
        state,
        gr.update(choices=state["sessions"], value=session_id),
        state["histories"][session_id],
        "تم إنشاء جلسة جديدة.",
    )


def load_session(session_id: str, state: dict) -> tuple[list, str]:
    history = state["histories"].get(session_id, [])
    document_id = state["documents"].get(session_id)
    document_name = state["document_names"].get(session_id)
    if document_id and document_name:
        status = f"العقد المرفوع لهذه الجلسة: {document_name}"
    elif document_id:
        status = "العقد المرفوع لهذه الجلسة موجود."
    else:
        status = "لا يوجد عقد مرفوع لهذه الجلسة."
    return history, status


def upload_document(file, session_id: str, state: dict) -> tuple[dict, str]:
    if file is None:
        return state, "يرجى اختيار ملف قبل الرفع."
    if not session_id:
        return state, "يرجى اختيار جلسة قبل الرفع."
    with open(file.name, "rb") as f:
        files = {"file": f}
        resp = requests.post(f"{API_URL}/uploads", files=files, timeout=60)
        resp.raise_for_status()
        document_id = resp.json()["document_id"]
    state["documents"][session_id] = document_id
    state["document_names"][session_id] = os.path.basename(file.name)
    return state, f"تم ربط العقد: {state['document_names'][session_id]}"


def handle_message(
    message: str,
    session_id: str,
    state: dict,
) -> tuple[list, dict, str, str]:
    if not message.strip():
        return state["histories"].get(session_id, []), state, "", ""

    history = state["histories"].get(session_id, [])
    status = ""
    document_id = state["documents"].get(session_id)
    if document_id:
        payload = {
            "session_id": session_id,
            "message": message,
            "document_id": document_id,
        }
        resp = requests.post(f"{API_URL}/agent/analyze", json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        plan = "\n".join([f"- {step}" for step in data.get("plan", [])])
        notes = "\n".join([f"- {n}" for n in data.get("notes", [])])
        citations = _format_citations(data.get("citations", []))
        answer = _append_sections(
            data["answer"],
            [
                ("خطة التحليل", plan),
                ("ملاحظات", notes),
                ("المصادر", citations),
            ],
        )
    else:
        payload = {"session_id": session_id, "message": message}
        resp = requests.post(f"{API_URL}/chat", json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        citations = _format_citations(data.get("citations", []))
        answer = _append_sections(data["answer"], [("المصادر", citations)])

    history = history + [[message, answer]]
    state["histories"][session_id] = history
    return history, state, "", status


with gr.Blocks(title="LegalMind Agent") as demo:
    gr.Markdown("# مساعد قانوني ذكي للأنظمة التونسية")

    state = gr.State(init_state())

    with gr.Row():
        with gr.Column(scale=1, min_width=220):
            gr.Markdown("## الجلسات")
            new_session_btn = gr.Button("جلسة جديدة")
            session_selector = gr.Dropdown(label="اختر جلسة", choices=[], value=None)
            contract_upload = gr.File(label="تحميل عقد (PDF/DOCX)")
            upload_btn = gr.Button("رفع العقد")
            status_box = gr.Markdown("")

        with gr.Column(scale=3):
            chatbot = gr.Chatbot(label="الدردشة", height=520, bubble_full_width=False)
            user_input = gr.Textbox(
                label="اكتب سؤالك",
                placeholder="اكتب سؤالك هنا...",
                lines=2,
            )
            send_btn = gr.Button("إرسال")

    demo.load(
        lambda s: gr.update(choices=s["sessions"], value=s["sessions"][0]),
        inputs=[state],
        outputs=[session_selector],
    )

    new_session_btn.click(
        create_session,
        inputs=[state],
        outputs=[state, session_selector, chatbot, status_box],
    )

    session_selector.change(
        load_session,
        inputs=[session_selector, state],
        outputs=[chatbot, status_box],
    )

    upload_btn.click(
        upload_document,
        inputs=[contract_upload, session_selector, state],
        outputs=[state, status_box],
    )

    send_btn.click(
        handle_message,
        inputs=[user_input, session_selector, state],
        outputs=[chatbot, state, user_input, status_box],
    )
    user_input.submit(
        handle_message,
        inputs=[user_input, session_selector, state],
        outputs=[chatbot, state, user_input, status_box],
    )


if __name__ == "__main__":
    demo.launch()
