<?php

use Illuminate\Console\Command;
use Illuminate\Support\ServiceProvider;

/*
| Official Pest presets. The Laravel preset assumes the framework's default
| layout (models in App\Models, enums in App\Enums, ...), which domain contexts
| deliberately break, so App\Domain is held to the rules in DomainBoundariesTest instead.
| The strict preset is not used: it demands final classes and strict_types,
| which the framework's own code and generators do not follow.
*/

arch()->preset()->php();

arch()->preset()->security();

arch()->preset()->laravel()->ignoring('App\Domain');

// ignoring() drops every Laravel preset rule for App\Domain, not only the two
// layout rules it breaks (enums outside App\Enums, models outside App\Models).
// These put back the ones domain code must still follow; mailables, notifications
// and exceptions may live in the context that owns them. FormRequests are banned
// with the rest of the delivery layer in DomainBoundariesTest.
arch('domain code has no debug, exit or env calls')
    ->expect('App\Domain')
    ->not->toUse(['dd', 'ddd', 'dump', 'env', 'exit', 'ray']);

arch('domain code declares no console commands')
    ->expect('App\Domain')
    ->not->toExtend(Command::class);

arch('domain code declares no service providers')
    ->expect('App\Domain')
    ->not->toExtend(ServiceProvider::class)
    ->not->toHaveSuffix('ServiceProvider');

arch('domain code declares no controllers')
    ->expect('App\Domain')
    ->not->toHaveSuffix('Controller');
