#!/usr/bin/env python3
"""SIGMOD 2027 Industrial Track v3.0 Master Figure Suite for HermesGov.

Implements all visual rules from `ccfa-visual-table-ref-mastery` & `sigmod-industrial-figure-craft`:
  - Figure 1 (`fig_architecture.pdf`): 3-column orthogonal architecture with concrete Path 1/2/3
    mechanism + microsecond badges inside the Hero Planner, wide non-crowded Pass/Fail channels,
    and zero badge-border overlaps.
  - Figure 2 (`fig_production_evolution.pdf`): 213-query contract evolution + 50-query manual
    boundary audit with shaded 14 pp audit-gap band and roomy bar labels.
  - Figure 3 (`fig_ablation_latency.pdf`): 3-panel overhead, 36->1,599-table O(1) scale invariance,
    and end-to-end log latency share with crisp inter-bar separation (zero touching labels).
  - Figure 4 (`fig_caliber_traps.pdf`): Shared-Y-axis aligned 3-panel horizontal matrix across all
    6 named foundation models + shaded HermesGov spotlight row — eliminating 100% of vertical
    x-tick collisions and cramped in-bar labels.
"""

import json
import os
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Ellipse, Rectangle
from matplotlib.lines import Line2D
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sigmod_arch_primitives import PALETTE as P, draw_zone, draw_diamond, draw_badge, draw_ortho_arrow

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, 'results')
FIG_DIR = os.path.join(ROOT, 'figures')
os.makedirs(FIG_DIR, exist_ok=True)

C_NAVY  = '#0B4F8C'
C_TEAL  = '#0D7C66'
C_AMBER = '#D97706'
C_VERM  = '#C94A1E'
C_SKY   = '#5B9BD5'
C_SLATE = '#334155'
C_GRAY  = '#64748B'

with open(os.path.join(BASE, 'experiments_microbench_results.json')) as f:
    MB = json.load(f)
with open(os.path.join(BASE, 'experiments_tpcds_public_microbench.json')) as f:
    TPC = json.load(f)
with open(os.path.join(BASE, 'experiments_stage2_formal_scale.json')) as f:
    S2 = json.load(f)['estate_scale_and_hit_ratio_sweep']
with open(os.path.join(BASE, 'experiments_6model_dual_benchmark.json')) as f:
    B6 = json.load(f)['results']


def save_both(fig, stem):
    pdf_p = os.path.join(FIG_DIR, f'{stem}.pdf')
    png_p = os.path.join(FIG_DIR, f'{stem}.png')
    fig.savefig(pdf_p, format='pdf', bbox_inches='tight', pad_inches=0.03)
    plt.close(fig)
    print('Saved:', pdf_p)


# ============================================================================
# FIGURE 1: System Architecture (fig_architecture.pdf)
# ============================================================================
def _card(ax, x, y, w, h, title, body='', fc='#FFFFFF', ec='#94A3B8', lw=0.8,
          tc='#0F172A', bc='#334155', tfs=6.2, bfs=5.3, r=0.55, z=3):
    p = FancyBboxPatch((x, y), w, h, boxstyle=f'round,pad=0.06,rounding_size={r}',
                       facecolor=fc, edgecolor=ec, linewidth=lw, zorder=z)
    ax.add_patch(p)
    if body:
        ax.text(x + w / 2, y + h * 0.73, title, ha='center', va='center',
                fontsize=tfs, fontweight='bold', color=tc, zorder=z + 1)
        ax.text(x + w / 2, y + h * 0.30, body, ha='center', va='center',
                fontsize=bfs, color=bc, linespacing=1.20, zorder=z + 1)
    else:
        ax.text(x + w / 2, y + h / 2, title, ha='center', va='center',
                fontsize=tfs, fontweight='bold', color=tc, zorder=z + 1)


def _path_operator_card(ax, x, y, w, h, title, formula, lat_badge, z=4):
    p = FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.05,rounding_size=0.45',
                       facecolor='#F4F9FF', edgecolor=P['hero_mid'], linewidth=0.8, zorder=z)
    ax.add_patch(p)
    # Left accent bar showing active compilation operator
    bar = FancyBboxPatch((x + 0.25, y + 0.45), 0.55, h - 0.90,
                         boxstyle='round,pad=0.02,rounding_size=0.2',
                         facecolor=P['hero_dark'], edgecolor='none', zorder=z + 1)
    ax.add_patch(bar)
    ax.text(x + 1.35, y + h * 0.71, title, ha='left', va='center',
            fontsize=5.20, fontweight='bold', color=P['hero_dark'], zorder=z + 2)
    ax.text(x + 1.35, y + h * 0.28, formula, ha='left', va='center',
            fontsize=4.55, color='#334155', zorder=z + 2)
    # Right-aligned latency pill (well clear of both title and formula!)
    bw, bh = 6.3, 2.2
    bx, by = x + w - bw - 0.60, y + (h - bh) / 2
    pill = FancyBboxPatch((bx, by), bw, bh, boxstyle='round,pad=0.04,rounding_size=0.35',
                          facecolor='#FFFFFF', edgecolor=P['hero_dark'], linewidth=0.65, zorder=z + 3)
    ax.add_patch(pill)
    ax.text(bx + bw / 2, by + bh / 2, lat_badge, ha='center', va='center',
            fontsize=4.65, fontweight='bold', color=P['hero_dark'], zorder=z + 4)


