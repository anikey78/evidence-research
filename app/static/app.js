const form = document.querySelector('#question-form');
const input = document.querySelector('#question');
const count = document.querySelector('#char-count');
const submitButton = document.querySelector('#submit-button');
const statusPanel = document.querySelector('#status-panel');
const statusTitle = document.querySelector('#status-title');
const statusDetail = document.querySelector('#status-detail');
const resultPanel = document.querySelector('#result');
const answerText = document.querySelector('#answer-text');
const evidenceBadge = document.querySelector('#evidence-badge');
const sourceSection = document.querySelector('#source-section');
const sourceCount = document.querySelector('#source-count');
const sourceList = document.querySelector('#source-list');
const errorMessage = document.querySelector('#error-message');

input.addEventListener('input', () => {
  count.textContent = `${input.value.length} / ${input.maxLength}`;
});

document.querySelectorAll('.suggestion').forEach((button) => {
  button.addEventListener('click', () => {
    input.value = button.textContent.trim();
    count.textContent = `${input.value.length} / ${input.maxLength}`;
    input.focus();
  });
});

function setBusy(busy) {
  submitButton.disabled = busy;
  submitButton.firstElementChild.textContent = busy ? 'Researching…' : 'Research answer';
  statusPanel.hidden = !busy;
  if (busy) {
    resultPanel.hidden = true;
    errorMessage.hidden = true;
  }
}

function safeHttpUrl(value) {
  try {
    const url = new URL(value);
    return ['http:', 'https:'].includes(url.protocol) ? url.href : null;
  } catch {
    return null;
  }
}

function renderSources(sources) {
  sourceList.replaceChildren();
  const validSources = sources
    .map((source) => ({ ...source, safeUrl: safeHttpUrl(source.url) }))
    .filter((source) => source.safeUrl);

  validSources.forEach((source) => {
    const item = document.createElement('li');
    const link = document.createElement('a');
    link.className = 'source-link';
    link.href = source.safeUrl;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    const label = document.createElement('span');
    const title = document.createElement('strong');
    title.textContent = source.title || new URL(source.safeUrl).hostname;
    const url = document.createElement('span');
    url.className = 'source-url';
    url.textContent = new URL(source.safeUrl).hostname;
    label.append(title, url);
    link.append(label);
    item.append(link);
    sourceList.append(item);
  });

  sourceSection.hidden = validSources.length === 0;
  sourceCount.textContent = validSources.length ? `${validSources.length} cited` : '';
}

function renderAnswer(text, spans) {
  answerText.replaceChildren();
  const safeSpans = (Array.isArray(spans) ? spans : [])
    .map((span) => ({ ...span, safeUrl: safeHttpUrl(span.url) }))
    .filter((span) => span.safeUrl && Number.isInteger(span.start) && Number.isInteger(span.end))
    .sort((left, right) => left.start - right.start);

  let cursor = 0;
  for (const span of safeSpans) {
    if (span.start < cursor || span.end <= span.start || span.end > text.length) continue;
    answerText.append(document.createTextNode(text.slice(cursor, span.start)));
    const link = document.createElement('a');
    link.href = span.safeUrl;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.textContent = text.slice(span.start, span.end);
    link.title = span.title || 'Open cited source';
    answerText.append(link);
    cursor = span.end;
  }
  answerText.append(document.createTextNode(text.slice(cursor)));
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const question = input.value.trim();
  if (question.length < 3) {
    input.focus();
    return;
  }

  setBusy(true);
  statusTitle.textContent = 'Researching your question';
  statusDetail.textContent = 'Searching sources and checking evidence…';
  try {
    const response = await fetch('/api/answer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Research could not be completed. Please try again.');

    renderAnswer(data.answer || 'No answer was returned.', data.citation_spans);
    renderSources(Array.isArray(data.citations) ? data.citations : []);
    evidenceBadge.textContent = data.grounded ? 'Sources attached' : (data.refused ? 'Safety response' : 'Not verified');
    evidenceBadge.classList.toggle('unverified', !data.grounded);
    resultPanel.hidden = false;
    resultPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (error) {
    errorMessage.textContent = error instanceof Error ? error.message : 'Research could not be completed. Please try again.';
    errorMessage.hidden = false;
  } finally {
    setBusy(false);
  }
});
