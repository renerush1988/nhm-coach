# -*- coding: utf-8 -*-
"""
pdf_generator.py — NHM Coach Backoffice
Generates a professional PDF coaching plan from plan content dict.
"""

import re
from fpdf import FPDF
from datetime import datetime

COLORS = {
    "bg":       (10, 15, 30),
    "accent":   (6, 182, 212),
    "gold":     (245, 158, 11),
    "white":    (241, 245, 249),
    "muted":    (148, 163, 184),
    "section":  (30, 41, 59),
    "training": (239, 68, 68),
    "nutrition":(16, 185, 129),
    "stress":   (139, 92, 246),
    "sleep":    (59, 130, 246),
}

PILLAR_COLORS = {
    "training":  (239, 68, 68),
    "nutrition": (16, 185, 129),
    "stress":    (139, 92, 246),
    "sleep":     (59, 130, 246),
}

PILLAR_ICONS = {
    "training":  "TRAINING",
    "nutrition": "ERNAEHRUNG",
    "stress":    "STRESS",
    "sleep":     "SCHLAF",
}

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


def strip_non_latin(text: str) -> str:
    """Remove characters not supported by Helvetica (Latin-1 subset)."""
    if not text:
        return ""
    # Replace common Unicode chars with ASCII equivalents
    replacements = {
        "\u2014": "-", "\u2013": "-", "\u2019": "'", "\u2018": "'",
        "\u201c": '"', "\u201d": '"', "\u2022": "-", "\u00e4": "ae",
        "\u00f6": "oe", "\u00fc": "ue", "\u00c4": "Ae", "\u00d6": "Oe",
        "\u00dc": "Ue", "\u00df": "ss", "\u00e9": "e", "\u00e8": "e",
        "\u00e0": "a", "\u00e1": "a", "\u00f3": "o", "\u00fa": "u",
        "\u00ed": "i", "\u2026": "...",
    }
    for orig, repl in replacements.items():
        text = text.replace(orig, repl)
    # Remove any remaining non-latin1 chars
    return text.encode("latin-1", errors="ignore").decode("latin-1")


def s(text) -> str:
    """Safe string for PDF output."""
    if text is None:
        return ""
    return strip_non_latin(str(text))


class CoachPDF(FPDF):
    def __init__(self, client_data, lang="de"):
        super().__init__()
        self.client_data = client_data
        self.lang = lang
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(20, 20, 20)

    def header(self):
        self.set_fill_color(10, 15, 30)
        self.rect(0, 0, 210, 18, "F")
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(6, 182, 212)
        self.set_y(5)
        self.cell(0, 8, "NeuroHealthMastery | Coaching Plan", align="C")
        self.set_text_color(241, 245, 249)
        self.ln(14)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(148, 163, 184)
        date_str = datetime.utcnow().strftime("%d.%m.%Y")
        self.cell(0, 10,
            f"NeuroHealthMastery | Rene Rusch | {date_str} | Seite {self.page_no()}",
            align="C")

    def section_header(self, title: str, pillar: str = None):
        color = PILLAR_COLORS.get(pillar, (6, 182, 212)) if pillar else (6, 182, 212)
        self.set_fill_color(*color)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 13)
        self.cell(0, 10, f"  {s(title)}", fill=True, ln=True)
        self.ln(4)
        self.set_text_color(30, 30, 30)

    def sub_header(self, title: str):
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(10, 15, 30)
        self.cell(0, 8, s(title), ln=True)
        self.set_draw_color(6, 182, 212)
        self.set_line_width(0.5)
        x = self.get_x()
        y = self.get_y()
        self.line(x, y, x + 170, y)
        self.ln(4)

    def body_text(self, text: str, indent: float = 0):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(40, 40, 40)
        if indent:
            self.set_x(self.get_x() + indent)
        self.multi_cell(0, 6, s(text))
        self.ln(1)

    def bullet(self, text: str):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(40, 40, 40)
        self.set_x(self.l_margin + 4)
        self.cell(6, 6, "-")
        self.multi_cell(0, 6, s(text))

    def info_box(self, label: str, value: str, color=None):
        if color:
            self.set_fill_color(*color)
        else:
            self.set_fill_color(240, 248, 255)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(10, 15, 30)
        self.cell(50, 8, s(label) + ":", fill=True)
        self.set_font("Helvetica", "", 9)
        self.cell(0, 8, s(value), ln=True)

    def exercise_row(self, ex: dict):
        name = s(ex.get("name", ""))
        sets = str(ex.get("sets", ""))
        reps = s(ex.get("reps", ""))
        note = s(ex.get("note", ""))
        self.set_font("Helvetica", "", 9)
        self.set_text_color(40, 40, 40)
        self.set_x(self.l_margin + 6)
        self.cell(70, 6, name)
        self.cell(20, 6, f"{sets}x")
        self.cell(25, 6, reps)
        self.cell(0, 6, note, ln=True)

    def meal_row(self, meal: dict):
        time = s(meal.get("time", ""))
        name = s(meal.get("name", ""))
        desc = s(meal.get("description", ""))
        kcal = meal.get("calories", "")
        prot = meal.get("protein_g", "")
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(10, 15, 30)
        self.set_x(self.l_margin + 4)
        self.cell(18, 6, time)
        self.cell(35, 6, name)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(60, 60, 60)
        if kcal:
            self.cell(30, 6, f"{kcal} kcal")
        if prot:
            self.cell(30, 6, f"{prot}g Protein")
        self.ln()
        self.set_x(self.l_margin + 8)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(100, 100, 100)
        self.multi_cell(0, 5, desc)
        self.ln(1)


