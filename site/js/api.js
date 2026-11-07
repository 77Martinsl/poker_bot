// Loads the exported JSON. The manifest is tiny and fetched fresh on every
// poll; the bigger files are fetched only when its fingerprint changes, and
// are keyed by it so a CDN or browser can cache them between changes.

import { normalizeTeams, normalizeTournament, tournamentFiles } from './tournament-core.js';
import { normalizeEvent, normalizeSubmissions } from './event-core.js';

export const data = {
  manifest: null,
  tournament: null, // tournament.json, normalised
  submissions: null, // manifest.submissions, normalised
  event: null, // event.json (the Home page text), normalised
  pairings: {},
  teams: [],
  lastOk: 0, // wall-clock ms of the last successful poll
  error: null,
};

const replayCache = new Map();

async function getJSON(path, bust) {
  const response = await fetch(`${path}?v=${encodeURIComponent(bust)}`, {
    cache: 'no-store',
  });
  if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
  return response.json();
}

/** Like getJSON, but a file that is not there (404) is null, not an error. */
async function getOptionalJSON(path, bust) {
  const response = await fetch(`${path}?v=${encodeURIComponent(bust)}`, {
    cache: 'no-store',
  });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
  return response.json();
}

/** Polls the manifest; resolves true when the data changed. */
export async function refresh() {
  try {
    const manifest = await getJSON('data/manifest.json', Date.now());
    data.lastOk = Date.now();
    data.error = null;
    if (data.manifest && data.manifest.fingerprint === manifest.fingerprint) {
      return false;
    }
    await loadAll(manifest);
    return true;
  } catch (error) {
    data.error = error;
    console.warn('Could not load results:', error);
    return false;
  }
}

/**
 * tournament.json always, and the pairings only when the manifest says they
 * are published. Nothing else is requested, so a not-yet-played round costs no
 * 404s. The group's ranked table travels inside tournament.json.
 */
async function loadAll(manifest) {
  const bust = manifest.fingerprint;
  const files = tournamentFiles(manifest);
  const pairingKinds = Object.keys(files.pairings);
  const [tournament, teams, event, ...rest] = await Promise.all([
    getJSON(files.tournament, bust),
    getOptionalJSON(files.teams, bust),
    manifest.has_event ? getOptionalJSON('data/event.json', bust) : null,
    ...pairingKinds.map((kind) => getOptionalJSON(files.pairings[kind], bust)),
  ]);
  data.pairings = {};
  pairingKinds.forEach((kind, index) => {
    data.pairings[kind] = rest[index] || [];
  });
  data.tournament = normalizeTournament(tournament);
  data.submissions = normalizeSubmissions(manifest.submissions);
  data.tournament.submissions = data.submissions;
  data.event = normalizeEvent(event);
  data.teams = normalizeTeams(teams && teams.teams);
  data.manifest = manifest;
  replayCache.clear(); // replay files may have been rebuilt
}

/** The how-to-submit guide as markdown text (cached until the data changes). */
let guideCache = null;
export async function loadGuide() {
  const bust = data.manifest ? data.manifest.fingerprint : '0';
  if (!guideCache || guideCache.bust !== bust) {
    const response = await fetch(`data/submitting.md?v=${encodeURIComponent(bust)}`, {
      cache: 'no-store',
    });
    if (!response.ok) throw new Error(`data/submitting.md: HTTP ${response.status}`);
    guideCache = { bust, text: await response.text() };
  }
  return guideCache.text;
}

export async function loadReplay(path) {
  if (!replayCache.has(path)) {
    const bust = data.manifest ? data.manifest.fingerprint : '0';
    replayCache.set(path, getJSON(path, bust));
  }
  try {
    return await replayCache.get(path);
  } catch (error) {
    replayCache.delete(path);
    throw error;
  }
}

/** All pairings, newest first. */
export function allPairings() {
  return Object.values(data.pairings)
    .flat()
    .sort((a, b) => (b.finished_at || 0) - (a.finished_at || 0));
}

export function findPairing(id) {
  return allPairings().find((p) => p.id === id) || null;
}

export function teamEntry(name) {
  return data.teams.find((t) => t.team === name) || null;
}
