// The Tournament page: the phase, the champion, and the round as one group
// card. Until the round is complete the data holds only the draw, so those
// parts say so in words.

import { h } from '../dom.js';
import { plural } from '../format.js';
import { groupMarks, groupsRevealed, phaseInfo, roundOneNote, statusCounts } from '../tournament-core.js';
import { leaderboardTable } from './leaderboard.js';
import { STATUS_LEGEND, rosterList } from './roster.js';

function teamLink(name) {
  return h('a', { href: `#/team/${encodeURIComponent(name)}` }, name);
}

/** A row of team names as links. */
export function teamChips(names, label) {
  return h('ul', { class: 'chips', 'aria-label': label }, names.map((name) => h('li', {}, teamLink(name))));
}

/** The phase in plain words. */
export function phaseBanner(t) {
  const info = phaseInfo(t.phase, t.submissions);
  return h(
    'section',
    { class: 'phase card', 'aria-label': 'Tournament status' },
    h('span', { class: 'badge' }, info.label),
    h('p', {}, info.text),
  );
}

/** The champion, as a banner with the word "Champion" (not colour alone). */
export function championBanner(t) {
  if (!t.champion) return null;
  return h(
    'section',
    { class: 'champion card', 'aria-label': 'Champion' },
    h('div', { class: 'k' }, h('span', { 'aria-hidden': 'true' }, '★ '), 'Champion'),
    h('div', { class: 'name' }, teamLink(t.champion)),
  );
}

/** One group: its team list before the reveal, its ranked table after. */
export function groupCard(group, t) {
  const count = plural(group.teams.length, 'team');
  const card = h('section', { class: 'group card', 'aria-label': `Group ${group.name}` });
  card.appendChild(h('h3', {}, `Group ${group.name}`, h('span', { class: 'muted small' }, count)));
  if (group.board) {
    card.appendChild(
      leaderboardTable(group.board, {
        marks: groupMarks(group, t),
        caption: `Group ${group.name} ranking by mean big blinds won per 100 hands, with 95% interval`,
      }),
    );
  } else {
    card.appendChild(teamChips(group.teams, `Teams in group ${group.name}`));
  }
  return card;
}

/** The round: the note, then the group. */
export function roundOneSection(t) {
  const section = h('section', { class: 'round', 'aria-labelledby': 'round-1' });
  section.appendChild(h('h2', { id: 'round-1' }, 'The round'));
  const note = roundOneNote(t);
  if (note) section.appendChild(h('p', { class: 'note' }, note));
  if (!t.groups.length) return section;
  section.appendChild(
    h('div', { class: groupsRevealed(t) ? 'groups ranked' : 'groups' }, t.groups.map((g) => groupCard(g, t))),
  );
  if (groupsRevealed(t)) {
    section.appendChild(
      h('p', { class: 'note' }, 'One round: every team plays every other, and the team with the best score is the champion.'),
    );
  }
  return section;
}

/**
 * Before the draw: every listed name with its status. A name is confirmed
 * when a bot with that name arrives.
 */
function registeredCard(teams) {
  if (!teams.length) return null;
  const { submitted, registered } = statusCounts(teams);
  return h(
    'section',
    { class: 'card', 'aria-label': 'Registered teams' },
    h('h3', {}, 'Registered teams', h('span', { class: 'muted small' }, String(teams.length))),
    h('p', { class: 'note' }, 'Registered teams are confirmed when their bot arrives.'),
    rosterList(teams, 'Registered teams'),
    h('p', { class: 'note' }, `${submitted} submitted, ${registered} registered. ${STATUS_LEGEND}`),
  );
}

const SCORE_NOTE =
  'Score is the mean number of big blinds won per 100 hands against every opponent in the round, ' +
  'each opponent counting equally. Every deal is played twice with the seats swapped, which ' +
  'removes most card luck. The bar shows the 95% interval: if it crosses zero or touches ' +
  'the next team’s, the order is not certain.';

export function tournamentView(ctx) {
  const t = ctx.data.tournament;
  const page = h(
    'div',
    { class: 'page' },
    h('header', {}, h('h1', {}, 'Tournament')),
    phaseBanner(t),
    championBanner(t),
    t.phase === 'registration' && !t.groups.length ? registeredCard(ctx.data.teams) : null,
    roundOneSection(t),
    groupsRevealed(t) ? h('p', { class: 'note' }, SCORE_NOTE) : null,
  );
  return { el: page, title: 'Tournament' };
}
