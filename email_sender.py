# -*- coding: utf-8 -*-
"""
email_sender.py — NHM Coach Backoffice
Sends coaching plan PDF to client via SMTP (Gmail or any SMTP provider).
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
FROM_NAME = os.environ.get("FROM_NAME", "René Rusch | NeuroHealthMastery")
FROM_EMAIL = os.environ.get("FROM_EMAIL", SMTP_USER)

NST_NAMES = {
    "lion":      {"de": "Löwe",      "en": "Lion"},
    "falcon":    {"de": "Falke",     "en": "Falcon"},
    "chameleon": {"de": "Chamäleon", "en": "Chameleon"},
    "wolf":      {"de": "Wolf",      "en": "Wolf"},
    "owl":       {"de": "Eule",      "en": "Owl"},
}

GOAL_LABELS = {
    "fat_loss":  {"de": "Fettreduktion",         "en": "Fat Loss"},
    "muscle":    {"de": "Muskelaufbau",           "en": "Muscle Building"},
    "energy":    {"de": "Mehr Energie",           "en": "More Energy"},
    "health":    {"de": "Allgemeine Gesundheit",  "en": "General Health"},
}


def build_email_body(client_data: dict, plan_version: int, lang: str) -> tuple[str, str]:
    """Returns (subject, html_body)"""
    name = client_data.get("name", "")
    nst = client_data.get("nst_type", "lion")
    goal_key = client_data.get("goal", "fat_loss")
    duration = client_data.get("duration", "4")

    nst_name = NST_NAMES.get(nst, {}).get(lang, nst)
    goal_label = GOAL_LABELS.get(goal_key, {}).get(lang, goal_key)

    if lang == "de":
        subject = f"Dein persönlicher Coaching-Plan – {name} | NeuroHealthMastery"
        if plan_version > 1:
            subject = f"Dein aktualisierter Coaching-Plan (v{plan_version}) – {name} | NeuroHealthMastery"

        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: Arial, sans-serif; background: #f8fafc; margin: 0; padding: 0; }}
  .container {{ max-width: 600px; margin: 0 auto; background: white; }}
  .header {{ background: #0a0f1e; padding: 32px 24px; text-align: center; }}
  .header h1 {{ color: #06b6d4; font-size: 22px; margin: 0 0 8px; }}
  .header p {{ color: #94a3b8; font-size: 14px; margin: 0; }}
  .body {{ padding: 32px 24px; }}
  .body h2 {{ color: #0a0f1e; font-size: 18px; }}
  .body p {{ color: #374151; font-size: 15px; line-height: 1.6; }}
  .highlight {{ background: #f0fdfa; border-left: 4px solid #06b6d4; padding: 16px; margin: 20px 0; border-radius: 4px; }}
  .highlight p {{ margin: 0; color: #0a0f1e; font-weight: bold; }}
  .footer {{ background: #f1f5f9; padding: 20px 24px; text-align: center; }}
  .footer p {{ color: #94a3b8; font-size: 12px; margin: 4px 0; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>NeuroHealthMastery</h1>
    <p>Dein persönlicher Coaching-Plan ist bereit</p>
  </div>
  <div class="body">
    <h2>Hallo {name},</h2>
    <p>
      dein persönlicher <strong>{duration}-Wochen-Coaching-Plan</strong> ist fertig und wartet auf dich.
      Er wurde speziell auf deinen <strong>Natural Signature Type – {nst_name}</strong> und dein
      Ziel <strong>{goal_label}</strong> abgestimmt.
    </p>
    <div class="highlight">
      <p>📎 Dein Plan ist als PDF-Datei an diese E-Mail angehängt.</p>
    </div>
    <p>
      Der Plan enthält konkrete, umsetzbare Maßnahmen – abgestimmt auf deine Biologie,
      deine Stärken und dein Ziel. Lies ihn durch, starte mit Woche 1 und melde dich
      bei Fragen jederzeit.
    </p>
    <p>
      Nach Abschluss des Plans werde ich mich bei dir melden, um Feedback zu sammeln
      und deinen Plan für den nächsten Zyklus anzupassen.
    </p>
    <p>
      Bei Fragen erreichst du mich jederzeit:<br>
      📧 info@neurohealthmastery.de<br>
      💬 WhatsApp: +49 157 37557085 (Mo–Fr, 9–18 Uhr)
    </p>
    <p>Auf deinen Erfolg!<br><strong>René Rusch</strong><br>NeuroHealthMastery</p>
  </div>
  <div class="footer">
    <p>NeuroHealthMastery | René Rusch | neurohealthmastery.de</p>
    <p>René Rusch ist kein Arzt. Alle Empfehlungen basieren auf professionellen Zertifikaten und wissenschaftlicher Literatur.</p>
  </div>
</div>
</body>
</html>"""
    else:
        subject = f"Your Personal Coaching Plan – {name} | NeuroHealthMastery"
        if plan_version > 1:
            subject = f"Your Updated Coaching Plan (v{plan_version}) – {name} | NeuroHealthMastery"

        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: Arial, sans-serif; background: #f8fafc; margin: 0; padding: 0; }}
  .container {{ max-width: 600px; margin: 0 auto; background: white; }}
  .header {{ background: #0a0f1e; padding: 32px 24px; text-align: center; }}
  .header h1 {{ color: #06b6d4; font-size: 22px; margin: 0 0 8px; }}
  .header p {{ color: #94a3b8; font-size: 14px; margin: 0; }}
  .body {{ padding: 32px 24px; }}
  .body h2 {{ color: #0a0f1e; font-size: 18px; }}
  .body p {{ color: #374151; font-size: 15px; line-height: 1.6; }}
  .highlight {{ background: #f0fdfa; border-left: 4px solid #06b6d4; padding: 16px; margin: 20px 0; border-radius: 4px; }}
  .highlight p {{ margin: 0; color: #0a0f1e; font-weight: bold; }}
  .footer {{ background: #f1f5f9; padding: 20px 24px; text-align: center; }}
  .footer p {{ color: #94a3b8; font-size: 12px; margin: 4px 0; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>NeuroHealthMastery</h1>
    <p>Your personal coaching plan is ready</p>
  </div>
  <div class="body">
    <h2>Hello {name},</h2>
    <p>
      your personal <strong>{duration}-week coaching plan</strong> is ready for you.
      It has been specifically tailored to your <strong>Natural Signature Type – {nst_name}</strong>
      and your goal of <strong>{goal_label}</strong>.
    </p>
    <div class="highlight">
      <p>📎 Your plan is attached as a PDF file to this email.</p>
    </div>
    <p>
      The plan contains concrete, actionable steps – aligned with your biology,
      your strengths, and your goal. Read through it, start with Week 1, and
      reach out any time with questions.
    </p>
    <p>
      After completing the plan, I will follow up to collect your feedback
      and adjust your plan for the next cycle.
    </p>
    <p>
      Questions? Reach me any time:<br>
      📧 info@neurohealthmastery.de<br>
      💬 WhatsApp: +49 157 37557085 (Mon–Fri, 9am–6pm CET)
    </p>
    <p>To your success!<br><strong>René Rusch</strong><br>NeuroHealthMastery</p>
  </div>
  <div class="footer">
    <p>NeuroHealthMastery | René Rusch | neurohealthmastery.de</p>
    <p>René Rusch is not a medical doctor. All recommendations are based on professional certifications and peer-reviewed literature.</p>
  </div>
</div>
</body>
</html>"""

    return subject, html


def send_plan_email(client_data: dict, pdf_bytes: bytes, plan_version: int = 1) -> bool:
    """Send coaching plan PDF to client. Returns True on success."""
    if not SMTP_USER or not SMTP_PASS:
        raise ValueError("SMTP credentials not configured. Set SMTP_USER and SMTP_PASS environment variables.")

    lang = client_data.get("lang", "de")
    to_email = client_data.get("email", "")
    to_name = client_data.get("name", "")

    subject, html_body = build_email_body(client_data, plan_version, lang)

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
    msg["To"] = f"{to_name} <{to_email}>"

    # HTML body
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    # PDF attachment
    pdf_part = MIMEApplication(pdf_bytes, _subtype="pdf")
    filename = f"NHM_Coaching_Plan_{to_name.replace(' ', '_')}_v{plan_version}.pdf"
    pdf_part.add_header("Content-Disposition", "attachment", filename=filename)
    msg.attach(pdf_part)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(FROM_EMAIL, to_email, msg.as_string())

    return True


def send_emergency_notification(coach_email: str, client_name: str, topic: str,
                                 message: str, ai_response: str,
                                 approval_url: str, req_id: int) -> bool:
    """Notify coach about a new emergency request and provide approval link."""
    if not SMTP_USER or not SMTP_PASS:
        print("SMTP not configured — skipping emergency notification email")
        return False

    subject = f"🆘 Notfallanfrage von {client_name} – {topic}"

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8">
<style>
  body {{ font-family: Arial, sans-serif; background: #f8fafc; margin: 0; padding: 0; }}
  .container {{ max-width: 600px; margin: 0 auto; background: white; }}
  .header {{ background: #0a0f1e; padding: 24px; text-align: center; }}
  .header h1 {{ color: #ef4444; font-size: 20px; margin: 0; }}
  .body {{ padding: 24px; }}
  .label {{ font-size: 11px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }}
  .box {{ background: #f8fafc; border-radius: 8px; padding: 14px; margin-bottom: 16px; font-size: 14px; line-height: 1.6; }}
  .ai-box {{ background: #f0fdfa; border-left: 4px solid #06b6d4; padding: 14px; margin-bottom: 16px; font-size: 14px; line-height: 1.6; }}
  .btn {{ display: inline-block; background: #22c55e; color: white; padding: 14px 28px; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 15px; }}
  .footer {{ background: #f1f5f9; padding: 16px; text-align: center; font-size: 12px; color: #94a3b8; }}
</style>
</head>
<body>
<div class="container">
  <div class="header"><h1>🆘 Neue Notfallanfrage</h1></div>
  <div class="body">
    <p><strong>Kunde:</strong> {client_name}<br><strong>Thema:</strong> {topic}</p>
    <div class="label">Kunden-Nachricht</div>
    <div class="box">{message}</div>
    <div class="label">KI-Antwort (Entwurf)</div>
    <div class="ai-box">{ai_response}</div>
    <p style="text-align:center;">
      <a href="{approval_url}" class="btn">✅ Prüfen & Freigeben</a>
    </p>
    <p style="font-size:13px;color:#6b7280;text-align:center;">
      Oder öffne direkt: {approval_url}
    </p>
  </div>
  <div class="footer">NeuroHealthMastery | NHM Coach System | Anfrage #{req_id}</div>
</div>
</body>
</html>"""

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
    msg["To"] = coach_email
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(FROM_EMAIL, coach_email, msg.as_string())
        return True
    except Exception as e:
        print(f"Emergency email send error: {e}")
        return False


def send_renewal_notification(coach_email: str, client: dict) -> bool:
    """Notify coach that a client's plan is ending and renewal is due."""
    if not SMTP_USER or not SMTP_PASS:
        print("SMTP not configured — skipping renewal notification")
        return False

    name = client.get("name", "")
    subject = f"⏰ Plan-Verlängerung fällig: {name}"

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8">
<style>
  body {{ font-family: Arial, sans-serif; background: #f8fafc; margin: 0; padding: 0; }}
  .container {{ max-width: 600px; margin: 0 auto; background: white; }}
  .header {{ background: #0a0f1e; padding: 24px; text-align: center; }}
  .header h1 {{ color: #f59e0b; font-size: 20px; margin: 0; }}
  .body {{ padding: 24px; }}
  .btn {{ display: inline-block; background: #06b6d4; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: bold; }}
  .footer {{ background: #f1f5f9; padding: 16px; text-align: center; font-size: 12px; color: #94a3b8; }}
</style>
</head>
<body>
<div class="container">
  <div class="header"><h1>⏰ Plan-Verlängerung fällig</h1></div>
  <div class="body">
    <p>Der Coaching-Plan von <strong>{name}</strong> läuft ab.</p>
    <p>Es ist Zeit, den nächsten Plan zu erstellen oder den bestehenden zu verlängern.</p>
    <p style="text-align:center;margin-top:20px;">
      <a href="{os.environ.get('APP_URL', 'https://web-production-f5f68a.up.railway.app')}/client/{client.get('id', '')}" class="btn">
        Zum Kundenprofil →
      </a>
    </p>
  </div>
  <div class="footer">NeuroHealthMastery | NHM Coach System</div>
</div>
</body>
</html>"""

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
    msg["To"] = coach_email
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(FROM_EMAIL, coach_email, msg.as_string())
        return True
    except Exception as e:
        print(f"Renewal email error: {e}")
        return False
