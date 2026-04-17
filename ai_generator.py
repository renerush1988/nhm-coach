# -*- coding: utf-8 -*-
"""
ai_generator.py — NHM Coach Backoffice
Generates personalised coaching plans using GPT-4.1.
All plans are tailored to the client's NST type, goal, and selected pillars.
"""

import os
import json
from openai import OpenAI

# Nutze Gemini API Key wenn vorhanden, sonst OpenAI
_gemini_key = os.environ.get("GEMINI_API_KEY", "")
_openai_key = os.environ.get("OPENAI_API_KEY", "")

if _gemini_key:
    # Gemini via OpenAI-kompatibler Endpunkt
    client = OpenAI(
        api_key=_gemini_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    _model = "gemini-2.0-flash"
else:
    client = OpenAI(api_key=_openai_key)
    _model = "gpt-4.1"

# ── NST Type Profiles ─────────────────────────────────────────────────────────

NST_PROFILES = {
    "lion": {
        "de": (
            "Der Löwe ist dopamingetrieben, wettbewerbsorientiert und braucht schnelle, "
            "sichtbare Ergebnisse. Er liebt intensive, kurze Sprints und verliert bei "
            "langweiligen, moderaten Ansätzen die Motivation. Trainingsempfehlung: HIIT, "
            "schweres Krafttraining, klare Leistungsziele. Ernährung: hohe Protein-Zufuhr, "
            "Kohlenhydrate nur nach dem Training. Stress: Dopamin-Erschöpfung ist das "
            "Hauptproblem – kurze intensive Erholungsphasen einbauen. Schlaf: "
            "Abendroutine mit klarem Abschalter, Magnesium Glycinat."
        ),
        "en": (
            "The Lion is dopamine-driven, competitive, and needs fast, visible results. "
            "Thrives on intense, short sprints and loses motivation with slow, moderate "
            "approaches. Training: HIIT, heavy strength training, clear performance goals. "
            "Nutrition: high protein intake, carbs only post-workout. Stress: dopamine "
            "depletion is the main issue – build in short intense recovery phases. "
            "Sleep: evening routine with a clear shutdown trigger, magnesium glycinate."
        )
    },
    "falcon": {
        "de": (
            "Der Falke ist analytisch, effizient und optimierungsgetrieben. Er braucht "
            "klare Daten, Strukturen und messbare Fortschritte. Training: periodisiertes "
            "Krafttraining mit klarer Progression. Ernährung: präzises Tracking, "
            "Makro-Optimierung. Stress: kognitive Überlastung vermeiden, "
            "Entscheidungsmüdigkeit reduzieren. Schlaf: Schlaftracking, optimale "
            "Schlafumgebung, konsistente Schlafzeiten."
        ),
        "en": (
            "The Falcon is analytical, efficient, and optimisation-driven. Needs clear "
            "data, structure, and measurable progress. Training: periodised strength "
            "training with clear progression. Nutrition: precise tracking, macro "
            "optimisation. Stress: avoid cognitive overload, reduce decision fatigue. "
            "Sleep: sleep tracking, optimal sleep environment, consistent sleep times."
        )
    },
    "chameleon": {
        "de": (
            "Das Chamäleon ist flexibel, anpassungsfähig und kontextabhängig. Es braucht "
            "Abwechslung und reagiert gut auf Routinen die sich anpassen lassen. Training: "
            "abwechslungsreiche Trainingsformen, keine starre Routine. Ernährung: "
            "flexible Ernährungsstrategien, intuitive Ansätze. Stress: "
            "Anpassungsfähigkeit ist eine Stärke – Überstimulation vermeiden. "
            "Schlaf: flexible Schlafzeiten, aber Mindestschlaf sicherstellen."
        ),
        "en": (
            "The Chameleon is flexible, adaptable, and context-dependent. Needs variety "
            "and responds well to routines that can be adjusted. Training: varied "
            "training formats, no rigid routine. Nutrition: flexible dietary strategies, "
            "intuitive approaches. Stress: adaptability is a strength – avoid "
            "overstimulation. Sleep: flexible sleep times but ensure minimum sleep."
        )
    },
    "wolf": {
        "de": (
            "Der Wolf ist sozial, teamorientiert und braucht Gemeinschaft und Unterstützung. "
            "Er funktioniert am besten mit einem Partner oder einer Gruppe. Training: "
            "Gruppentraining, Trainingspartner, soziale Accountability. Ernährung: "
            "gemeinsame Mahlzeiten, soziale Essenssituationen einplanen. Stress: "
            "Isolation ist der Hauptstressor – soziale Verbindungen pflegen. "
            "Schlaf: Oxytocin-fördernde Abendroutinen, soziale Entspannung."
        ),
        "en": (
            "The Wolf is social, team-oriented, and needs community and support. "
            "Functions best with a partner or group. Training: group training, "
            "training partner, social accountability. Nutrition: plan for shared "
            "meals and social eating situations. Stress: isolation is the main "
            "stressor – maintain social connections. Sleep: oxytocin-promoting "
            "evening routines, social relaxation."
        )
    },
    "owl": {
        "de": (
            "Die Eule ist tiefgründig, reflektiert und braucht Sinn und Verständnis. "
            "Sie recherchiert gründlich bevor sie handelt. Training: wissenschaftlich "
            "fundierte Methoden, Verständnis der Mechanismen. Ernährung: evidenzbasierte "
            "Ernährungsstrategien, Verstehen der Biochemie. Stress: Overthinking ist "
            "das Hauptproblem – Entscheidungsrahmen setzen. Schlaf: Schlafarchitektur "
            "verstehen, Tiefschlaf optimieren."
        ),
        "en": (
            "The Owl is deep, reflective, and needs meaning and understanding. "
            "Researches thoroughly before acting. Training: science-based methods, "
            "understanding the mechanisms. Nutrition: evidence-based dietary strategies, "
            "understanding the biochemistry. Stress: overthinking is the main issue – "
            "set decision frameworks. Sleep: understand sleep architecture, "
            "optimise deep sleep."
        )
    }
}

GOAL_LABELS = {
    "fat_loss":    {"de": "Fettreduktion",    "en": "Fat Loss"},
    "muscle":      {"de": "Muskelaufbau",     "en": "Muscle Building"},
    "energy":      {"de": "Mehr Energie",     "en": "More Energy"},
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


def build_system_prompt(lang: str) -> str:
    if lang == "de":
        return (
            "Du bist René Rusch, zertifizierter Natural Signature Typing Coach und "
            "Ernährungscoach bei NeuroHealthMastery. Du erstellst hochindividuelle, "
            "wissenschaftlich fundierte Coaching-Pläne auf Deutsch. "
            "Deine Pläne sind konkret, umsetzbar und auf den jeweiligen NST-Typ abgestimmt. "
            "Antworte IMMER als valides JSON-Objekt gemäß dem vorgegebenen Schema. "
            "Verwende korrekte deutsche Umlaute (ä, ö, ü, ß). "
            "Kein Markdown außerhalb von JSON-Strings."
        )
    else:
        return (
            "You are René Rusch, certified Natural Signature Typing Coach and "
            "Nutrition Coach at NeuroHealthMastery. You create highly individualised, "
            "science-based coaching plans in English. "
            "Your plans are concrete, actionable, and tailored to the client's NST type. "
            "ALWAYS respond as a valid JSON object according to the provided schema. "
            "No markdown outside JSON strings."
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

    pillar_list = [PILLAR_LABELS.get(p, {}).get(lang, p) for p in pillars]

    if lang == "de":
        prompt = f"""Erstelle einen vollständigen {duration}-Wochen-Coaching-Plan für:

**Kunde:** {name}
**NST-Typ:** {nst_name} (Natural Signature Type)
**Ziel:** {goal_label}
**Aktive Säulen:** {', '.join(pillar_list)}
**Trainingsdauer:** {duration} Wochen
**Trainingstage pro Woche:** {train_days}
{f'**Kalorien-Ziel:** {calories} kcal/Tag' if calories else ''}
{f'**Besonderheiten/Notizen:** {notes}' if notes else ''}

**NST-Profil des Löwen/Typs:**
{nst_profile}
"""
        if feedback:
            prompt += f"\n**Feedback des Kunden (für Plananpassung):**\n"
            for q, a in feedback.items():
                prompt += f"- {q}: {a}\n"
            prompt += "\nBitte berücksichtige dieses Feedback vollständig im neuen Plan.\n"

        prompt += f"""
Erstelle das JSON-Objekt mit folgender Struktur (nur die gewählten Säulen einbeziehen):

{{
  "summary": "Kurze persönliche Einleitung für {name} (2-3 Sätze, motivierend)",
  "training": {{  // nur wenn 'training' in den Säulen
    "overview": "Kurze Übersicht des Trainingsansatzes",
    "weeks": [
      {{
        "week": 1,
        "label": "Woche 1 – [Thema]",
        "sessions": [
          {{
            "day": "Montag",
            "type": "Kraft / HIIT / Ausdauer / Erholung",
            "duration_min": 45,
            "exercises": [
              {{"name": "Übungsname", "sets": 4, "reps": "8-10", "note": "optional"}}
            ]
          }}
        ]
      }}
    ],
    "tips": ["Tipp 1", "Tipp 2", "Tipp 3"]
  }},
  "nutrition": {{  // nur wenn 'nutrition' in den Säulen
    "overview": "Kurze Übersicht des Ernährungsansatzes",
    "daily_calories": {calories if calories else "nach Bedarf berechnet"},
    "macros": {{"protein_g": 0, "carbs_g": 0, "fat_g": 0}},
    "meal_plan": [
      {{
        "day_type": "Trainingstag",
        "meals": [
          {{"time": "07:00", "name": "Frühstück", "description": "Beschreibung", "calories": 500, "protein_g": 40}},
          {{"time": "12:30", "name": "Mittagessen", "description": "Beschreibung", "calories": 700, "protein_g": 50}},
          {{"time": "16:00", "name": "Pre-Workout Snack", "description": "Beschreibung", "calories": 300, "protein_g": 25}},
          {{"time": "19:30", "name": "Abendessen", "description": "Beschreibung", "calories": 600, "protein_g": 45}}
        ]
      }},
      {{
        "day_type": "Ruhetag",
        "meals": [
          {{"time": "08:00", "name": "Frühstück", "description": "Beschreibung", "calories": 450, "protein_g": 35}},
          {{"time": "13:00", "name": "Mittagessen", "description": "Beschreibung", "calories": 650, "protein_g": 45}},
          {{"time": "19:00", "name": "Abendessen", "description": "Beschreibung", "calories": 550, "protein_g": 40}}
        ]
      }}
    ],
    "supplements": ["Supplement 1 – Dosierung & Timing", "Supplement 2"],
    "tips": ["Ernährungstipp 1", "Tipp 2", "Tipp 3"]
  }},
  "stress": {{  // nur wenn 'stress' in den Säulen
    "overview": "Kurze Übersicht des Stressmanagement-Ansatzes",
    "daily_routine": [
      {{"time": "morgens", "action": "Maßnahme", "duration_min": 10, "description": "Details"}},
      {{"time": "abends", "action": "Maßnahme", "duration_min": 15, "description": "Details"}}
    ],
    "techniques": [
      {{"name": "Technikname", "description": "Beschreibung", "when": "Wann anwenden"}}
    ],
    "tips": ["Tipp 1", "Tipp 2"]
  }},
  "sleep": {{  // nur wenn 'sleep' in den Säulen
    "overview": "Kurze Übersicht der Schlafoptimierung",
    "target_hours": 8,
    "bedtime": "22:30",
    "wake_time": "06:30",
    "evening_routine": [
      {{"time": "21:00", "action": "Maßnahme", "description": "Details"}}
    ],
    "environment": ["Umgebungsoptimierung 1", "Optimierung 2"],
    "supplements": ["Schlaf-Supplement 1 – Dosierung & Timing"],
    "tips": ["Schlaff-Tipp 1", "Tipp 2"]
  }}
}}

Wichtig: Gib NUR das JSON zurück, kein Text davor oder danach."""
    else:
        # English prompt (same structure)
        prompt = f"""Create a complete {duration}-week coaching plan for:

**Client:** {name}
**NST Type:** {nst_name} (Natural Signature Type)
**Goal:** {goal_label}
**Active Pillars:** {', '.join(pillar_list)}
**Plan Duration:** {duration} weeks
**Training Days per Week:** {train_days}
{f'**Calorie Target:** {calories} kcal/day' if calories else ''}
{f'**Special Notes:** {notes}' if notes else ''}

**NST Type Profile:**
{nst_profile}
"""
        if feedback:
            prompt += f"\n**Client Feedback (for plan adjustment):**\n"
            for q, a in feedback.items():
                prompt += f"- {q}: {a}\n"
            prompt += "\nPlease fully incorporate this feedback into the new plan.\n"

        prompt += f"""
Create the JSON object with the following structure (include only selected pillars):

{{
  "summary": "Short personal introduction for {name} (2-3 sentences, motivating)",
  "training": {{
    "overview": "Brief overview of the training approach",
    "weeks": [
      {{
        "week": 1,
        "label": "Week 1 – [Theme]",
        "sessions": [
          {{
            "day": "Monday",
            "type": "Strength / HIIT / Cardio / Recovery",
            "duration_min": 45,
            "exercises": [
              {{"name": "Exercise name", "sets": 4, "reps": "8-10", "note": "optional"}}
            ]
          }}
        ]
      }}
    ],
    "tips": ["Tip 1", "Tip 2", "Tip 3"]
  }},
  "nutrition": {{
    "overview": "Brief overview of the nutrition approach",
    "daily_calories": {calories if calories else "calculated based on needs"},
    "macros": {{"protein_g": 0, "carbs_g": 0, "fat_g": 0}},
    "meal_plan": [
      {{
        "day_type": "Training Day",
        "meals": [
          {{"time": "07:00", "name": "Breakfast", "description": "Description", "calories": 500, "protein_g": 40}},
          {{"time": "12:30", "name": "Lunch", "description": "Description", "calories": 700, "protein_g": 50}},
          {{"time": "16:00", "name": "Pre-Workout Snack", "description": "Description", "calories": 300, "protein_g": 25}},
          {{"time": "19:30", "name": "Dinner", "description": "Description", "calories": 600, "protein_g": 45}}
        ]
      }},
      {{
        "day_type": "Rest Day",
        "meals": [
          {{"time": "08:00", "name": "Breakfast", "description": "Description", "calories": 450, "protein_g": 35}},
          {{"time": "13:00", "name": "Lunch", "description": "Description", "calories": 650, "protein_g": 45}},
          {{"time": "19:00", "name": "Dinner", "description": "Description", "calories": 550, "protein_g": 40}}
        ]
      }}
    ],
    "supplements": ["Supplement 1 – Dosage & Timing", "Supplement 2"],
    "tips": ["Nutrition tip 1", "Tip 2", "Tip 3"]
  }},
  "stress": {{
    "overview": "Brief overview of the stress management approach",
    "daily_routine": [
      {{"time": "morning", "action": "Action", "duration_min": 10, "description": "Details"}},
      {{"time": "evening", "action": "Action", "duration_min": 15, "description": "Details"}}
    ],
    "techniques": [
      {{"name": "Technique name", "description": "Description", "when": "When to apply"}}
    ],
    "tips": ["Tip 1", "Tip 2"]
  }},
  "sleep": {{
    "overview": "Brief overview of sleep optimisation",
    "target_hours": 8,
    "bedtime": "22:30",
    "wake_time": "06:30",
    "evening_routine": [
      {{"time": "21:00", "action": "Action", "description": "Details"}}
    ],
    "environment": ["Environment optimisation 1", "Optimisation 2"],
    "supplements": ["Sleep supplement 1 – Dosage & Timing"],
    "tips": ["Sleep tip 1", "Tip 2"]
  }}
}}

Important: Return ONLY the JSON, no text before or after."""

    return prompt


async def generate_plan(client_data: dict, feedback: dict = None) -> dict:
    """Generate a coaching plan using GPT-4.1. Returns parsed JSON dict."""
    lang = client_data.get("lang", "de")
    system_prompt = build_system_prompt(lang)
    user_prompt = build_user_prompt(client_data, feedback)

    response = client.chat.completions.create(
        model=_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=6000,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract JSON from response
        import re
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Could not parse AI response as JSON: {raw[:200]}")
