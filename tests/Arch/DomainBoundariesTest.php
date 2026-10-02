<?php

/*
| Domain boundaries (ARCHITECTURE.md, ADR-0004). Contexts are listed from the
| bottom up; each may depend only on the contexts below it, and only through
| their Contracts and Events namespaces. Models, actions and other classes stay
| private to the context that owns them.
*/

const DOMAIN_CONTEXTS = [
    'Shared' => [],
    'Organization' => ['Shared'],
    'People' => ['Organization', 'Shared'],
    'Movements' => ['People', 'Organization', 'Shared'],
    'Absence' => ['People', 'Organization', 'Shared'],
    'Agents' => ['Absence', 'Movements', 'People', 'Organization', 'Shared'],
];

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
        $expectation->ignoring(["App\\Domain\\{$other}\\Contracts", "App\\Domain\\{$other}\\Events"]);
    }
})->with(contextPairs());
