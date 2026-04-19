#!/usr/bin/env python3
"""
Erstellt eine professionelle Tempo-Infografik für den NHM Coach PDF.
Stil: Dunkel, modern, 4 Felder mit Pfeilen und Beschriftungen.
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import matplotlib.patheffects as pe
import numpy as np

fig, ax = plt.subplots(figsize=(10, 3.2))
fig.patch.set_facecolor('#1a1a2e')
ax.set_facecolor('#1a1a2e')
ax.set_xlim(0, 10)
ax.set_ylim(0, 3.2)
ax.axis('off')

# Farben
COLOR_BG_DARK = '#0f3460'
COLOR_BG_MID = '#16213e'
COLOR_ACCENT = '#00d4aa'
COLOR_RED = '#e94560'
COLOR_YELLOW = '#f5a623'
COLOR_WHITE = '#ffffff'
COLOR_LIGHT = '#b0c4de'
COLOR_HEADER = '#00d4aa'

# Titel oben
ax.text(5.0, 3.0, 'TEMPO ERKLÄRT', fontsize=16, fontweight='bold',
        color=COLOR_ACCENT, ha='center', va='center',
        fontfamily='DejaVu Sans')

# Beispiel-Zahl groß in der Mitte
ax.text(5.0, 2.35, '4  -  1  -  X  -  0', fontsize=22, fontweight='bold',
        color=COLOR_WHITE, ha='center', va='center',
        fontfamily='DejaVu Sans',
        path_effects=[pe.withStroke(linewidth=3, foreground='#00d4aa')])

# 4 Felder
fields = [
    {'x': 0.4, 'num': '4', 'color': COLOR_RED,
     'label1': 'EXZENTRISCH', 'label2': '(Absenken)',
     'arrow': '↓', 'arrow_color': COLOR_RED},
    {'x': 3.0, 'num': '1', 'color': COLOR_YELLOW,
     'label1': 'PAUSE UNTEN', 'label2': '(Endposition)',
     'arrow': '⏸', 'arrow_color': COLOR_YELLOW},
    {'x': 5.6, 'num': 'X', 'color': COLOR_ACCENT,
     'label1': 'KONZENTRISCH', 'label2': '(Heben / explosiv)',
     'arrow': '↑', 'arrow_color': COLOR_ACCENT},
    {'x': 8.2, 'num': '0', 'color': COLOR_LIGHT,
     'label1': 'PAUSE OBEN', 'label2': '(Startposition)',
     'arrow': '⏸', 'arrow_color': COLOR_LIGHT},
]

box_w = 1.8
box_h = 1.55
box_y = 0.35

for f in fields:
    # Box Hintergrund
    box = FancyBboxPatch((f['x'], box_y), box_w, box_h,
                         boxstyle="round,pad=0.06",
                         facecolor=COLOR_BG_DARK,
                         edgecolor=f['color'],
                         linewidth=2.0)
    ax.add_patch(box)

    # Große Zahl
    ax.text(f['x'] + box_w/2, box_y + box_h - 0.32,
            f['num'], fontsize=28, fontweight='bold',
            color=f['color'], ha='center', va='center',
            fontfamily='DejaVu Sans')

    # Trennlinie
    ax.plot([f['x'] + 0.15, f['x'] + box_w - 0.15],
            [box_y + box_h - 0.62, box_y + box_h - 0.62],
            color=f['color'], linewidth=0.8, alpha=0.5)

    # Label 1
    ax.text(f['x'] + box_w/2, box_y + 0.72,
            f['label1'], fontsize=7.5, fontweight='bold',
            color=COLOR_WHITE, ha='center', va='center',
            fontfamily='DejaVu Sans')

    # Label 2
    ax.text(f['x'] + box_w/2, box_y + 0.34,
            f['label2'], fontsize=6.5,
            color=COLOR_LIGHT, ha='center', va='center',
            fontfamily='DejaVu Sans', style='italic')

# Verbindungspfeile zwischen Boxen
arrow_y = box_y + box_h/2
arrow_positions = [
    (fields[0]['x'] + box_w + 0.02, fields[1]['x'] - 0.02),
    (fields[1]['x'] + box_w + 0.02, fields[2]['x'] - 0.02),
    (fields[2]['x'] + box_w + 0.02, fields[3]['x'] - 0.02),
]
for (x1, x2) in arrow_positions:
    ax.annotate('', xy=(x2, arrow_y), xytext=(x1, arrow_y),
                arrowprops=dict(arrowstyle='->', color=COLOR_ACCENT,
                                lw=1.5, mutation_scale=12))

# Hinweis unten
ax.text(5.0, 0.12, 'X = explosiv / so schnell wie möglich  |  0 = keine Pause',
        fontsize=7, color=COLOR_LIGHT, ha='center', va='center',
        fontfamily='DejaVu Sans', style='italic')

plt.tight_layout(pad=0.1)
plt.savefig('/home/ubuntu/nhm_coach/static/img/tempo_graphic.png',
            dpi=150, bbox_inches='tight',
            facecolor=fig.get_facecolor())
plt.close()
print("Tempo-Grafik gespeichert: static/img/tempo_graphic.png")
