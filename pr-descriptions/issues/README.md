# Follow-up issues

Drafts to open on GitHub as the PRs they depend on are reviewed and merged. Each file is one issue: its title is the first line, and it names the PR it waits for.

| # | Issue | Open after | Lane |
| --- | --- | --- | --- |
| 01 | [bridge: run acceptance tests on the Node major the package pins](01-bridge-acceptance-on-pinned-node.md) | `bridge/apply-and-verify` (P11) | non-chain |
| 02 | [bridge: package managers behind version-manager shims](02-bridge-version-manager-shims.md) | `bridge/apply-and-verify` (P11) | non-chain |
| 03 | [bridge: keep the release manifest with each purchase](03-bridge-store-release-with-purchase.md) | `bridge/apply-and-verify` (P11), with the payment work's `lemma_buy_resolution` | non-chain, touches the payment seam |
| 04 | [bridge: recognise a moved repository by its history](04-bridge-repository-identity.md) | `bridge/apply-and-verify` (P11) | non-chain |
| 05 | [bridge: exact liveness for journal holders in other namespaces](05-bridge-exact-liveness-across-namespaces.md) | `bridge/apply-and-verify` (P11) | non-chain |
| 06 | [bridge: stop installs when the bridge is killed](06-bridge-installs-die-with-the-bridge.md) | `bridge/apply-and-verify` (P11) | non-chain |
| 07 | [bridge: fewer release-chosen words in agent answers](07-bridge-release-words-in-answers.md) | `bridge/apply-and-verify` (P11) | non-chain |
| 08 | [bridge: confine acceptance runs beyond the network](08-bridge-acceptance-sandbox.md) | `bridge/apply-and-verify` (P11) | non-chain |
| 09 | [bridge scan: range-check dist-tag specifiers](09-bridge-dist-tag-specifiers.md) | `bridge/scan-and-tools` (P9) | non-chain |
| 10 | [benchmark: find the Cursor key in any of the user's shells](10-benchmark-credential-check-other-shells.md) | `benchmark/harness-and-probe` (P10) | non-chain |
| 11 | [benchmark: runs whose agent id the provider never recognises](11-benchmark-unrecognised-agent-ids.md) | `benchmark/harness-and-probe` (P10) | non-chain |
| 12 | [benchmark: first probe run with a real draft bundle](12-benchmark-probe-with-draft-bundle.md) | `benchmark/harness-and-probe` (P10), with a draft bundle from the payment work (HANDOFF ask 8) | non-chain, waits on the payment work |
| 13 | [catalog: check public evidence against frozen benchmark reports](13-catalog-evidence-against-frozen-reports.md) | `catalog/loader-and-fixtures` (P6), after the first frozen benchmark | non-chain |
| 14 | [catalog: measured chain cost and price floor](14-catalog-economics.md) | `catalog/loader-and-fixtures` (P6), with HANDOFF item 4 | waits on the payment work |
| 15 | [web: benchmark evidence and payment panes](15-dashboard-evidence-and-payment-panes.md) | `web/read-models-dashboard` (P12) | non-chain for evidence; payment panes belong to the payment work |
| 16 | [server: demand counts that one prober cannot inflate](16-server-demand-sybil-resistance.md) | `server/persistence-and-resolution-service` (P8) | non-chain |
| 17 | [Tracking: payment work handoff asks](17-payment-work-handoff.md) | when the payment work starts | payment work |
