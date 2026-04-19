# -*- coding: utf-8 -*-
"""
ai_generator.py — NHM Coach Backoffice
Generates personalised coaching plans using Gemini 2.5 Flash Lite.
Plans are tailored to the client's NST type, goal, and selected pillars.

JSON schema v2:
- training.training_concept: WHY this plan, WHY these exercises (NST-specific)
- training.weeks[].sessions[].exercises[]: name, sets, reps, tempo, rest, note
- nutrition: carb-cycling structure (workout_day / rest_day macros + meals)
"""

import os
import json
from google import genai as _genai

_gemini_key = os.environ.get("GEMINI_API_KEY", "")
_gemini_client = _genai.Client(api_key=_gemini_key) if _gemini_key else None
_model = "gemini-2.5-flash-lite"

# ── NST Type Profiles (Thibarmy / Natural Signature Typing) ───────────────────

NST_PROFILES = {
    "lion": {
        "de": (
            "NST-Typ 1A – Der Löwe (dopamingetrieben, neurodominant).\n"
            "Trainingsprinzip: Muskelaufbau durch Kraftzuwachs. Braucht hohe Intensität (85–100%), "
            "langsame Exzentriks, Pausen beim Heben, Grinding. Wenige Übungen (3–4), wenige Arbeitssätze (2–3), "
            "kurze Einheiten (35–45 min). Lange Pausen (3–4 min) um Adrenalin nicht zu erhöhen. "
            "Keine Variation nötig – Intensität ist der Schlüssel. Häufigkeit: 5–7x/Woche möglich.\n"
            "Tempo-Empfehlung: Langsame Exzentriks (3–5 Sek.), Pausen unten (1–2 Sek.), explosive Konzentriks.\n"
            "Beispiel-Tempo: 4-1-X-0 (4 Sek. runter, 1 Sek. Pause, explosiv hoch, keine Pause oben).\n"
            "Stressmanagement: Dopamin-Erschöpfung ist das Hauptproblem. Kurze, intensive Erholungsphasen.\n"
            "Schlaf: Klare Abendroutine, Magnesium Glycinat, frühes Abschalten."
        ),
        "en": (
            "NST Type 1A – The Lion (dopamine-driven, neurodominant).\n"
            "Training principle: Build muscle by getting stronger. Needs high intensity (85–100%), "
            "slow eccentrics, paused lifting, grinding. Few exercises (3–4), few work sets (2–3), "
            "short sessions (35–45 min). Long rest intervals (3–4 min) to avoid increasing adrenalin. "
            "No variety needed – intensity is the key. Frequency: 5–7x/week possible.\n"
            "Tempo recommendation: Slow eccentrics (3–5 sec), pauses at bottom (1–2 sec), explosive concentrics.\n"
            "Example tempo: 4-1-X-0 (4 sec down, 1 sec pause, explosive up, no pause at top).\n"
            "Stress: Dopamine depletion is the main issue. Short intense recovery phases.\n"
            "Sleep: Clear evening routine, magnesium glycinate, early shutdown."
        )
    },
    "falcon": {
        "de": (
            "NST-Typ 1B – Der Falke (dopamingetrieben, explosiv, neurodominant).\n"
            "Trainingsprinzip: Muskelaufbau durch mehr Power. Braucht hohe Intensität (80–95%) mit Explosivität, "
            "Stretch-Reflex, Variation und viele verschiedene Aufgaben pro Einheit. 5–6 Übungen, 2–3 Arbeitssätze, "
            "45–60 min. Pausen max. 2 min (Paarungen geben Erholungszeit). Frequenz: 5–6x/Woche.\n"
            "Tempo-Empfehlung: Explosiv konzentrisch, Stretch-Reflex nutzen, schnelle Exzentriks.\n"
            "Beispiel-Tempo: 2-0-X-0 (2 Sek. runter, keine Pause, explosiv hoch, keine Pause oben).\n"
            "Stressmanagement: Kognitive Überlastung vermeiden, Entscheidungsmüdigkeit reduzieren.\n"
            "Schlaf: Schlaftracking, konsistente Schlafzeiten, optimale Schlafumgebung."
        ),
        "en": (
            "NST Type 1B – The Falcon (dopamine-driven, explosive, neurodominant).\n"
            "Training principle: Build muscle by getting more powerful. Needs high intensity (80–95%) with explosiveness, "
            "stretch reflex, variation, and many different tasks per session. 5–6 exercises, 2–3 work sets, "
            "45–60 min. Rest max. 2 min (pairings provide recovery). Frequency: 5–6x/week.\n"
            "Tempo recommendation: Explosive concentric, use stretch reflex, fast eccentrics.\n"
            "Example tempo: 2-0-X-0 (2 sec down, no pause, explosive up, no pause at top).\n"
            "Stress: Avoid cognitive overload, reduce decision fatigue.\n"
            "Sleep: Sleep tracking, consistent sleep times, optimal sleep environment."
        )
    },
    "chameleon": {
        "de": (
            "NST-Typ 2A – Das Chamäleon (neurodominant-muskulär, Abwechslung).\n"
            "Trainingsprinzip: Alles funktioniert – aber nichts funktioniert lange. Braucht Abwechslung "
            "in der Einheit, der Woche, dem Block und zwischen Blöcken. Kombination aus neuralem und "
            "muskulärem Training in jeder Einheit. 5–6 Übungen, 3–4 Arbeitssätze, 60–75 min. "
            "Pausen unter 2 min (kürzeste Pausen aller Typen – Adrenalin ist Stärke). Frequenz: 4–6x/Woche.\n"
            "Tempo-Empfehlung: Alle Tempos funktionieren! Variation ist wichtig.\n"
            "Beispiel-Tempos: 3-1-2-0 (kontrolliert) oder 2-0-X-0 (explosiv) – mix pro Einheit.\n"
            "Ernährung: Carb-Cycling ideal (Abwechslung zwischen Trainings- und Ruhetagen).\n"
            "Stressmanagement: Überstimulation vermeiden, Anpassungsfähigkeit ist Stärke.\n"
            "Schlaf: Flexible Schlafzeiten, aber Mindestschlaf sicherstellen."
        ),
        "en": (
            "NST Type 2A – The Chameleon (neuromuscular, variety-driven).\n"
            "Training principle: Everything works – but nothing works for long. Needs variety "
            "in the session, week, block, and between blocks. Combination of neural and muscular "
            "training in every session. 5–6 exercises, 3–4 work sets, 60–75 min. "
            "Rest under 2 min (shortest rest of all types – adrenalin is a strength). Frequency: 4–6x/week.\n"
            "Tempo recommendation: All tempos work! Variation is key.\n"
            "Example tempos: 3-1-2-0 (controlled) or 2-0-X-0 (explosive) – mix per session.\n"
            "Nutrition: Carb cycling ideal (variety between training and rest days).\n"
            "Stress: Avoid overstimulation, adaptability is a strength.\n"
            "Sleep: Flexible sleep times but ensure minimum sleep."
        )
    },
    "wolf": {
        "de": (
            "NST-Typ 2B – Der Wolf (muskulär, Sensation).\n"
            "Trainingsprinzip: Stärker werden durch größer werden. Braucht Mind-Muscle-Connection, "
            "langsames Tempo, Laktat-Toleranz. Hauptsächlich leichtere Arbeit (50–85%), Fokus auf Pump. "
            "5–6+ Übungen, 3–6 Arbeitssätze, 60–75 min. Kurze Pausen bei muskulärer Arbeit (<2 min), "
            "längere bei neuralem Anteil (3–4 min). Keine Explosivarbeit. Frequenz: 3–6x/Woche.\n"
            "Tempo-Empfehlung: Langsame Tempos, Pausen, Holds. Fokus auf Muskelkontraktion.\n"
            "Beispiel-Tempo: 3-2-2-1 (3 Sek. runter, 2 Sek. Pause unten, 2 Sek. hoch, 1 Sek. Pause oben).\n"
            "Stressmanagement: Isolation ist Hauptstressor – soziale Verbindungen pflegen.\n"
            "Schlaf: Oxytocin-fördernde Abendroutinen, soziale Entspannung."
        ),
        "en": (
            "NST Type 2B – The Wolf (muscular, sensation-driven).\n"
            "Training principle: Get stronger by getting bigger. Needs mind-muscle connection, "
            "slow tempo, lactic acid tolerance. Mostly lighter work (50–85%), focus on pump. "
            "5–6+ exercises, 3–6 work sets, 60–75 min. Short rest for muscular work (<2 min), "
            "longer for neural work (3–4 min). No explosive work. Frequency: 3–6x/week.\n"
            "Tempo recommendation: Slow tempos, pauses, holds. Focus on muscle contraction.\n"
            "Example tempo: 3-2-2-1 (3 sec down, 2 sec pause at bottom, 2 sec up, 1 sec pause at top).\n"
            "Stress: Isolation is the main stressor – maintain social connections.\n"
            "Sleep: Oxytocin-promoting evening routines, social relaxation."
        )
    },
    "owl": {
        "de": (
            "NST-Typ 3 – Die Eule (strukturell, Kontrolle).\n"
            "Trainingsprinzip: Kann nur hart trainieren wenn alles unter Kontrolle ist. Braucht "
            "Wiederholung, Widerstand, Ausdauer, Fokus, Planverfolgung. Wenige Übungen (3–4), "
            "3–4 Arbeitssätze, 45–75 min. Lange Pausen (3–4 min), aber aktiv (Mobilität, SMR, Visualisierung). "
            "Intensität leicht (50–80%), Fokus auf Präzision und motorisches Lernen. Keine Variation. Frequenz: 3–4x/Woche.\n"
            "Tempo-Empfehlung: Langsame Tempos, Pausen, Holds. Präzision über Intensität.\n"
            "Beispiel-Tempo: 4-2-3-1 (4 Sek. runter, 2 Sek. Pause, 3 Sek. hoch, 1 Sek. Pause oben).\n"
            "Stressmanagement: Overthinking ist Hauptproblem – Entscheidungsrahmen setzen.\n"
            "Schlaf: Schlafarchitektur verstehen, Tiefschlaf optimieren."
        ),
        "en": (
            "NST Type 3 – The Owl (structural, control-driven).\n"
            "Training principle: Can only push hard when in perfect control. Needs repetitive work, "
            "resistance, endurance, focus, following a plan. Few exercises (3–4), 3–4 work sets, "
            "45–75 min. Long rest (3–4 min), but active (mobility, SMR, visualisation). "
            "Light intensity (50–80%), focus on precision and motor learning. No variation. Frequency: 3–4x/week.\n"
            "Tempo recommendation: Slow tempos, pauses, holds. Precision over intensity.\n"
            "Example tempo: 4-2-3-1 (4 sec down, 2 sec pause, 3 sec up, 1 sec pause at top).\n"
            "Stress: Overthinking is the main issue – set decision frameworks.\n"
            "Sleep: Understand sleep architecture, optimise deep sleep."
        )
    }
}

