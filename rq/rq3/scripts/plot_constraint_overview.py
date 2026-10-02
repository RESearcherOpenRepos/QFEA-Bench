#!/usr/bin/env python3
"""Plot three test-composition pies and three agent pass-rate bar charts."""
from __future__ import annotations

import argparse
from pathlib import Path
import os
os.environ.setdefault('MPLCONFIGDIR', '/tmp/qfea-rq3-matplotlib')
os.environ.setdefault('XDG_CACHE_HOME', '/tmp/qfea-rq3-cache')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Arc, Patch
from matplotlib.lines import Line2D
import constraint_figure_data as source

OUT = source.ROOT / 'rq/rq3/results/figures/rq3_constraint_overview'
# Related hues encode category membership; modest shade changes identify subtypes.
# Shades are categorical identifiers, not an encoding of magnitude or rank.
# Guidance: https://colorbrewer2.org/learnmore/schemes_full.html
COLORS = ['#639F7A', '#78AE8D', '#8DBDA0', '#A0A3A6', '#D89148', '#E0A15D', '#E8B171']
CATEGORY_COLORS = {'Classical': '#39724E', 'Interface': '#676C72', 'Quantum': '#A46023'}
BAR_LABELS = ['MO', 'DP', 'AS', 'CO', 'I', 'QO', 'Op', 'Cir', 'App']
AGENTS = ['minisweagent', 'openhands', 'autocoderover']


