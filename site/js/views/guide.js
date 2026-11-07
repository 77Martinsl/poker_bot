import { loadGuide } from '../api.js';
import { h } from '../dom.js';
import { renderMarkdown } from '../markdown.js';
import { submissionsCard } from './home.js';

/** The how-to-submit guide shown as a page. */
export async function guideView(ctx) {
  const page = h('div', { class: 'page guide' });
  if (!ctx.data.manifest.has_guide) {
    page.appendChild(h('header', {}, h('h1', {}, 'How to submit')));
    page.appendChild(
      h('div', { class: 'empty card' }, 'The organiser has not published a submission guide.'),
    );
    return { el: page, title: 'How to submit' };
  }
  let text;
  try {
    text = await loadGuide();
  } catch (error) {
    page.appendChild(h('div', { class: 'empty card' }, 'The guide could not be loaded. This page tries again every few seconds.'));
    return { el: page, title: 'How to submit' };
  }
  const submissions = submissionsCard(ctx.data.submissions);
  if (submissions) page.appendChild(submissions);
  page.appendChild(renderMarkdown(text));
  return { el: page, title: 'How to submit' };
}