GOAL_LABELS = {
    "fat_loss":    {"de": "Fettreduktion",         "en": "Fat Loss"},
    "muscle":      {"de": "Muskelaufbau",          "en": "Muscle Building"},
    "energy":      {"de": "Mehr Energie",          "en": "More Energy"},
    "health":      {"de": "Allgemeine Gesundheit", "en": "General Health"},
}

PILLAR_LABELS = {
    "training":  {"de": "Training",          "en": "Training"},
    "nutrition": {"de": "Ernährung",         "en": "Nutrition"},
    "stress":    {"de": "Stressmanagement",  "en": "Stress Management"},
    "sleep":     {"de": "Schlafoptimierung", "en": "Sleep Optimisation"},
}

NST_NAMES = {
    "lion":       {"de": "Löwe",      "en": "Lion"},
    "falcon":     {"de": "Falke",     "en": "Falcon"},
    "chameleon":  {"de": "Chamäleon", "en": "Chameleon"},
    "wolf":       {"de": "Wolf",      "en": "Wolf"},
    "owl":        {"de": "Eule",      "en": "Owl"},
}

# ── Tempo defaults per NST type ───────────────────────────────────────────────
NST_TEMPO_DEFAULTS = {
    "lion":      {"primary": "4-1-X-0", "secondary": "3-1-2-0"},
    "falcon":    {"primary": "2-0-X-0", "secondary": "1-0-X-0"},
    "chameleon": {"primary": "3-1-2-0", "secondary": "2-0-X-0"},
    "wolf":      {"primary": "3-2-2-1", "secondary": "4-1-2-1"},
    "owl":       {"primary": "4-2-3-1", "secondary": "3-1-3-1"},
}

