# -*- coding: utf-8 -*-
"""
pdf_generator.py — NHM Coach Backoffice
Generates a professional PDF coaching plan from plan content dict.
Supports v2 schema: training_concept, tempo/rest columns, carb-cycling nutrition.
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
    replacements = {
        "\u2014": "-", "\u2013": "-", "\u2019": "'", "\u2018": "'",
        "\u201c": '"', "\u201d": '"', "\u2022": "-", "\u00e4": "ae",
        "\u00f6": "oe", "\u00fc": "ue", "\u00c4": "Ae", "\u00d6": "Oe",
        "\u00dc": "Ue", "\u00df": "ss", "\u00e9": "e", "\u00e8": "e",
        "\u00e0": "a", "\u00e1": "a", "\u00f3": "o", "\u00fa": "u",
        "\u00ed": "i", "\u2026": "...", "\u00b7": "-",
    }
    for orig, repl in replacements.items():
        text = text.replace(orig, repl)
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

    def concept_box(self, concept: dict, lang: str = "de"):
        """Render the training concept explanation box."""
        self.set_fill_color(235, 245, 255)
        self.set_draw_color(6, 182, 212)
        self.set_line_width(0.8)
        # Box title
        title = s(concept.get("title", "Trainingskonzept"))
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(6, 182, 212)
        self.cell(0, 8, f"  {title}", fill=True, ln=True)
        self.set_text_color(40, 40, 40)

        sections = [
            ("why_this_plan",        "Warum dieser Plan?" if lang == "de" else "Why this plan?"),
            ("why_these_exercises",  "Warum diese Uebungen?" if lang == "de" else "Why these exercises?"),
            ("why_this_tempo",       "Warum dieses Tempo?" if lang == "de" else "Why this tempo?"),
            ("progression",          "Progression"),
        ]
        for key, label in sections:
            val = concept.get(key, "")
            if val:
                self.set_font("Helvetica", "B", 9)
                self.set_text_color(10, 15, 30)
                self.set_x(self.l_margin + 4)
                self.cell(0, 6, s(label), ln=True)
                self.set_font("Helvetica", "", 9)
                self.set_text_color(60, 60, 60)
                self.set_x(self.l_margin + 8)
                self.multi_cell(0, 5, s(val))
                self.ln(1)

        principles = concept.get("key_principles", [])
        if principles:
            key_label = "Schluesselprinzipien:" if lang == "de" else "Key Principles:"
            self.set_font("Helvetica", "B", 9)
            self.set_text_color(10, 15, 30)
            self.set_x(self.l_margin + 4)
            self.cell(0, 6, s(key_label), ln=True)
            for p in principles:
                self.set_font("Helvetica", "", 9)
                self.set_text_color(60, 60, 60)
                self.set_x(self.l_margin + 8)
                self.cell(5, 5, "-")
                self.multi_cell(0, 5, s(p))
        self.ln(4)

    def exercise_row(self, ex: dict):
        """Render one exercise row with tempo and rest columns."""
        name  = s(ex.get("name", ""))
        sets  = str(ex.get("sets", ""))
        reps  = s(ex.get("reps", ""))
        tempo = s(ex.get("tempo", ""))
        rest  = s(ex.get("rest", ""))
        note  = s(ex.get("note", ""))
        self.set_font("Helvetica", "", 8)
        self.set_text_color(40, 40, 40)
        self.set_x(self.l_margin + 4)
        self.cell(52, 5, name)
        self.cell(14, 5, f"{sets}x")
        self.cell(18, 5, reps)
        self.cell(22, 5, tempo)
        self.cell(24, 5, rest)
        self.cell(0, 5, note, ln=True)

    def exercise_header_row(self, lang: str = "de"):
        """Render the exercise table header."""
        self.set_font("Helvetica", "B", 7)
        self.set_text_color(100, 100, 100)
        self.set_x(self.l_margin + 4)
        if lang == "de":
            self.cell(52, 5, "Uebung")
            self.cell(14, 5, "Saetze")
            self.cell(18, 5, "Wdh.")
            self.cell(22, 5, "Tempo")
            self.cell(24, 5, "Pause")
            self.cell(0, 5, "Hinweis", ln=True)
        else:
            self.cell(52, 5, "Exercise")
            self.cell(14, 5, "Sets")
            self.cell(18, 5, "Reps")
            self.cell(22, 5, "Tempo")
            self.cell(24, 5, "Rest")
            self.cell(0, 5, "Note", ln=True)
        self.set_draw_color(200, 200, 200)
        self.set_line_width(0.3)
        x = self.get_x()
        y = self.get_y()
        self.line(self.l_margin + 4, y, self.l_margin + 170, y)
        self.ln(1)

    def meal_row(self, meal: dict):
        time = s(meal.get("time", ""))
        name = s(meal.get("name", ""))
        desc = s(meal.get("description", ""))
        kcal = meal.get("calories", "")
        prot = meal.get("protein_g", "")
        carbs = meal.get("carbs_g", "")
        fat  = meal.get("fat_g", "")
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(10, 15, 30)
        self.set_x(self.l_margin + 4)
        self.cell(18, 6, time)
        self.cell(40, 6, name)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(60, 60, 60)
        macro_parts = []
        if kcal: macro_parts.append(f"{kcal} kcal")
        if prot: macro_parts.append(f"{prot}g P")
        if carbs: macro_parts.append(f"{carbs}g K")
        if fat: macro_parts.append(f"{fat}g F")
        self.cell(0, 6, "  ".join(macro_parts), ln=True)
        if desc:
            self.set_x(self.l_margin + 8)
            self.set_font("Helvetica", "", 8)
            self.set_text_color(100, 100, 100)
            self.multi_cell(0, 5, desc)
        self.ln(1)

    def macros_summary_row(self, day_data: dict, lang: str = "de"):
        """Render a macro summary bar for a day type."""
        cal   = day_data.get("calories", 0)
        prot  = day_data.get("protein_g", 0)
        carbs = day_data.get("carbs_g", 0)
        fat   = day_data.get("fat_g", 0)
        ratio = s(day_data.get("macro_ratio", ""))
        self.set_fill_color(240, 255, 248)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(10, 15, 30)
        if lang == "de":
            macro_str = f"Kalorien: {cal} kcal  |  Protein: {prot}g  |  Kohlenhydrate: {carbs}g  |  Fett: {fat}g"
        else:
            macro_str = f"Calories: {cal} kcal  |  Protein: {prot}g  |  Carbs: {carbs}g  |  Fat: {fat}g"
        self.cell(0, 7, s(macro_str), fill=True, ln=True)
        if ratio:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(80, 80, 80)
            self.cell(0, 5, s(ratio), ln=True)
        self.ln(2)


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
        pdf.add_page()
        pdf.section_header("Training", "training")

        overview = t_data.get("overview", "")
        if overview:
            pdf.body_text(overview)
            pdf.ln(2)

        # Training Concept section
        concept = t_data.get("training_concept", {})
        if concept:
            concept_label = "Trainingskonzept" if lang == "de" else "Training Concept"
            pdf.sub_header(concept_label)
            pdf.concept_box(concept, lang)

        # Weeks
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
                    pdf.exercise_header_row(lang)
                    for ex in exercises:
                        pdf.exercise_row(ex)
                pdf.ln(2)

        tips = t_data.get("tips", [])
        if tips:
            tips_label = "Wichtige Tipps" if lang == "de" else "Key Tips"
            pdf.sub_header(tips_label)
            for tip in tips:
                pdf.bullet(tip)

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

        approach = n_data.get("approach", "")

        if approach == "carb_cycling":
            # ── Carb Cycling Layout ──
            workout_day = n_data.get("workout_day", {})
            rest_day = n_data.get("rest_day", {})

            if workout_day:
                wd_label = "Trainingstag" if lang == "de" else "Training Day"
                pdf.sub_header(wd_label)
                pdf.macros_summary_row(workout_day, lang)
                for meal in workout_day.get("meals", []):
                    pdf.meal_row(meal)
                pdf.ln(3)

            if rest_day:
                rd_label = "Ruhetag" if lang == "de" else "Rest Day"
                pdf.sub_header(rd_label)
                pdf.macros_summary_row(rest_day, lang)
                for meal in rest_day.get("meals", []):
                    pdf.meal_row(meal)
                pdf.ln(3)

        else:
            # ── Legacy meal_plan layout ──
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
            supp_label = "Supplements"
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
