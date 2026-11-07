import test from 'node:test';
import assert from 'node:assert/strict';
import { normalizeEvent, normalizeSubmissions, submissionsText } from '../../site/js/event-core.js';
import { groupMarks, normalizeTournament, phaseInfo } from '../../site/js/tournament-core.js';

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
    repo: '',
    whatsapp: '',
  });
  assert.equal(normalizeEvent({ prize: 'x'.repeat(500) }).prize.length, 200);
});

test('one round: the champion is marked in the table, nobody else is', () => {
  const t = normalizeTournament({
    phase: 'done',
    groups: [{ name: 'A', teams: ['ant', 'bee'], board: { teams: [{ team: 'ant', score: 1 }, { team: 'bee', score: -1 }] } }],
    champion: 'ant',
  });
  assert.deepEqual([...groupMarks(t.groups[0], t)], [['ant', 'Champion']]);
  const running = normalizeTournament({ phase: 'groups', groups: [{ name: 'A', teams: ['ant', 'bee'], board: null }] });
  assert.equal(groupMarks(running.groups[0], running).size, 0);
  const elsewhere = normalizeTournament({ phase: 'done', groups: [{ name: 'A', teams: ['bee'], board: null }], champion: 'ant' });
  assert.equal(groupMarks(elsewhere.groups[0], elsewhere).size, 0);
});

test('the WhatsApp link must be https', () => {
  assert.equal(normalizeEvent({ intro: ['x'], whatsapp: 'https://tr.ee/abc' }).whatsapp, 'https://tr.ee/abc');
  assert.equal(normalizeEvent({ intro: ['x'], whatsapp: 'javascript:alert(1)' }).whatsapp, '');
  assert.equal(normalizeEvent({ intro: ['x'] }).whatsapp, '');
});

test('the repo link must be https', () => {
  assert.equal(normalizeEvent({ intro: ['x'], repo: 'https://github.com/a/b' }).repo, 'https://github.com/a/b');
  assert.equal(normalizeEvent({ intro: ['x'], repo: 'javascript:alert(1)' }).repo, '');
});

test('submissions: the form link is only ever an https link, and only while open', () => {
  assert.equal(normalizeSubmissions(null), null);
  const open = normalizeSubmissions({ status: 'open', opens: '16:00', closes: '18:00', form_url: 'https://forms.example/x' });
  assert.equal(open.status, 'open');
  assert.equal(open.formUrl, 'https://forms.example/x');
  assert.equal(normalizeSubmissions({ status: 'open', form_url: 'javascript:alert(1)' }).formUrl, null);
  assert.equal(normalizeSubmissions({ status: 'closed', form_url: 'https://forms.example/x' }).formUrl, null);
  assert.equal(normalizeSubmissions({ status: 'weird' }).status, 'closed');
  assert.equal(normalizeSubmissions({ status: 'closed' }).why, 'not_yet');
  assert.equal(normalizeSubmissions({ status: 'closed', why: 'over' }).why, 'over');
});

test('submissions are described in plain words', () => {
  assert.equal(submissionsText(null), null);
  const closed = submissionsText(normalizeSubmissions({ status: 'closed', why: 'not_yet', opens: '16:00' }));
  assert.equal(closed.label, 'Submissions closed');
  assert.equal(closed.text, 'Submissions are closed. They open at 16:00.');
  assert.equal(submissionsText(normalizeSubmissions({ status: 'closed' })).text, 'Submissions are closed.');
  assert.equal(submissionsText(normalizeSubmissions({ status: 'open', closes: '18:00' })).text, 'Submissions are open until 18:00.');
  assert.match(submissionsText(normalizeSubmissions({ status: 'closed', why: 'over' })).text, /round is about to start/);
});

test('before the draw the status banner says whether submissions are open', () => {
  assert.match(phaseInfo('registration').text, /Submissions are open/);
  const sub = normalizeSubmissions({ status: 'closed', why: 'not_yet', opens: '16:00' });
  assert.equal(phaseInfo('registration', sub).label, 'Submissions closed');
  assert.match(phaseInfo('registration', sub).text, /closed/);
  assert.equal(phaseInfo('done', sub).label, 'Finished');
});