NST_REST_DEFAULTS = {
    "lion":      "3–4 min",
    "falcon":    "60–90 sek",
    "chameleon": "60–90 sek",
    "wolf":      "45–90 sek",
    "owl":       "3–4 min",
}


def build_system_prompt(lang: str) -> str:
    if lang == "de":
        return (
            "Du bist René Rusch, zertifizierter Natural Signature Typing Coach und "
            "Ernährungscoach bei NeuroHealthMastery. Du erstellst hochindividuelle, "
            "wissenschaftlich fundierte Coaching-Pläne auf Deutsch, basierend auf der "
            "Thibarmy-Neurotyping-Methodik von Christian Thibaudeau. "
            "Deine Pläne sind konkret, umsetzbar und auf den jeweiligen NST-Typ abgestimmt. "
            "Antworte IMMER als valides JSON-Objekt gemäß dem vorgegebenen Schema. "
            "Verwende korrekte deutsche Umlaute (ä, ö, ü, ß). "
            "Kein Markdown außerhalb von JSON-Strings. "
            "Tempo-Notation: 4 Zahlen = Exzentrisch.Isometrisch-unten.Konzentrisch.Isometrisch-oben "
            "(z.B. 4-1-2-0 = 4 Sek. runter, 1 Sek. Pause, 2 Sek. hoch, keine Pause oben). "
            "X = so schnell wie möglich (explosiv)."
        )
    else:
        return (
            "You are René Rusch, certified Natural Signature Typing Coach and "
            "Nutrition Coach at NeuroHealthMastery. You create highly individualised, "
            "science-based coaching plans in English, based on Christian Thibaudeau's "
            "Thibarmy Neurotyping methodology. "
            "Your plans are concrete, actionable, and tailored to the client's NST type. "
            "ALWAYS respond as a valid JSON object according to the provided schema. "
            "No markdown outside JSON strings. "
            "Tempo notation: 4 numbers = Eccentric.Isometric-bottom.Concentric.Isometric-top "
            "(e.g. 4-1-2-0 = 4 sec down, 1 sec pause, 2 sec up, no pause at top). "
            "X = as fast as possible (explosive)."
        )


