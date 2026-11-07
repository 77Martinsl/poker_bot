import { cellColors, matrixMax } from '../charts.js';
import { h } from '../dom.js';
import { MINUS, buildHash, fmtBB, fmtPlain } from '../format.js';
import { NOT_YET, revealedBoards } from '../tournament-core.js';

/** Reads the colour tokens as hex so cell text contrast can be computed. */
function readTokens() {
  const style = getComputedStyle(document.documentElement);
  const token = (name) => style.getPropertyValue(name).trim();
  return { pos: token('--pos'), neg: token('--neg'), mid: token('--mid') };
}

function legend(max, tokens) {
  const left = cellColors(-max, 0, max, tokens).bg;
  const right = cellColors(max, 0, max, tokens).bg;
  return h(
    'div',
    { class: 'legend' },
    h('span', {}, `Row team loses ${MINUS}${fmtPlain(max, max < 1 ? 2 : 1)}`),
    h('span', {
      class: 'ramp',
      'aria-hidden': 'true',
      style: `background:linear-gradient(90deg,${left},${tokens.mid},${right})`,
    }),
    h('span', {}, `wins +${fmtPlain(max, max < 1 ? 2 : 1)} bb/100`),
    h('span', {}, 'Faded cell: result not statistically clear'),
  );
}

/**
 * Builds the head-to-head grid: row team's mean bb/100 against each column
 * team, teams ordered by rank. `numbers` shows the values inside the cells
 * (it is also the table view for readers who cannot use colour).
 */
export function matrixGrid(board, { numbers, cellPx = null }) {
  const tokens = readTokens();
  const order = board.teams.map((t) => t.team);
  const values = [];
  for (const me of order) {
    for (const other of order) {
      const cell = board.matrix[me] && board.matrix[me][other];
      if (cell && cell.mean_bb != null) values.push(cell.mean_bb);
    }
  }
  const max = matrixMax(values);

  const rows = order.map((me) =>
    h(
      'tr',
      {},
      h('th', { scope: 'row' }, h('a', { href: `#/team/${encodeURIComponent(me)}`, style: 'color:inherit;text-decoration:none' }, me)),
      order.map((other) => {
        if (other === me) return h('td', { class: 'self', 'aria-label': 'same team' });
        const cell = board.matrix[me] && board.matrix[me][other];
        if (!cell || cell.mean_bb == null) {
          return h('td', { class: 'none', title: `${me} vs ${other}: not played yet` }, '·');
        }
        const colors = cellColors(cell.mean_bb, cell.ci95_bb, max, tokens);
        const half = cell.ci95_bb == null ? 'interval unknown' : `± ${fmtPlain(cell.ci95_bb)}`;
        const text = `${me} vs ${other}: ${fmtBB(cell.mean_bb)} bb/100 ${half}` +
          (colors.clear ? '' : ' (not statistically clear)');
        return h(
          'td',
          {
            style: `background:${colors.bg};color:${colors.fg}`,
            title: text,
          },
          h(
            'a',
            {
              href: `#/matches?team=${encodeURIComponent(me)}&other=${encodeURIComponent(other)}`,
              'aria-label': text,
            },
            numbers ? fmtBB(cell.mean_bb, 0) : '',
          ),
        );
      }),
    ),
  );
  return {
    grid: h(
      'div',
      { class: 'tablewrap' },
      h(
        'table',
        {
          class: 'matrix',
          style: cellPx ? `--cell:${cellPx}px;--label:${Math.round(cellPx * 4.2)}px` : null,
        },
        h(
          'thead',
          {},
          h(
            'tr',
            {},
            h('td', {}),
            order.map((name) => h('th', { scope: 'col', title: name }, h('span', {}, name))),
          ),
        ),
        h('tbody', {}, rows),
      ),
    ),
    legend: legend(max, tokens),
    teams: order.length,
  };
}

/**
 * The controls, the grid and the explanation for one board. Returns the
 * elements to put on the page.
 */
function matrixBody(board) {
  const holder = h('div', { class: 'card' });
  const toggle = h('input', {
    type: 'checkbox',
    id: 'show-numbers',
    onchange: () => draw(),
  });
  toggle.checked = board.teams.length <= 12;
  function draw() {
    const { grid, legend: key } = matrixGrid(board, { numbers: toggle.checked });
    holder.replaceChildren(grid, key);
  }
  draw();
  return [
    h(
      'div',
      { class: 'controls' },
      h('label', { for: 'show-numbers' }, toggle, 'Show numbers (bb/100)'),
      h('span', { class: 'muted small' }, 'Click a cell to see those matches.'),
    ),
    holder,
    h(
      'p',
      { class: 'note' },
      'Each cell is the row team’s average big blinds won per 100 hands against the column team. ' +
        'Blue means the row team is ahead, grey that it is behind (the sign and the number say the same); a faded cell means the ' +
        'difference could just be luck.',
    ),
  ];
}

/** Pick which group to look at (there is one). */
export function matrixView(ctx) {
  const boards = revealedBoards(ctx.data.tournament);
  const page = h('div', { class: 'page' }, h('header', {}, h('h1', {}, 'Head-to-head')));
  if (!boards.length) {
    page.appendChild(h('div', { class: 'empty card' }, NOT_YET));
    return { el: page, title: 'Head-to-head' };
  }
  const chosen = boards.find((b) => b.id === ctx.query.board) || boards[0];
  const select = h(
    'select',
    {
      id: 'f-board',
      onchange: (e) => (location.hash = buildHash(['matrix'], { board: e.target.value })),
    },
    boards.map((b) => h('option', { value: b.id, selected: b.id === chosen.id }, b.label)),
  );
  page.appendChild(
    h('div', { class: 'controls' }, h('label', { for: 'f-board' }, 'Show ', select)),
  );
  if (chosen.board.teams.length < 2) {
    page.appendChild(h('div', { class: 'empty card' }, `${chosen.label} has fewer than two teams, so there is nothing to compare.`));
    return { el: page, title: 'Head-to-head' };
  }
  page.append(...matrixBody(chosen.board));
  return { el: page, title: 'Head-to-head' };
}
