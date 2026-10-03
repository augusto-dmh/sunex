---
status: accepted
date: 2026-10-02
decision-makers: Augusto Henriques
consulted:
informed:
---

# ADR-0012: Write UI copy in English behind translation keys; add pt-BR later

This decision amends the original language decision ("pt-BR UI behind translation keys; English
identifiers, README, ADRs, commits and docs"). The part about code and documentation stands; the
UI language for now changes from pt-BR to English.

## Context and Problem Statement

Sunex is for Brazilian employers, so the product must eventually speak Brazilian Portuguese. It is
also a public portfolio read by international reviewers, and most of its contributors are coding
agents that write English fluently. Writing careful pt-BR copy on every screen while the screens
are still changing every week turns copywriting into a cost on every early pull request.

In which language do we write UI copy now, and how do we keep the door open for pt-BR?

## Decision Drivers

- Brazilian employers must eventually see a native product (product value "Brazil first,
  legible everywhere").
- Early feature work should not pay a copywriting cost on screens that will still change.
- International reviewers should be able to use the demo.
- Adding a locale later must be a translation task, not a refactor of every component.
- Legal terms have no faithful English equivalent and must not be mistranslated.

## Considered Options

- pt-BR literal strings in components
- pt-BR behind translation keys from day one
- English behind translation keys now, pt-BR as a later roadmap row (chosen)
- English literal strings

## Decision Outcome

Chosen option: "English behind translation keys now, pt-BR as a later roadmap row", because it
removes copywriting from every early feature while making the eventual pt-BR locale a matter of
adding `lang/pt_BR` files and a locale switch.

Rules:

1. Every user-visible string, in PHP (validation messages, notifications, mail) and in Vue
   components, goes through a translation key. Source strings live in `lang/en`.
2. Keys are namespaced by area, for example `absence.vacation.request.submit`.
3. **Brazilian legal and eSocial terms stay in Portuguese even in the English UI**: férias,
   afastamento, abono pecuniário, período aquisitivo, matrícula, CPF, CNPJ, CLT, eSocial. A
   glossary page (and a docs file) explains each in one English sentence. Translating "férias" to
   "vacation" in the UI would hide which statute applies.
4. Code identifiers, documentation, commits and pull requests are English (unchanged).
5. Dates and numbers are formatted through locale-aware helpers, never by string concatenation,
   so the pt-BR locale gets `dd/mm/yyyy` and `R$ 1.234,56` without code changes.
6. The pt-BR locale is a roadmap row of its own, scheduled after the v1 screens stabilise.

### Consequences

- Good, because features ship without waiting for copy, and international reviewers can use the
  demo.
- Good, because the pt-BR row becomes translation plus review, not a sweep through every
  component.
- Bad, because until the pt-BR row ships, Brazilian HR users see an English product with
  Portuguese legal terms; the demo audience accepts this, a production customer would not.
- Bad, because translation keys make components slightly harder to read than literals.
- Neutral, because Boost has a conditional localization guideline that agents follow when the
  project cares about localization ([Boost docs](https://laravel.com/docs/13.x/boost)).

### Confirmation

- A test scans `resources/js` and `app/` for translation-key usages and fails when a key is
  missing from `lang/en`.
- Review rejects literal user-visible strings in Vue templates and controllers.
- The pt-BR roadmap row adds the reverse check: every key in `lang/en` exists in `lang/pt_BR`.

## Pros and Cons of the Options

### pt-BR literal strings

- Good, because the product is native from day one with the least code.
- Bad, because adding any other locale later means touching every component, and international
  reviewers cannot use the demo.

### pt-BR behind keys from day one

- Good, because it matches the target market immediately and is translation-ready.
- Bad, because every early pull request carries careful pt-BR copywriting for screens that will
  still change; agents' pt-BR copy needs more human review than English.

### English behind keys now, pt-BR later

- Good, because it keeps early rows cheap and the later locale cheap.
- Bad, because the native experience is postponed to a later row.

### English literal strings

- Good, because it is the fastest to write.
- Bad, because it makes the pt-BR locale a refactor, contradicting the Brazil-first product value.

## More Information

- The Brazilian market context (vendors, eSocial vocabulary) that makes the legal terms
  non-negotiable is summarised in the TDD; eSocial identifies workers by CPF and events by
  Portuguese names (S-2200 "Admissão", S-2230 "Afastamento Temporário")
  ([gov.br eSocial leiautes](https://www.gov.br/esocial/pt-br/documentacao-tecnica/leiautes-esocial-v-s-1-3-nt-07-2026-rev-24-09-2026)).
- Related: [ADR-0003](0003-inertia-vue-typescript-frontend.md) (where the keys are rendered).
- Revisit if: a first real Brazilian user or deployment appears before v1 ends (then pull the
  pt-BR row forward), or if the glossary approach confuses users in testing.
