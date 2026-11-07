// Pure helpers for the tournament: one round, one group, every team plays
// every other. Nothing here touches the DOM, so Node can test it (tests/site_js).
//
// The exporter publishes nothing about how anyone is doing until a round is
// complete: before that the data holds only the draw and the phase. These
// helpers therefore treat every result field as possibly missing, and say
// "results are shown when the round is complete" instead of showing zeros.

import { submissionsText } from './event-core.js';
import { ago } from './format.js';

export const NOT_YET = 'Results are shown when the round is complete.';

const PHASES = {
  registration: {
    label: 'Submissions',
    text: 'Submissions are open: teams are handing in their bots.',
  },
  groups: {
    label: 'Round 1',
    text: 'Round 1 (groups) is in progress. Results are shown when the round ends.',
  },
  done: {
    label: 'Finished',
    text: 'The tournament is finished.',
  },
};

export const PHASE_ORDER = Object.keys(PHASES);

/** {phase, label, text, known} for a phase name; unknown names stay readable. */
export function phaseInfo(phase, submissions = null) {
  const info = PHASES[phase];
  // Before the draw the banner says whether teams may submit right now.
  if (phase === 'registration' && submissions) return { phase, ...submissionsText(submissions), known: true };
  if (info) return { phase, ...info, known: true };
  return { phase: phase || '', label: 'Tournament', text: 'The tournament is under way.', known: false };
}

/** A tournament.json payload with every field present, whatever was missing. */
export function normalizeTournament(raw) {
  const t = raw && typeof raw === 'object' ? raw : {};
  const board = (b) => (b && Array.isArray(b.teams) ? b : null);
  return {
    phase: t.phase || '',
    groups: Array.isArray(t.groups)
      ? t.groups.map((g) => ({
          name: String(g.name),
          teams: Array.isArray(g.teams) ? g.teams : [],
          board: board(g.board),
        }))
      : [],
    champion: t.champion || null,
  };
}

/**
 * The status of a teams.json entry: 'submitted' (a bot with that name has
 * arrived, so the name is confirmed) or 'registered' (only the name is listed).
 * An export that predates the field has only teams with bots: 'submitted'.
 */
export function entryStatus(entry) {
  return entry && entry.status === 'registered' ? 'registered' : 'submitted';
}

/** teams.json's list with `status` always present, sorted by name like the export. */
export function normalizeTeams(list) {
  if (!Array.isArray(list)) return [];
  return list.map((entry) => ({ ...entry, status: entryStatus(entry) }));
}

/** How many of the listed teams have a bot ('submitted') and how many only a name. */
export function statusCounts(teams) {
  const list = teams || [];
  const submitted = list.filter((e) => entryStatus(e) === 'submitted').length;
  return { submitted, registered: list.length - submitted };
}

/** The data files to fetch: only those the manifest says exist. */
export function tournamentFiles(manifest) {
  const kinds = (manifest && manifest.kinds) || [];
  const files = { tournament: 'data/tournament.json', teams: 'data/teams.json', pairings: {} };
  // Group boards travel inside tournament.json; only the pairings have their own file.
  if (kinds.includes('group')) files.pairings.group = 'data/pairings-group.json';
  return files;
}

/** Whether the round has been published (any group has a ranked table). */
export function groupsRevealed(t) {
  return t.groups.some((g) => g.board);
}

/** The boards a visitor can look at, in order: each revealed group. */
export function revealedBoards(t) {
  return t.groups.filter((g) => g.board).map((g) => ({ id: g.name, label: `Group ${g.name}`, board: g.board }));
}

/** What to say under the round heading, or null once results are shown. */
export function roundOneNote(t) {
  if (groupsRevealed(t)) return null;
  switch (t.phase) {
    case 'registration':
      return 'The draw is made when submissions close. Everyone plays everyone in one round.';
    case 'groups':
      return `Round 1 is in progress. ${NOT_YET}`;
    default:
      return NOT_YET;
  }
}

/** Marks for a group table: team name -> text. Only the champion is marked. */
export function groupMarks(group, t) {
  return t.champion && group.teams.includes(t.champion) ? new Map([[t.champion, 'Champion']]) : new Map();
}

/** Where one team stands. Everything result-like is null until revealed. */
export function teamStanding(name, t) {
  const group = t.groups.find((g) => g.teams.includes(name)) || null;
  const groupRow = group && group.board ? group.board.teams.find((r) => r.team === name) || null : null;
  return {
    group: group ? group.name : null,
    groupSize: group ? group.teams.length : 0,
    groupRow,
    champion: t.champion === name,
  };
}

/** The "last updated" label for the header, and when the link is stale. */
export function updatedText(ageSeconds, { stale = false } = {}) {
  const changed = ago(ageSeconds);
  // There is no live result in this format, so never claim a "last result".
  return stale ? `Connection lost – showing data from ${changed}` : `Updated ${changed}`;
}
