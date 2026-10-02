# Security policy

Sunex stores personal and employment data of workers, including identifiers (CPF), salaries and
absence records. Security reports are welcome and are handled before any feature work.

## Supported versions

Sunex has not had a release yet. Until v1.0.0, only the `main` branch receives fixes. After v1.0.0,
the latest minor release receives security fixes.

## Reporting a vulnerability

Do **not** open a public issue, discussion or pull request for a vulnerability.

Report it privately through GitHub's
[private vulnerability reporting](https://github.com/augusto-dmh/sunex/security/advisories/new)
for this repository. Include:

- the affected route, MCP tool, webhook or command, and the commit you tested;
- the steps to reproduce, and what an attacker gains (data read, data changed, privilege gained);
- whether real personal data was involved (please use the seeded demo data only).

What to expect:

| Step | Target |
|---|---|
| Acknowledgement | within 3 business days |
| First assessment and severity | within 10 business days |
| Fix or mitigation for high or critical issues | as soon as possible; the advisory is published with the fix |

Reporters are credited in the advisory unless they ask not to be.

## Scope

In scope: the application in this repository, including authorization (roles, reach, field-group
masking), agent principals and their tool gateway, the MCP server and its OAuth flow, webhook
signing, and data exports.

Out of scope: denial of service by volume, findings that need a compromised administrator account,
missing hardening headers without a demonstrated impact, and third-party services.

## Design commitments

These are the security properties Sunex is designed to keep. A report that breaks one of them is a
vulnerability even if no data leaks in the demo:

- Every human, in-app agent and MCP client passes through one policy function; an agent never sees
  or does what its sponsor could not ([ADR-0006](docs/adr/0006-permission-model-roles-reach-field-groups.md),
  [ADR-0007](docs/adr/0007-agents-as-principals-one-toolset.md)).
- Masked field groups never reach the browser or a tool result.
- Every agent tool call is audited in the same database transaction as the change it caused.
- MCP access tokens are only accepted when issued for this server (RFC 8707 audience check).
- Outbound webhooks are signed with HMAC-SHA256 and a timestamp
  ([ADR-0010](docs/adr/0010-transactional-outbox-signed-webhooks.md)).
