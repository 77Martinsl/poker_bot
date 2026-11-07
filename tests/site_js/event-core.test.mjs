import test from 'node:test';
import assert from 'node:assert/strict';
import { normalizeEvent } from '../../site/js/event-core.js';
import { groupMarks, normalizeTournament } from '../../site/js/tournament-core.js';

test('the Home page text keeps only short plain strings and known fields', () => {
  assert.equal(normalizeEvent(null), null);
  assert.equal(normalizeEvent({}), null);
  assert.equal(normalizeEvent([1]), null);
  const event = normalizeEvent({
    tagline: ' Go ',
    intro: ['a', 5, '', ' b '],
    prize: '£300',
    timeline: [{ time: '12:00', title: 'Start', detail: 'd', evil: '<b>' }, { time: '1' }, 'x', { title: 7 }],
    rules: 'not a list',
    contact: 'ask',
    other: 'ignored',
  });
  assert.deepEqual(event, {
    tagline: 'Go',
    intro: ['a', 'b'],
    prize: '£300',
    timeline: [{ time: '12:00', title: 'Start', detail: 'd' }],
    rules: [],
    contact: 'ask',
  });
  assert.equal(normalizeEvent({ prize: 'x'.repeat(500) }).prize.length, 200);
});

test('one round: no one qualifies, the champion is marked in the table', () => {
  const t = normalizeTournament({
    phase: 'done',
    rounds: 1,
    groups: [{ name: 'A', teams: ['ant', 'bee'], board: { teams: [{ team: 'ant', score: 1 }, { team: 'bee', score: -1 }] } }],
    champion: 'ant',
  });
  assert.equal(t.rounds, 1);
  assert.deepEqual([...groupMarks(t.groups[0], t)], [['ant', 'Champion']]);
  assert.equal(normalizeTournament({ phase: 'done' }).rounds, 2, 'two rounds unless the export says one');
});