def _cylinder(ax, x, y, w, h, title, body='', fc='#FFFFFF', top_fc='#E2E8F0',
              ec='#64748B', tc='#0F172A', bc='#475569', tfs=5.35, bfs=4.9, lw=0.9, z=3):
    eh = min(2.1, h * 0.19)
    ax.add_patch(Ellipse((x + w / 2, y + eh / 2), w, eh, facecolor=fc, edgecolor=ec, lw=lw, zorder=z))
    ax.add_patch(Rectangle((x, y + eh / 2), w, h - eh, facecolor=fc, edgecolor='none', zorder=z))
    ax.plot([x, x], [y + eh / 2, y + h - eh / 2], color=ec, lw=lw, zorder=z + 1)
    ax.plot([x + w, x + w], [y + eh / 2, y + h - eh / 2], color=ec, lw=lw, zorder=z + 1)
    ax.add_patch(Ellipse((x + w / 2, y + h - eh / 2), w, eh, facecolor=top_fc, edgecolor=ec, lw=lw, zorder=z + 2))
    body_h = h - eh
    ax.text(x + w / 2, y + eh / 2 + body_h * 0.69, title, ha='center', va='center',
            fontsize=tfs, fontweight='bold', color=tc, zorder=z + 3)
    ax.text(x + w / 2, y + eh / 2 + body_h * 0.27, body, ha='center', va='center',
            fontsize=bfs, color=bc, linespacing=1.18, zorder=z + 3)