def generate_pdf(client_data: dict, plan_content: dict) -> bytes:
    lang = client_data.get("lang", "de")
    name = client_data.get("name", "")
    nst = client_data.get("nst_type", "lion")
    goal_key = client_data.get("goal", "fat_loss")
    duration = client_data.get("duration", "4")
    pillars = client_data.get("pillars", [])

    nst_name = NST_NAMES.get(nst, {}).get(lang, nst)
    goal_label = GOAL_LABELS.get(goal_key, {}).get(lang, goal_key)

    pdf = CoachPDF(client_data, lang)
    pdf.add_page()

    # ── Cover ─────────────────────────────────────────────────────────────────
    pdf.set_fill_color(10, 15, 30)
    pdf.rect(0, 18, 210, 60, "F")
    pdf.set_y(24)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(6, 182, 212)
    pdf.cell(0, 12, "NeuroHealthMastery", align="C", ln=True)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(241, 245, 249)
    title = "Dein persoenlicher Coaching-Plan" if lang == "de" else "Your Personal Coaching Plan"
    pdf.cell(0, 8, s(title), align="C", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 6, f"Natural Signature Type: {s(nst_name)}", align="C", ln=True)
    pdf.ln(8)

    # Client info box
    pdf.set_y(85)
    pdf.set_fill_color(30, 41, 59)
    pdf.rect(20, 85, 170, 36, "F")
    pdf.set_y(89)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(6, 182, 212)
    for_label = "Erstellt fuer:" if lang == "de" else "Prepared for:"
    pdf.cell(0, 7, s(for_label), align="C", ln=True)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(241, 245, 249)
    pdf.cell(0, 9, s(name), align="C", ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(148, 163, 184)
    dur_label = f"Ziel: {s(goal_label)} | Dauer: {duration} Wochen" if lang == "de" else f"Goal: {s(goal_label)} | Duration: {duration} weeks"
    pdf.cell(0, 7, s(dur_label), align="C", ln=True)
    pdf.ln(16)

    # Summary
    summary = plan_content.get("summary", "")
    if summary:
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(60, 60, 60)
        pdf.multi_cell(0, 6, s(summary))
        pdf.ln(6)

    # ── Training ──────────────────────────────────────────────────────────────
    if "training" in plan_content and "training" in pillars:
        t_data = plan_content["training"]
        label = "Training" if lang == "en" else "Training"
        pdf.add_page()
        pdf.section_header(f"{'Training' if lang == 'en' else 'Training'}", "training")

        overview = t_data.get("overview", "")
        if overview:
            pdf.body_text(overview)
            pdf.ln(2)

        weeks = t_data.get("weeks", [])
        for week in weeks:
            pdf.sub_header(s(week.get("label", f"Week {week.get('week', '')}")))
            sessions = week.get("sessions", [])
            for session in sessions:
                day = s(session.get("day", ""))
                stype = s(session.get("type", ""))
                dur = session.get("duration_min", "")
                pdf.set_font("Helvetica", "B", 10)
                pdf.set_text_color(10, 15, 30)
                dur_str = f" ({dur} min)" if dur else ""
                pdf.cell(0, 7, f"{day}: {stype}{dur_str}", ln=True)
                exercises = session.get("exercises", [])
                if exercises:
                    pdf.set_font("Helvetica", "B", 8)
                    pdf.set_text_color(100, 100, 100)
                    pdf.set_x(pdf.l_margin + 6)
                    ex_header = "Uebung                              Saetze  Wdh." if lang == "de" else "Exercise                            Sets    Reps"
                    pdf.cell(0, 5, ex_header, ln=True)
                    for ex in exercises:
                        pdf.exercise_row(ex)
                pdf.ln(2)

        tips = t_data.get("tips", [])
        if tips:
            tips_label = "Wichtige Tipps" if lang == "de" else "Key Tips"
            pdf.sub_header(tips_label)
            for tip in tips:
                pdf.bullet(tip)
            pdf.ln(2)

    # ── Nutrition ─────────────────────────────────────────────────────────────
    if "nutrition" in plan_content and "nutrition" in pillars:
        n_data = plan_content["nutrition"]
        pdf.add_page()
        nut_label = "Ernaehrungsplan" if lang == "de" else "Nutrition Plan"
        pdf.section_header(nut_label, "nutrition")

        overview = n_data.get("overview", "")
        if overview:
            pdf.body_text(overview)
            pdf.ln(2)

        # Macros
        macros = n_data.get("macros", {})
        daily_cal = n_data.get("daily_calories", "")
        if macros or daily_cal:
            pdf.set_fill_color(240, 255, 248)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(10, 15, 30)
            kcal_label = "Tageskalorien" if lang == "de" else "Daily Calories"
            pdf.cell(0, 7, f"{kcal_label}: {s(str(daily_cal))} kcal", fill=True, ln=True)
            if macros:
                macro_str = f"Protein: {macros.get('protein_g', 0)}g  |  Kohlenhydrate: {macros.get('carbs_g', 0)}g  |  Fett: {macros.get('fat_g', 0)}g"
                if lang == "en":
                    macro_str = f"Protein: {macros.get('protein_g', 0)}g  |  Carbs: {macros.get('carbs_g', 0)}g  |  Fat: {macros.get('fat_g', 0)}g"
                pdf.set_font("Helvetica", "", 9)
                pdf.cell(0, 6, s(macro_str), ln=True)
            pdf.ln(3)

        # Meal plan
        meal_plan = n_data.get("meal_plan", [])
        for day_type_data in meal_plan:
            day_type = s(day_type_data.get("day_type", ""))
            pdf.sub_header(day_type)
            meals = day_type_data.get("meals", [])
            for meal in meals:
                pdf.meal_row(meal)
            pdf.ln(2)

        # Supplements
        supps = n_data.get("supplements", [])
        if supps:
            supp_label = "Supplements" if lang == "en" else "Supplements"
            pdf.sub_header(supp_label)
            for s_item in supps:
                pdf.bullet(s_item)
            pdf.ln(2)

        tips = n_data.get("tips", [])
        if tips:
            tips_label = "Ernaehrungs-Tipps" if lang == "de" else "Nutrition Tips"
            pdf.sub_header(tips_label)
            for tip in tips:
                pdf.bullet(tip)

    # ── Stress ────────────────────────────────────────────────────────────────
    if "stress" in plan_content and "stress" in pillars:
        st_data = plan_content["stress"]
        pdf.add_page()
        stress_label = "Stressmanagement" if lang == "de" else "Stress Management"
        pdf.section_header(stress_label, "stress")

        overview = st_data.get("overview", "")
        if overview:
            pdf.body_text(overview)
            pdf.ln(2)

        routine = st_data.get("daily_routine", [])
        if routine:
            routine_label = "Taegliche Routine" if lang == "de" else "Daily Routine"
            pdf.sub_header(routine_label)
            for item in routine:
                time_str = s(item.get("time", ""))
                action = s(item.get("action", ""))
                dur = item.get("duration_min", "")
                desc = s(item.get("description", ""))
                dur_str = f" ({dur} min)" if dur else ""
                pdf.set_font("Helvetica", "B", 10)
                pdf.set_text_color(10, 15, 30)
                pdf.cell(0, 7, f"{time_str}: {action}{dur_str}", ln=True)
                if desc:
                    pdf.set_font("Helvetica", "", 9)
                    pdf.set_text_color(80, 80, 80)
                    pdf.set_x(pdf.l_margin + 6)
                    pdf.multi_cell(0, 5, desc)
                pdf.ln(1)

        techniques = st_data.get("techniques", [])
        if techniques:
            tech_label = "Techniken" if lang == "de" else "Techniques"
            pdf.sub_header(tech_label)
            for tech in techniques:
                pdf.set_font("Helvetica", "B", 10)
                pdf.set_text_color(10, 15, 30)
                pdf.cell(0, 7, s(tech.get("name", "")), ln=True)
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(80, 80, 80)
                pdf.set_x(pdf.l_margin + 6)
                pdf.multi_cell(0, 5, s(tech.get("description", "")))
                when = tech.get("when", "")
                if when:
                    when_label = "Wann:" if lang == "de" else "When:"
                    pdf.set_x(pdf.l_margin + 6)
                    pdf.set_font("Helvetica", "I", 8)
                    pdf.cell(0, 5, f"{when_label} {s(when)}", ln=True)
                pdf.ln(2)

        tips = st_data.get("tips", [])
        if tips:
            tips_label = "Stress-Tipps" if lang == "de" else "Stress Tips"
            pdf.sub_header(tips_label)
            for tip in tips:
                pdf.bullet(tip)

    # ── Sleep ─────────────────────────────────────────────────────────────────
    if "sleep" in plan_content and "sleep" in pillars:
        sl_data = plan_content["sleep"]
        pdf.add_page()
        sleep_label = "Schlafoptimierung" if lang == "de" else "Sleep Optimisation"
        pdf.section_header(sleep_label, "sleep")

        overview = sl_data.get("overview", "")
        if overview:
            pdf.body_text(overview)
            pdf.ln(2)

        # Sleep times
        target = sl_data.get("target_hours", "")
        bedtime = sl_data.get("bedtime", "")
        wake = sl_data.get("wake_time", "")
        if target or bedtime or wake:
            pdf.set_fill_color(235, 245, 255)
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(10, 15, 30)
            if lang == "de":
                info = f"Ziel-Schlafdauer: {target}h  |  Schlafenszeit: {bedtime}  |  Aufstehzeit: {wake}"
            else:
                info = f"Target Sleep: {target}h  |  Bedtime: {bedtime}  |  Wake Time: {wake}"
            pdf.cell(0, 8, s(info), fill=True, ln=True)
            pdf.ln(3)

        routine = sl_data.get("evening_routine", [])
        if routine:
            routine_label = "Abendroutine" if lang == "de" else "Evening Routine"
            pdf.sub_header(routine_label)
            for item in routine:
                time_str = s(item.get("time", ""))
                action = s(item.get("action", ""))
                desc = s(item.get("description", ""))
                pdf.set_font("Helvetica", "B", 10)
                pdf.set_text_color(10, 15, 30)
                pdf.cell(0, 7, f"{time_str}: {action}", ln=True)
                if desc:
                    pdf.set_font("Helvetica", "", 9)
                    pdf.set_text_color(80, 80, 80)
                    pdf.set_x(pdf.l_margin + 6)
                    pdf.multi_cell(0, 5, desc)
                pdf.ln(1)

        env = sl_data.get("environment", [])
        if env:
            env_label = "Schlafumgebung" if lang == "de" else "Sleep Environment"
            pdf.sub_header(env_label)
            for item in env:
                pdf.bullet(item)
            pdf.ln(2)

        supps = sl_data.get("supplements", [])
        if supps:
            supp_label = "Schlaf-Supplements" if lang == "de" else "Sleep Supplements"
            pdf.sub_header(supp_label)
            for s_item in supps:
                pdf.bullet(s_item)
            pdf.ln(2)

        tips = sl_data.get("tips", [])
        if tips:
            tips_label = "Schlaf-Tipps" if lang == "de" else "Sleep Tips"
            pdf.sub_header(tips_label)
            for tip in tips:
                pdf.bullet(tip)

    # ── Closing page ──────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.set_fill_color(10, 15, 30)
    pdf.rect(0, 18, 210, 80, "F")
    pdf.set_y(40)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(6, 182, 212)
    closing = "Viel Erfolg auf deinem Weg!" if lang == "de" else "Best of luck on your journey!"
    pdf.cell(0, 10, s(closing), align="C", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(241, 245, 249)
    pdf.cell(0, 8, "NeuroHealthMastery | Rene Rusch", align="C", ln=True)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 6, "neurohealthmastery.de", align="C", ln=True)
    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(148, 163, 184)
    disclaimer = (
        "Hinweis: Rene Rusch ist kein Arzt. Alle Empfehlungen basieren auf professionellen "
        "Zertifikaten (Natural Signature Typing, Ernaehrungscoaching) und wissenschaftlicher "
        "Literatur. Dieser Plan ersetzt keine aerztliche Beratung."
    ) if lang == "de" else (
        "Disclaimer: Rene Rusch is not a medical doctor. All recommendations are based on "
        "professional certifications (Natural Signature Typing, Nutrition Coaching) and "
        "peer-reviewed literature. This plan does not replace medical advice."
    )
    pdf.set_y(100)
    pdf.multi_cell(0, 5, s(disclaimer))

    output = pdf.output()
    if isinstance(output, bytearray):
        return bytes(output)
    return output
