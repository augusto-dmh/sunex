---
status: accepted
date: 2026-10-02
decision-makers: Augusto Henriques
---

# ADR-0009: No payroll and no eSocial transmission; Sunex is the structured source, via signed events and eSocial-shaped CSV

## Context and Problem Statement

Brazilian employers report employment facts to eSocial, a government XML event pipeline (layout
version S-1.3, consolidated up to Nota Técnica 07/2026 revised on 2026-09-24). Its events fall in
three families: tables (S-1000 to S-1070), non-periodic lifecycle events (S-2190 to S-2399:
admission S-2200, contract change S-2206, temporary absence S-2230, termination S-2299) and periodic
payroll events (S-1200 to S-1299), each with hard deadlines. After the monthly closing (S-1299),
eSocial feeds DCTFWeb and FGTS Digital.

Sunex manages employment history, férias and afastamentos, so it holds most of the source data
for the lifecycle events. The question is how far it goes: calculate payroll, produce the XML,
transmit it, or stop at being the best-structured source for the payroll system that does.

## Decision Drivers

- Product value 3: "The source, not the transmitter."
- Legal risk: a wrong payroll or a rejected event carries fines and wrong FGTS/INSS amounts; a
  solo, open-source project cannot carry that.
- Change rate of the government rules: Nota Técnica 06/2026 changed S-1200, S-2190, S-2299 and
  S-2500 validations mid-year; tracking every NT is a full-time job.
- Operational burden of transmission: ICP-Brasil certificates, receipts, retifications and
  exclusions (S-3000).
- How Brazilian companies actually work: payroll (folha) runs in an ERP or a payroll provider, and
  people tools integrate with it.
- The 12-week appetite for v1.

## Considered Options

1. Build payroll (calculation, rubrics, periodic events).
2. Generate eSocial XML and transmit it.
3. Generate eSocial XML only, for the payroll system to sign and send.
4. Store eSocial-shaped source data and emit signed webhook events plus CSV files shaped like the
   lifecycle events.

## Decision Outcome

Chosen: **option 4**. Sunex never calculates payroll, never generates eSocial XML and never
transmits to eSocial. It is the best-structured source of the lifecycle facts payroll needs.

Concretely, v1:

- Stores eSocial-shaped source data on persons, employments and employment versions: CPF (the
  worker key), matrícula (unique per employer), categoria (eSocial Tabela 01 code), CBO, salary and
  its unit, weekly hours and schedule description, establishment, admission date; afastamentos keep
  their Tabela 18 motive code and dates, never a diagnosis.
- Runs an **admission readiness checklist**: an admission cannot be approved until the S-2200
  source fields are complete and valid, and the dashboard shows the S-2200 deadline (the day before
  the first day of work).
- Emits lifecycle events through the signed outbox ([ADR-0010](0010-transactional-outbox-signed-webhooks.md))
  and offers **CSV exports shaped like S-2200, S-2206, S-2230 and S-2299**, with column names
  mirroring the leiaute tags. Column mappings are marked "to verify" until checked against the
  S-1.3 leiaute and the Manual de Orientação.
- Stores only effective-dated salary and cost centre for finance. A people-cost module (cost
  multipliers, headcount plan vs actual, GL CSV) comes later; salary bands, compa-ratio and expense
  claims are not planned.

### Consequences

- Good, because Sunex carries no filing liability: payroll remains the system of record and the
  transmitter, which the UI states next to every calculated balance and deadline.
- Good, because the scope fits the appetite and the effort goes into the parts payroll tools do
  badly: dated history, approvals and audit.
- Good, because signed events and CSV are what HR vendors already offer and what payroll
  integrations consume.
- Bad, because a customer still needs a payroll system and an integration; Sunex cannot claim
  "eSocial compliant" end to end.
- Bad, because the CSV shapes must be kept close to the leiaute by hand; a layout change can make
  them stale (mitigated: they are an integration aid, not a filing).
- Neutral, because SST events (S-2210, S-2220, S-2240) stay with occupational-health providers.

### Confirmation

- No dependency, class or route generates XML or talks to an eSocial endpoint (reviewed in every
  PR; an architecture test forbids XML signing libraries in `app/`).
- Feature tests: an incomplete admission cannot be approved; each lifecycle event appears once in
  the outbox and once in the matching CSV export with the same values.
- The column map in `docs/esocial/csv-columns.md` (roadmap row `esocial-csv-export`) lists each
  column's leiaute tag and its verification status.
