---
# How to use this template:
# 1. Copy this file to docs/adr/NNNN-kebab-case-title.md, where NNNN is the next free number.
# 2. Fill every section; delete the guidance in italics. Keep the section order.
# 3. Open it as `status: proposed` in the pull request that needs the decision; the merge
#    makes it `accepted`. To change an accepted decision, write a new ADR that supersedes it
#    and set this one to `superseded by ADR-NNNN` (see ADR-0001).
status: proposed # proposed | accepted | deprecated | superseded by ADR-NNNN
date: YYYY-MM-DD # when the status last changed
decision-makers: Augusto Henriques
consulted: # people or sources asked for input (two-way)
informed: # people kept up to date (one-way)
---

# ADR-NNNN: {short title of the problem and the chosen solution}

## Context and Problem Statement

_Describe the context and the problem in two to five sentences, or as a question. Link the
TDD section, roadmap row or issue that raised it. State the forces at play: product values from
`docs/brief.md`, constraints, deadlines._

## Decision Drivers

- _{driver 1, e.g. a quality attribute or a product value}_
- _{driver 2}_
- _…_

## Considered Options

- _{title of option 1}_
- _{title of option 2}_
- _{title of option 3}_

## Decision Outcome

Chosen option: "_{title of option}_", because _{justification: which drivers it satisfies best,
which knock-out criterion the others fail}_.

### Consequences

- Good, because _{positive consequence, e.g. an improved quality attribute}_.
- Bad, because _{negative consequence, e.g. a cost, a new risk, a capability given up}_.
- Neutral, because _{a consequence that is neither, but worth knowing}_.

### Confirmation

_How compliance with this decision is checked: an architecture test, a CI job, a database
constraint, a review checklist item. A decision nobody can check is a wish._

## Pros and Cons of the Options

### {title of option 1}

_{description or link to more information}_

- Good, because _{argument}_.
- Neutral, because _{argument}_.
- Bad, because _{argument}_.

### {title of option 2}

- Good, because _{argument}_.
- Bad, because _{argument}_.

## More Information

_Related ADRs, the TDD section that implements the decision, the evidence consulted (public
URLs only), and the conditions that would make us revisit the decision._
