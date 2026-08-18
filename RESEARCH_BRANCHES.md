# Local CVA6 research branches

This checkout uses ordinary Git branches, not worktrees.

## Branches

- `golden-a3dc2c5e` points at the untouched upstream baseline commit
  `a3dc2c5e7835b25dc8437eee3e956ab12857ead7`.
- `local-fault-injection` contains the directed `2 + 3` ALU stuck-at fault and
  its bare-metal probe.

The intended CVA6 configuration for these experiments is `cv32a65x`.

## Switching safely

First check that the current branch is clean:

```bash
cd /home/nightwalkerhea/testingResearch/ricerca/cva6
git status --short --branch
```

Switch to the untouched design:

```bash
git switch golden-a3dc2c5e
```

Switch to the fault-injected design:

```bash
git switch local-fault-injection
```

Switch back to the branch used immediately before the current one:

```bash
git switch -
```

Show both recovery points:

```bash
git log --oneline --decorate --all --max-count=12
```

The generated `fi-results/` directory is intentionally ignored only in this
local clone through `.git/info/exclude`. It remains on disk when branches are
switched, but is not committed.
