---
status: accepted
date: 2026-10-02
decision-makers: Augusto Henriques
consulted: research notes on open-source HR systems and their licenses
informed:
---

# ADR-0014: License Sunex under AGPL-3.0-only and develop it in public

## Context and Problem Statement

Sunex is meant to be read, run and self-hosted by anyone, and its commit history, ADRs and pull
requests are part of its value as public evidence of engineering work. An HR application is also
exactly the kind of software someone could take, host as a closed SaaS and sell without giving
anything back.

Under which license do we publish, and from when is the repository public?

## Decision Drivers

- Anyone may read, run, modify and self-host Sunex.
- A hosted, modified version offered to users over a network must share its changes.
- The license must be OSI-approved, so "open source" is literally true.
- The history must be public from the first commit, because the history is evidence.
- The author keeps control over whether future license versions apply.

## Considered Options

- MIT
- Apache-2.0
- GPL-3.0
- AGPL-3.0 (chosen, in its `-only` form)
- Source-available (Elastic License 2.0, Business Source License)

## Decision Outcome

Chosen option: "AGPL-3.0-only", because it is the OSI-approved license that closes the hosted
closed-fork path: anyone offering a modified Sunex to users over a network must publish their
changes under the same terms.

- **`-only`, not `-or-later`**: future versions of the AGPL are written by the FSF; choosing
  `-only` means a later version applies to Sunex only if the copyright holder decides so.
- The repository is **public on GitHub from the first commit**. The research behind the decisions
  stays private; the public reasoning is in the ADRs and the TDD, citing public sources only.
- `LICENSE` holds the copyright line (Copyright (C) 2026 Augusto Henriques) followed by the
  unmodified AGPL-3.0 text.
- Contributions are accepted under AGPL-3.0-only (stated in `CONTRIBUTING.md`); there is no
  contributor license agreement.

### Consequences

- Good, because a hosted closed fork is not a free option; improvements made by hosters come back.
- Good, because the license is familiar in self-hosted business software: Twenty CRM, Monica and
  Kimai all use AGPL-3.0 ([Twenty LICENSE](https://github.com/twentyhq/twenty/blob/main/LICENSE),
  [monicahq/monica](https://github.com/monicahq/monica), [kimai/kimai](https://github.com/kimai/kimai)).
- Bad, because some companies forbid AGPL dependencies, so Sunex will not be embedded in their
  proprietary products. That is acceptable: Sunex is an application, not a library.
- Bad, because without a CLA, relicensing later requires every contributor's consent.
- Neutral, because the scaffold's `composer.json` still declares `"license": "MIT"`; it must be
  changed to `AGPL-3.0-only` by the pull request that owns the composer files (recorded as a
  follow-up). `package.json` should carry the same identifier.

### Confirmation

- GitHub's license detection shows "AGPL-3.0" on the repository.
- The `license` field in `composer.json` and `package.json` equals `AGPL-3.0-only` (follow-up row).
- Review rejects added dependencies whose licenses are incompatible with AGPL-3.0.

## Pros and Cons of the Options

### MIT

- Good, because it is maximally permissive and frictionless for adopters.
- Bad, because anyone can host a closed, modified Sunex as a paid service and share nothing.

### Apache-2.0

- Good, because it adds an explicit patent grant to permissive terms.
- Bad, because it has the same closed-SaaS path as MIT.

### GPL-3.0

- Good, because it is copyleft for distributed copies; Frappe HR uses GPL-3.0
  ([frappe/hrms](https://github.com/frappe/hrms)).
- Bad, because offering software over a network is not distribution, so a hosted fork owes
  nothing: the gap AGPL closes.

### AGPL-3.0

- Good, because it extends copyleft to network use and is OSI-approved.
- Bad, because some organisations avoid it by policy.

### Source-available (ELv2, BSL)

- Good, because it can forbid competing hosted offerings outright.
- Bad, because it is not open source: IceHRM's Elastic License 2.0 is "not an OSI-approved
  open-source licence" and even third-party comparisons misreport it
  ([IceHRM LICENSE](https://github.com/gamonoid/icehrm/blob/master/LICENSE);
  [pistack](https://www.pistack.xyz/posts/2026-04-21-orangehrm-vs-icehrm-vs-sentrifugo-self-hosted-hrms-guide-2026/)).
  It would also contradict "anyone can read and self-host" as a product promise.

## More Information

- Comparable licenses in the HR space: Frappe HR (GPL-3.0), Odoo community (LGPL-3,
  [LICENSE](https://github.com/odoo/odoo/blob/master/LICENSE)), OrangeHRM (GPL-3.0), IceHRM (ELv2).
- Related: [ADR-0001](0001-record-architecture-decisions.md) (public ADRs cite public sources only),
  [ADR-0013](0013-delivery-process-ship-cycle.md) (public pull requests as evidence).
- Revisit if: a dual-licensing or commercial model is ever wanted (which would need a CLA from that
  point on), or if a dependency Sunex cannot avoid turns out to be AGPL-incompatible.
