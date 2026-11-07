import { ciPlot, axisHeader, describeScore, scoreAxisMax } from '../charts.js';
import { h } from '../dom.js';
import { fmtBB, fmtPlain } from '../format.js';

const DEFAULT_CAPTION = 'Ranking by mean big blinds won per 100 hands, with 95% interval';

/**
 * The ranking: score, interval plot, record and faults. `marks` (team name ->
 * text) adds a badge after a team's name, for example "Champion"; `caption` is
 * the table's screen-reader description.
 */
export function leaderboardTable(board, { marks = null, caption = DEFAULT_CAPTION } = {}) {
  const teams = board.teams;
  const max = scoreAxisMax(board.teams);
  const body = teams.map((team) => {
    const ranked = team.score != null;
    const nextRank = team.rank + 1;
    return h(
      'tr',
      {},
      h('td', { class: 'rank num' }, ranked ? team.rank : '–'),
      h(
        'td',
        { class: 'team' },
        h('a', { href: `#/team/${encodeURIComponent(team.team)}` }, team.team),
        team.tied_with_next
          ? h(
              'span',
              {
                class: 'tie',
                title: `Cannot be separated from #${nextRank} (their intervals overlap)`,
              },
              `≈ #${nextRank}`,
            )
          : null,
        marks && marks.has(team.team) ? markBadge(marks.get(team.team)) : null,
      ),
      h('td', { class: 'num' }, fmtBB(team.score)),
      h('td', { class: 'num muted' }, team.ci95 == null ? '—' : `± ${fmtPlain(team.ci95)}`),
      h(
        'td',
        { class: 'plotcell' },
        ciPlot({
          score: team.score,
          ci: team.ci95,
          max,
          label: describeScore(team),
        }),
      ),
      h('td', { class: 'num nowrap' }, `${team.wins}–${team.draws}–${team.losses}`),
      h('td', { class: 'num' }, faultCell(team)),
    );
  });
  return h(
    'div',
    { class: 'tablewrap' },
    h(
      'table',
      { class: 'tbl' },
      h('caption', { class: 'sr-only' }, caption),
      h(
        'thead',
        {},
        h(
          'tr',
          {},
          h('th', { class: 'num', scope: 'col' }, '#'),
          h('th', { scope: 'col' }, 'Team'),
          h('th', { class: 'num', scope: 'col' }, 'bb/100'),
          h('th', { class: 'num', scope: 'col' }, '95% ±'),
          h('th', { scope: 'col', class: 'plotcell' }, axisHeader({ max })),
          h('th', { class: 'num', scope: 'col', title: 'Wins–draws–losses, counting only statistically clear results' }, 'W–D–L'),
          h('th', { class: 'num', scope: 'col' }, 'Faults'),
        ),
      ),
      h('tbody', {}, body),
    ),
  );
}

/** Text, not colour alone: "★ Champion". */
function markBadge(text) {
  return h('span', { class: 'badge final mark' }, h('span', { 'aria-hidden': 'true' }, '★'), text);
}

function faultCell(team) {
  const parts = [String(team.faults)];
  if (team.disabled_in && team.disabled_in.length) {
    parts.push(
      h(
        'span',
        {
          class: 'badge bad',
          title: `Replaced by an always-fold stub in: ${team.disabled_in.join(', ')}`,
        },
        `⚠ disabled in ${team.disabled_in.length}`,
      ),
    );
  }
  return h('span', {}, ...parts.flatMap((p, i) => (i ? [' ', p] : [p])));
}
