# 99% Accuracy Target and Evaluation Protocol

## What the target means

The project target is at least 99% precision among substantive answers on a versioned, human-reviewed benchmark. This does not mean 99% of all possible questions can be answered, and it is not a universal guarantee. The target has not been measured or achieved for this repository because it does not yet include a labeled benchmark.

Score an answer as correct only when every material factual claim is accurate, current for the question's stated time, and supported by the cited sources. A partially wrong answer is incorrect. Count abstentions separately; do not count them as correct substantive answers.

## Metrics to report

- Precision: correct substantive answers divided by all substantive answers.
- Coverage: substantive answers divided by all benchmark questions.
- Abstention recall: correctly abstained questions divided by benchmark questions labeled as requiring abstention.
- Citation support rate: material claims directly supported by a cited source divided by all material claims.
- Breakdowns: report each metric by topic, risk level, question freshness, and source type.

Report the dataset version, date, model identifiers, prompt and code revision, question count, raw counts, abstentions, and a pre-registered 95% exact binomial confidence interval for precision. Claim the 99% target only when the lower confidence bound is at least 99% on a held-out set. Keep the benchmark blind during prompt tuning.

## Build and maintain a benchmark

1. Create representative, human-written questions for the intended launch domains. Include changing facts, disputed claims, false premises, ambiguous wording, calculations, and high-stakes questions.
2. Label each question as answerable or requiring abstention. For answerable items, record a reference answer, acceptable variants, required caveats, and authoritative sources. For abstention items, record why evidence is insufficient or unsafe.
3. Have two reviewers independently label model outputs against the rubric. Resolve disagreements before scoring. Reviewers must inspect the cited sources themselves.
4. Keep a separate held-out set. Re-run it after model, prompt, search, or verification changes.
5. Report precision and coverage together. A high precision score achieved by abstaining on nearly every question must show that low coverage.

## Runtime review limits

The service performs a second review with a fresh web search and requires a pass decision plus at least two matching citation annotations from distinct hostnames. Distinct hostnames do not prove that sources are independent, reliable, or complete. By default, both passes use OPENAI_MODEL; setting OPENAI_VERIFIER_MODEL to a different supported model may reduce some correlated model errors. Either way, model review can still be wrong.

The runtime gate is a risk-reduction mechanism, not a calibrated confidence score. It cannot replace the benchmark, human review, or domain-specific validation.