def build_user_prompt(client_data: dict, feedback: dict = None) -> str:
    lang = client_data.get("lang", "de")
    nst = client_data["nst_type"]
    name = client_data["name"]
    goal_key = client_data["goal"]
    pillars = client_data.get("pillars", ["training", "nutrition", "stress", "sleep"])
    duration = int(client_data.get("duration", 4))
    calories = client_data.get("calories", "")
    train_days = client_data.get("train_days", "3")
    notes = client_data.get("notes", "")

    nst_profile = NST_PROFILES.get(nst, {}).get(lang, "")
    goal_label = GOAL_LABELS.get(goal_key, {}).get(lang, goal_key)
    nst_name = NST_NAMES.get(nst, {}).get(lang, nst)
    tempo_default = NST_TEMPO_DEFAULTS.get(nst, {})
    rest_default = NST_REST_DEFAULTS.get(nst, "2–3 min")

    pillar_list = [PILLAR_LABELS.get(p, {}).get(lang, p) for p in pillars]

    # ── Calorie calculation hint for nutrition ────────────────────────────────
    cal_hint = ""
    if calories:
        cal_hint = f"{calories} kcal/Tag (vom Coach vorgegeben)" if lang == "de" else f"{calories} kcal/day (set by coach)"
    else:
        if goal_key == "fat_loss":
            cal_hint = "Körpergewicht (kg) × 22 kcal (Fettreduktion)" if lang == "de" else "Bodyweight (kg) × 22 kcal (fat loss)"
        elif goal_key == "muscle":
            cal_hint = "Körpergewicht (kg) × 33 kcal (Muskelaufbau)" if lang == "de" else "Bodyweight (kg) × 33 kcal (muscle gain)"
        else:
            cal_hint = "Erhaltungskalorien berechnen" if lang == "de" else "Calculate maintenance calories"

    if lang == "de":
        prompt = f"""Erstelle einen vollständigen {duration}-Wochen-Coaching-Plan für:

**Kunde:** {name}
**NST-Typ:** {nst_name} (Natural Signature Type)
**Ziel:** {goal_label}
**Aktive Säulen:** {', '.join(pillar_list)}
**Trainingsdauer:** {duration} Wochen
**Trainingstage pro Woche:** {train_days}
**Kalorien:** {cal_hint}
{f'**Besonderheiten/Notizen:** {notes}' if notes else ''}

**NST-Profil und Trainingsempfehlungen:**
{nst_profile}

**Standard-Tempo für diesen Typ:** Primär: {tempo_default.get('primary', '3-1-2-0')}, Sekundär: {tempo_default.get('secondary', '2-0-X-0')}
**Standard-Pause für diesen Typ:** {rest_default}
"""
        if feedback:
            prompt += f"\n**Feedback des Kunden (für Plananpassung):**\n"
            for q, a in feedback.items():
                prompt += f"- {q}: {a}\n"
            prompt += "\nBitte berücksichtige dieses Feedback vollständig im neuen Plan.\n"

        prompt += f"""
Erstelle das JSON-Objekt mit folgender Struktur (NUR die gewählten Säulen einbeziehen):

{{
  "summary": "Kurze persönliche Einleitung für {name} (2-3 Sätze, motivierend, auf NST-Typ eingehen)",
  
  "training": {{
    "overview": "Kurze Übersicht des Trainingsansatzes (2-3 Sätze)",
    
    "training_concept": {{
      "title": "Trainingskonzept für {nst_name}",
      "why_this_plan": "Erkläre WARUM dieser Plan für den {nst_name}-Typ optimal ist (3-4 Sätze, Neurotyping-Prinzipien)",
      "why_these_exercises": "Erkläre WARUM genau diese Übungen gewählt wurden (3-4 Sätze, Bewegungsmuster, NST-Typ)",
      "why_this_tempo": "Erkläre WARUM dieses Tempo für den {nst_name}-Typ ideal ist (2-3 Sätze, neurologische Basis)",
      "progression": "Wie soll der Kunde in den {duration} Wochen progressieren? (2-3 Sätze)",
      "key_principles": ["Prinzip 1", "Prinzip 2", "Prinzip 3"]
    }},
    
    "weeks": [
      {{
        "week": 1,
        "label": "Woche 1 – [Thema, z.B. Akkumulation/Intensivierung]",
        "sessions": [
          {{
            "day": "Montag",
            "type": "Kraft / Hypertrophie / Kraft-Hypertrophie / Erholung",
            "duration_min": 50,
            "exercises": [
              {{
                "name": "Übungsname (konkret, z.B. Kniebeugen mit Langhantel)",
                "sets": 4,
                "reps": "6-8",
                "tempo": "{tempo_default.get('primary', '3-1-2-0')}",
                "rest": "{rest_default}",
                "note": "Optionaler Hinweis zur Ausführung"
              }}
            ]
          }}
        ]
      }}
    ],
    "tips": ["Trainingsspezifischer Tipp 1", "Tipp 2", "Tipp 3"]
  }},
  
  "nutrition": {{
    "overview": "Kurze Übersicht des Ernährungsansatzes mit Carb-Cycling-Erklärung (2-3 Sätze)",
    "approach": "carb_cycling",
    "workout_day": {{
      "calories": 0,
      "protein_g": 0,
      "carbs_g": 0,
      "fat_g": 0,
      "macro_ratio": "50% Kohlenhydrate / 50% Fett (der verbleibenden Kalorien nach Protein)",
      "meals": [
        {{"time": "07:00", "name": "Frühstück", "description": "Konkrete Lebensmittel mit Mengen (z.B. 3 Eier, 150g Rindersteak, 2 Tassen Spinat)", "calories": 500, "protein_g": 40, "carbs_g": 5, "fat_g": 25}},
        {{"time": "12:30", "name": "Mittagessen", "description": "Konkrete Lebensmittel mit Mengen", "calories": 600, "protein_g": 50, "carbs_g": 10, "fat_g": 20}},
        {{"time": "16:00", "name": "Pre-Workout Snack", "description": "Leicht verdaulich, Protein + wenig Fett", "calories": 300, "protein_g": 30, "carbs_g": 20, "fat_g": 5}},
        {{"time": "19:30", "name": "Post-Workout / Abendessen", "description": "Hauptteil der Kohlenhydrate am Abend nach dem Training", "calories": 650, "protein_g": 50, "carbs_g": 60, "fat_g": 10}},
        {{"time": "22:00", "name": "Abend-Snack (optional)", "description": "Protein-Shake oder leichter Snack", "calories": 200, "protein_g": 25, "carbs_g": 5, "fat_g": 5}}
      ]
    }},
    "rest_day": {{
      "calories": 0,
      "protein_g": 0,
      "carbs_g": 0,
      "fat_g": 0,
      "macro_ratio": "70% Kohlenhydrate / 30% Fett (der verbleibenden Kalorien nach Protein)",
      "meals": [
        {{"time": "08:00", "name": "Frühstück", "description": "Mehr Kohlenhydrate am Ruhetag (z.B. Haferflocken, Beeren, Eier)", "calories": 500, "protein_g": 40, "carbs_g": 50, "fat_g": 10}},
        {{"time": "13:00", "name": "Mittagessen", "description": "Reis/Süßkartoffel + mageres Protein + Gemüse", "calories": 600, "protein_g": 55, "carbs_g": 65, "fat_g": 8}},
        {{"time": "16:00", "name": "Snack", "description": "Obst + Protein", "calories": 250, "protein_g": 25, "carbs_g": 30, "fat_g": 3}},
        {{"time": "19:00", "name": "Abendessen", "description": "Leichtes Abendessen, weniger Kalorien als Trainingstag", "calories": 450, "protein_g": 45, "carbs_g": 40, "fat_g": 8}}
      ]
    }},
    "supplements": ["Supplement 1 – Dosierung & Timing", "Supplement 2 – Dosierung & Timing"],
    "tips": ["Ernährungstipp 1 (spezifisch für {nst_name})", "Tipp 2", "Tipp 3"]
  }},
  
  "stress": {{
    "overview": "Kurze Übersicht des Stressmanagement-Ansatzes für den {nst_name}-Typ (2-3 Sätze)",
    "daily_routine": [
      {{"time": "morgens", "action": "Konkrete Maßnahme", "duration_min": 10, "description": "Detaillierte Beschreibung"}},
      {{"time": "mittags", "action": "Konkrete Maßnahme", "duration_min": 5, "description": "Details"}},
      {{"time": "abends", "action": "Konkrete Maßnahme", "duration_min": 15, "description": "Details"}}
    ],
    "techniques": [
      {{"name": "Technikname", "description": "Detaillierte Beschreibung der Technik", "when": "Wann genau anwenden"}}
    ],
    "tips": ["Stress-Tipp 1 (NST-spezifisch)", "Tipp 2"]
  }},
  
  "sleep": {{
    "overview": "Kurze Übersicht der Schlafoptimierung für den {nst_name}-Typ (2-3 Sätze)",
    "target_hours": 8,
    "bedtime": "22:30",
    "wake_time": "06:30",
    "evening_routine": [
      {{"time": "21:00", "action": "Konkrete Maßnahme", "description": "Details"}},
      {{"time": "22:00", "action": "Konkrete Maßnahme", "description": "Details"}}
    ],
    "environment": ["Schlafumgebungs-Optimierung 1", "Optimierung 2", "Optimierung 3"],
    "supplements": ["Schlaf-Supplement 1 – Dosierung & Timing (z.B. Magnesium Glycinat 400mg, 30 min vor dem Schlafen)"],
    "tips": ["Schlaf-Tipp 1 (NST-spezifisch)", "Tipp 2"]
  }}
}}

WICHTIG:
1. Gib NUR das JSON zurück, kein Text davor oder danach.
2. Erstelle {duration} Wochen mit je {train_days} Trainingstagen pro Woche.
3. Jede Übung MUSS Tempo und Pause haben (passend zum {nst_name}-Typ).
4. Das Trainingskonzept (training_concept) MUSS vor den Wochen kommen.
5. Nutrition: Berechne die Makros für Trainings- und Ruhetage nach dem Carb-Cycling-Prinzip.
6. Verwende konkrete Lebensmittel mit Mengenangaben in den Mahlzeiten.
7. Passe ALLES an den {nst_name}-Typ an (Übungsauswahl, Tempo, Pausen, Ernährung, Stress, Schlaf)."""

    else:
        # English prompt
        prompt = f"""Create a complete {duration}-week coaching plan for:

**Client:** {name}
**NST Type:** {nst_name} (Natural Signature Type)
**Goal:** {goal_label}
**Active Pillars:** {', '.join(pillar_list)}
**Plan Duration:** {duration} weeks
**Training Days per Week:** {train_days}
**Calories:** {cal_hint}
{f'**Special Notes:** {notes}' if notes else ''}

**NST Type Profile and Training Recommendations:**
{nst_profile}

**Default Tempo for this Type:** Primary: {tempo_default.get('primary', '3-1-2-0')}, Secondary: {tempo_default.get('secondary', '2-0-X-0')}
**Default Rest for this Type:** {rest_default}
"""
        if feedback:
            prompt += f"\n**Client Feedback (for plan adjustment):**\n"
            for q, a in feedback.items():
                prompt += f"- {q}: {a}\n"
            prompt += "\nPlease fully incorporate this feedback into the new plan.\n"

        prompt += f"""
Create the JSON object with the following structure (include ONLY selected pillars):

{{
  "summary": "Short personal introduction for {name} (2-3 sentences, motivating, reference NST type)",
  
  "training": {{
    "overview": "Brief overview of the training approach (2-3 sentences)",
    
    "training_concept": {{
      "title": "Training Concept for {nst_name}",
      "why_this_plan": "Explain WHY this plan is optimal for the {nst_name} type (3-4 sentences, neurotyping principles)",
      "why_these_exercises": "Explain WHY exactly these exercises were chosen (3-4 sentences, movement patterns, NST type)",
      "why_this_tempo": "Explain WHY this tempo is ideal for the {nst_name} type (2-3 sentences, neurological basis)",
      "progression": "How should the client progress over {duration} weeks? (2-3 sentences)",
      "key_principles": ["Principle 1", "Principle 2", "Principle 3"]
    }},
    
    "weeks": [
      {{
        "week": 1,
        "label": "Week 1 – [Theme, e.g. Accumulation/Intensification]",
        "sessions": [
          {{
            "day": "Monday",
            "type": "Strength / Hypertrophy / Strength-Hypertrophy / Recovery",
            "duration_min": 50,
            "exercises": [
              {{
                "name": "Exercise name (specific, e.g. Barbell Back Squat)",
                "sets": 4,
                "reps": "6-8",
                "tempo": "{tempo_default.get('primary', '3-1-2-0')}",
                "rest": "{rest_default}",
                "note": "Optional execution note"
              }}
            ]
          }}
        ]
      }}
    ],
    "tips": ["Training-specific tip 1", "Tip 2", "Tip 3"]
  }},
  
  "nutrition": {{
    "overview": "Brief overview of the nutrition approach with carb cycling explanation (2-3 sentences)",
    "approach": "carb_cycling",
    "workout_day": {{
      "calories": 0,
      "protein_g": 0,
      "carbs_g": 0,
      "fat_g": 0,
      "macro_ratio": "50% Carbs / 50% Fat (of remaining calories after protein)",
      "meals": [
        {{"time": "07:00", "name": "Breakfast", "description": "Specific foods with amounts (e.g. 3 whole eggs, 150g sirloin steak, 2 cups spinach)", "calories": 500, "protein_g": 40, "carbs_g": 5, "fat_g": 25}},
        {{"time": "12:30", "name": "Lunch", "description": "Specific foods with amounts", "calories": 600, "protein_g": 50, "carbs_g": 10, "fat_g": 20}},
        {{"time": "16:00", "name": "Pre-Workout Snack", "description": "Easy to digest, protein + low fat", "calories": 300, "protein_g": 30, "carbs_g": 20, "fat_g": 5}},
        {{"time": "19:30", "name": "Post-Workout / Dinner", "description": "Main carbs in the evening after training", "calories": 650, "protein_g": 50, "carbs_g": 60, "fat_g": 10}},
        {{"time": "22:00", "name": "Evening Snack (optional)", "description": "Protein shake or light snack", "calories": 200, "protein_g": 25, "carbs_g": 5, "fat_g": 5}}
      ]
    }},
    "rest_day": {{
      "calories": 0,
      "protein_g": 0,
      "carbs_g": 0,
      "fat_g": 0,
      "macro_ratio": "70% Carbs / 30% Fat (of remaining calories after protein)",
      "meals": [
        {{"time": "08:00", "name": "Breakfast", "description": "More carbs on rest day (e.g. oatmeal, berries, eggs)", "calories": 500, "protein_g": 40, "carbs_g": 50, "fat_g": 10}},
        {{"time": "13:00", "name": "Lunch", "description": "Rice/sweet potato + lean protein + vegetables", "calories": 600, "protein_g": 55, "carbs_g": 65, "fat_g": 8}},
        {{"time": "16:00", "name": "Snack", "description": "Fruit + protein", "calories": 250, "protein_g": 25, "carbs_g": 30, "fat_g": 3}},
        {{"time": "19:00", "name": "Dinner", "description": "Light dinner, fewer calories than training day", "calories": 450, "protein_g": 45, "carbs_g": 40, "fat_g": 8}}
      ]
    }},
    "supplements": ["Supplement 1 – Dosage & Timing", "Supplement 2 – Dosage & Timing"],
    "tips": ["Nutrition tip 1 (specific for {nst_name})", "Tip 2", "Tip 3"]
  }},
  
  "stress": {{
    "overview": "Brief overview of stress management approach for the {nst_name} type (2-3 sentences)",
    "daily_routine": [
      {{"time": "morning", "action": "Specific action", "duration_min": 10, "description": "Detailed description"}},
      {{"time": "midday", "action": "Specific action", "duration_min": 5, "description": "Details"}},
      {{"time": "evening", "action": "Specific action", "duration_min": 15, "description": "Details"}}
    ],
    "techniques": [
      {{"name": "Technique name", "description": "Detailed description of the technique", "when": "When exactly to apply"}}
    ],
    "tips": ["Stress tip 1 (NST-specific)", "Tip 2"]
  }},
  
  "sleep": {{
    "overview": "Brief overview of sleep optimisation for the {nst_name} type (2-3 sentences)",
    "target_hours": 8,
    "bedtime": "22:30",
    "wake_time": "06:30",
    "evening_routine": [
      {{"time": "21:00", "action": "Specific action", "description": "Details"}},
      {{"time": "22:00", "action": "Specific action", "description": "Details"}}
    ],
    "environment": ["Sleep environment optimisation 1", "Optimisation 2", "Optimisation 3"],
    "supplements": ["Sleep supplement 1 – Dosage & Timing (e.g. Magnesium Glycinate 400mg, 30 min before sleep)"],
    "tips": ["Sleep tip 1 (NST-specific)", "Tip 2"]
  }}
}}

IMPORTANT:
1. Return ONLY the JSON, no text before or after.
2. Create {duration} weeks with {train_days} training days per week.
3. Every exercise MUST have tempo and rest (matching the {nst_name} type).
4. The training concept (training_concept) MUST come before the weeks.
5. Nutrition: Calculate macros for training and rest days using the carb cycling principle.
6. Use specific foods with quantities in the meals.
7. Adapt EVERYTHING to the {nst_name} type (exercise selection, tempo, rest, nutrition, stress, sleep)."""

    return prompt


async def generate_plan(client_data: dict, feedback: dict = None) -> dict:
    """Generate a coaching plan using Gemini 2.5 Flash Lite. Returns parsed JSON dict."""
    lang = client_data.get("lang", "de")
    system_prompt = build_system_prompt(lang)
    user_prompt = build_user_prompt(client_data, feedback)

    full_prompt = system_prompt + "\n\n" + user_prompt
    response = _gemini_client.models.generate_content(
        model=_model,
        contents=full_prompt,
        config=_genai.types.GenerateContentConfig(
            temperature=0.7,
            max_output_tokens=16000,
            response_mime_type="application/json",
        )
    )

    raw = response.text
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract JSON from response
        import re
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Could not parse AI response as JSON: {raw[:200]}")
