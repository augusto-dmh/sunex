# Domain

Business rules live here, one namespace per bounded context (`App\Domain\<Context>`).
[ARCHITECTURE.md](../../ARCHITECTURE.md) is the map and
[ADR-0004](../../docs/adr/0004-domain-namespaces-with-architecture-tests.md) the reasoning.
Where this summary and ARCHITECTURE.md disagree, ARCHITECTURE.md wins.

| Context                                | Owns                                                         | May depend on                |
| -------------------------------------- | ------------------------------------------------------------ | ---------------------------- |
| [Shared](Shared/README.md)             | Identifiers, dates, access control, approvals, audit, outbox | the framework only           |
| [Organization](Organization/README.md) | Companies, establishments, org units, positions              | Shared                       |
| [People](People/README.md)             | Persons, employments, bitemporal employment versions         | Organization, Shared         |
| [Movements](Movements/README.md)       | Movement requests and their approval                         | People, Organization, Shared |
| [Absence](Absence/README.md)           | Férias and afastamentos under the CLT                        | People, Organization, Shared |
| [Agents](Agents/README.md)             | AI agents as accountable principals, and their tools         | all of the above             |

`tests/Arch/DomainBoundariesTest.php` enforces that:

- domain code never depends on the delivery layer (`Illuminate\Http`, routing, Inertia,
  `App\Http`);
- a context uses only the contexts it may depend on, and only through their `Contracts` and
  `Events` namespaces.
