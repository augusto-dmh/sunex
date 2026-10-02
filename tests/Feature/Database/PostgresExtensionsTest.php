<?php

use Illuminate\Database\QueryException;
use Illuminate\Support\Facades\DB;

it('runs the suite on PostgreSQL 17', function () {
    expect(DB::connection()->getDriverName())->toBe('pgsql')
        ->and((int) DB::scalar('show server_version_num'))->toBeGreaterThanOrEqual(170000);
});

it('enables the extensions the domain model depends on', function (string $extension) {
    expect(DB::table('pg_extension')->where('extname', $extension)->exists())->toBeTrue();
})->with(['vector', 'btree_gist']);

it('rejects overlapping date ranges for the same key through an exclusion constraint', function () {
    DB::statement('create temporary table range_probe (person_id bigint not null, during daterange not null, exclude using gist (person_id with =, during with &&))');
    DB::table('range_probe')->insert(['person_id' => 1, 'during' => '[2026-01-01,2026-02-01)']);
    DB::table('range_probe')->insert(['person_id' => 2, 'during' => '[2026-01-15,2026-02-15)']);

    expect(fn () => DB::table('range_probe')->insert(['person_id' => 1, 'during' => '[2026-01-15,2026-02-15)']))
        ->toThrow(QueryException::class, 'range_probe_person_id_during_excl');
});

it('stores and compares pgvector embeddings', function () {
    $distance = DB::scalar("select '[1,0,0]'::vector <=> '[0,1,0]'::vector");

    expect((float) $distance)->toBe(1.0);
});
