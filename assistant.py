# -*- coding: utf-8 -*-
"""
assistant.py — NHM Coach Backoffice
KI-Assistent für René Rusch. Beantwortet Fragen rund um das NHM-Konzept,
Neurotyping, Training, Ernährung, Stress und Schlaf.
Kann Kundendaten und hochgeladene Dokumente als Kontext nutzen.
"""

import os
import json
from openai import OpenAI

_gemini_key = os.environ.get("GEMINI_API_KEY", "")
_openai_key = os.environ.get("OPENAI_API_KEY", "")

if _gemini_key:
    client = OpenAI(
        api_key=_gemini_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    _model = "gemini-2.0-flash"
else:
    client = OpenAI(api_key=_openai_key)
    _model = "gpt-4.1-mini"

SYSTEM_PROMPT = """Du bist der persönliche KI-Assistent von René Rusch, dem Gründer von NeuroHealth Mastery (NHM).

Deine Aufgabe:
- Beantworte Fragen rund um das NHM-Konzept: Neurotyping, Natural Signature Types (NST), Training, Ernährung, Stressmanagement und Schlafoptimierung
- Gib konkrete, umsetzbare Empfehlungen basierend auf dem NHM-Konzept
- Hilf René bei der Planerstellung und Anpassung für seine Kunden
- Analysiere Kundendaten und mache Verbesserungsvorschläge
- Sei ehrlich, kritisch und denke "out of the box", bleibe aber realistisch

Die 5 NST-Typen im NHM-System:
- Löwe (Lion): Dopamingetrieben, wettbewerbsorientiert, braucht schnelle Ergebnisse, HIIT & schweres Krafttraining
- Falke (Falcon): Analytisch, effizient, optimierungsgetrieben, periodisiertes Training, präzises Tracking
- Chamäleon (Chameleon): Anpassungsfähig, vielseitig, braucht Abwechslung, funktionelles Training
- Wolf (Wolf): Teamorientiert, ausdauernd, braucht soziale Motivation, Gruppentraining & Ausdauer
- Eule (Owl): Introvertiert, tiefgründig, braucht Sinn & Struktur, ruhiges fokussiertes Training

Die 4 Säulen des NHM-Konzepts:
1. Training (individuell nach NST-Typ)
2. Ernährung (zielgerichtet, NST-angepasst)
3. Stressmanagement (Neurotyp-spezifisch)
4. Schlafoptimierung (Regeneration & Performance)

Antworte immer auf Deutsch, es sei denn, René fragt explizit auf Englisch.
Sei präzise, professionell und praxisorientiert.
"""


async def chat_with_assistant(messages_history: list, user_message: str,
                               knowledge_text: str = "", client_context: dict = None) -> str:
    """
    Sendet eine Nachricht an den KI-Assistenten und gibt die Antwort zurück.
    
    messages_history: Liste von {"role": "user"/"assistant", "content": "..."}
    user_message: Die neue Nachricht von René
    knowledge_text: Kombinierter Text aus Wissensbasis + Dokumenten
    client_context: Kundendaten falls kundenbezogene Frage
    """
    
    # System Prompt aufbauen
    system_content = SYSTEM_PROMPT
    
    if knowledge_text:
        system_content += f"\n\n--- DEINE WISSENSBASIS & DOKUMENTE ---\n{knowledge_text[:8000]}"
    
    if client_context:
        nst_labels = {
            "lion": "Löwe", "falcon": "Falke", "chameleon": "Chamäleon",
            "wolf": "Wolf", "owl": "Eule"
        }
        goal_labels = {
            "fat_loss": "Fettreduktion", "muscle_gain": "Muskelaufbau",
            "energy": "Mehr Energie", "health": "Allgemeine Gesundheit"
        }
        pillars = client_context.get("pillars", [])
        if isinstance(pillars, str):
            try:
                pillars = json.loads(pillars)
            except Exception:
                pillars = [pillars]
        
        system_content += f"""

--- AKTUELLER KUNDENBEZUG ---
Kunde: {client_context.get('name', 'Unbekannt')}
E-Mail: {client_context.get('email', '')}
NST-Typ: {nst_labels.get(client_context.get('nst_type', ''), client_context.get('nst_type', ''))}
Hauptziel: {goal_labels.get(client_context.get('goal', ''), client_context.get('goal', ''))}
Aktive Säulen: {', '.join(pillars)}
Plandauer: {client_context.get('duration', '4')} Wochen
Kalorien: {client_context.get('calories', 'nicht angegeben')} kcal
Trainingstage/Woche: {client_context.get('train_days', '3')}
Interne Notizen: {client_context.get('notes', 'keine')}
"""
    
    # Nachrichten-Liste aufbauen
    messages = [{"role": "system", "content": system_content}]
    
    # Gesprächsverlauf (max. letzte 20 Nachrichten)
    for msg in messages_history[-20:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    
    # Neue Nachricht
    messages.append({"role": "user", "content": user_message})
    
    response = client.chat.completions.create(
        model=_model,
        messages=messages,
        max_tokens=1500,
        temperature=0.7,
    )
    
    return response.choices[0].message.content


async def extract_text_from_upload(file_content: bytes, filename: str) -> str:
    """Extrahiert Text aus hochgeladenen Dateien (PDF, TXT, DOCX)."""
    filename_lower = filename.lower()
    
    if filename_lower.endswith(".txt") or filename_lower.endswith(".md"):
        try:
            return file_content.decode("utf-8")
        except Exception:
            return file_content.decode("latin-1", errors="replace")
    
    elif filename_lower.endswith(".pdf"):
        try:
            import io
            from pdfminer.high_level import extract_text_to_fp
            from pdfminer.layout import LAParams
            output = io.StringIO()
            extract_text_to_fp(io.BytesIO(file_content), output, laparams=LAParams())
            return output.getvalue()
        except ImportError:
            # Fallback: pypdf
            try:
                import io
                import pypdf
                reader = pypdf.PdfReader(io.BytesIO(file_content))
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text
            except Exception as e:
                return f"[PDF konnte nicht gelesen werden: {e}]"
    
    elif filename_lower.endswith(".docx"):
        try:
            import io
            import docx
            doc = docx.Document(io.BytesIO(file_content))
            return "\n".join([para.text for para in doc.paragraphs])
        except Exception as e:
            return f"[DOCX konnte nicht gelesen werden: {e}]"
    
    else:
        try:
            return file_content.decode("utf-8")
        except Exception:
            return f"[Datei '{filename}' konnte nicht gelesen werden]"
