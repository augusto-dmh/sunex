## Description

<!-- What this PR changes and why, in two to four sentences an outside reader can follow. -->

## Context

<!-- The problem or roadmap item behind the change, and what was true before it. Link public sources (Laravel docs, CLT articles on planalto.gov.br, eSocial manuals) instead of internal notes. -->

## Architecture

<!-- Where the change sits: domain namespaces touched, new classes and their responsibilities, data flow, migrations and constraints. A short diagram is welcome. Write "No architectural change." when that is true. -->

## Main changes

<!-- Bulleted list of the meaningful changes, grouped by area. One line each. -->

## Decisions

<!-- One entry per decision taken while building this: the options considered, why-yes and why-not for each, and the option chosen. Write "None beyond the existing ADRs." when that is true. -->

## Tests

<!-- What is tested and how: new Pest tests and what they assert, architecture tests, browser tests, and the gate commands run with their results. -->

## Configuration

<!-- New or changed environment variables, config keys, queues, scheduled tasks or services. Write "None." when nothing changes. -->

## Dependencies

<!-- Composer or npm packages added, removed or upgraded, with the reason and licence. Write "None." when nothing changes. -->

## Impact

<!-- Who or what is affected: data migrations, breaking changes, performance, security and privacy surface, follow-up work this enables or requires. -->

## How to validate

<!-- Exact steps a reviewer can run locally: commands, seed data, pages to open, expected results. -->

## Checklist

- [ ] Conventional Commit title, atomic commits, each with a body that explains why and `Assisted-by: Claude Code` as its only trailer when an assistant helped
- [ ] Every new behaviour has a test; gates are green (lint, static analysis, refactor check, tests, frontend type check and build)
- [ ] Authorization goes through policies; no sensitive field reaches an Inertia prop unmasked
- [ ] Migrations are reversible and constraints live in the database
- [ ] Clean-room check passed on the branch
- [ ] No internal planning IDs in commits or in this description

## AI assistance

<!-- What the agent wrote (code, tests, docs, this description) and what a human reviewed, run or changed. Be specific. -->
