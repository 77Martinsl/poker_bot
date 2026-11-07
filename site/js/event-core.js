// The Home page's text (event.json via the exporter). It is untrusted: every
// field is optional, only short plain strings survive, and the page shows it
// as text, never as markup. Pure (no DOM), tested in Node.

const isObject = (value) => value !== null && typeof value === 'object' && !Array.isArray(value);
const list = (value) => (Array.isArray(value) ? value : []);

/** event.json made safe; null when the organiser gave nothing. */
export function normalizeEvent(raw) {
  if (!isObject(raw)) return null;
  const text = (v, max = 1200) => (typeof v === 'string' ? v.trim().slice(0, max) : '');
  const texts = (v) => list(v).map((x) => text(x)).filter(Boolean).slice(0, 20);
  const timeline = list(raw.timeline)
    .filter((row) => isObject(row) && text(row.title))
    .slice(0, 30)
    .map((row) => ({ time: text(row.time, 40), title: text(row.title, 120), detail: text(row.detail) }));
  const repo = text(raw.repo, 200);
  const whatsapp = text(raw.whatsapp, 200);
  const event = {
    repo: repo.startsWith('https://') ? repo : '',
    whatsapp: whatsapp.startsWith('https://') ? whatsapp : '',
    tagline: text(raw.tagline, 200),
    intro: texts(raw.intro),
    prize: text(raw.prize, 200),
    timeline,
    rules: texts(raw.rules),
    contact: text(raw.contact),
  };
  const empty = !event.tagline && !event.intro.length && !event.prize && !timeline.length && !event.rules.length && !event.contact;
  return empty ? null : event;
}

/**
 * manifest.submissions: whether teams may submit now. The form's address is
 * in the data only while submissions are open, and only an https address is
 * ever turned into a link. null when the data has none.
 */
export function normalizeSubmissions(raw) {
  if (!isObject(raw)) return null;
  const text = (v) => (typeof v === 'string' ? v.trim().slice(0, 40) : '');
  const open = raw.status === 'open';
  const url = typeof raw.form_url === 'string' && raw.form_url.startsWith('https://') ? raw.form_url : null;
  return {
    status: open ? 'open' : 'closed',
    why: open ? null : raw.why === 'over' ? 'over' : 'not_yet',
    opens: text(raw.opens),
    closes: text(raw.closes),
    formUrl: open ? url : null,
  };
}

/** What to tell a team about submitting right now: {label, text}. */
export function submissionsText(sub) {
  if (!sub) return null;
  if (sub.status === 'open') {
    return { label: 'Submissions open', text: `Submissions are open${sub.closes ? ` until ${sub.closes}` : ''}.` };
  }
  if (sub.why === 'over') {
    return { label: 'Submissions closed', text: 'Submissions are closed. The round is about to start.' };
  }
  return { label: 'Submissions closed', text: `Submissions are closed${sub.opens ? `. They open at ${sub.opens}` : ''}.` };
}
