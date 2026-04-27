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
    delete_knowledge_doc, get_all_knowledge_text, get_knowledge_base, save_knowledge_base,
    # Portal
    get_or_create_client_token, get_client_by_token, regenerate_client_token,
    add_client_note, get_client_notes, flag_client_note, delete_client_note,
    save_exercise_weight, get_exercise_weights,
    add_client_message, get_client_messages, mark_messages_read, get_unread_count,
    get_released_pillars, set_released_pillars,
    # Session 2
    save_checkin, get_checkins, get_latest_checkin, flag_checkin_for_ki, get_ki_flagged_checkins,
    save_progress_entry, get_progress_entries, get_streak, update_streak,
    create_emergency_request, get_emergency_request, update_emergency_ai_response,
    approve_emergency_request, get_pending_emergency_requests, get_approved_emergency_for_client
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


# ═══════════════════════════════════════════════════════════════════════════════
# KUNDEN-PORTAL
# ═══════════════════════════════════════════════════════════════════════════════

def get_portal_client(request: Request):
    """Returns client dict if portal cookie is valid, else None."""
    token = request.cookies.get("nhm_portal_token")
    if not token:
        return None
    return get_client_by_token(token)


def require_portal_auth(request: Request):
    client = get_portal_client(request)
    if not client:
        raise HTTPException(status_code=302, headers={"Location": "/portal/login"})
    return client


# ── Portal Login ──────────────────────────────────────────────────────────────

@app.get("/portal/login", response_class=HTMLResponse)
async def portal_login_page(request: Request, error: str = ""):
    return templates.TemplateResponse("portal_login.html", {"request": request, "error": error})


@app.post("/portal/login")
async def portal_login_submit(request: Request, token: str = Form(...)):
    client = get_client_by_token(token.strip())
    if not client:
        return RedirectResponse("/portal/login?error=1", status_code=302)
    response = RedirectResponse("/portal/dashboard", status_code=302)
    response.set_cookie("nhm_portal_token", token.strip(), max_age=86400 * 30, httponly=True, samesite="lax")
    return response


@app.get("/portal/logout")
async def portal_logout():
    response = RedirectResponse("/portal/login", status_code=302)
    response.delete_cookie("nhm_portal_token")
    return response


# Magic link: /portal/access/{token}
@app.get("/portal/access/{token}", response_class=HTMLResponse)
async def portal_magic_link(request: Request, token: str):
    client = get_client_by_token(token)
    if not client:
        return RedirectResponse("/portal/login?error=1", status_code=302)
    response = RedirectResponse("/portal/dashboard", status_code=302)
    response.set_cookie("nhm_portal_token", token, max_age=86400 * 30, httponly=True, samesite="lax")
    return response


# ── Portal Dashboard ──────────────────────────────────────────────────────────

@app.get("/portal/dashboard", response_class=HTMLResponse)
async def portal_dashboard(request: Request):
    client = get_portal_client(request)
    if not client:
        return RedirectResponse("/portal/login", status_code=302)
    plan = get_latest_plan(client["id"])
    released = get_released_pillars(client["id"])
    unread = get_unread_count(client["id"])
    notes = get_client_notes(client["id"])
    return templates.TemplateResponse("portal_dashboard.html", {
        "request": request,
        "client": client,
        "plan": plan,
        "released_pillars": released,
        "unread_count": unread,
        "notes": notes[:5],  # last 5 notes preview
    })


# ── Portal Plan View ──────────────────────────────────────────────────────────

@app.get("/portal/plan", response_class=HTMLResponse)
async def portal_plan(request: Request):
    client = get_portal_client(request)
    if not client:
        return RedirectResponse("/portal/login", status_code=302)
    plan = get_latest_plan(client["id"])
    if not plan:
        return RedirectResponse("/portal/dashboard", status_code=302)
    released = get_released_pillars(client["id"])
    weights = get_exercise_weights(client["id"], plan["id"])
    # Build weight lookup: key = "week_day_exercise"
    weight_map = {}
    for w in weights:
        key = f"{w['week']}_{w['day']}_{w['exercise']}"
        weight_map[key] = {"weight": w["weight"], "unit": w["unit"], "reps_done": w.get("reps_done")}
    return templates.TemplateResponse("portal_plan.html", {
        "request": request,
        "client": client,
        "plan": plan,
        "released_pillars": released,
        "weight_map": weight_map,
    })


