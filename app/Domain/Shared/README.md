# Shared

The shared kernel: Brazilian identifiers (CPF, CNPJ, CBO) as value objects, date ranges and
the clock, the access-control primitives and the one policy function every read and write
passes through, the approval engine, audit conventions, and the integration outbox with its
signed webhooks and CSV exports.

Other contexts use it through `Contracts`, `Events` and the kernel namespaces `Access`,
`Approvals`, `Audit`, `Identifiers`, `Integration` and `Time`; anything else stays private.

May depend on: the framework only. When Shared needs something a context knows (such as a
person's reach), it declares an interface here and that context implements it.