- An export returns only events of employments the exporting user reaches, as of today.

## Pros and Cons of the Options

### 1. Build payroll

- Good, because it would make Sunex a complete HR suite.
- Bad, because payroll must produce legally binding monthly outputs (S-1200 and S-1210 by the 15th,
  S-1299 last, FGTS Digital by the 20th) with a rubric table (S-1010) that must exist before use.
- Bad, because the cost and legal risk dwarf the rest of v1; mature vendors treat it as a separate
  product.

### 2. Generate XML and transmit

- Good, because it removes the payroll integration for lifecycle events.
- Bad, because transmission requires ICP-Brasil certificate handling, receipt tracking, retification
  (`indRetif`) and exclusion (S-3000), and the people app and payroll system would both send events
  for the same worker.
- Bad, because every Nota Técnica becomes a release-blocking task.

### 3. Generate XML only

- Good, because it is closer to "plug-in" for some payroll systems.
- Bad, because it inherits the schema-tracking cost of option 2 without its benefit, and payroll
  systems generate their own XML from their own data anyway.

### 4. Signed events and eSocial-shaped CSV (chosen)

- Good, because the data model is still eSocial-shaped, so a payroll system can build S-2200,
  S-2206, S-2230 and S-2299 from it without re-keying.
- Good, because it reuses one mechanism (the outbox) for webhooks and files.
- Bad, because "shaped like" needs discipline: tag names and code tables must be verified.

## More Information

Sources (research on compliance and the Brazilian market, read 2026-09-30):

- eSocial S-1.3 leiautes consolidated to NT 07/2026 —
  [gov.br](https://www.gov.br/esocial/pt-br/documentacao-tecnica/leiautes-esocial-v-s-1-3-nt-07-2026-rev-24-09-2026).
- NT 06/2026 changed validations of S-1200, S-2190, S-2299 and S-2500 —
  [Rolmyjun, eSocial 2026](https://rolmyjuncontabilidade.com.br/financas/obrigacoes-trabalhistas/esocial/);
  event table and deadlines — [Rolmyjun, eventos](https://rolmyjuncontabilidade.com.br/financas/obrigacoes-trabalhistas/eventos-esocial/).
- S-2200 deadline (day before the start of work) and required fields —
  [Senior, leiaute S-2200](https://documentacao.senior.com.br/gestao-de-pessoas-hcm/esocial/leiautes/nao-periodicos/s-2200.htm);
  CPF as the mandatory worker identifier, matrícula consistent across events —
  [TecnoSpeed](https://atendimento.tecnospeed.com.br/hc/pt-br/articles/27165521606551-S-2200-Cadastramento-Inicial-do-V%C3%ADnculo-e-Admiss%C3%A3o-Ingresso-de-Trabalhador).
- S-2230 covers every Tabela 18 motive, including férias —
  [Senior, leiaute S-2230](https://documentacao.senior.com.br/gestao-de-pessoas-hcm/esocial/leiautes/nao-periodicos/s-2230.htm).
- Payroll closing feeds DCTFWeb and FGTS Digital —
  [Keevo](https://keevo.com.br/blog-ec/folha-de-pagamento-esocial/);
  FGTS Digital due on the 20th —
  [Escola Superior ESN](https://escolasuperioresn.com.br/fgts-digital-2026-guia-completo-funcionamento/).
- People-cost components that a later module can compute without payroll —
  [Valor Final](https://valorfinal.com.br/guia/custo-funcionario).
- The market keeps folha in an ERP and integrates people tools with it; Gupy quotes up to 43 days
  for a payroll integration — [Gupy developers](https://developers.gupy.io/docs/integra%C3%A7%C3%B5es-com-folha-de-pagamento),
  [Portal Software](https://portalsoftware.com.br/blog/gupy-ou-solides-qual-software-escolher-para-rh).

Related: [ADR-0005](0005-bitemporal-employment-versions.md) (the history the events come from),
[ADR-0010](0010-transactional-outbox-signed-webhooks.md) (delivery), [brief](../brief.md) (no-gos),
[TDD-0001](../tdd/0001-v1-architecture.md) (identifiers, checklist and CSV columns).

**What would reverse this decision:** a dedicated team and funding to run payroll as a product, or
a payroll partner that requires Sunex to deliver signed eSocial XML. Either needs a new ADR that
supersedes this one; neither is expected.
