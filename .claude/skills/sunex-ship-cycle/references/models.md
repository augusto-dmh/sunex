# Model selection and cost discipline

Prices and constraints below were checked on 2026-10-02 against the Claude API reference bundled with Claude Code. Re-check them when a new model ships; the rules that follow depend on the ratios, not on the exact numbers.

| Model | Agent tool `model` | Input / output per MTok | Role in this pipeline |
|---|---|---|---|
| Claude Opus 5.5 | `opus` | $4 / $20 | Default for everything that reasons |
| Claude Fable 5.1 | `fable` | $10 / $50 (2.5× Opus 5.5) | Upshift for the Verifier and triage |
| Claude Haiku 4.5 | `haiku` | $1 / $5 | Mechanical chores dispatched as their own unit |

Sonnet is not part of this pipeline. The earlier project this process comes from measured that a Sonnet worker's output per task was large enough to erase the price gap for this kind of work; that measurement is not repeated for Sonnet 5.5, so it stays out until someone measures it on Sunex cycles.

## Default: Opus 5.5

A cheap worker that slips is not cheap: its output, plus the Verifier catching it, plus a fix task, plus re-verification can cost more than doing it right on Opus. So the default for any unit that makes a decision or carries an invariant is Opus 5.5. When the harness exposes effort (a Houston pane's `effort`, `/effort` in a session), run phase workers at `high` and the Verifier at `xhigh`.

## Downshift to Haiku 4.5: the four-condition test

Downshift a delegated unit only when all four hold. Fail any one, or be unsure, and it stays on Opus.

1. **Fully specified.** Exact files, signatures and steps are already in the spec or design; the worker transcribes, it does not decide.
2. **No correctness-critical invariant.** Nothing touching authorization or policies, company scoping, masking of sensitive fields, migrations or constraints, transactions, queue idempotency, effective dating, CLT rules, agent scopes or audit rows. A weak model fails quietly there: it passes a thin gate and only the Verifier catches it, or nobody does.
3. **A fast local gate catches a slip.** A failing Pest file, Pint, Larastan or `vue-tsc` run surfaces the mistake at once.
4. **Small blast radius.** Few files, no ripple into shared contracts or schema.

Typical Haiku units: worktree setup and teardown, comment deletion (Stage 6), the wrap bookkeeping (Stage 8), a doc-only chore such as an `.env.example` entry or a translation-key file, and the pr-review consolidation pass. A phase that mixes a chore with a hard kernel is one worker, and the kernel sets the model: keep it on Opus.

## Upshift to Fable 5.1

Fable 5.1 is stronger at long autonomous work, at ambiguity, and at reading code for what it can do rather than what it currently does. That is exactly the Verifier's and the triager's job, and both are a small share of a cycle's tokens. It also takes noticeably longer per turn.

| Unit | Model |
|---|---|
| Stage 1 Verifier | Fable 5.1 when the cycle touches domain rules, data invariants or migrations (most domain cycles); Opus 5.5 for scaffolding, tooling or docs-only cycles, and for cycles that are mainly authentication or security hardening |
| Stage 4 triage | A fresh Fable 5.1 triager for findings from every lane except Security; the orchestrator (Opus 5.5) triages Security-lane findings itself |
| Stage 1 phase workers | Opus 5.5. Fable only when the brief is goal-shaped (worker-briefs.md): a step-listed brief measurably lowers Fable's output quality, so it would underperform Opus at 2.5× the price |
| pr-review lanes | Governed by pr-review: Opus, never Fable for Security |
| Mechanical chores | Never Fable |

Hard preconditions and fallbacks:

- **Data retention.** Fable 5.1 requires the organisation to allow 30-day data retention; under zero data retention every request fails with a 400. Check this first when Fable calls fail with a valid payload.
- **Safety classifiers.** Fable 5.1 declines some requests (`refusal` stop reason), and security-focused analysis is where that happens most. That is why the Security lane and security-lane triage stay on Opus. (Opus 5.5 has classifiers too, narrower ones; a refusal on either model is reported, never silently treated as "no findings".)
- **Fallback.** A Fable refusal or 400 on a unit: re-run that unit on Opus 5.5 and record the fallback in the cycle's `context.md` and the ship report.

## Recommending the next row's model (Stage 8)

End every wrap with a one-line recommendation for the next row's phase workers and Verifier, using the tables above. Example: "Next: vacation balance engine. Workers Opus 5.5 (CLT kernel with table-driven rules); Verifier Fable 5.1 (rule boundaries are where mutants survive)."

## Context hygiene

- Delegate the opening codebase survey to an `Explore` agent that returns seams (signatures and `file:line` references), not file bodies. Scope globs to `app/**`, `database/**`, `routes/**`, `resources/js/**`, `tests/**`; never sweep `vendor/` or `node_modules/`.
- The Verifier's discrimination mutations run only the target Pest file (`--filter` or the file path), not the whole suite per mutant.