def make_fig1_v3():
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': ['Helvetica', 'Arial', 'DejaVu Sans'],
        'pdf.fonttype': 42,
        'ps.fonttype': 42,
    })
    fig, ax = plt.subplots(figsize=(7.10, 4.32))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 66)
    ax.axis('off')

    # --- COLUMN I (x=0.6..25.6): Online Query Entry + Offline Governance Plane ---
    draw_zone(ax, 0.6, 46.2, 25.0, 19.0, 'I. Query Entry (Online)',
              bg=P['infra_bg'], edge=P['infra_edge'], header_bg=P['infra_dark'],
              header_fg='#FFFFFF', header_h=3.6, lw=0.85, title_fs=6.4)
    _card(ax, 1.7, 54.5, 22.8, 6.7,
          'Concrete Business Query',
          '"Oct US RMA return rate\n by product category?"',
          fc='#FFFFFF', ec=P['infra_edge'], tc=P['infra_dark'], bc='#1E293B', tfs=5.5, bfs=5.15)
    _card(ax, 1.7, 47.2, 22.8, 5.8,
          'Swappable LLM Parser',
          'Claude / GPT / Gemini / DeepSeek\n-> Typed Spec S (No Raw SQL)',
          fc='#F1F5F9', ec=P['infra_edge'], tc=P['infra_dark'], bc=P['muted'], tfs=5.55, bfs=4.85)
    draw_ortho_arrow(ax, [(13.1, 54.4), (13.1, 53.1)], color=P['infra_dark'], lw=0.9)

    draw_zone(ax, 0.6, 8.6, 25.0, 35.8, 'Offline Governance Plane',
              bg=P['ctrl_bg'], edge=P['ctrl_edge'], header_bg=P['ctrl_dark'],
              header_fg='#FFFFFF', header_h=3.6, lw=0.9, title_fs=6.4)
    _card(ax, 1.7, 33.7, 22.8, 5.9,
          '1. Metric Def. Center',
          'Atomic / Deriv. · Additivity\n(Zero Physical Table Refs)',
          fc='#FFFFFF', ec='#D97706', lw=0.75, tc=P['ctrl_dark'], tfs=5.65, bfs=4.9)
    _card(ax, 1.7, 26.6, 22.8, 5.9,
          '2. Physical Impl. Center',
          'OneData: Atomic -> DWD Only\nfixed_filters + pop_ref + FX',
          fc='#FFFFFF', ec='#D97706', lw=0.75, tc=P['ctrl_dark'], tfs=5.65, bfs=4.9)
    _card(ax, 1.7, 19.5, 22.8, 5.9,
          '3. Shared Gov. Assets',
          'SHA-256 Profiles · Lineage\nVerified Joins · 86.9K Entities',
          fc='#FFFFFF', ec='#D97706', lw=0.75, tc=P['ctrl_dark'], tfs=5.65, bfs=4.9)
    _cylinder(ax, 2.0, 9.6, 22.2, 7.6,
              'Immutable Snapshot (Redis)',
              '7-Tuple Version Set\n6-Field Warehouse Scope',
              fc='#FEF3C7', top_fc='#FDE68A', ec='#B45309',
              tc=P['ctrl_dark'], bc='#78350F', tfs=5.25, bfs=4.8, lw=0.9)
    draw_ortho_arrow(ax, [(13.1, 33.6), (13.1, 32.6)], color=P['ctrl_dark'], lw=0.8)
    draw_ortho_arrow(ax, [(13.1, 26.5), (13.1, 25.5)], color=P['ctrl_dark'], lw=0.8)
    draw_ortho_arrow(ax, [(13.1, 19.4), (13.1, 17.3)], color=P['ctrl_dark'], lw=0.85)
    draw_badge(ax, 10.6, 18.35, '1', kind='offline', r=0.98, fs=5.5)

    # --- COLUMN II (x=28.4..69.2): HERO SPOTLIGHT — HermesGov Deterministic Core ---
    draw_zone(ax, 28.4, 8.6, 40.8, 56.6, 'II. HermesGov Deterministic Core',
              bg=P['hero_bg'], edge=P['hero_dark'], header_bg=P['hero_dark'],
              header_fg='#FFFFFF', header_h=3.8, lw=1.35, title_fs=6.4)

    _card(ax, 30.0, 56.4, 37.6, 3.9,
          '   Unified MCP Gateway  |  SSO · Tool RBAC · Audit Trace',
          '', fc='#FFFFFF', ec=P['hero_mid'], lw=0.85, tc=P['hero_dark'], tfs=5.15)
    draw_badge(ax, 31.5, 58.35, '2', kind='online', r=0.95, fs=5.4, z=6)

    chips = [
        ('Unified\nData', False),
        ('Certified\nKPI', False),
        ('Recursive\nPlanner*', True),
        ('Guarded\nSQL', False),
        ('Scoped\nReport', False),
    ]
    cw, cg = 6.92, 0.75
    for idx, (clbl, is_hero) in enumerate(chips):
        cx = 30.0 + idx * (cw + cg)
        _card(ax, cx, 51.0, cw, 4.2, clbl, '',
              fc=P['hero_dark'] if is_hero else '#FFFFFF',
              ec=P['hero_dark'] if is_hero else P['infra_edge'],
              lw=1.0 if is_hero else 0.7,
              tc='#FFFFFF' if is_hero else P['infra_dark'],
              tfs=4.65, r=0.45)
    draw_ortho_arrow(ax, [(48.8, 56.3), (48.8, 55.3)], color=P['hero_dark'], lw=0.85)

    # Enriched Planner Sub-Zone with Algebraic + Microsecond Operator Cards
    draw_zone(ax, 30.0, 26.8, 37.6, 21.8, 'Unified Recursive Planner (Alg. 1) & Join BFS (Alg. 2)',
              bg='#FFFFFF', edge=P['hero_mid'], header_bg=P['hero_chip'],
              header_fg=P['hero_dark'], header_h=3.2, lw=0.95, title_fs=5.6, r=0.6)

    _path_operator_card(
        ax, 31.1, 39.8, 35.4, 4.6,
        'Path 1: ADS Direct Reuse (Stop-on-Hit)',
        'All 6 equivalence flags attested (Thm. 4.1)',
        '3.2 µs P50',
    )
    _path_operator_card(
        ax, 31.1, 34.0, 35.4, 4.6,
        'Path 2: DWS + DIM Unique-Path BFS',
        'Whitelist ≤3 hops · No DWS-DWS · SCD2',
        '13.3 µs P50',
    )
    _path_operator_card(
        ax, 31.1, 28.2, 35.4, 4.6,
        'Path 3: Hybrid Child Expansion',
        'SUM(num)/NULLIF(SUM(den),0) + fixed_filters',
        '16.7 µs P50',
    )

    draw_ortho_arrow(ax, [(48.8, 50.9), (48.8, 48.7)], color=P['hero_dark'], lw=1.0)
    draw_badge(ax, 46.3, 49.8, '3', kind='online', r=0.92, fs=5.3)

    # Bottom of Col II: 8-Dimension Gate Diamond + AST Guard Card
    draw_diamond(ax, 42.2, 17.3, 11.2, 6.2,
                 '8-Dim Cert. Gate\n& 7-Tuple Fence\n(Pass All?)',
                 fc='#FFFFFF', ec=P['hero_dark'], tc=P['hero_dark'], fs=5.65, lw=1.2)
    _card(ax, 55.8, 13.2, 11.8, 8.2,
          'AST SQL Guard',
          'sqlglot Parser\nTenant Inject\nNo ODS · EXPLAIN',
          fc='#FFFFFF', ec=P['hero_mid'], lw=0.85, tc=P['hero_dark'], bc=P['muted'], tfs=5.35, bfs=4.8)

    draw_ortho_arrow(ax, [(42.2, 26.7), (42.2, 23.6)], color=P['hero_dark'], lw=1.0)
    draw_badge(ax, 39.8, 25.2, '4', kind='online', r=0.98, fs=5.5)
    draw_ortho_arrow(ax, [(53.5, 17.3), (55.7, 17.3)], color=P['hero_dark'], lw=0.95)

    # --- COLUMN III (x=74.0..99.4): Dual Outcomes, StarRocks, Closed-Loop Audit ---
    draw_zone(ax, 74.0, 46.2, 25.4, 19.0, 'III. Governed Outcomes',
              bg=P['infra_bg'], edge=P['infra_edge'], header_bg=P['infra_dark'],
              header_fg='#FFFFFF', header_h=3.6, lw=0.85, title_fs=6.4)
    _card(ax, 75.1, 54.5, 23.2, 6.7,
          'Certified Primary KPI',
          'Exact Num/Den + Provenance\n(100% Invariants Enforced)',
          fc=P['ok_bg'], ec=P['ok_edge'], lw=1.05, tc=P['ok_dark'], bc='#115E59', tfs=5.45, bfs=5.0)
    _card(ax, 75.1, 47.2, 23.2, 6.1,
          'Diagnostic / Clean Refusal',
          'Uncertified Pop · Stale Hash\nUnmodeled (No Silent 0)',
          fc=P['warn_bg'], ec=P['warn_edge'], lw=1.0, tc=P['warn_dark'], bc='#7C2D12', tfs=5.55, bfs=4.85)

    draw_zone(ax, 74.0, 24.2, 25.4, 20.0, 'StarRocks Warehouse',
              bg=P['infra_bg'], edge=P['infra_edge'], header_bg='#475569',
              header_fg='#FFFFFF', header_h=3.4, lw=0.85, title_fs=6.3)
    _cylinder(ax, 75.3, 25.4, 22.8, 14.0,
              'Governed Core (105 Non-ODS)',
              'ADS (30) · DWS (13) · DWD (11)\nDIM/BR (47) · ACL/ETL (4)\n(Estate: 1,599 Tables / 9 DBs)',
              fc='#FFFFFF', top_fc='#E2E8F0', ec='#64748B',
              tc=P['infra_dark'], bc=P['muted'], tfs=5.25, bfs=4.8, lw=0.9)

    draw_zone(ax, 74.0, 8.6, 25.4, 13.6, 'Closed-Loop Audit',
              bg=P['ctrl_bg'], edge=P['ctrl_edge'], header_bg=P['ctrl_dark'],
              header_fg='#FFFFFF', header_h=3.3, lw=0.9, title_fs=6.3)
    _card(ax, 75.1, 9.8, 23.2, 8.0,
          'Daily Reconcile & 7-Code Audit',
          'Daily Drift Tickets (646 / 97d)\nERP-vs.-MCP Cross-Check',
          fc='#FFFFFF', ec='#D97706', lw=0.8, tc=P['ctrl_dark'], bc='#78350F', tfs=5.1, bfs=4.95)

    # --- INTER-COLUMN ORTHOGONAL CHANNELS (Wide 4.8-unit Right Gutter: 69.2..74.0) ---
    # [1] LLM Parser -> Unified MCP Gateway (Left Gutter x=27.0)
    draw_ortho_arrow(ax, [(24.6, 50.1), (27.0, 50.1), (27.0, 58.35), (29.9, 58.35)],
                     color=P['hero_dark'], lw=1.05)
    draw_badge(ax, 27.0, 54.2, '1', kind='online', r=0.98, fs=5.5)

    # Offline Snapshot -> 8-Dim Gate (Left Gutter x=27.0)
    draw_ortho_arrow(ax, [(24.3, 13.4), (27.0, 13.4), (27.0, 17.3), (30.9, 17.3)],
                     color='#B45309', lw=1.0, ls='--')

    # AST Guard -> StarRocks Read-Only SQL (Right Gutter outer lane x=72.6)
    draw_ortho_arrow(ax, [(67.7, 17.3), (72.6, 17.3), (72.6, 29.8), (75.2, 29.8)],
                     color=P['hero_dark'], lw=1.05)

    # StarRocks -> Certified Primary KPI (Pass lane x=72.6)
    draw_ortho_arrow(ax, [(75.2, 36.2), (72.6, 36.2), (72.6, 57.85), (75.0, 57.85)],
                     color=P['ok_edge'], lw=1.05)
    draw_badge(ax, 72.6, 57.85, '5', kind='online', r=1.02, fs=5.6)
    ax.text(72.6, 60.4, 'Pass', ha='center', va='center', fontsize=5.6, fontweight='bold',
            color=P['ok_dark'], bbox=dict(facecolor='white', edgecolor='none', pad=0.4), zorder=8)

    # 8-Dim Gate -> Diagnostic / Clean Refusal (Fail lane x=70.6 — 2.0 units clear of x=72.6!)
    draw_ortho_arrow(ax, [(42.2, 11.0), (42.2, 9.7), (70.6, 9.7), (70.6, 50.25), (75.0, 50.25)],
                     color=P['warn_edge'], lw=0.95, ls='--')
    ax.text(70.6, 52.3, 'Fail', ha='center', va='center', fontsize=5.6, fontweight='bold',
            color=P['warn_dark'], bbox=dict(facecolor='white', edgecolor='none', pad=0.4), zorder=8)

    # StarRocks -> Closed-Loop Audit
    draw_ortho_arrow(ax, [(86.7, 24.1), (86.7, 22.3)], color='#B45309', lw=0.95, ls='--')

    # (2) Outer Bottom Feedback Loop: Closed-Loop Audit -> Offline Governance Plane
    draw_ortho_arrow(ax, [(86.7, 8.5), (86.7, 5.7), (13.1, 5.7), (13.1, 8.5)],
                     color='#B45309', lw=1.0, ls='--')
    draw_badge(ax, 33.8, 5.7, '2', kind='offline', r=1.05, fs=5.6, z=8)
    ax.text(35.6, 5.7, 'Drift Auto-Stale & Governance Feedback Loop', ha='left', va='center',
            fontsize=5.9, fontweight='bold', color=P['ctrl_dark'],
            bbox=dict(facecolor='white', edgecolor='none', pad=0.9), zorder=8)

    # --- Bottom 1-Line Legend ---
    ly = 1.8
    ax.plot([1.5, 4.8], [ly, ly], color=P['hero_dark'], lw=1.1)
    draw_badge(ax, 6.2, ly, 'n', kind='online', r=0.92, fs=5.3)
    ax.text(7.8, ly, 'Online Query Path (1–5)', ha='left', va='center', fontsize=5.9, color=P['text'])

    ax.plot([31.5, 34.8], [ly, ly], color='#B45309', lw=1.0, ls='--')
    draw_badge(ax, 36.2, ly, 'n', kind='offline', r=0.92, fs=5.3)
    ax.text(37.8, ly, 'Offline Sync / Audit Loop (1–2)', ha='left', va='center', fontsize=5.9, color=P['text'])

    leg_box = FancyBboxPatch((67.5, ly - 0.85), 2.7, 1.7, boxstyle='round,pad=0.05,rounding_size=0.3',
                             facecolor=P['hero_bg'], edgecolor=P['hero_dark'], lw=1.0)
    ax.add_patch(leg_box)
    ax.text(71.1, ly, 'HermesGov Core  (*Pilot Branch)', ha='left', va='center',
            fontsize=5.9, color=P['hero_dark'], fontweight='bold')

    save_both(fig, 'fig_architecture')


