const form = document.querySelector('#question-form');
const input = document.querySelector('#question');
const modeSelect = document.querySelector('#mode');
const examFields = document.querySelector('#exam-fields');
const practiceFields = document.querySelector('#practice-fields');
const examTarget = document.querySelector('#exam-target');
const subject = document.querySelector('#subject');
const marks = document.querySelector('#marks');
const questionType = document.querySelector('#question-type');
const difficulty = document.querySelector('#difficulty');
const questionCount = document.querySelector('#question-count');
const includeAnswerKey = document.querySelector('#answer-key');
const language = document.querySelector('#language');
const questionLabel = document.querySelector('#question-label');
const modeDescription = document.querySelector('#mode-description');
const count = document.querySelector('#char-count');
const submitButton = document.querySelector('#submit-button');
const statusPanel = document.querySelector('#status-panel');
const statusTitle = document.querySelector('#status-title');
const statusDetail = document.querySelector('#status-detail');
const resultPanel = document.querySelector('#result');
const answerText = document.querySelector('#answer-text');
const evidenceBadge = document.querySelector('#evidence-badge');
const resultEyebrow = document.querySelector('#result-eyebrow');
const resultTitle = document.querySelector('#result-title');
const formatNote = document.querySelector('#format-note');
const limitNote = document.querySelector('#limit-note');
const sourceSection = document.querySelector('#source-section');
const sourceCount = document.querySelector('#source-count');
const sourceList = document.querySelector('#source-list');
const errorMessage = document.querySelector('#error-message');

input.addEventListener('input', () => {
  count.textContent = `${input.value.length} / ${input.maxLength}`;
});

const modeCopy = {
  exam_answer: {
    label: 'Your exam question',
    placeholder: 'Paste or type your exam question…',
    description: 'Add your exam, subject, and marks for a closer format. The app does not claim to reproduce an official marking scheme.',
    button: 'Get exam answer',
    eyebrow: 'EXAM ANSWER',
    title: 'Ready-to-write answer',
    status: 'Writing an exam-style answer',
    limit: 'Use the exam, subject, and marks fields for a closer format. Always compare important answers with your official syllabus or marking scheme.',
  },
  practice: {
    label: 'Topic or concept to practice',
    placeholder: 'For example: quadratic equations, causes of the French Revolution…',
    description: 'Creates new practice questions using public syllabus or sample-paper guidance when available. Similar style is not a promise about the real exam.',
    button: 'Create practice set',
    eyebrow: 'PRACTICE SET',
    title: 'New exam-style questions',
    status: 'Creating and checking practice questions',
    limit: 'These are newly generated practice questions, not official or leaked papers, and cannot predict the questions on an upcoming exam.',
  },
  daily: {
    label: 'What do you need help with?',
    placeholder: 'Ask for a draft, plan, explanation, calculation, or checklist…',
    description: 'Use this for drafts, plans, and explanations. It prepares text but does not send messages or perform actions outside this app; factual claims are not web-verified in this mode.',
    button: 'Get daily help',
    eyebrow: 'DAILY HELPER',
    title: 'Your draft or plan',
    status: 'Preparing your result',
    limit: 'This is a one-time draft or plan, not an external action. Check factual details before relying on them.',
  },
  research: {
    label: 'What factual question should I research?',
    placeholder: 'Ask about a topic, claim, event, or decision…',
    description: 'Uses live web search, citations, and a separate evidence review for factual questions.',
    button: 'Research answer',
    eyebrow: 'RESEARCH RESULT',
    title: 'What the evidence says',
    status: 'Researching your question',
    limit: 'Sources support the answer; they do not guarantee certainty. Check the original material, especially for high-stakes decisions.',
  },
};

function updateMode() {
  const mode = modeSelect.value;
  const copy = modeCopy[mode] || modeCopy.exam_answer;
  examFields.hidden = !['exam_answer', 'practice'].includes(mode);
  practiceFields.hidden = mode !== 'practice';
  questionLabel.textContent = copy.label;
  input.placeholder = copy.placeholder;
  modeDescription.textContent = copy.description;
  submitButton.firstElementChild.textContent = copy.button;
  resultEyebrow.textContent = copy.eyebrow;
  resultTitle.textContent = copy.title;
  statusTitle.textContent = copy.status;
}

modeSelect.addEventListener('change', updateMode);
updateMode();

document.querySelectorAll('.suggestion').forEach((button) => {
  button.addEventListener('click', () => {
    modeSelect.value = button.dataset.mode || 'exam_answer';
    updateMode();
    input.value = button.textContent.trim();
    count.textContent = `${input.value.length} / ${input.maxLength}`;
    input.focus();
  });
});

function setBusy(busy) {
  submitButton.disabled = busy;
  submitButton.firstElementChild.textContent = busy ? 'Working…' : (modeCopy[modeSelect.value]?.button || 'Get exam answer');
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
  sourceCount.textContent = validSources.length ? `${validSources.length} cited`;
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
  const mode = modeSelect.value;
  statusTitle.textContent = modeCopy[mode]?.status || 'Working on your request';
  statusDetail.textContent = mode === 'daily'
    ? 'Preparing a one-time draft. This mode does not save a history or check facts against the web.'
    : 'Checking public sources and reviewing the result…';
  try {
    const response = await fetch('/api/answer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question,
        mode,
        exam_target: examTarget.value.trim(),
        subject: subject.value.trim(),
        marks: marks.value ? Number(marks.value) : null,
        question_type: questionType.value,
        difficulty: difficulty.value,
        question_count: Number(questionCount.value) || 5,
        include_answer_key: includeAnswerKey.checked,
        language: language.value,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Research could not be completed. Please try again.');

    resultEyebrow.textContent = modeCopy[data.mode || mode]?.eyebrow || modeCopy.exam_answer.eyebrow;
    resultTitle.textContent = modeCopy[data.mode || mode]?.title || modeCopy.exam_answer.title;
    limitNote.textContent = modeCopy[data.mode || mode]?.limit || modeCopy.exam_answer.limit;
    formatNote.textContent = data.format_note || '';
    formatNote.hidden = !formatNote.textContent;
    renderAnswer(data.answer || 'No answer was returned.', data.citation_spans);
    renderSources(Array.isArray(data.citations) ? data.citations : []);
    evidenceBadge.textContent = data.verified
      ? 'Evidence review passed'
      : (data.refused ? 'Safety response' : (mode === 'daily' ? 'Draft — not fact-checked' : 'Not verified'));
    evidenceBadge.title = data.verified
      ? 'A separate fresh-search review passed. This is not a guarantee of correctness.'
      : (mode === 'daily'
        ? 'Daily helper mode does not browse or verify factual claims.'
        : 'The app withholds substantive answers that do not pass its evidence review.');
    evidenceBadge.classList.toggle('unverified', !data.verified);
    resultPanel.hidden = false;
    resultPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (error) {
    errorMessage.textContent = error instanceof Error ? error.message : 'Research could not be completed. Please try again.';
    errorMessage.hidden = false;
  } finally {
    setBusy(false);
  }
});
