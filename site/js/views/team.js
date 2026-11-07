import { teamEntry } from '../api.js';
import { h } from '../dom.js';
import { fmtBB, fmtPlain, plural } from '../format.js';
import { NOT_YET, teamStanding } from '../tournament-core.js';

/** One opponent's result seen from `me`'s side (signs flip when me is B). */
function fromSide(p, me) {
  const isA = p.a === me;
  const sign = isA ? 1 : -1;
  const verdict = p.verdict === 'tie' ? 'draw' : (p.verdict === 'a') === isA ? 'win' : 'loss';
  return {
    other: isA ? p.b : p.a,
    mean: p.mean_bb == null ? null : sign * p.mean_bb,
    ci: p.ci95_bb,
    verdict,
    faults: isA ? p.faults_a : p.faults_b,
    stub: isA ? p.disabled_a : p.disabled_b,
    pairing: p,
  };
}

const WORD = { win: 'Won', draw: 'No clear winner', loss: 'Lost' };

/** The results table: one row per opponent, from `name`'s side. */
function resultsTable(pairings, name) {
  const results = pairings.map((p) => fromSide(p, name)).sort((x, y) => (y.mean ?? -Infinity) - (x.mean ?? -Infinity));
  return h(
    'div',
    { class: 'card tablewrap' },
    h(
      'table',
      { class: 'tbl' },
      h(
        'thead',
        {},
        h(
          'tr',
          {},
          h('th', {}, 'Opponent'),
          h('th', {}, 'Result'),
          h('th', { class: 'num' }, 'bb/100'),
          h('th', { class: 'num' }, '95% ±'),
          h('th', { class: 'num' }, 'Hands'),
          h('th', { class: 'num' }, 'Faults'),
          h('th', {}, ''),
        ),
      ),
      h(
        'tbody',
        {},
        results.map((r) =>
          h(
            'tr',
            {},
            h('td', { class: 'team' }, h('a', { href: `#/team/${encodeURIComponent(r.other)}` }, r.other)),
            h(
              'td',
              {},
              h('span', { class: r.verdict === 'win' ? 'win' : r.verdict === 'loss' ? 'lose' : 'muted' }, WORD[r.verdict]),
            ),
            h('td', { class: 'num' }, fmtBB(r.mean)),
            h('td', { class: 'num muted' }, r.ci == null ? '—' : fmtPlain(r.ci)),
            h('td', { class: 'num' }, r.pairing.hands),
            h('td', { class: 'num' }, r.faults + (r.stub ? ' ⚠' : '')),
            h('td', {}, r.pairing.replay ? h('a', { href: `#/replay/${r.pairing.id}` }, 'Watch hands') : ''),
          ),
        ),
      ),
    ),
  );
}

const stat = (value, label) =>
  h('div', { class: 'stat' }, h('div', { class: 'v' }, value), h('div', { class: 'k' }, label));

/** The team's group, and its results once the round is out. */
function tournamentTeamView(ctx, name) {
  const t = ctx.data.tournament;
  const me = teamStanding(name, t);
  const mine = (ctx.data.pairings.group || []).filter((p) => p.a === name || p.b === name);
  const page = h('div', { class: 'page' });
  page.appendChild(
    h(
      'header',
      {},
      h('h1', {}, name),
      me.group ? h('span', { class: 'badge' }, `GROUP ${me.group}`) : null,
      me.champion ? h('span', { class: 'badge final mark' }, h('span', { 'aria-hidden': 'true' }, '★'), 'Champion') : null,
    ),
  );
  if (!ctx.data.manifest.kinds.length) {
    page.appendChild(
      h(
        'p',
        {},
        me.group ? `${name} is in group ${me.group} (${plural(me.groupSize, 'team')}). ` : `${name} has not been drawn into a group yet. `,
        NOT_YET,
      ),
    );
    return { el: page, title: name };
  }

  const row = me.groupRow;
  page.appendChild(
    h(
      'div',
      { class: 'stats' },
      stat(me.group ? `Group ${me.group}` : '–', 'round 1 group'),
      stat(row && row.score != null ? `#${row.rank}` : '–', 'rank in group'),
      stat(row ? fmtBB(row.score) : '—', 'bb/100'),
      stat(row ? `${row.wins}–${row.draws}–${row.losses}` : '—', 'W–D–L'),
    ),
  );
  if (mine.length) {
    page.appendChild(h('h2', {}, 'Round 1 results against each team'));
    page.appendChild(resultsTable(mine, name));
  }
  return { el: page, title: name };
}

export function teamView(ctx) {
  const name = ctx.path[1];
  if (!teamEntry(name)) {
    const page = h('div', { class: 'page' });
    page.appendChild(h('header', {}, h('h1', {}, 'Team not found')));
    page.appendChild(
      h('p', {}, `There is no team called “${name}”. `, h('a', { href: '#/' }, 'Back to the home page')),
    );
    return { el: page, title: 'Team not found' };
  }
  return tournamentTeamView(ctx, name);
}
