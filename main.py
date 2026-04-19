# -*- coding: utf-8 -*-
"""
main.py — NHM Coach Backoffice
FastAPI backend for René Rusch's personal coaching plan generator.
Password-protected. René is the only user.
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, Form, HTTPException, Depends, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from database import (
    init_db, create_client, get_client, update_client, list_clients, delete_client,
    create_plan, get_plan, get_latest_plan, list_plans, update_plan_content,
    mark_plan_sent, get_next_version, save_feedback, get_feedback,
    create_chat, get_chat, list_chats, update_chat_title, touch_chat, delete_chat,
    add_message, get_messages, save_knowledge_doc, list_knowledge_docs,
    delete_knowledge_doc, get_all_knowledge_text, get_knowledge_base, save_knowledge_base
)
from ai_generator import generate_plan
from pdf_generator import generate_pdf
from email_sender import send_plan_email
from assistant import chat_with_assistant, extract_text_from_upload

# ── App Setup ─────────────────────────────────────────────────────────────────

app = FastAPI(title="NHM Coach Backoffice")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

SECRET_KEY = os.environ.get("SECRET_KEY", "nhm-coach-secret-2025-change-me")
COACH_PASSWORD = os.environ.get("COACH_PASSWORD", "nhm2025")
serializer = URLSafeTimedSerializer(SECRET_KEY)

init_db()

# ── Auth ──────────────────────────────────────────────────────────────────────

def get_session_token(request: Request) -> Optional[str]:
    return request.cookies.get("nhm_session")


def is_authenticated(request: Request) -> bool:
    token = get_session_token(request)
    if not token:
        return False
    try:
        serializer.loads(token, max_age=86400 * 7)  # 7 days
        return True
    except (BadSignature, SignatureExpired):
        return False


def require_auth(request: Request):
    if not is_authenticated(request):
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    return True


# ── Login ─────────────────────────────────────────────────────────────────────

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = ""):
    if is_authenticated(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": error})


@app.post("/login")
async def login_submit(request: Request, password: str = Form(...)):
    if password == COACH_PASSWORD:
        token = serializer.dumps("coach")
        response = RedirectResponse("/", status_code=302)
        response.set_cookie(
            "nhm_session", token,
            max_age=86400 * 7,
            httponly=True,
            samesite="lax"
        )
        return response
    return RedirectResponse("/login?error=1", status_code=302)


@app.get("/logout")
async def logout():
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie("nhm_session")
    return response


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    if not is_authenticated(request):
        return RedirectResponse("/login", status_code=302)
    clients = list_clients()
    # Enrich with latest plan status
    for c in clients:
        plan = get_latest_plan(c["id"])
        c["plan_status"] = plan["status"] if plan else "none"
        c["plan_version"] = plan["version"] if plan else 0
        c["plan_id"] = plan["id"] if plan else None
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "clients": clients,
        "total": len(clients),
    })


# ── New Client ────────────────────────────────────────────────────────────────

@app.get("/client/new", response_class=HTMLResponse)
async def new_client_page(request: Request):
    if not is_authenticated(request):
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("client_form.html", {
        "request": request,
        "client": None,
        "mode": "create",
    })


@app.post("/client/new")
async def new_client_submit(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    lang: str = Form("de"),
    nst_type: str = Form(...),
    goal: str = Form(...),
    duration: str = Form("4"),
    calories: str = Form(""),
    train_days: str = Form("3"),
    notes: str = Form(""),
):
    if not is_authenticated(request):
        return RedirectResponse("/login", status_code=302)

    form_data = await request.form()
    pillars = form_data.getlist("pillars")
    if not pillars:
        pillars = ["training", "nutrition", "stress", "sleep"]

    client_id = create_client(
        name=name, email=email, lang=lang, nst_type=nst_type,
        goal=goal, pillars=pillars, duration=duration,
        calories=calories, train_days=train_days, notes=notes
    )
    return RedirectResponse(f"/client/{client_id}", status_code=302)


# ── Client Detail ─────────────────────────────────────────────────────────────

@app.get("/client/{client_id}", response_class=HTMLResponse)
async def client_detail(request: Request, client_id: int):
    if not is_authenticated(request):
        return RedirectResponse("/login", status_code=302)
    client = get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    plans = list_plans(client_id)
    latest_plan = plans[0] if plans else None
    return templates.TemplateResponse("client_detail.html", {
        "request": request,
        "client": client,
        "plans": plans,
        "latest_plan": latest_plan,
    })


# ── Edit Client ───────────────────────────────────────────────────────────────

@app.get("/client/{client_id}/edit", response_class=HTMLResponse)
async def edit_client_page(request: Request, client_id: int):
    if not is_authenticated(request):
        return RedirectResponse("/login", status_code=302)
    client = get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return templates.TemplateResponse("client_form.html", {
        "request": request,
        "client": client,
        "mode": "edit",
    })


@app.post("/client/{client_id}/edit")
async def edit_client_submit(
    request: Request,
    client_id: int,
    name: str = Form(...),
    email: str = Form(...),
    lang: str = Form("de"),
    nst_type: str = Form(...),
    goal: str = Form(...),
    duration: str = Form("4"),
    calories: str = Form(""),
    train_days: str = Form("3"),
    notes: str = Form(""),
):
    if not is_authenticated(request):
        return RedirectResponse("/login", status_code=302)
    form_data = await request.form()
    pillars = form_data.getlist("pillars")
    if not pillars:
        pillars = ["training", "nutrition", "stress", "sleep"]
    update_client(client_id, name=name, email=email, lang=lang, nst_type=nst_type,
                  goal=goal, pillars=pillars, duration=duration,
                  calories=calories, train_days=train_days, notes=notes)
    return RedirectResponse(f"/client/{client_id}", status_code=302)


# ── Delete Client ─────────────────────────────────────────────────────────────

@app.post("/client/{client_id}/delete")
async def delete_client_route(request: Request, client_id: int):
    if not is_authenticated(request):
        return RedirectResponse("/login", status_code=302)
    delete_client(client_id)
    return RedirectResponse("/", status_code=302)


# ── Generate Plan ─────────────────────────────────────────────────────────────

@app.post("/client/{client_id}/generate")
async def generate_plan_route(request: Request, client_id: int):
    if not is_authenticated(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    client = get_client(client_id)
    if not client:
        return JSONResponse({"error": "Client not found"}, status_code=404)

    try:
        plan_content = await generate_plan(client)
        version = get_next_version(client_id)
        plan_id = create_plan(client_id, plan_content, version)
        return JSONResponse({
            "success": True,
            "plan_id": plan_id,
            "version": version,
            "redirect": f"/plan/{plan_id}"
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ── Plan Preview & Edit ───────────────────────────────────────────────────────

@app.get("/plan/{plan_id}", response_class=HTMLResponse)
async def plan_preview(request: Request, plan_id: int):
    if not is_authenticated(request):
        return RedirectResponse("/login", status_code=302)
    plan = get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    client = get_client(plan["client_id"])
    return templates.TemplateResponse("plan_preview.html", {
        "request": request,
        "plan": plan,
        "client": client,
        "content": plan["content"],
        "content_json": json.dumps(plan["content"], ensure_ascii=False),
    })


@app.post("/plan/{plan_id}/save")
async def save_plan(request: Request, plan_id: int):
    if not is_authenticated(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    data = await request.json()
    content = data.get("content")
    if not content:
        return JSONResponse({"error": "No content"}, status_code=400)
    update_plan_content(plan_id, content)
    return JSONResponse({"success": True})


# ── PDF Download ──────────────────────────────────────────────────────────────

@app.get("/plan/{plan_id}/pdf")
async def download_pdf(request: Request, plan_id: int, pillars: str = ""):
    if not is_authenticated(request):
        return RedirectResponse("/login", status_code=302)
    plan = get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    client = get_client(plan["client_id"])

    # Optional pillars filter via query param: ?pillars=training,nutrition
    plan_content = plan["content"]
    client_for_pdf = dict(client)
    if pillars:
        selected = [p.strip() for p in pillars.split(',') if p.strip()]
        plan_content = {k: v for k, v in plan_content.items()
                        if k not in ('training', 'nutrition', 'stress', 'sleep')
                        or k in selected}
        client_for_pdf["pillars"] = selected

    pdf_bytes = generate_pdf(client_for_pdf, plan_content)
    filename = f"NHM_Plan_{client['name'].replace(' ', '_')}_v{plan['version']}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# ── Send Plan via Email ───────────────────────────────────────────────────────

@app.post("/plan/{plan_id}/send")
async def send_plan(request: Request, plan_id: int):
    if not is_authenticated(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    plan = get_plan(plan_id)
    if not plan:
        return JSONResponse({"error": "Plan not found"}, status_code=404)
    client = get_client(plan["client_id"])

    # Parse optional pillars filter from request body
    selected_pillars = None
    try:
        body = await request.json()
        selected_pillars = body.get("pillars")  # list like ['training', 'nutrition']
    except Exception:
        pass  # No body or not JSON → send all pillars

    try:
        # Build filtered content for PDF if pillars specified
        plan_content = plan["content"]
        if selected_pillars:
            filtered_content = {k: v for k, v in plan_content.items()
                                if k not in ('training', 'nutrition', 'stress', 'sleep')
                                or k in selected_pillars}
        else:
            filtered_content = plan_content

        # Build a filtered client dict with only selected pillars
        client_for_pdf = dict(client)
        if selected_pillars:
            client_for_pdf["pillars"] = selected_pillars

        pdf_bytes = generate_pdf(client_for_pdf, filtered_content)
        send_plan_email(client, pdf_bytes, plan["version"])
        mark_plan_sent(plan_id)
        pillars_label = ', '.join(selected_pillars) if selected_pillars else 'alle Säulen'
        return JSONResponse({"success": True, "message": f"Plan ({pillars_label}) erfolgreich an {client['email']} gesendet."})
    except ValueError as e:
        return JSONResponse({"error": str(e), "smtp_not_configured": True}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ── Feedback Round ────────────────────────────────────────────────────────────

@app.get("/client/{client_id}/feedback", response_class=HTMLResponse)
async def feedback_page(request: Request, client_id: int):
    if not is_authenticated(request):
        return RedirectResponse("/login", status_code=302)
    client = get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    latest_plan = get_latest_plan(client_id)
    return templates.TemplateResponse("feedback_form.html", {
        "request": request,
        "client": client,
        "latest_plan": latest_plan,
        "pillars": client.get("pillars", []),
    })


@app.post("/client/{client_id}/feedback")
async def feedback_submit(request: Request, client_id: int):
    if not is_authenticated(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    client = get_client(client_id)
    if not client:
        return JSONResponse({"error": "Client not found"}, status_code=404)

    data = await request.json()
    answers = data.get("answers", {})
    plan_id = data.get("plan_id")

    if plan_id:
        save_feedback(plan_id, client_id, answers)

    try:
        plan_content = await generate_plan(client, feedback=answers)
        version = get_next_version(client_id)
        new_plan_id = create_plan(client_id, plan_content, version)
        return JSONResponse({
            "success": True,
            "plan_id": new_plan_id,
            "version": version,
            "redirect": f"/plan/{new_plan_id}"
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ── Meal Replace ──────────────────────────────────────────────────────────────

@app.post("/plan/{plan_id}/replace-meal")
async def replace_meal(request: Request, plan_id: int):
    if not is_authenticated(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    plan = get_plan(plan_id)
    if not plan:
        return JSONResponse({"error": "Plan not found"}, status_code=404)
    client = get_client(plan["client_id"])

    data = await request.json()
    day_type = data.get("day_type", "")
    meal_name = data.get("meal_name", "")
    reason = data.get("reason", "")

    lang = client.get("lang", "de")
    nst = client.get("nst_type", "lion")

    if lang == "de":
        prompt = (
            f"Erstelle eine einzelne Ersatzmahlzeit für '{meal_name}' ({day_type}) "
            f"für einen {nst}-Typ. Grund: {reason}. "
            f"Behalte ähnliche Kalorien und Makros bei. "
            f"Antworte als JSON: {{\"name\": \"...\", \"description\": \"...\", "
            f"\"calories\": 0, \"protein_g\": 0, \"time\": \"...\"}}"
        )
    else:
        prompt = (
            f"Create a single replacement meal for '{meal_name}' ({day_type}) "
            f"for a {nst}-type client. Reason: {reason}. "
            f"Keep similar calories and macros. "
            f"Respond as JSON: {{\"name\": \"...\", \"description\": \"...\", "
            f"\"calories\": 0, \"protein_g\": 0, \"time\": \"...\"}}"
        )

    from openai import OpenAI
    ai = OpenAI()
    response = ai.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        max_tokens=300,
    )
    new_meal = json.loads(response.choices[0].message.content)
    return JSONResponse({"success": True, "meal": new_meal})


# ── KI-Assistent ──────────────────────────────────────────────────────────────

@app.get("/assistant", response_class=HTMLResponse)
async def assistant_home(request: Request):
    if not is_authenticated(request):
        return RedirectResponse("/login", status_code=302)
    chats = list_chats()
    docs = list_knowledge_docs()
    kb = get_knowledge_base()
    clients = list_clients()
    return templates.TemplateResponse("assistant.html", {
        "request": request,
        "chats": chats,
        "docs": docs,
        "knowledge_base": kb["content"] if kb else "",
        "clients": clients,
        "active_chat": None,
        "messages": [],
    })


@app.get("/assistant/new", response_class=HTMLResponse)
async def assistant_new_chat(request: Request):
    if not is_authenticated(request):
        return RedirectResponse("/login", status_code=302)
    chat_id = create_chat("Neues Gespräch")
    return RedirectResponse(f"/assistant/{chat_id}", status_code=302)


@app.post("/assistant/new-json")
async def assistant_new_chat_json(request: Request):
    if not is_authenticated(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    chat_id = create_chat("Neues Gespräch")
    return JSONResponse({"chat_id": chat_id})


@app.get("/assistant/{chat_id}", response_class=HTMLResponse)
async def assistant_chat(request: Request, chat_id: int):
    if not is_authenticated(request):
        return RedirectResponse("/login", status_code=302)
    chat = get_chat(chat_id)
    if not chat:
        return RedirectResponse("/assistant", status_code=302)
    msgs = get_messages(chat_id)
    chats = list_chats()
    docs = list_knowledge_docs()
    kb = get_knowledge_base()
    clients = list_clients()

    # Client-Name für aktiven Chat
    active_chat = dict(chat)
    if active_chat.get("client_id"):
        c = get_client(active_chat["client_id"])
        active_chat["client_name"] = c["name"] if c else ""
    else:
        active_chat["client_name"] = ""

    # Client-Namen für Chat-Liste
    enriched_chats = []
    for ch in chats:
        ch_dict = dict(ch)
        if not ch_dict.get("client_name"):
            ch_dict["client_name"] = ""
        enriched_chats.append(ch_dict)

    return templates.TemplateResponse("assistant.html", {
        "request": request,
        "chats": enriched_chats,
        "docs": docs,
        "knowledge_base": kb["content"] if kb else "",
        "clients": clients,
        "active_chat": active_chat,
        "messages": msgs,
    })


@app.post("/assistant/{chat_id}/message")
async def assistant_send_message(request: Request, chat_id: int):
    if not is_authenticated(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    chat = get_chat(chat_id)
    if not chat:
        return JSONResponse({"error": "Chat not found"}, status_code=404)

    data = await request.json()
    user_msg = data.get("message", "").strip()
    client_id = data.get("client_id")

    if not user_msg:
        return JSONResponse({"error": "Empty message"}, status_code=400)

    # Gesprächsverlauf laden
    history = get_messages(chat_id)

    # Wissensbasis + Dokumente
    knowledge_text = get_all_knowledge_text()

    # Kundendaten falls Kundenbezug
    client_context = None
    if client_id:
        try:
            client_context = get_client(int(client_id))
        except Exception:
            pass

    # Nachricht speichern
    add_message(chat_id, "user", user_msg)

    # KI-Antwort generieren
    try:
        reply = await chat_with_assistant(
            messages_history=history,
            user_message=user_msg,
            knowledge_text=knowledge_text,
            client_context=client_context
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    # Antwort speichern
    add_message(chat_id, "assistant", reply)
    touch_chat(chat_id)

    # Chat-Titel automatisch setzen (erste Nachricht)
    if not history and len(user_msg) > 5:
        title = user_msg[:50] + ("..." if len(user_msg) > 50 else "")
        update_chat_title(chat_id, title)

    return JSONResponse({"reply": reply})


@app.post("/assistant/{chat_id}/delete")
async def assistant_delete_chat(request: Request, chat_id: int):
    if not is_authenticated(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    delete_chat(chat_id)
    return JSONResponse({"success": True})


@app.post("/assistant/{chat_id}/rename")
async def assistant_rename_chat(request: Request, chat_id: int):
    if not is_authenticated(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    data = await request.json()
    title = data.get("title", "Gespräch")
    update_chat_title(chat_id, title)
    return JSONResponse({"success": True})


@app.post("/assistant/{chat_id}/set-client")
async def assistant_set_client(request: Request, chat_id: int):
    if not is_authenticated(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    data = await request.json()
    client_id = data.get("client_id")
    conn_module = __import__("database")
    import sqlite3
    conn = conn_module.get_conn()
    from datetime import datetime as dt
    conn.execute(
        "UPDATE assistant_chats SET client_id=?, updated_at=? WHERE id=?",
        (client_id, dt.utcnow().isoformat(), chat_id)
    )
    conn.commit()
    conn.close()
    return JSONResponse({"success": True})


@app.post("/assistant/upload-doc")
async def assistant_upload_doc(request: Request, file: UploadFile = File(...)):
    if not is_authenticated(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    try:
        content_bytes = await file.read()
        text = await extract_text_from_upload(content_bytes, file.filename)
        doc_id = save_knowledge_doc(file.filename, text, len(content_bytes))
        return JSONResponse({"success": True, "doc_id": doc_id, "filename": file.filename})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/assistant/doc/{doc_id}/delete")
async def assistant_delete_doc(request: Request, doc_id: int):
    if not is_authenticated(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    delete_knowledge_doc(doc_id)
    return JSONResponse({"success": True})


@app.post("/assistant/knowledge")
async def assistant_save_knowledge(request: Request):
    if not is_authenticated(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    data = await request.json()
    content = data.get("content", "")
    save_knowledge_base(content)
    return JSONResponse({"success": True})
