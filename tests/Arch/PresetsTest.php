<?php

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
