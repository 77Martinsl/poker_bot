import test from 'node:test';
import assert from 'node:assert/strict';
import { data, refresh } from '../../site/js/api.js';

/** A fake server: `files` maps a path to its JSON; anything else is a 404. */
function serve(files) {
  const requested = [];
  globalThis.fetch = async (url) => {
    const path = String(url).split('?')[0];
    requested.push(path);
    if (!(path in files)) return { ok: false, status: 404, json: async () => ({}) };
    return { ok: true, status: 200, json: async () => files[path] };
  };
  return requested;
}

const tournament = { phase: 'groups', rounds: 1, groups: [{ name: 'A', teams: ['x', 'y'], board: null }], champion: null };
const teams = { teams: [{ team: 'x', group: 'A', versions: [] }], registrations: [] };

function manifest(phase, kinds, fingerprint) {
  return { mode: 'tournament', phase, kinds, fingerprint, generated_at: 1 };
}

test('before a round is complete only the manifest, tournament and teams are requested', async () => {
  for (const phase of ['registration', 'groups']) {
    const requested = serve({
      'data/manifest.json': manifest(phase, [], `fp-${phase}`),
      'data/tournament.json': tournament,
      'data/teams.json': teams,
    });
    data.manifest = null;
    assert.equal(await refresh(), true, phase);
    assert.deepEqual(requested.sort(), ['data/manifest.json', 'data/teams.json', 'data/tournament.json'], phase);
    assert.deepEqual(data.pairings, {});
    assert.equal(data.tournament.phase, 'groups');
    assert.equal(data.teams.length, 1);
  }
});

test('the published round loads its pairings, and no other file', async () => {
  const requested = serve({
    'data/manifest.json': manifest('done', ['group'], 'done'),
    'data/tournament.json': { ...tournament, phase: 'done' },
    'data/teams.json': teams,
    'data/pairings-group.json': [{ id: 'group-1' }],
  });
  data.manifest = null;
  assert.equal(await refresh(), true);
  assert.deepEqual(requested.sort(), ['data/manifest.json', 'data/pairings-group.json', 'data/teams.json', 'data/tournament.json']);
  assert.deepEqual(data.pairings, { group: [{ id: 'group-1' }] });
});

test('a listed file that is missing (404) does not break the page', async () => {
  serve({
    'data/manifest.json': manifest('groups', ['group'], 'gone'),
    'data/tournament.json': tournament,
    'data/teams.json': teams,
  });
  data.manifest = null;
  assert.equal(await refresh(), true);
  assert.deepEqual(data.pairings.group, []);
  assert.equal(data.manifest.phase, 'groups');
});

test('a missing tournament.json is reported, and the next poll tries again', async () => {
  const original = console.warn;
  console.warn = () => {};
  try {
    serve({ 'data/manifest.json': manifest('groups', [], 'late') });
    data.manifest = null;
    assert.equal(await refresh(), false);
    assert.ok(data.error);
    serve({
      'data/manifest.json': manifest('groups', [], 'late'),
      'data/tournament.json': tournament,
      'data/teams.json': teams,
    });
    assert.equal(await refresh(), true);
    assert.equal(data.error, null);
  } finally {
    console.warn = original;
  }
});

test('an unchanged fingerprint fetches nothing but the manifest', async () => {
  const files = {
    'data/manifest.json': manifest('groups', [], 'same'),
    'data/tournament.json': tournament,
    'data/teams.json': teams,
  };
  serve(files);
  data.manifest = null;
  await refresh();
  const requested = serve(files);
  assert.equal(await refresh(), false);
  assert.deepEqual(requested, ['data/manifest.json']);
});

test('team status is loaded, and a missing status counts as submitted', async () => {
  serve({
    'data/manifest.json': manifest('registration', [], 'status'),
    'data/tournament.json': { ...tournament, phase: 'registration', groups: [] },
    'data/teams.json': { teams: [{ team: 'a', status: 'registered' }, { team: 'b', status: 'submitted' }, { team: 'c' }] },
  });
  data.manifest = null;
  assert.equal(await refresh(), true);
  assert.deepEqual(data.teams.map((t) => [t.team, t.status]), [['a', 'registered'], ['b', 'submitted'], ['c', 'submitted']]);
});
