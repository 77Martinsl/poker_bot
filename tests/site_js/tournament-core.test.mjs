import test from 'node:test';
import assert from 'node:assert/strict';
import {
  NOT_YET,
  PHASE_ORDER,
  entryStatus,
  normalizeTeams,
  statusCounts,
  groupMarks,
  groupsRevealed,
  normalizeTournament,
  phaseInfo,
  revealedBoards,
  roundOneNote,
  teamStanding,
  tournamentFiles,
  updatedText,
} from '../../site/js/tournament-core.js';

const row = (team, rank, score = 0.1) => ({ team, rank, score, ci95: 0.2, wins: 1, draws: 0, losses: 0 });
const board = (...names) => ({ kind: 'group', teams: names.map((n, i) => row(n, i + 1, 1 - i / 10)), matrix: {} });

/** The shape the exporter writes for each phase (one group, every team in it). */
function sample(phase) {
  const teams = ['a1', 'a2', 'a3'];
  const base = { phase, groups: [], champion: null };
  switch (phase) {
    case 'registration':
      return base;
    case 'groups':
      return { ...base, groups: [{ name: 'A', teams, board: null }] };
    default:
      return { ...base, groups: [{ name: 'A', teams, board: board('a3', 'a2', 'a1') }], champion: 'a3' };
  }
}

test('every phase has a plain-words banner', () => {
  assert.deepEqual(PHASE_ORDER, ['registration', 'groups', 'done']);
  const texts = PHASE_ORDER.map((p) => phaseInfo(p));
  for (const info of texts) {
    assert.ok(info.known);
    assert.ok(info.label && info.text.endsWith('.'), info.phase);
  }
  assert.match(phaseInfo('registration').text, /handing in their bots/);
  assert.match(phaseInfo('groups').text, /Round 1.*in progress.*when the round ends/);
  assert.match(phaseInfo('done').text, /finished/);
  assert.equal(new Set(texts.map((i) => i.text)).size, 3);
});

test('an unknown or missing phase still reads sensibly', () => {
  for (const phase of ['', undefined, null, 'warmup']) {
    const info = phaseInfo(phase);
    assert.equal(info.known, false);
    assert.ok(info.text.length > 0);
  }
});

test('normalizing tolerates missing and null parts', () => {
  for (const raw of [null, undefined, {}, { groups: null }, 'x']) {
    const t = normalizeTournament(raw);
    assert.deepEqual(t.groups, []);
    assert.equal(t.champion, null);
    assert.equal(t.phase, '');
  }
  const t = normalizeTournament({
    groups: [{ name: 'A', teams: null, board: { teams: 'nope' } }, { name: 'B', teams: ['x'], board: null }],
    champion: 'x',
  });
  assert.deepEqual(t.groups[0], { name: 'A', teams: [], board: null });
  assert.equal(t.champion, 'x');
});

test('only files the manifest lists are requested', () => {
  const none = tournamentFiles({ mode: 'tournament', kinds: [] });
  assert.equal(none.tournament, 'data/tournament.json');
  assert.equal(none.teams, 'data/teams.json');
  assert.deepEqual(none.pairings, {});

  // The group table travels inside tournament.json: there is no leaderboard file.
  assert.deepEqual(tournamentFiles({ kinds: ['group'] }).pairings, { group: 'data/pairings-group.json' });

  // A manifest with no kinds field, or an unknown kind, requests nothing extra.
  assert.deepEqual(tournamentFiles({}).pairings, {});
  assert.deepEqual(tournamentFiles({ kinds: ['ladder', 'final'] }).pairings, {});
});

test('before the draw there is nothing to show', () => {
  const t = normalizeTournament(sample('registration'));
  assert.equal(groupsRevealed(t), false);
  assert.deepEqual(revealedBoards(t), []);
  assert.match(roundOneNote(t), /draw is made when submissions close.*Everyone plays everyone in one round/);
});

test('while the round is played the draw shows but no results', () => {
  const t = normalizeTournament(sample('groups'));
  assert.equal(groupsRevealed(t), false);
  assert.deepEqual(revealedBoards(t), []);
  assert.ok(roundOneNote(t).includes(NOT_YET));
  assert.match(roundOneNote(t), /in progress/);
  assert.equal(groupMarks(t.groups[0], t).size, 0);
  assert.equal(roundOneNote(normalizeTournament({ phase: 'weird' })), NOT_YET);
});

test('when done the table and the champion are there', () => {
  const t = normalizeTournament(sample('done'));
  assert.equal(groupsRevealed(t), true);
  assert.equal(roundOneNote(t), null);
  assert.deepEqual(revealedBoards(t).map((b) => [b.id, b.label]), [['A', 'Group A']]);
  assert.deepEqual([...groupMarks(t.groups[0], t)], [['a3', 'Champion']]);
});

test('the champion is marked only in the group they play in', () => {
  const t = normalizeTournament({ ...sample('done'), champion: 'elsewhere' });
  assert.equal(groupMarks(t.groups[0], t).size, 0);
});

test('a team page knows the group before and the results after', () => {
  const before = teamStanding('a2', normalizeTournament(sample('groups')));
  assert.equal(before.group, 'A');
  assert.equal(before.groupSize, 3);
  assert.equal(before.groupRow, null);
  assert.equal(before.champion, false);

  const done = normalizeTournament(sample('done'));
  assert.equal(teamStanding('a2', done).groupRow.rank, 2);
  assert.equal(teamStanding('a3', done).champion, true);
  assert.equal(teamStanding('a1', done).champion, false);

  const stranger = teamStanding('nobody', done);
  assert.equal(stranger.group, null);
  assert.equal(stranger.groupRow, null);
});

test('the header never claims a last result in a tournament', () => {
  assert.equal(updatedText(120), 'Updated 2 min ago');
  assert.equal(updatedText(1), 'Updated just now');
  assert.equal(updatedText(600, { stale: true }), 'Connection lost – showing data from 10 min ago');
  for (const text of [updatedText(5), updatedText(5, { stale: true })]) {
    assert.doesNotMatch(text, /last result/i);
  }
});

test('a team entry without a status (an older export) is submitted', () => {
  assert.equal(entryStatus({ team: 'x' }), 'submitted');
  assert.equal(entryStatus({ team: 'x', status: 'submitted' }), 'submitted');
  assert.equal(entryStatus({ team: 'x', status: 'registered' }), 'registered');
  assert.equal(entryStatus({ team: 'x', status: 'whatever' }), 'submitted');
  assert.equal(entryStatus(null), 'submitted');
  assert.deepEqual(normalizeTeams([{ team: 'a' }, { team: 'b', status: 'registered' }]).map((e) => e.status), ['submitted', 'registered']);
  assert.deepEqual(normalizeTeams(undefined), []);
  assert.deepEqual(normalizeTeams({}), []);
});

test('counts split by status', () => {
  const teams = normalizeTeams([{ team: 'a' }, { team: 'b' }, { team: 'c' }, { team: 'd', status: 'registered' }, { team: 'e' }]);
  assert.deepEqual(statusCounts(teams), { submitted: 4, registered: 1 });
  assert.deepEqual(statusCounts([]), { submitted: 0, registered: 0 });
});