def main():
    global OUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUT, help='Output path stem, without extension.')
    OUT = parser.parse_args().output
    OUT.parent.mkdir(parents=True, exist_ok=True)
    primary = {(r['agent'], r['split'], r['category']):
               (int(r['passed']), int(r['total'])) for r in source.read_csv(source.SOURCE)}
    _, counts, _, split_tests, _ = source.pooled_subcategory_data(primary)
    sub = {(r['agent'], r['split'], r['subcategory']):
           (int(r['passed']), int(r['total'])) for r in source.read_csv(source.SUBCATEGORY_SOURCE)}
    groups = ([x[0] for x in source.SUBCATEGORIES['general_semantics']]
              + ['interface']
              + [x[0] for x in source.SUBCATEGORIES['quantum_semantics']])
    f = np.array([len(split_tests[(g, 'F2P')]) for g in groups])
    p = np.array([len(split_tests[(g, 'P2P')]) for g in groups])
    assert np.array_equal(f+p, [counts[g] for g in groups])
    assert sum(f+p) == source.selected_test_count()
    plt.rcParams.update({'font.family': 'serif', 'font.serif': ['STIXGeneral'],
                         'font.size': 8, 'pdf.fonttype': 42, 'ps.fonttype': 42})
    fig = plt.figure(figsize=(8.8, 3.85), facecolor='white')
    positions = [.060, .310, .560]
    width = .205
    for i, (split, values) in enumerate(zip(['F2P', 'P2P', 'All'], [f, p, f+p])):
        ax = fig.add_axes([positions[i]-.022, .53, width+.044, .40])
        wedges, _, texts = ax.pie(values, colors=COLORS, startangle=90, counterclock=False,
                                  wedgeprops={'edgecolor': 'white', 'linewidth': .65},
                                  autopct=lambda pct: f'{pct:.1f}%', pctdistance=.76,
                                  textprops={'fontsize': 7.0, 'color': '#171717'})
        for j, text in enumerate(texts):
            mid = np.deg2rad((wedges[j].theta1+wedges[j].theta2)/2)
            radius = .62 if j in (3,4) else .75
            text.set_position((radius*np.cos(mid),radius*np.sin(mid)))
        # Contiguous sectors retain the ordinary pie geometry. Outer arcs
        # identify the parent groups without adding a second ring of data.
        for start, stop, label, color in [(0,3,'Classical',CATEGORY_COLORS['Classical']),
                                         (3,4,'Interface',CATEGORY_COLORS['Interface']),
                                         (4,7,'Quantum',CATEGORY_COLORS['Quantum'])]:
            lower, upper = wedges[stop-1].theta1, wedges[start].theta2
            ax.add_patch(Arc((0,0),2.15,2.15,theta1=lower+1.5,theta2=upper-1.5,
                             color=color,lw=1.1))
            angle = np.deg2rad((lower+upper)/2)
            share = 100*sum(values[start:stop])/sum(values)
            align = 'left' if np.cos(angle)>.45 else 'right' if np.cos(angle)<-.45 else 'center'
            ax.text(1.24*np.cos(angle),1.42*np.sin(angle),
                    f'{label}\n{share:.1f}%',ha=align,va='center',fontsize=8,color=color,
                    linespacing=1.0)
        ax.set_title(f'({chr(97+i)}) {split} (n = {sum(values):,})', fontsize=9.3, pad=4)
        ax.set_xlim(-1.8,1.8); ax.set_ylim(-1.65,1.65)

    for i, agent in enumerate(AGENTS):
        ax = fig.add_axes([positions[i], .15, width, .28])
        bar_groups = groups[:3] + ['general_semantics', 'interface', 'quantum_semantics'] + groups[4:]
        bar_colors = COLORS[:3] + [CATEGORY_COLORS['Classical'], COLORS[3], CATEGORY_COLORS['Quantum']] + COLORS[4:]
        aggregate_indices = {3,4,5}
        rates = []
        for group in bar_groups:
            data = primary if group in ('general_semantics','quantum_semantics') else sub
            passed, total = map(sum, zip(data[(agent,'F2P',group)], data[(agent,'P2P',group)]))
            assert total == 5*counts[group], (agent, group)
            if group in ('general_semantics','quantum_semantics'):
                family = [item[0] for item in source.SUBCATEGORIES[group]]
                # Verify totals against the underlying subcategories, not their mean rates.
                assert (passed,total) == tuple(sum(sub[(agent,split,g)][k]
                    for split in ('F2P','P2P') for g in family) for k in (0,1))
            rates.append(100*passed/total)
        x = np.array([0,1,2,3.6,4.6,5.6,7.2,8.2,9.2])
        ax.bar(x, rates, width=.72, color=bar_colors, zorder=3)
        for index, (pos, rate) in enumerate(zip(x,rates)):
            ax.text(pos, rate+1, f'{rate:.1f}', ha='center', va='bottom', fontsize=6.8,
                    weight='bold' if index in aggregate_indices else 'normal')
        ax.set_title(f'({chr(100+i)}) {source.AGENT_LABELS[agent]} · All',
                     fontsize=9.0, pad=8)
        lower = 30 if agent == 'autocoderover' else 60
        # Equal spans preserve the visual scale of percentage-point differences.
        # Two points of headroom keep labels clear of the upper tick.
        assert min(rates) >= lower and max(rates) <= lower+40
        ax.set(xlim=(-.65,9.85), ylim=(lower,lower+42),
               yticks=np.arange(lower,lower+41,10))
        ax.set_xticks(x, BAR_LABELS, fontsize=7.1)
        for index in aggregate_indices:
            tick = ax.get_xticklabels()[index]
            tick.set_weight('bold')
        ax.tick_params(axis='both', length=0, pad=3)
        ax.tick_params(axis='y', labelsize=7)
        ax.set_axisbelow(True); ax.grid(axis='y', color='#e3e5e7', linewidth=.5)
        ax.spines[['top','right','left']].set_visible(False)
        ax.spines['bottom'].set_color('#afb4ba'); ax.spines['bottom'].set_linewidth(.6)
        if i == 0:
            ax.set_ylabel('Test pass rate (%)', fontsize=8, labelpad=5)

    # A single, conventional legend in the upper-right corner serves every panel.
    legend_labels = ['MO: Mathematical operations', 'DP: Data processing',
                     'AS: Algorithmic solving', 'I: Interface',
                     'Op: Operator semantics', 'Cir: Circuit semantics',
                     'App: Application semantics']
    handles = []
    heading_positions = []
    for title, color, indices in [('Classical', CATEGORY_COLORS['Classical'], range(0,3)),
                                  ('Interface', CATEGORY_COLORS['Interface'], range(3,4)),
                                  ('Quantum', CATEGORY_COLORS['Quantum'], range(4,7))]:
        heading_positions.append(len(handles))
        handles.append(Line2D([], [], linestyle='none', marker='o', markersize=4,
                              color=color, label=title))
        handles.extend(Patch(facecolor=COLORS[j], label='  '+legend_labels[j]) for j in indices)
        if title != 'Interface':
            code = 'CO' if title == 'Classical' else 'QO'
            handles.append(Patch(facecolor=color, label=f'  {code}: {title} Overall'))
    legend = fig.legend(handles=handles, loc='upper right', bbox_to_anchor=(.995,.94),
                        frameon=False, fontsize=8, handlelength=1.1,
                        handletextpad=.5, labelspacing=.6, borderaxespad=0)
    for index in heading_positions:
        legend.get_texts()[index].set_weight('bold')
    fig.savefig(OUT.with_suffix('.pdf'), dpi=240)
    plt.close(fig)
    print(OUT.with_suffix('.pdf'))

if __name__=='__main__':
    main()