# ============================================================================
#SHARED SERIF RC FOR DATA CHARTS (Figures 2, 3, 4)
# ============================================================================
def _set_chart_rc():
    plt.rcParams.update({
        'font.family': 'serif',
        'font.serif': ['Times New Roman', 'Times', 'DejaVu Serif'],
        'mathtext.fontset': 'stix',
        'font.size': 8.2,
        'axes.titlesize': 8.8,
        'axes.labelsize': 8.1,
        'xtick.labelsize': 7.4,
        'ytick.labelsize': 7.4,
        'legend.fontsize': 7.2,
        'axes.spines.top': False,
        'axes.spines.right': False,
        'pdf.fonttype': 42,
        'ps.fonttype': 42,
    })


# ============================================================================
# FIGURE 2: Production Evolution & 50-Query Audit Gap (fig_production_evolution.pdf)
# ============================================================================
def make_fig2_v3():
    _set_chart_rc()
    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(7.05, 2.48), gridspec_kw={'width_ratios': [1.0, 1.08]}
    )

    versions = ['Iter. 1\n(Initial)', 'Iter. 2\n(Aligned)', 'Iter. 3\n(Hardened)']
    x = np.arange(len(versions))
    w = 0.25
    probe_pass = [64, 102, 109]
    route_mis  = [58, 36, 36]
    sem_mis    = [28, 6, 0]

    b1 = ax1.bar(x - w, probe_pass, width=w, color=C_NAVY, edgecolor='#0F172A', lw=0.55, label='Probe Pass')
    b2 = ax1.bar(x,     route_mis,  width=w, color=C_AMBER, edgecolor='#0F172A', lw=0.55, hatch='///', label='Route Mismatch')
    b3 = ax1.bar(x + w, sem_mis,    width=w, color=C_VERM, edgecolor='#0F172A', lw=0.55, hatch='xxx', label='Sem. Mismatch')

    for bars in (b1, b2, b3):
        for bar in bars:
            h = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width() / 2, h + 2.3, f'{int(h)}',
                     ha='center', va='bottom', fontsize=7.3, fontweight='bold', color='#0F172A')

    ax1.annotate('28 → 0', xy=(2 + w, 12.0), xytext=(2 + w, 58),
                 ha='center', va='center', fontsize=6.9, fontweight='bold', color=C_VERM,
                 bbox=dict(boxstyle='round,pad=0.22', facecolor='#FFF5F2', edgecolor=C_VERM, lw=0.75),
                 arrowprops=dict(arrowstyle='->', color=C_VERM, lw=0.95))

    ax1.set_xticks(x)
    ax1.set_xticklabels(versions, fontsize=7.4)
    ax1.set_xlim(-0.52, 2.60)
    ax1.set_ylabel('Queries (out of 213)')
    ax1.set_ylim(0, 130)
    ax1.set_title('(a) 213-Query Production Library Evolution', fontweight='bold', pad=21)
    ax1.grid(axis='y', linestyle=':', alpha=0.4)
    ax1.set_axisbelow(True)
    ax1.legend(loc='lower center', bbox_to_anchor=(0.5, 1.00), ncol=3, frameon=False,
               handlelength=1.15, columnspacing=0.85, fontsize=7.1)

    # Panel (b): 50-Query Manual Boundary Audit
    cats = ['SQL Exec.\n& Ans.', 'Auto Obs.\nPass', 'Human\nFaithful', 'Correct\nRefusal', 'Silent Sem.\nError']
    vals = [33, 34, 27, 3, 6]
    pcts = ['66.0%', '68.0%', '54.0%', '6.0%', '12.0%\n(18.2% SQL)']
    cols = [C_SKY, C_NAVY, C_TEAL, '#94A3B8', C_VERM]
    hatches = ['', '', '', '...', 'xxx']
    x2 = np.arange(len(cats))
    bars2 = ax2.bar(x2, vals, width=0.60, color=cols, edgecolor='#0F172A', lw=0.55, zorder=3)
    for idx, (bar, h_pat, v, p) in enumerate(zip(bars2, hatches, vals, pcts)):
        if h_pat:
            bar.set_hatch(h_pat)
        lbl = f'{v}\n({p})' if '\n' not in p else f'{v}\n{p}'
        if idx == 2:
            ax2.text(bar.get_x() + bar.get_width() / 2, v * 0.52, lbl,
                     ha='center', va='center', fontsize=6.4, fontweight='bold', color='white', zorder=4)
        else:
            ax2.text(bar.get_x() + bar.get_width() / 2, v + 0.95, lbl,
                     ha='center', va='bottom', fontsize=6.6, fontweight='bold', color='#0F172A',
                     bbox=dict(boxstyle='square,pad=0.04', facecolor='white', alpha=0.88, edgecolor='none'), zorder=4)

    ax2.fill_between([1.70, 2.30], 27, 34, color='#FDECE7', edgecolor=C_VERM,
                     linestyle='--', linewidth=0.8, zorder=2)
    ax2.text(2.0, 30.5, '−7', ha='center', va='center', fontsize=7.2, fontweight='bold', color=C_VERM, zorder=4)
    ax2.plot([1.30, 2.30], [34, 34], color=C_VERM, linestyle='--', lw=0.85, zorder=3)
    ax2.annotate('14 pp Audit Gap\n(Auto 68% vs. Faithful 54%)',
                 xy=(2.30, 30.8), xytext=(3.36, 39.2),
                 ha='center', va='center', fontsize=6.6, fontweight='bold', color=C_VERM,
                 bbox=dict(boxstyle='round,pad=0.22', facecolor='#FFF5F2', edgecolor=C_VERM, lw=0.75),
                 arrowprops=dict(arrowstyle='->', color=C_VERM, lw=0.9, connectionstyle='arc3,rad=0.14'),
                 zorder=5)

    ax2.set_xticks(x2)
    ax2.set_xticklabels(cats, fontsize=7.1)
    ax2.set_xlim(-0.55, 4.62)
    ax2.set_ylabel('Queries (out of 50)')
    ax2.set_ylim(0, 46.5)
    ax2.set_title('(b) 50-Query Manual Boundary Audit', fontweight='bold', pad=21)
    ax2.grid(axis='y', linestyle=':', alpha=0.4)
    ax2.set_axisbelow(True)

    plt.tight_layout(w_pad=1.4)
    save_both(fig, 'fig_production_evolution')