# ── Portal: Save Exercise Weight ──────────────────────────────────────────────

@app.post("/portal/weight")
async def portal_save_weight(request: Request):
    client = get_portal_client(request)
    if not client:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    data = await request.json()
    plan = get_latest_plan(client["id"])
    if not plan:
        return JSONResponse({"error": "No plan"}, status_code=404)
    save_exercise_weight(
        client_id=client["id"],
        plan_id=plan["id"],
        week=data.get("week", 1),
        day=data.get("day", ""),
        exercise=data.get("exercise", ""),
        weight=data.get("weight"),
        unit=data.get("unit", "kg"),
        reps_done=data.get("reps_done")
    )
    return JSONResponse({"success": True})


# ── Portal: Notes ─────────────────────────────────────────────────────────────

@app.post("/portal/note")
async def portal_add_note(request: Request):
    client = get_portal_client(request)
    if not client:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    data = await request.json()
    note_id = add_client_note(client["id"], data.get("text", ""), data.get("category", "allgemein"))
    return JSONResponse({"success": True, "note_id": note_id})


@app.get("/portal/notes", response_class=HTMLResponse)
async def portal_notes_page(request: Request):
    client = get_portal_client(request)
    if not client:
        return RedirectResponse("/portal/login", status_code=302)
    notes = get_client_notes(client["id"])
    return templates.TemplateResponse("portal_notes.html", {
        "request": request,
        "client": client,
        "notes": notes,
    })


# ── Portal: Chat ──────────────────────────────────────────────────────────────

@app.get("/portal/chat", response_class=HTMLResponse)
async def portal_chat_page(request: Request):
    client = get_portal_client(request)
    if not client:
        return RedirectResponse("/portal/login", status_code=302)
    messages = get_client_messages(client["id"])
    return templates.TemplateResponse("portal_chat.html", {
        "request": request,
        "client": client,
        "messages": messages,
    })


@app.post("/portal/chat/send")
async def portal_chat_send(request: Request):
    client = get_portal_client(request)
    if not client:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    form = await request.form()
    text = form.get("text", "").strip()
    file_path = None
    if "file" in form:
        upload = form["file"]
        if upload.filename:
            import uuid, aiofiles
            ext = upload.filename.rsplit(".", 1)[-1] if "." in upload.filename else "bin"
            fname = f"chat_{client['id']}_{uuid.uuid4().hex[:8]}.{ext}"
            fpath = f"static/uploads/{fname}"
            os.makedirs("static/uploads", exist_ok=True)
            content = await upload.read()
            with open(fpath, "wb") as f:
                f.write(content)
            file_path = f"/static/uploads/{fname}"
    if text or file_path:
        add_client_message(client["id"], text or "(Datei)", "client", file_path)
    return JSONResponse({"success": True})


@app.post("/portal/chat/send-json")
async def portal_chat_send_json(request: Request):
    client = get_portal_client(request)
    if not client:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    data = await request.json()
    text = data.get("text", "").strip()
    if text:
        add_client_message(client["id"], text, "client")
    return JSONResponse({"success": True})


# ── Portal PDF Download ───────────────────────────────────────────────────────

@app.get("/portal/plan/pdf")
async def portal_plan_pdf(request: Request):
    client = get_portal_client(request)
    if not client:
        return RedirectResponse("/portal/login", status_code=302)
    plan = get_latest_plan(client["id"])
    if not plan:
        raise HTTPException(status_code=404, detail="Kein Plan gefunden")
    released = get_released_pillars(client["id"])
    client_for_pdf = dict(client)
    if released:
        client_for_pdf["pillars"] = released
    pdf_bytes = generate_pdf(plan["content"], client_for_pdf)
    filename = f"NHM_Plan_{client['name'].replace(' ', '_')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ═══════════════════════════════════════════════════════════════════════════════
