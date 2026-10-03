<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

/**
 * Enables the PostgreSQL extensions the domain model depends on:
 * - vector: embeddings for policy search by the in-app agents (pgvector).
 * - btree_gist: lets exclusion constraints mix equality on scalar columns with
 *   overlap on date ranges, so overlapping employment versions or absence periods
 *   for the same person are rejected by the database itself.
 *
 * btree_gist is a trusted extension, so a role with CREATE on the database can
 * enable it. vector is not: the migrating role must be a superuser (as the
 * Compose and CI databases' owner is), or a superuser must run
 * `create extension vector;` beforehand in every database, the test one included.
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::ensureVectorExtensionExists();
        Schema::ensureExtensionExists('btree_gist');
    }

    public function down(): void
    {
        // No CASCADE: rolling back must fail loudly while a column or constraint still uses them.
        DB::statement('drop extension if exists btree_gist');
        DB::statement('drop extension if exists vector');
    }
};