# ============================================================================
# FIGURE 3: Overhead, Estate-Scale Invariance & End-to-End Share (fig_ablation_latency.pdf)
# ============================================================================
def make_fig3_v3():
    _set_chart_rc()
    fig, (ax1, ax2, ax3) = plt.subplots(
        1, 3, figsize=(7.15, 2.48),
        gridspec_kw={'width_ratios': [1.22, 1.12, 0.96]}
    )

    # Panel (a): Cross-Warehouse Path Latency (crisp gap between paired bars -> zero touching labels!)
    pl_l, sg_l = MB['planning_latency_us'], MB['sql_guard_eval']
    pl_t, sg_t = TPC['planning_latency_us'], TPC['sql_guard_eval']
    paths = ['ADS\nDirect', 'AST\nGuard', '3-Hop\nBFS', 'Hybrid\nRatio']
    loc_p50 = [pl_l['ADS_Direct_Reuse']['p50_us'], sg_l['p50_us'],
               pl_l['DWS_Plus_DIM_3Hop']['p50_us'], pl_l['Hybrid_Derivative_Ratio']['p50_us']]
    tpc_p50 = [pl_t['ADS_Direct_Reuse']['p50_us'], sg_t['p50_us'],
               pl_t['DWS_Plus_DIM_3Hop']['p50_us'], pl_t['Hybrid_Derivative_Ratio']['p50_us']]
    loc_p99 = [pl_l['ADS_Direct_Reuse']['p99_us'], sg_l['p95_us'],
               pl_l['DWS_Plus_DIM_3Hop']['p99_us'], pl_l['Hybrid_Derivative_Ratio']['p99_us']]
    tpc_p99 = [pl_t['ADS_Direct_Reuse']['p99_us'], sg_t['p95_us'],
               pl_t['DWS_Plus_DIM_3Hop']['p99_us'], pl_t['Hybrid_Derivative_Ratio']['p99_us']]

    x = np.arange(len(paths))
    w = 0.34
    dx = 0.195  # leaves a crisp 0.05 gap between paired bars!
    b1 = ax1.bar(x - dx, loc_p50, width=w, color=C_NAVY, edgecolor='#0F172A', lw=0.5,
                 label='Loctek 105 (P50)', zorder=3)
    b2 = ax1.bar(x + dx, tpc_p50, width=w, color=C_TEAL, edgecolor='#0F172A', lw=0.5,
                 hatch='///', label='TPC-DS 36 (P50)', zorder=3)
    ax1.scatter(x - dx, loc_p99, marker='D', s=15, color=C_VERM, edgecolors='#0F172A',
                lw=0.35, zorder=5, label='Tail P99/P95')
    ax1.scatter(x + dx, tpc_p99, marker='D', s=15, color=C_VERM, edgecolors='#0F172A', lw=0.35, zorder=5)

    for idx in range(len(paths)):
        # Left bar (Navy solid -> crisp white P50 text inside bar, zero wide white pill!)
        cx_l = b1[idx].get_x() + w / 2
        ax1.text(cx_l - 0.02, loc_p99[idx] + 0.9, f'{loc_p99[idx]:.1f}', ha='center', va='bottom',
                 fontsize=5.8, fontweight='bold', color=C_VERM, zorder=6)
        ax1.text(cx_l, loc_p50[idx] * 0.48, f'{loc_p50[idx]:.1f}', ha='center', va='center',
                 fontsize=5.7, fontweight='bold', color='white', zorder=6)

        # Right bar (Teal hatched -> compact white pill well within bar width)
        cx_r = b2[idx].get_x() + w / 2
        ax1.text(cx_r + 0.02, tpc_p99[idx] + 0.9, f'{tpc_p99[idx]:.1f}', ha='center', va='bottom',
                 fontsize=5.8, fontweight='bold', color=C_VERM, zorder=6)
        ax1.text(cx_r, tpc_p50[idx] * 0.48, f'{tpc_p50[idx]:.1f}', ha='center', va='center',
                 fontsize=5.6, fontweight='bold', color='#0F172A',
                 bbox=dict(boxstyle='round,pad=0.07', facecolor='white', alpha=0.92, edgecolor='none'), zorder=6)

    ax1.axhline(20.0, color=C_GRAY, linestyle='--', lw=0.75, alpha=0.8, zorder=2)
    ax1.text(-0.46, 20.7, '20 $\\mu$s median budget', fontsize=6.1, style='italic', color=C_SLATE)
    ax1.set_xticks(x)
    ax1.set_xticklabels(paths, fontsize=6.9)
    ax1.set_xlim(-0.54, 3.54)
    ax1.set_ylabel('Latency ($\\mu$s)')
    ax1.set_ylim(0, 29.8)
    ax1.set_title('(a) Path Overhead (105 vs. 36)', fontweight='bold', pad=26)
    ax1.grid(axis='y', linestyle=':', alpha=0.4)
    ax1.set_axisbelow(True)
    ax1.legend(loc='lower center', bbox_to_anchor=(0.50, 1.01), ncol=3, frameon=False,
               handlelength=0.95, columnspacing=0.45, fontsize=6.0)

    # Panel (b): Multi-Scale Estate Invariance (36 -> 1,599 Tables)
    scales = S2['scales']
    sx = np.arange(len(scales))
    un_y   = [S2['unscoped_full_graph'][str(s)]['p50_us'] for s in scales]
    r0_y   = [S2['hermesgov_scoped'][str(s)]['rho_0']['mean_us'] for s in scales]
    r50_y  = [S2['hermesgov_scoped'][str(s)]['rho_50']['mean_us'] for s in scales]
    r100_y = [S2['hermesgov_scoped'][str(s)]['rho_100']['mean_us'] for s in scales]

    ax2.plot(sx, un_y, 's--', color=C_VERM, lw=1.35, markersize=4.4, label='Unscoped $O(|T|)$', zorder=4)
    ax2.plot(sx, r0_y, 'o-', color=C_NAVY, lw=1.45, markersize=4.4, label='Scoped ($\\rho$=0%)', zorder=5)
    ax2.plot(sx, r50_y, '^-', color=C_TEAL, lw=1.25, markersize=4.2, label='Scoped ($\\rho$=50%)', zorder=4)
    ax2.plot(sx, r100_y, 'D:', color=C_AMBER, lw=1.25, markersize=3.9, label='Scoped ($\\rho$=100%)', zorder=4)

    for i, yv in enumerate(un_y):
        lbl = f'{yv:.0f}' if yv < 1000 else f'{yv/1000:.2f}k'
        ax2.text(sx[i], yv * 1.25, lbl, ha='center', va='bottom', fontsize=6.0, fontweight='bold', color=C_VERM)
    ax2.text(sx[-1] - 0.16, r0_y[-1] * 1.32, f'{r0_y[-1]:.1f}$\\mu$s', ha='right', va='bottom',
             fontsize=6.0, fontweight='bold', color=C_NAVY)

    ax2.annotate('', xy=(3.10, r0_y[-1]), xytext=(3.10, un_y[-1]),
                 arrowprops=dict(arrowstyle='<->', color=C_SLATE, lw=0.9))
    ax2.text(2.04, 30.0, '203$\\times$ faster\n$O(1)$ vs. $|T|$ (Thm. 4.2)',
             ha='center', va='center', fontsize=5.85, fontweight='bold', color=C_NAVY,
             bbox=dict(boxstyle='round,pad=0.18', facecolor='#EDF4FB', edgecolor=C_NAVY, lw=0.55), zorder=6)

    ax2.set_yscale('log')
    ax2.set_ylim(0.45, 3600)
    ax2.set_xticks(sx)
    ax2.set_xticklabels(['36', '105', '500', '1,599'], fontsize=7.0)
    ax2.set_xlim(-0.32, 3.34)
    ax2.set_xlabel('Warehouse Tables $|T|$')
    ax2.set_ylabel('Plan Latency ($\\mu$s, log)')
    ax2.set_title('(b) Estate-Scale Invariance', fontweight='bold', pad=26)
    ax2.grid(axis='y', which='major', linestyle=':', alpha=0.4)
    ax2.set_axisbelow(True)
    ax2.legend(loc='lower center', bbox_to_anchor=(0.50, 1.00), ncol=2, frameon=False,
               handlelength=1.15, columnspacing=0.55, fontsize=5.9, labelspacing=0.18)

    # Panel (c): End-to-End Log-Scale Share
    stages = ['ADS Hit\n(Loctek)', 'Hybrid\n(TPC-DS)', 'Hybrid\n(Loctek)',
              'Cached\nMCP', 'LLM\nIntent', 'Full Query\n(Iter. 3)']
    ms_vals = [pl_l['ADS_Direct_Reuse']['p50_us'] / 1000.0,
               pl_t['Hybrid_Derivative_Ratio']['p50_us'] / 1000.0,
               pl_l['Hybrid_Derivative_Ratio']['p50_us'] / 1000.0,
               403.4, 2094.3, 25820.0]
    cols3 = [C_NAVY, C_TEAL, C_NAVY, '#2A9D8F', C_AMBER, C_GRAY]
    hatches3 = ['', '///', '///', '', '\\\\\\', '']
    y3 = np.arange(len(stages))
    bars3 = ax3.barh(y3, ms_vals, height=0.58, color=cols3, edgecolor='#0F172A', lw=0.45, zorder=3)
    for bar, hp, v in zip(bars3, hatches3, ms_vals):
        if hp:
            bar.set_hatch(hp)
        lbl = f'{v*1000:.1f}$\\mu$s' if v < 1.0 else (f'{v:.0f}ms' if v < 1000 else f'{v/1000:.1f}s')
        ax3.text(v * 1.48, bar.get_y() + bar.get_height() / 2, lbl,
                 va='center', ha='left', fontsize=6.3, fontweight='bold', color='#0F172A')

    ax3.text(2.4e2, 0.95, '<0.001%\nshare', ha='center', va='center', fontsize=6.1, fontweight='bold',
             color=C_NAVY, bbox=dict(boxstyle='round,pad=0.16', facecolor='#EDF4FB', edgecolor=C_NAVY, lw=0.55))
    ax3.set_xscale('log')
    ax3.set_xlim(1e-3, 1.1e6)
    ax3.set_xticks([1e-3, 1e0, 1e3])
    ax3.set_yticks(y3)
    ax3.set_yticklabels(stages, fontsize=6.6)
    ax3.invert_yaxis()
    ax3.set_xlabel('P50 Latency (ms, log)')
    ax3.set_title('(c) End-to-End Share', fontweight='bold', pad=26)
    ax3.grid(axis='x', which='major', linestyle=':', alpha=0.4)
    ax3.set_axisbelow(True)

    plt.tight_layout(w_pad=0.85)
    save_both(fig, 'fig_ablation_latency')


