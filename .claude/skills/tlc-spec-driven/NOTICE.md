# Notice: vendored third-party skill

This directory is a verbatim copy of the `tlc-spec-driven` skill from the Tech Leads Club agent-skills catalog. Sunex did not modify any file in it; Sunex-specific behaviour lives in `sunex-ship-cycle`, which tells the skill where Sunex keeps its files and which steps it overrides.

| | |
|---|---|
| Upstream | https://github.com/tech-leads-club/agent-skills |
| Path | `packages/skills-catalog/skills/(development)/tlc-spec-driven` |
| Commit | `916a86748ff5600a86839007cca7bed8da19d462` (2026-08-03) |
| Skill version | 3.3.0 |
| Author | Felipe Rodrigues (github.com/felipfr) and Tech Leads Club contributors |
| Tree hash | `359e7d676f63af45fd14a427664ae0ae3d23a7496b1970ab5c620655ff6835f3` (see below) |

## Licences

- `SKILL.md` and `references/*.md` are licensed under the Creative Commons Attribution 4.0 International licence (CC-BY-4.0), as declared in the skill's front matter and in the upstream `LICENSE` note on dual licensing. Licence text: https://creativecommons.org/licenses/by/4.0/legalcode
- `scripts/*.py` are source code from the same repository, licensed under the MIT licence:

```text
MIT License

Copyright (c) 2026 Tech Leads Club

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

Both licences allow redistribution inside an AGPL-3.0 repository. The vendored files keep their own licences; the AGPL-3.0 licence of the rest of Sunex does not relicense them.

## Updating

1. Download the upstream directory at the new commit into a scratch folder.
2. Read the upstream diff completely; reject the update if it changes the execution contract in a way `sunex-ship-cycle` does not handle.
3. Replace every file here except this notice, then update the commit, version and tree hash above.
4. Recompute the tree hash from this directory, excluding this notice:

```bash
cd .claude/skills/tlc-spec-driven && find . -type f ! -name NOTICE.md | sort | xargs sha256sum | sha256sum
```
