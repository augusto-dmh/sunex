# Changelog

All notable changes to Sunex are recorded here. The format follows
[Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html). Until v1.0.0 the public surface
(HTTP routes, webhook payloads, MCP tools) may change between minor versions; every such change is
listed under **Changed** with a migration note.

## [Unreleased]

### Added

- Foundation documents: README, architecture overview, product brief, technical design document
  for v1 (TDD-0001), architecture decision records 0001–0014, roadmap with PR-sized rows and
  parallel-safe groups, project state log, contributor and security policies.
- Project guidance for coding agents in `.ai/guidelines/`, rendered into `AGENTS.md` and
  `CLAUDE.md` by Laravel Boost.
- AGPL-3.0-only license.
- Laravel 13 application scaffold from the official installer (Vue starter kit, Pest, PostgreSQL,
  Boost), committed unchanged.