# ============================================================================
# FIGURE 4: Shared-Y-Axis Aligned Horizontal 3-Panel Matrix (fig_caliber_traps.pdf)
#           Eliminates 100% of x-tick label collisions & cramped in-bar labels!
# ============================================================================
def make_fig4_v3():
    _set_chart_rc()
    MODELS = [
        'Claude-Opus-5.5',
        'GPT-6.2-Sol',
        'Gemini-4-Argon',
        'Kimi-K3.1-Pro',
        'DeepSeek-V4-Pro',
        'Qwen3.8-27B',
    ]
    ROW_LABELS = MODELS + ['HermesGov (Ours)']
    TENANT_VIOLS = [0, 0, 0, 1, 1, 13]
    lookup = {(r['benchmark'], r['label']): r for r in B6}

    fig, (ax1, ax2, ax3) = plt.subplots(
        1, 3, figsize=(7.15, 2.62), sharey=True,
        gridspec_kw={'width_ratios': [1.02, 1.02, 1.12]}
    )

    n_rows = len(ROW_LABELS)
    y_all = np.arange(n_rows)
    y_m = np.arange(len(MODELS))
    bh = 0.35

    # Spotlight band across all 3 panels for HermesGov (row 6)
    for ax in (ax1, ax2, ax3):
        ax.axhspan(5.52, 6.48, facecolor='#EDF4FB', edgecolor='none', zorder=0)
        ax.axhline(5.52, color='#94A3B8', linestyle=':', lw=0.8, zorder=1)

    for ax, bench, title, hg_us in [
        (ax1, 'loctek', '(a) Loctek Enterprise (12 Traps)', '16.7 $\\mu$s'),
        (ax2, 'tpcds',  '(b) Public TPC-DS (12 Traps)',     '15.5 $\\mu$s'),
    ]:
        dir_pct = [lookup[(bench, m)]['direct_pct'] for m in MODELS]
        glo_pct = [lookup[(bench, m)]['glossary_pct'] for m in MODELS]

        b_dir = ax.barh(y_m - bh / 2, dir_pct, height=bh, color=C_VERM, edgecolor='#0F172A',
                        lw=0.48, hatch='xxx', zorder=3)
        b_glo = ax.barh(y_m + bh / 2, glo_pct, height=bh, color=C_AMBER, edgecolor='#0F172A',
                        lw=0.48, hatch='///', zorder=3)
        b_hg = ax.barh([6.0], [100.0], height=0.52, color=C_NAVY, edgecolor='#0F172A', lw=0.55, zorder=3)
        ax.axvline(100.0, color=C_NAVY, linestyle='--', lw=0.95, alpha=0.65, zorder=1)

        for bar, v in zip(b_dir, dir_pct):
            ax.text(v + 1.6, bar.get_y() + bar.get_height() / 2, f'{v:.0f}%',
                    va='center', ha='left', fontsize=5.85, fontweight='bold', color=C_VERM,
                    bbox=dict(boxstyle='square,pad=0.03', facecolor='white', edgecolor='none', alpha=0.90),
                    zorder=5)
        for bar, v in zip(b_glo, glo_pct):
            ax.text(v + 1.6, bar.get_y() + bar.get_height() / 2, f'{v:.0f}%',
                    va='center', ha='left', fontsize=5.85, fontweight='bold', color='#92400E',
                    bbox=dict(boxstyle='square,pad=0.03', facecolor='white', edgecolor='none', alpha=0.92),
                    zorder=5)
        ax.text(101.8, 6.0, f'100% ({hg_us})', va='center', ha='left',
                fontsize=5.85, fontweight='bold', color=C_NAVY, zorder=5)

        ax.set_xlim(0, 140)
        ax.set_xticks([0, 25, 50, 75, 100])
        ax.set_xlabel('Trap Safety Rate (%)')
        ax.set_title(title, fontweight='bold', pad=7)
        ax.grid(axis='x', linestyle=':', alpha=0.4)
        ax.set_axisbelow(True)

    # Panel (c): Glossary Latency, Prompt Token Bloat & Hardcoded Tenant Leaks
    mean_glo_s = []
    tok_bloat_pct = []
    for m in MODELS:
        r_l, r_t = lookup[('loctek', m)], lookup[('tpcds', m)]
        lat_s = 0.5 * (r_l['glossary_mean_ms'] + r_t['glossary_mean_ms']) / 1000.0
        mean_glo_s.append(lat_s)
        d_tok = sum(c['direct']['prompt_tokens'] for c in r_l['cases'] + r_t['cases'])
        g_tok = sum(c['glossary']['prompt_tokens'] for c in r_l['cases'] + r_t['cases'])
        tok_bloat_pct.append(100.0 * (g_tok - d_tok) / max(d_tok, 1))

    bar_cols = [C_AMBER if tv == 0 else C_VERM for tv in TENANT_VIOLS]
    bars_c = ax3.barh(y_m, mean_glo_s, height=0.54, color=bar_cols, edgecolor='#0F172A', lw=0.48, zorder=3)
    for idx, bar in enumerate(bars_c):
        tv = TENANT_VIOLS[idx]
        bar.set_hatch('///' if tv == 0 else 'xxx')
        lat = mean_glo_s[idx]
        tb = tok_bloat_pct[idx]
        if tv == 0:
            tag = f'{lat:.1f}s (+{tb:.0f}% tok)'
            tcol = '#0F172A'
        else:
            leak_w = 'leak' if tv == 1 else 'leaks'
            tag = f'{lat:.1f}s (+{tb:.0f}%, {tv} {leak_w}!)'
            tcol = C_VERM
        ax3.text(lat + 0.5, bar.get_y() + bar.get_height() / 2, tag,
                 va='center', ha='left', fontsize=5.85, fontweight='bold', color=tcol, zorder=5)

    ax3.barh([6.0], [0.12], height=0.52, color=C_NAVY, edgecolor='#0F172A', lw=0.55, zorder=3)
    ax3.text(0.65, 6.0, '16.1 $\\mu$s (0% +tok, 0 leaks)',
             va='center', ha='left', fontsize=6.0, fontweight='bold', color=C_NAVY, zorder=5)

    ax3.set_xlim(0, 34.5)
    ax3.set_xticks([0, 10, 20, 30])
    ax3.set_xlabel('Mean Glossary Latency (s)')
    ax3.set_title('(c) Glossary Latency, +Tok & Leaks', fontweight='bold', pad=7)
    ax3.grid(axis='x', linestyle=':', alpha=0.4)
    ax3.set_axisbelow(True)

    ax1.set_yticks(y_all)
    ax1.set_yticklabels(ROW_LABELS, fontsize=7.2)
    # Bold the HermesGov spotlight row label on the shared left axis
    ytick_objs = ax1.get_yticklabels()
    if ytick_objs:
        ytick_objs[-1].set_fontweight('bold')
        ytick_objs[-1].set_color(C_NAVY)
    ax1.set_ylim(6.55, -0.58)  # inverted top-to-bottom order
    ax2.tick_params(axis='y', left=False)
    ax3.tick_params(axis='y', left=False)

    # Clean 4-item legend across top of figure
    legend_handles = [
        FancyBboxPatch((0, 0), 1, 1, facecolor=C_NAVY, edgecolor='#0F172A', lw=0.5,
                       label='HermesGov Gates (100%, <20 $\\mu$s)'),
        FancyBboxPatch((0, 0), 1, 1, facecolor=C_VERM, edgecolor='#0F172A', lw=0.5, hatch='xxx',
                       label='Direct-SQL / Glossary Leak'),
        FancyBboxPatch((0, 0), 1, 1, facecolor=C_AMBER, edgecolor='#0F172A', lw=0.5, hatch='///',
                       label='Prompt-Glossary (+8 Rules, 0 Leak)'),
        Line2D([0], [0], color=C_NAVY, linestyle='--', lw=1.1, label='100% Safety Target'),
    ]
    fig.legend(handles=legend_handles, loc='upper center', bbox_to_anchor=(0.52, 1.055),
               ncol=4, frameon=False, handlelength=1.25, columnspacing=0.95, fontsize=6.9)

    plt.tight_layout(w_pad=0.65)
    save_both(fig, 'fig_caliber_traps')


if __name__ == '__main__':
    make_fig1_v3()
    make_fig2_v3()
    make_fig3_v3()
    make_fig4_v3()
    print('All 4 SIGMOD v3.0 figures generated cleanly.')
