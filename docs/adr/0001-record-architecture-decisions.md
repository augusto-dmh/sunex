---
status: accepted
date: 2026-10-02
decision-makers: Augusto Henriques
consulted:
informed:
---

# ADR-0001: Record architecture decisions as MADR files in the repository

## Context and Problem Statement

Sunex is public from its first commit and is built in small pull requests, many of them written
by coding agents working in parallel worktrees. Every one of those contributors, human or agent,
arrives without the conversation in which a choice was made. Without a written record they either
re-open settled questions (wasting a cycle) or silently contradict them (breaking an invariant).
Reviewers of the repository also judge it by how decisions were reached, not only by the code.

Where and in what form do we record decisions so that each is findable, reviewable in a pull
request, and impossible to change silently?

## Decision Drivers

- Decisions must be reviewable in the same pull request as the code that depends on them.
- A new contributor (or a fresh-context agent) must find the reason for a choice in one place.
- Accepted decisions must not drift: changing one has to be an explicit, visible act.
- Three levels of decision exist and need different homes: durable architecture, design detail
  for one phase, and small choices taken inside a delivery cycle.
- Low ceremony: a solo maintainer with a 12-week appetite cannot afford a process that slows
  every pull request.

## Considered Options

- No written records (decisions live in commit messages and pull request bodies)
- A wiki outside the repository
- Michael Nygard's original ADR format in the repository
- MADR 4 files in `docs/adr/` (chosen)
- RFC documents only, no ADRs

## Decision Outcome

Chosen option: "MADR 4 files in `docs/adr/`", because MADR keeps Nygard's one-decision-per-file
discipline and adds the two sections a reviewer needs most: the options that were considered with
their pros and cons, and how compliance is confirmed.

Rules:

1. One file per decision: `docs/adr/NNNN-kebab-case-title.md`, numbered sequentially, copied from
   [`0000-template.md`](0000-template.md).
2. Status is one of `proposed`, `accepted`, `deprecated` or `superseded by ADR-NNNN`. A proposal
   is accepted when the pull request that contains it merges.
3. **An accepted decision's outcome is never edited.** Typos and added links are fine. To change
   the decision, write a new ADR that supersedes it and update the old one's status only.
4. Each decision has exactly one home:
   - **ADR** (`docs/adr/`): durable, cross-cutting decisions that constrain future work: stack,
     invariants, boundaries, process, license.
   - **TDD** (`docs/tdd/`): how a phase is designed (tables, flows, algorithms). A TDD cites ADRs;
     it does not re-decide them.
   - **`AD-NNN` rows** in `.specs/project/STATE.md`: choices taken while planning or building one
     roadmap row (a column name, a library option, a sequencing call), each with options,
     choice and rationale. An `AD` row that turns out to constrain other rows is promoted to an ADR.
5. Every ADR names the conditions that would reverse it, so the next reader knows what evidence
   would justify a superseding ADR.
6. ADRs cite public sources only, because the repository is public.

### Consequences

- Good, because the reasoning for every invariant (bitemporal versions, one policy function,
  agents as principals, the outbox) sits next to the code and is reviewed with it.
- Good, because fresh-context agents can be told "read the ADR" instead of being briefed by hand.
- Good, because "supersede, never edit" leaves a history of how the design evolved.
- Bad, because writing an ADR costs time on each significant choice; the three-level split keeps
  that cost on the decisions that deserve it.
- Neutral, because MADR is a convention, not a tool: nothing generates or validates the files.

### Confirmation

- The pull request template and the review step check that a change contradicting an accepted
  ADR ships with a superseding ADR.
- Reviewers reject edits to the "Decision Outcome" of an accepted ADR.
- `AGENTS.md` / `CLAUDE.md` tell agents to read the relevant ADR before changing an area.

## Pros and Cons of the Options

### No written records

- Good, because there is no overhead.
- Bad, because commit messages describe changes, not the alternatives rejected; the reasoning is
  scattered and unsearchable.
- Bad, because parallel agents cannot read a conversation that happened elsewhere.

### A wiki outside the repository

- Good, because it is easy to edit and link.
- Bad, because it is not versioned with the code and not reviewed in pull requests; it drifts.
- Bad, because the repository's history stops telling the whole story.

### Nygard ADRs in the repository

- Good, because the format is minimal and well known
  ([Nygard, 2011](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)).
- Bad, because it has no explicit place for the considered options and their trade-offs, which
  is the part a reviewer most wants to see.

### MADR 4 in `docs/adr/`

- Good, because it structures options, pros and cons, consequences and confirmation
  ([MADR](https://adr.github.io/madr/)).
- Good, because it is plain Markdown, rendered by GitHub, diffable in pull requests.
- Bad, because the template is longer than Nygard's; short decisions leave sections thin.

### RFC documents only

- Good, because RFCs suit open proposals that need discussion.
- Bad, because an RFC records a proposal, not an accepted state; readers cannot tell what is
  binding today. Sunex may still use an RFC for a large open proposal, ending in an ADR.

## More Information

- Template: [0000-template.md](0000-template.md).
- Reviewers of senior engineering work look for "Design documents and technical specifications,
  Architecture diagrams showing decision-making, Trade-off analysis in technical choices"
  ([whatisthesalary.com](https://whatisthesalary.com/guides/software-engineer-portfolio/)).
- Related: [ADR-0013](0013-delivery-process-ship-cycle.md) (where `AD-NNN` rows are written during
  a cycle).
- Revisit if the number of ADRs makes the index hard to navigate (then add a generated index) or
  if a team grows large enough to need a formal RFC stage before ADRs.
