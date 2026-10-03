<?php

use Symfony\Component\Process\Process;

function checkCommitMessage(string $message): Process
{
    $process = new Process(['sh', 'scripts/check-commit-msg.sh', '-'], dirname(__DIR__, 3));
    $process->setInput($message);
    $process->run();

    return $process;
}

it('accepts conventional commits with an allowed scope and the Assisted-by trailer', function (string $message) {
    $process = checkCommitMessage($message);

    expect($process->getExitCode())->toBe(0, $process->getErrorOutput());
})->with([
    'no scope' => "chore: update dependencies\n",
    'context scope' => "feat(absence): split férias into up to three periods\n\nWhy it matters.\n\nAssisted-by: Claude Code\n",
    'documentation scope' => "docs(adr): record the decision to keep payroll out\n",
    'context scope named as the context' => "feat(organization): add companies\n",
    'specs scope' => "docs(specs): add the vacation spec\n",
    'harness scope' => "fix(skills): stop the ship cycle on a verifier failure\n",
    'breaking change' => "refactor(people)!: rename the employment reader\n",
    'leading digit' => "chore(deps): 2 packages need a newer php\n",
    'merge commit' => "Merge branch 'main' into feat/people\n",
    'pull request merge commit' => "Merge pull request #12 from augusto-dmh/feat/people\n\nfeat(people): add persons\n",
    'git revert' => "Revert \"feat(org): add positions\"\n",
    'regenerated in the body' => "fix(deps): complete the lockfile\n\nRegenerated with npm 11.\n",
    'generated files described in the body' => "fix(deps): complete the lockfile\n\nThe lock was generated with npm 11, and the helpers\nare auto-generated with wayfinder:generate.\n",
    '72 characters with accents' => 'feat(absence): f'.str_repeat('é', 56)."\n",
]);

it('rejects messages that break the convention', function (string $message, string $reason) {
    $process = checkCommitMessage($message);

    expect($process->getExitCode())->toBe(1)
        ->and($process->getErrorOutput())->toContain($reason);
})->with([
    'missing type' => ["update dependencies\n", "'<type>(<scope>): <lowercase summary>'"],
    'unknown type' => ["feature(people): add persons\n", "'<type>(<scope>): <lowercase summary>'"],
    'unknown scope' => ["feat(payroll): calculate salaries\n", "'<type>(<scope>): <lowercase summary>'"],
    'abbreviated context scope' => ["feat(org): add companies\n", "'<type>(<scope>): <lowercase summary>'"],
    'capitalised summary' => ["feat(people): Add persons\n", "'<type>(<scope>): <lowercase summary>'"],
    'accented first letter' => ["feat(absence): édit férias\n", "'<type>(<scope>): <lowercase summary>'"],
    'header over 72 characters' => ['feat(people): '.str_repeat('a', 59)."\n", 'the limit is 72'],
    'merge-shaped header git did not write' => ["Merge everything I changed today into one commit\n", "'<type>(<scope>): <lowercase summary>'"],
    'merge commit with a tool co-author' => ["Merge branch 'main' into feat/people\n\nCo-Authored-By: Someone <a@b.c>\n", 'forbidden trailer'],
    'revert with a tool co-author' => ["Revert \"feat(people): add persons\"\n\nCo-Authored-By: Someone <a@b.c>\n", 'forbidden trailer'],
    'co-authored-by trailer' => ["feat(people): add persons\n\nCo-Authored-By: Someone <a@b.c>\n", 'forbidden trailer'],
    'signed-off-by trailer' => ["feat(people): add persons\n\nSigned-off-by: Someone <a@b.c>\n", 'forbidden trailer'],
    'generated-with footer' => ["feat(people): add persons\n\nGenerated with a tool\n", 'forbidden trailer'],
    'generated-with footer after an emoji' => ["feat(people): add persons\n\n🤖 Generated with [a tool](https://example.com)\n", 'forbidden trailer'],
]);
