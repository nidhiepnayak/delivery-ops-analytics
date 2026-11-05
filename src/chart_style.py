"""
chart_style.py — one consistent, quiet look for every chart in this project.

Rule of thumb used throughout: one colour for the bar that tells the story,
muted grey for everything else, so the reader's eye goes straight to the point.
"""

import matplotlib.pyplot as plt

SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_2 = "#52514e"
GRID = "#e1e0d9"
ACCENT = "#2a78d6"   # the bar that matters
MUTED = "#c3c2b7"    # everything else


def apply_style():
    plt.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "axes.edgecolor": GRID,
        "axes.labelcolor": TEXT_2,
        "axes.titlecolor": TEXT,
        "axes.titlesize": 13,
        "axes.titleweight": "semibold",
        "axes.titlelocation": "left",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "xtick.color": TEXT_2,
        "ytick.color": TEXT_2,
        "font.size": 10.5,
        "figure.dpi": 110,
        "savefig.dpi": 160,
        "savefig.bbox": "tight",
    })


def hbar(ax, labels, values, highlight=None, fmt="{:.0f}%", xlabel="", xmax=None):
    """Horizontal bar chart. `highlight` = list of labels drawn in the accent colour."""
    highlight = set(highlight or [])
    colors = [ACCENT if lab in highlight else MUTED for lab in labels]
    bars = ax.barh(labels, values, color=colors, height=0.55)
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    ax.set_axisbelow(True)
    ax.set_xlabel(xlabel)
    top = xmax or max(values) * 1.18
    ax.set_xlim(0, top)
    for bar, v in zip(bars, values):
        ax.text(bar.get_width() + top * 0.01, bar.get_y() + bar.get_height() / 2,
                fmt.format(v), va="center", color=TEXT, fontsize=10)
    return bars


def subtitle(ax, text):
    ax.text(0, 1.02, text, transform=ax.transAxes, color=TEXT_2, fontsize=10, va="bottom")
