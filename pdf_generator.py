# -*- coding: utf-8 -*-
"""
pdf_generator.py — NHM Coach Backoffice
Generates a professional PDF coaching plan from plan content dict.
v3: DejaVu Unicode fonts (Umlaute!), wrapping exercise rows, tempo graphic, improved spacing.
"""

import os
import re
from fpdf import FPDF
from datetime import datetime

# ── Font paths ─────────────────────────────────────────────────────────────────
_BASE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(_BASE, "static", "fonts")
FONT_REGULAR = os.path.join(FONT_DIR, "DejaVuSans.ttf")
FONT_BOLD    = os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")
FONT_ITALIC  = os.path.join(FONT_DIR, "DejaVuSans-Oblique.ttf")
TEMPO_IMG    = os.path.join(_BASE, "static", "img", "tempo_graphic.png")

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


def safe(text) -> str:
    """Return text as string; Unicode is handled by DejaVu font."""
    if text is None:
        return ""
    return str(text)


class CoachPDF(FPDF):
    def __init__(self, client_data, lang="de"):
        super().__init__()
        self.client_data = client_data
        self.lang = lang
        self.set_auto_page_break(auto=True, margin=22)
        self.set_margins(18, 20, 18)

        # Register DejaVu Unicode fonts
        self.add_font("DejaVu",  "",  FONT_REGULAR, uni=True)
        self.add_font("DejaVu",  "B", FONT_BOLD,    uni=True)
        self.add_font("DejaVu",  "I", FONT_ITALIC,  uni=True)

    def header(self):
        self.set_fill_color(10, 15, 30)
        self.rect(0, 0, 210, 18, "F")
        self.set_font("DejaVu", "B", 9)
        self.set_text_color(6, 182, 212)
        self.set_y(5)
        self.cell(0, 8, "NeuroHealthMastery | Coaching Plan", align="C")
        self.set_text_color(241, 245, 249)
        self.ln(14)

    def footer(self):
        self.set_y(-15)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(148, 163, 184)
        date_str = datetime.utcnow().strftime("%d.%m.%Y")
        self.cell(0, 10,
            f"NeuroHealthMastery | Rene Rusch | {date_str} | Seite {self.page_no()}",
            align="C")

    def section_header(self, title: str, pillar: str = None):
        color = PILLAR_COLORS.get(pillar, (6, 182, 212)) if pillar else (6, 182, 212)
        self.set_fill_color(*color)
        self.set_text_color(255, 255, 255)
        self.set_font("DejaVu", "B", 13)
        self.cell(0, 11, f"  {safe(title)}", fill=True, ln=True)
        self.ln(4)
        self.set_text_color(30, 30, 30)

    def sub_header(self, title: str):
        self.set_font("DejaVu", "B", 11)
        self.set_text_color(10, 15, 30)
        self.cell(0, 8, safe(title), ln=True)
        self.set_draw_color(6, 182, 212)
        self.set_line_width(0.5)
        x = self.l_margin
        y = self.get_y()
        self.line(x, y, x + 174, y)
        self.ln(4)

    def body_text(self, text: str, indent: float = 0):
        self.set_font("DejaVu", "", 10)
        self.set_text_color(40, 40, 40)
        if indent:
            self.set_x(self.get_x() + indent)
        self.multi_cell(0, 6, safe(text))
        self.ln(1)

    def bullet(self, text: str):
        self.set_font("DejaVu", "", 10)
        self.set_text_color(40, 40, 40)
        self.set_x(self.l_margin + 4)
        self.cell(5, 6, "–")
        self.multi_cell(0, 6, safe(text))

    def concept_box(self, concept: dict, lang: str = "de", show_tempo_graphic: bool = True):
        """Render the training concept explanation box with optional tempo graphic."""
        title = safe(concept.get("title", "Trainingskonzept"))
        self.set_fill_color(235, 245, 255)
        self.set_draw_color(6, 182, 212)
        self.set_line_width(0.8)
        self.set_font("DejaVu", "B", 11)
        self.set_text_color(6, 182, 212)
        self.cell(0, 9, f"  {title}", fill=True, ln=True)
        self.set_text_color(40, 40, 40)

        sections = [
            ("why_this_plan",       "Warum dieser Plan?"     if lang == "de" else "Why this plan?"),
            ("why_these_exercises", "Warum diese Übungen?"   if lang == "de" else "Why these exercises?"),
            ("why_this_tempo",      "Warum dieses Tempo?"    if lang == "de" else "Why this tempo?"),
            ("progression",         "Progression"),
        ]
        for key, label in sections:
            val = concept.get(key, "")
            if val:
                self.set_font("DejaVu", "B", 9)
                self.set_text_color(10, 15, 30)
                self.set_x(self.l_margin + 4)
                self.cell(0, 6, safe(label), ln=True)
                self.set_font("DejaVu", "", 9)
                self.set_text_color(60, 60, 60)
                self.set_x(self.l_margin + 8)
                self.multi_cell(0, 5, safe(val))
                self.ln(2)

        principles = concept.get("key_principles", [])
        if principles:
            key_label = "Schlüsselprinzipien:" if lang == "de" else "Key Principles:"
            self.set_font("DejaVu", "B", 9)
            self.set_text_color(10, 15, 30)
            self.set_x(self.l_margin + 4)
            self.cell(0, 6, safe(key_label), ln=True)
            for p in principles:
                self.set_font("DejaVu", "", 9)
                self.set_text_color(60, 60, 60)
                self.set_x(self.l_margin + 8)
                self.cell(5, 5, "–")
                self.multi_cell(0, 5, safe(p))
        self.ln(5)

        # ── Tempo-Grafik einbinden ──────────────────────────────────────────────
        if show_tempo_graphic and os.path.exists(TEMPO_IMG):
            tempo_label = "So liest du das Tempo:" if lang == "de" else "How to read the tempo:"
            self.set_font("DejaVu", "B", 10)
            self.set_text_color(6, 182, 212)
            self.cell(0, 7, tempo_label, ln=True)
            self.ln(1)
            # Grafik zentriert, Breite 174mm
            img_w = 174
            img_h = img_w * (3.2 / 10.0)  # Seitenverhältnis aus create_tempo_graphic.py
            x_img = self.l_margin
            self.image(TEMPO_IMG, x=x_img, y=self.get_y(), w=img_w, h=img_h)
            self.ln(img_h + 4)

    # ── Exercise table helpers ─────────────────────────────────────────────────
    # Column widths (total usable = 174mm)
    COL_NAME  = 58   # Übung
    COL_SETS  = 13   # Sätze
    COL_REPS  = 18   # Wdh.
    COL_TEMPO = 20   # Tempo
    COL_REST  = 20   # Pause
    COL_NOTE  = 45   # Hinweis  (rest)

    def exercise_header_row(self, lang: str = "de"):
        """Render the exercise table header."""
        self.set_font("DejaVu", "B", 8)
        self.set_text_color(80, 80, 80)
        self.set_fill_color(230, 240, 255)
        x0 = self.l_margin
        y0 = self.get_y()
        row_h = 6

        if lang == "de":
            headers = ["Übung", "Sätze", "Wdh.", "Tempo", "Pause", "Hinweis"]
        else:
            headers = ["Exercise", "Sets", "Reps", "Tempo", "Rest", "Note"]

        widths = [self.COL_NAME, self.COL_SETS, self.COL_REPS,
                  self.COL_TEMPO, self.COL_REST, self.COL_NOTE]

        self.set_x(x0)
        for h, w in zip(headers, widths):
            self.cell(w, row_h, h, fill=True)
        self.ln(row_h)

        self.set_draw_color(6, 182, 212)
        self.set_line_width(0.4)
        y = self.get_y()
        self.line(x0, y, x0 + sum(widths), y)
        self.ln(1)

    def exercise_row(self, ex: dict):
        """Render one exercise row using a fixed-height approach to avoid page-break issues."""
        name  = safe(ex.get("name", ""))
        sets  = safe(ex.get("sets", ""))
        reps  = safe(ex.get("reps", ""))
        tempo = safe(ex.get("tempo", ""))
        rest  = safe(ex.get("rest", ""))
        note  = safe(ex.get("note", ""))

        x0     = self.l_margin
        line_h = 5.0

        self.set_font("DejaVu", "", 8.5)

        # Estimate row height based on wrapping
        name_lines = max(1, self._count_lines(name, self.COL_NAME - 2))
        note_lines = max(1, self._count_lines(note, self.COL_NOTE - 2))
        row_lines  = max(name_lines, note_lines)
        row_h      = row_lines * line_h + 2  # +2mm padding

        # Check if row fits on current page; if not, add new page
        if self.get_y() + row_h > self.page_break_trigger:
            self.add_page()
            self.exercise_header_row(self.lang)

        y_start = self.get_y()
        total_w = self.COL_NAME + self.COL_SETS + self.COL_REPS + self.COL_TEMPO + self.COL_REST + self.COL_NOTE

        # Alternating row background
        if not hasattr(self, '_row_toggle'):
            self._row_toggle = False
        self._row_toggle = not self._row_toggle
        if self._row_toggle:
            self.set_fill_color(248, 251, 255)
            self.rect(x0, y_start, total_w, row_h, "F")

        # --- Name column (wraps) ---
        self.set_font("DejaVu", "", 8.5)
        self.set_text_color(30, 30, 30)
        self.set_xy(x0, y_start + 1)
        self.multi_cell(self.COL_NAME, line_h, name, border=0)

        # --- Fixed single-line columns (vertically centered) ---
        cy = y_start + (row_h - line_h) / 2

        self.set_xy(x0 + self.COL_NAME, cy)
        self.set_font("DejaVu", "", 8.5)
        self.set_text_color(50, 50, 50)
        self.cell(self.COL_SETS, line_h, f"{sets}x", align="C")
        self.cell(self.COL_REPS, line_h, reps, align="C")

        # Tempo — gold bold
        self.set_font("DejaVu", "B", 8.5)
        self.set_text_color(180, 100, 0)
        self.cell(self.COL_TEMPO, line_h, tempo, align="C")

        self.set_font("DejaVu", "", 8.5)
        self.set_text_color(50, 50, 50)
        self.cell(self.COL_REST, line_h, rest, align="C")

        # --- Note column (wraps, italic) ---
        self.set_font("DejaVu", "I", 8)
        self.set_text_color(80, 80, 80)
        note_x = x0 + self.COL_NAME + self.COL_SETS + self.COL_REPS + self.COL_TEMPO + self.COL_REST
        self.set_xy(note_x, y_start + 1)
        self.multi_cell(self.COL_NOTE, line_h, note, border=0)

        # Move cursor to end of row
        self.set_xy(x0, y_start + row_h)
        self.set_text_color(30, 30, 30)
        self.set_font("DejaVu", "", 8.5)

        # Thin separator line
        self.set_draw_color(210, 220, 235)
        self.set_line_width(0.2)
        self.line(x0, self.get_y(), x0 + total_w, self.get_y())
        self.ln(0.5)

    def _count_lines(self, text: str, width: float) -> int:
        """Estimate number of lines text will occupy in given width."""
        if not text:
            return 1
        # Approximate: avg char width ~1.8mm at 8.5pt DejaVu
        chars_per_line = max(1, int(width / 1.8))
        # Split by existing newlines first
        lines = 0
        for part in text.split('\n'):
            lines += max(1, -(-len(part) // chars_per_line))  # ceiling division
        return lines

    # ── Meal helpers ───────────────────────────────────────────────────────────
    def meal_row(self, meal: dict):
        time  = safe(meal.get("time", ""))
        name  = safe(meal.get("name", ""))
        desc  = safe(meal.get("description", ""))
        kcal  = meal.get("calories", "")
        prot  = meal.get("protein_g", "")
        carbs = meal.get("carbs_g", "")
        fat   = meal.get("fat_g", "")

        self.set_font("DejaVu", "B", 9)
        self.set_text_color(10, 15, 30)
        self.set_x(self.l_margin + 4)
        self.cell(18, 6, time)
        self.cell(50, 6, name)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(60, 60, 60)
        macro_parts = []
        if kcal:  macro_parts.append(f"{kcal} kcal")
        if prot:  macro_parts.append(f"{prot}g P")
        if carbs: macro_parts.append(f"{carbs}g K")
        if fat:   macro_parts.append(f"{fat}g F")
        self.cell(0, 6, "  ".join(macro_parts), ln=True)
        if desc:
            self.set_x(self.l_margin + 8)
            self.set_font("DejaVu", "I", 8)
            self.set_text_color(100, 100, 100)
            self.multi_cell(0, 5, desc)
        self.ln(1)

    def macros_summary_row(self, day_data: dict, lang: str = "de"):
        cal   = day_data.get("calories", 0)
        prot  = day_data.get("protein_g", 0)
        carbs = day_data.get("carbs_g", 0)
        fat   = day_data.get("fat_g", 0)
        ratio = safe(day_data.get("macro_ratio", ""))
        self.set_fill_color(240, 255, 248)
        self.set_font("DejaVu", "B", 9)
        self.set_text_color(10, 15, 30)
        if lang == "de":
            macro_str = f"Kalorien: {cal} kcal  |  Protein: {prot}g  |  Kohlenhydrate: {carbs}g  |  Fett: {fat}g"
        else:
            macro_str = f"Calories: {cal} kcal  |  Protein: {prot}g  |  Carbs: {carbs}g  |  Fat: {fat}g"
        self.cell(0, 7, safe(macro_str), fill=True, ln=True)
        if ratio:
            self.set_font("DejaVu", "I", 8)
            self.set_text_color(80, 80, 80)
            self.cell(0, 5, safe(ratio), ln=True)
        self.ln(2)


# ── Main generator ─────────────────────────────────────────────────────────────
def generate_pdf(client_data: dict, plan_content: dict) -> bytes:
    lang     = client_data.get("lang", "de")
    name     = client_data.get("name", "")
    nst      = client_data.get("nst_type", "lion")
    goal_key = client_data.get("goal", "fat_loss")
    duration = client_data.get("duration_weeks", 4)
    pillars  = plan_content.get("pillars", ["training", "nutrition", "stress", "sleep"])

    nst_name   = NST_NAMES.get(nst, {}).get(lang, nst)
    goal_label = GOAL_LABELS.get(goal_key, {}).get(lang, goal_key)

    pdf = CoachPDF(client_data, lang)
    pdf.add_page()

    # ── Cover ─────────────────────────────────────────────────────────────────
    pdf.set_fill_color(10, 15, 30)
    pdf.rect(0, 18, 210, 62, "F")
    pdf.set_y(26)
    pdf.set_font("DejaVu", "B", 22)
    pdf.set_text_color(6, 182, 212)
    pdf.cell(0, 12, "NeuroHealthMastery", align="C", ln=True)
    pdf.set_font("DejaVu", "B", 14)
    pdf.set_text_color(241, 245, 249)
    title = "Dein persönlicher Coaching-Plan" if lang == "de" else "Your Personal Coaching Plan"
    pdf.cell(0, 8, safe(title), align="C", ln=True)
    pdf.set_font("DejaVu", "", 10)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 6, f"Natural Signature Type: {safe(nst_name)}", align="C", ln=True)
    pdf.ln(8)

    # Client info box
    pdf.set_y(88)
    pdf.set_fill_color(30, 41, 59)
    pdf.rect(18, 88, 174, 38, "F")
    pdf.set_y(93)
    pdf.set_font("DejaVu", "B", 10)
    pdf.set_text_color(6, 182, 212)
    for_label = "Erstellt für:" if lang == "de" else "Prepared for:"
    pdf.cell(0, 7, safe(for_label), align="C", ln=True)
    pdf.set_font("DejaVu", "B", 15)
    pdf.set_text_color(241, 245, 249)
    pdf.cell(0, 9, safe(name), align="C", ln=True)
    pdf.set_font("DejaVu", "", 9)
    pdf.set_text_color(148, 163, 184)
    dur_label = (f"Ziel: {safe(goal_label)} | Dauer: {duration} Wochen"
                 if lang == "de" else
                 f"Goal: {safe(goal_label)} | Duration: {duration} weeks")
    pdf.cell(0, 7, safe(dur_label), align="C", ln=True)
    pdf.ln(18)

    # Summary / Intro
    summary = plan_content.get("summary", "")
    if summary:
        pdf.set_font("DejaVu", "I", 10)
        pdf.set_text_color(60, 60, 60)
        pdf.multi_cell(0, 6, safe(summary))
        pdf.ln(6)

    # ── Training ──────────────────────────────────────────────────────────────
    if "training" in plan_content and "training" in pillars:
        t_data = plan_content["training"]
        pdf.add_page()
        t_label = "Training" if lang == "de" else "Training"
        pdf.section_header(t_label, "training")

        overview = t_data.get("overview", "")
        if overview:
            pdf.body_text(overview)
            pdf.ln(2)

        # Training Concept + Tempo Graphic
        concept = t_data.get("training_concept", {})
        if concept:
            concept_label = "Trainingskonzept" if lang == "de" else "Training Concept"
            pdf.sub_header(concept_label)
            pdf.concept_box(concept, lang, show_tempo_graphic=True)

        # Weeks
        weeks = t_data.get("weeks", [])
        for week in weeks:
            pdf.sub_header(safe(week.get("label", f"Woche {week.get('week', '')}")))
            sessions = week.get("sessions", [])
            for session in sessions:
                day   = safe(session.get("day", ""))
                stype = safe(session.get("type", ""))
                dur   = session.get("duration_min", "")
                pdf.set_font("DejaVu", "B", 10)
                pdf.set_text_color(10, 15, 30)
                dur_str = f" ({dur} min)" if dur else ""
                pdf.cell(0, 7, f"{day}: {stype}{dur_str}", ln=True)
                pdf.ln(1)
                exercises = session.get("exercises", [])
                if exercises:
                    pdf._row_toggle = False  # reset alternating rows
                    pdf.exercise_header_row(lang)
                    for ex in exercises:
                        pdf.exercise_row(ex)
                pdf.ln(3)

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
        nut_label = "Ernährungsplan" if lang == "de" else "Nutrition Plan"
        pdf.section_header(nut_label, "nutrition")

        overview = n_data.get("overview", "")
        if overview:
            pdf.body_text(overview)
            pdf.ln(2)

        approach = n_data.get("approach", "")

        if approach == "carb_cycling":
            workout_day = n_data.get("workout_day", {})
            rest_day    = n_data.get("rest_day", {})

            if workout_day:
                wd_label = "🏋️ Trainingstag" if lang == "de" else "🏋️ Training Day"
                pdf.sub_header(wd_label)
                pdf.macros_summary_row(workout_day, lang)
                for meal in workout_day.get("meals", []):
                    pdf.meal_row(meal)
                pdf.ln(4)

            if rest_day:
                rd_label = "😴 Ruhetag" if lang == "de" else "😴 Rest Day"
                pdf.sub_header(rd_label)
                pdf.macros_summary_row(rest_day, lang)
                for meal in rest_day.get("meals", []):
                    pdf.meal_row(meal)
                pdf.ln(4)
        else:
            # Legacy layout
            macros    = n_data.get("macros", {})
            daily_cal = n_data.get("daily_calories", "")
            if macros or daily_cal:
                pdf.set_fill_color(240, 255, 248)
                pdf.set_font("DejaVu", "B", 9)
                pdf.set_text_color(10, 15, 30)
                kcal_label = "Tageskalorien" if lang == "de" else "Daily Calories"
                pdf.cell(0, 7, f"{kcal_label}: {safe(str(daily_cal))} kcal", fill=True, ln=True)
                if macros:
                    macro_str = (
                        f"Protein: {macros.get('protein_g', 0)}g  |  "
                        f"Kohlenhydrate: {macros.get('carbs_g', 0)}g  |  "
                        f"Fett: {macros.get('fat_g', 0)}g"
                    ) if lang == "de" else (
                        f"Protein: {macros.get('protein_g', 0)}g  |  "
                        f"Carbs: {macros.get('carbs_g', 0)}g  |  "
                        f"Fat: {macros.get('fat_g', 0)}g"
                    )
                    pdf.set_font("DejaVu", "", 9)
                    pdf.cell(0, 6, safe(macro_str), ln=True)
                pdf.ln(3)

            meal_plan = n_data.get("meal_plan", [])
            for day_type_data in meal_plan:
                day_type = safe(day_type_data.get("day_type", ""))
                pdf.sub_header(day_type)
                for meal in day_type_data.get("meals", []):
                    pdf.meal_row(meal)
                pdf.ln(2)

        supps = n_data.get("supplements", [])
        if supps:
            pdf.sub_header("Supplements")
            for s_item in supps:
                pdf.bullet(s_item)
            pdf.ln(2)

        tips = n_data.get("tips", [])
        if tips:
            tips_label = "Ernährungs-Tipps" if lang == "de" else "Nutrition Tips"
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
            routine_label = "Tägliche Routine" if lang == "de" else "Daily Routine"
            pdf.sub_header(routine_label)
            for item in routine:
                time_str = safe(item.get("time", ""))
                action   = safe(item.get("action", ""))
                dur      = item.get("duration_min", "")
                desc     = safe(item.get("description", ""))
                dur_str  = f" ({dur} min)" if dur else ""
                pdf.set_font("DejaVu", "B", 10)
                pdf.set_text_color(10, 15, 30)
                pdf.cell(0, 7, f"{time_str}: {action}{dur_str}", ln=True)
                if desc:
                    pdf.set_font("DejaVu", "", 9)
                    pdf.set_text_color(80, 80, 80)
                    pdf.set_x(pdf.l_margin + 6)
                    pdf.multi_cell(0, 5, desc)
                pdf.ln(1)

        techniques = st_data.get("techniques", [])
        if techniques:
            tech_label = "Techniken" if lang == "de" else "Techniques"
            pdf.sub_header(tech_label)
            for tech in techniques:
                pdf.set_font("DejaVu", "B", 10)
                pdf.set_text_color(10, 15, 30)
                pdf.cell(0, 7, safe(tech.get("name", "")), ln=True)
                pdf.set_font("DejaVu", "", 9)
                pdf.set_text_color(80, 80, 80)
                pdf.set_x(pdf.l_margin + 6)
                pdf.multi_cell(0, 5, safe(tech.get("description", "")))
                when = tech.get("when", "")
                if when:
                    when_label = "Wann:" if lang == "de" else "When:"
                    pdf.set_x(pdf.l_margin + 6)
                    pdf.set_font("DejaVu", "I", 8)
                    pdf.cell(0, 5, f"{when_label} {safe(when)}", ln=True)
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

        target  = sl_data.get("target_hours", "")
        bedtime = sl_data.get("bedtime", "")
        wake    = sl_data.get("wake_time", "")
        if target or bedtime or wake:
            pdf.set_fill_color(235, 245, 255)
            pdf.set_font("DejaVu", "", 9)
            pdf.set_text_color(10, 15, 30)
            info = (f"Ziel-Schlafdauer: {target}h  |  Schlafenszeit: {bedtime}  |  Aufstehzeit: {wake}"
                    if lang == "de" else
                    f"Target Sleep: {target}h  |  Bedtime: {bedtime}  |  Wake Time: {wake}")
            pdf.cell(0, 8, safe(info), fill=True, ln=True)
            pdf.ln(3)

        routine = sl_data.get("evening_routine", [])
        if routine:
            routine_label = "Abendroutine" if lang == "de" else "Evening Routine"
            pdf.sub_header(routine_label)
            for item in routine:
                time_str = safe(item.get("time", ""))
                action   = safe(item.get("action", ""))
                desc     = safe(item.get("description", ""))
                pdf.set_font("DejaVu", "B", 10)
                pdf.set_text_color(10, 15, 30)
                pdf.cell(0, 7, f"{time_str}: {action}", ln=True)
                if desc:
                    pdf.set_font("DejaVu", "", 9)
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
    pdf.set_y(42)
    pdf.set_font("DejaVu", "B", 16)
    pdf.set_text_color(6, 182, 212)
    closing = "Viel Erfolg auf deinem Weg!" if lang == "de" else "Best of luck on your journey!"
    pdf.cell(0, 10, safe(closing), align="C", ln=True)
    pdf.set_font("DejaVu", "", 10)
    pdf.set_text_color(241, 245, 249)
    pdf.cell(0, 8, "NeuroHealthMastery | Rene Rusch", align="C", ln=True)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 6, "neurohealthmastery.de", align="C", ln=True)
    pdf.ln(8)
    pdf.set_font("DejaVu", "I", 8)
    pdf.set_text_color(148, 163, 184)
    disclaimer = (
        "Hinweis: Rene Rusch ist kein Arzt. Alle Empfehlungen basieren auf professionellen "
        "Zertifikaten (Natural Signature Typing, Ernährungscoaching) und wissenschaftlicher "
        "Literatur. Dieser Plan ersetzt keine ärztliche Beratung."
    ) if lang == "de" else (
        "Disclaimer: Rene Rusch is not a medical doctor. All recommendations are based on "
        "professional certifications (Natural Signature Typing, Nutrition Coaching) and "
        "peer-reviewed literature. This plan does not replace medical advice."
    )
    pdf.set_y(102)
    pdf.multi_cell(0, 5, safe(disclaimer))

    # fpdf 1.7.2 output() returns a str (latin-1 encoded PDF bytes as str)
    raw = pdf.output(dest='S')
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    return raw.encode('latin-1')
