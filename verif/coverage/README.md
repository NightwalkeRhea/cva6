# Milestone 3: golden RTL coverage

This experiment runs a small mixed bare-metal corpus on the golden `cv32a65x`
RTL with Verilator line coverage enabled. Full-core toggle coverage was measured
as impractical on the local machine (about 2.5 GB and multiple minutes for an
approximately 1,100-cycle test), so toggle coverage is deferred until after
module shortlisting. RTL coverage is not structural fault coverage.

Run from the `milestone3-rtl-coverage` branch:

```bash
source ~/.bashrc
cva6-research-env
cd /home/nightwalkerhea/testingResearch/ricerca/cva6
verif/coverage/run_milestone3.sh
```

To reuse an already-built coverage-enabled simulator, set
`CVA6_COVERAGE_SKIP_BUILD=1`.

Results are written below `fi-results/milestone3-coverage/`. The merged LCOV
file is `merged.info`, the native Verilator database is `merged.dat`, and
annotated RTL source files are under `annotated/`.
The per-source summary used for initial module shortlisting is
`module-line-coverage.csv`.