# COMMANDER: Kunden-Portal verwalten
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/client/{client_id}/portal", response_class=HTMLResponse)
async def client_portal_manage(request: Request, client_id: int):
    if not is_authenticated(request):
        return RedirectResponse("/login", status_code=302)
    client = get_client(client_id)
    if not client:
        raise HTTPException(status_code=404)
    token_data = get_or_create_client_token(client_id)
    released = get_released_pillars(client_id)
    messages = get_client_messages(client_id, limit=50)
    notes = get_client_notes(client_id)
    unread = get_unread_count(client_id)
    mark_messages_read(client_id)
    plan = get_latest_plan(client_id)
    base_url = str(request.base_url).rstrip("/")
    portal_link = f"{base_url}/portal/access/{token_data['token']}"
    return templates.TemplateResponse("client_portal_manage.html", {
        "request": request,
        "client": client,
        "token": token_data["token"],
        "portal_link": portal_link,
        "released_pillars": released,
        "messages": messages,
        "notes": notes,
        "unread_count": unread,
        "plan": plan,
    })


@app.post("/client/{client_id}/portal/release-pillars")
async def release_pillars(request: Request, client_id: int):
    if not is_authenticated(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    data = await request.json()
    pillars = data.get("pillars", [])
    set_released_pillars(client_id, pillars)
    return JSONResponse({"success": True, "pillars": pillars})


@app.post("/client/{client_id}/portal/regenerate-token")
async def regenerate_token(request: Request, client_id: int):
    if not is_authenticated(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    token = regenerate_client_token(client_id)
    base_url = str(request.base_url).rstrip("/")
    portal_link = f"{base_url}/portal/access/{token}"
    return JSONResponse({"success": True, "token": token, "portal_link": portal_link})


@app.post("/client/{client_id}/portal/reply")
async def coach_reply(request: Request, client_id: int):
    if not is_authenticated(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    data = await request.json()
    text = data.get("text", "").strip()
    if text:
        add_client_message(client_id, text, "coach")
    return JSONResponse({"success": True})


@app.post("/client/{client_id}/note/flag")
async def flag_note(request: Request, client_id: int):
    if not is_authenticated(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    data = await request.json()
    flag_client_note(data.get("note_id"), data.get("flagged", True))
    return JSONResponse({"success": True})


@app.post("/client/{client_id}/note/delete")
async def delete_note(request: Request, client_id: int):
    if not is_authenticated(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    data = await request.json()
    delete_client_note(data.get("note_id"))
    return JSONResponse({"success": True})


# ── Commander Dashboard: Unread counts ───────────────────────────────────────

@app.get("/api/unread-counts")
async def get_all_unread_counts(request: Request):
    if not is_authenticated(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    clients = list_clients()
    counts = {str(c["id"]): get_unread_count(c["id"]) for c in clients}
    return JSONResponse(counts)


# ═══════════════════════════════════════════════════════════════════════════════
# SESSION 2: CHECK-IN, PROGRESS, EMERGENCY, AUDIO
# ═══════════════════════════════════════════════════════════════════════════════

def get_portal_client(request: Request):
    """Return client dict from portal session cookie, or None."""
    token = request.cookies.get("nhm_portal_session")
    if not token:
        return None
    try:
        client_id = serializer.loads(token, max_age=86400 * 30, salt="portal")
        return get_client(client_id)
    except Exception:
        return None


# ── Check-in ─────────────────────────────────────────────────────────────────

@app.get("/portal/checkin", response_class=HTMLResponse)
async def portal_checkin_page(request: Request):
    client = get_portal_client(request)
    if not client:
        return RedirectResponse("/portal/login")
    checkins = get_checkins(client["id"], limit=5)
    for ci in checkins:
        if isinstance(ci.get("answers"), str):
            try:
                ci["answers"] = json.loads(ci["answers"])
            except Exception:
                ci["answers"] = {}
    return templates.TemplateResponse("portal_checkin.html", {
        "request": request, "client": client, "checkins": checkins
    })


@app.post("/portal/checkin")
async def portal_checkin_submit(request: Request):
    client = get_portal_client(request)
    if not client:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    answers = await request.json()
    # Build a short KI summary
    summary_parts = []
    if answers.get("training_intensity"):
        summary_parts.append(f"Training-Intensität: {answers['training_intensity']}/10")
    if answers.get("nutrition_adherence"):
        summary_parts.append(f"Ernährungs-Umsetzung: {answers['nutrition_adherence']}/10")
    if answers.get("sleep_hours"):
        summary_parts.append(f"Schlaf: {answers['sleep_hours']}h")
    if answers.get("stress_level"):
        summary_parts.append(f"Stress: {answers['stress_level']}/10")
    if answers.get("general_note"):
        summary_parts.append(f"Notiz: {answers['general_note']}")
    summary = " | ".join(summary_parts)
    plan = get_latest_plan(client["id"])
    plan_id = plan["id"] if plan else None
    save_checkin(client["id"], answers, plan_id=plan_id, summary=summary)
    return JSONResponse({"ok": True})


# ── Progress Tracking ─────────────────────────────────────────────────────────

@app.get("/portal/progress", response_class=HTMLResponse)
async def portal_progress_page(request: Request):
    client = get_portal_client(request)
    if not client:
        return RedirectResponse("/portal/login")
    entries = get_progress_entries(client["id"], limit=30)
    streak = get_streak(client["id"])
    today = datetime.utcnow().strftime("%Y-%m-%d")
    return templates.TemplateResponse("portal_progress.html", {
        "request": request, "client": client,
        "entries": entries, "streak": streak, "today": today
    })


@app.post("/portal/progress")
async def portal_progress_save(request: Request):
    client = get_portal_client(request)
    if not client:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    data = await request.json()
    save_progress_entry(
        client["id"],
        date=data.get("date", datetime.utcnow().strftime("%Y-%m-%d")),
        weight_kg=data.get("weight_kg"),
        body_fat=data.get("body_fat"),
        energy=data.get("energy"),
        sleep_hours=data.get("sleep_hours"),
        note=data.get("note", "")
    )
    if data.get("count_streak"):
        update_streak(client["id"])
    return JSONResponse({"ok": True})


# ── Emergency / Notfalltaste ──────────────────────────────────────────────────

@app.get("/portal/emergency", response_class=HTMLResponse)
async def portal_emergency_page(request: Request):
    client = get_portal_client(request)
    if not client:
        return RedirectResponse("/portal/login")
    requests_list = get_approved_emergency_for_client(client["id"])
    # Also show pending
    all_reqs = get_pending_emergency_requests(client["id"])
    combined = {r["id"]: r for r in requests_list}
    for r in all_reqs:
        if r["id"] not in combined:
            combined[r["id"]] = r
    sorted_reqs = sorted(combined.values(), key=lambda x: x["created_at"], reverse=True)
    return templates.TemplateResponse("portal_emergency.html", {
        "request": request, "client": client, "requests": sorted_reqs
    })


@app.post("/portal/emergency")
async def portal_emergency_submit(request: Request):
    client = get_portal_client(request)
    if not client:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    data = await request.json()
    topic = data.get("topic", "allgemein")
    message = data.get("message", "").strip()
    if not message:
        return JSONResponse({"error": "Nachricht fehlt"}, status_code=400)

    req_id = create_emergency_request(client["id"], topic, message)

    # Generate AI response asynchronously
    asyncio.create_task(_process_emergency(req_id, client, topic, message))
    return JSONResponse({"ok": True, "req_id": req_id})


async def _process_emergency(req_id: int, client: dict, topic: str, message: str):
    """Background task: KI-Antwort generieren, dann Coach per E-Mail benachrichtigen."""
    try:
        from openai import OpenAI
        oai = OpenAI()
        knowledge = get_all_knowledge_text()
        system_prompt = f"""Du bist ein erfahrener NeuroHealthMastery-Coach-Assistent.
Ein Kunde hat eine Notfall-Anfrage gestellt. Antworte professionell, empathisch und konkret auf Deutsch.
Basiere deine Antwort auf dem NHM-Konzept und den folgenden Wissensquellen:
{knowledge[:3000] if knowledge else 'Keine zusätzlichen Dokumente verfügbar.'}
Wichtig: Gib eine klare, handlungsorientierte Antwort. Maximal 200 Wörter."""

        resp = oai.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Thema: {topic}\n\nKunde schreibt: {message}"}
            ],
            max_tokens=400
        )
        ai_response = resp.choices[0].message.content.strip()
        update_emergency_ai_response(req_id, ai_response)

        # E-Mail an Coach
        coach_email = os.environ.get("COACH_EMAIL", "rene@neurohealthmastery.de")
        approval_url = f"{os.environ.get('APP_URL', 'https://web-production-f5f68a.up.railway.app')}/emergency/{req_id}/approve"
        try:
            from email_sender import send_emergency_notification
            send_emergency_notification(
                coach_email=coach_email,
                client_name=client["name"],
                topic=topic,
                message=message,
                ai_response=ai_response,
                approval_url=approval_url,
                req_id=req_id
            )
        except Exception as e:
            print(f"Emergency email error: {e}")
    except Exception as e:
        print(f"Emergency AI error: {e}")


@app.get("/emergency/{req_id}/approve", response_class=HTMLResponse)
async def emergency_approve_page(req_id: int, request: Request):
    """Coach-Freigabe-Seite (auch ohne Login zugänglich via E-Mail-Link)."""
    if not is_authenticated(request):
        return RedirectResponse(f"/login?next=/emergency/{req_id}/approve")
    req = get_emergency_request(req_id)
    if not req:
        raise HTTPException(404)
    client = get_client(req["client_id"])
    return templates.TemplateResponse("emergency_approve.html", {
        "request": request, "req": req, "client": client
    })


@app.post("/emergency/{req_id}/approve")
async def emergency_approve_submit(req_id: int, request: Request):
    if not is_authenticated(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    data = await request.json()
    coach_edit = data.get("coach_edit", "").strip() or None
    approve_emergency_request(req_id, coach_edit=coach_edit)
    return JSONResponse({"ok": True})


# ── Audio / Sprache-zu-Text ───────────────────────────────────────────────────

@app.post("/api/speech-to-text")
async def speech_to_text(request: Request, audio: UploadFile = File(...)):
    """Browser-Mikrofon → Whisper → Text. Funktioniert für Coach und Kunden."""
    # Check auth (coach or portal client)
    if not is_authenticated(request) and not get_portal_client(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    try:
        from openai import OpenAI
        oai = OpenAI()
        audio_bytes = await audio.read()
        # Save temp file
        import tempfile
        suffix = ".webm"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        with open(tmp_path, "rb") as f:
            transcript = oai.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language="de"
            )
        os.unlink(tmp_path)
        return JSONResponse({"text": transcript.text})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ── Commander: Check-in Auswertung ────────────────────────────────────────────

@app.get("/client/{client_id}/checkins", response_class=HTMLResponse)
async def commander_checkins(client_id: int, request: Request):
    if not is_authenticated(request):
        return RedirectResponse("/login")
    client = get_client(client_id)
    if not client:
        raise HTTPException(404)
    checkins = get_checkins(client_id, limit=20)
    for ci in checkins:
        if isinstance(ci.get("answers"), str):
            try:
                ci["answers"] = json.loads(ci["answers"])
            except Exception:
                ci["answers"] = {}
    return templates.TemplateResponse("commander_checkins.html", {
        "request": request, "client": client, "checkins": checkins
    })


@app.post("/client/{client_id}/checkin/flag")
async def flag_checkin(client_id: int, request: Request):
    if not is_authenticated(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    data = await request.json()
    flag_checkin_for_ki(data["checkin_id"], data.get("flag", True))
    return JSONResponse({"ok": True})


# ── Commander: Emergency Requests ─────────────────────────────────────────────

@app.get("/emergencies", response_class=HTMLResponse)
async def commander_emergencies(request: Request):
    if not is_authenticated(request):
        return RedirectResponse("/login")
    reqs = get_pending_emergency_requests()
    return templates.TemplateResponse("commander_emergencies.html", {
        "request": request, "requests": reqs
    })
