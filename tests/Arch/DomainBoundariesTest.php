<?php

/*
| Domain boundaries (ARCHITECTURE.md, ADR-0004). Contexts are listed from the
| bottom up; each may depend only on the contexts below it, and only through
| their Contracts and Events namespaces. Models, actions and other classes stay
| private to the context that owns them.
|
| Shared is the shared kernel: ARCHITECTURE.md names the Authorizer, the
| approval engine, the outbox and the value objects as its public surface, and
| TDD-0001 places them in the namespaces below, so every context may use those.
*/

const DOMAIN_CONTEXTS = [
    'Shared' => [],
    'Organization' => ['Shared'],
    'People' => ['Organization', 'Shared'],
    'Movements' => ['People', 'Organization', 'Shared'],
    'Absence' => ['People', 'Organization', 'Shared'],
    'Agents' => ['Absence', 'Movements', 'People', 'Organization', 'Shared'],
];

const PUBLIC_NAMESPACES = ['Contracts', 'Events'];

const SHARED_KERNEL_NAMESPACES = ['Access', 'Approvals', 'Audit', 'Identifiers', 'Integration', 'Time'];

arch('domain code does not depend on the delivery layer')
    ->expect('App\Domain')
    ->not->toUse([
        'Illuminate\Http',
        'Illuminate\Routing',
        'Inertia',
        'App\Http',
    ]);

/**
 * @return array<string, array{string, string, bool}>
 */
function contextPairs(): array
{
    $pairs = [];

    foreach (DOMAIN_CONTEXTS as $context => $allowed) {
        foreach (array_keys(DOMAIN_CONTEXTS) as $other) {
            if ($other !== $context) {
                $pairs["{$context} -> {$other}"] = [$context, $other, in_array($other, $allowed, true)];
            }
        }
    }

    return $pairs;
}

test('a context reaches another only when the dependency table allows it, and only through its public surface', function (string $context, string $other, bool $allowed) {
    $expectation = expect("App\\Domain\\{$context}")->not->toUse("App\\Domain\\{$other}");

    if ($allowed) {
        $public = $other === 'Shared' ? [...PUBLIC_NAMESPACES, ...SHARED_KERNEL_NAMESPACES] : PUBLIC_NAMESPACES;

        $expectation->ignoring(array_map(fn (string $namespace): string => "App\\Domain\\{$other}\\{$namespace}", $public));
    }
})->with(contextPairs());
