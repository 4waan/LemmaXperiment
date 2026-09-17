# candidate/

Owner: creator agent. Populated during the creation run; empty until then.

Nothing in this directory may be human-written without an entry in the
intervention log. Reused code needs attribution in `compositionManifest`.

## Expected contents

```text
candidate/
  module/            the reusable module (Rust)
  adapter/           integration with the pinned RSP/SP1 insertion point
  tests/             public correctness checks the agent used locally
  build/             reproducible build recipe and guest key derivation
  manifest.json      asset manifest, see below
```

## Asset manifest fields

```text
candidateId, demandId, sourceCommit, artifactDigest
moduleInterface, compatibilityManifest
reproducibleBuildRecipe, guestProgramKey
dependencyVersions, dependencyLicenses
originalContributions, compositionManifest
theoremStatements, leanToolchain, axiomReport
modelToImplementationMap, knownFormalGaps
publicCheckResults, developmentBenchmarkReport
integrationInstructions, contributorPayee
licenseReference, agreedUsageTerms
agentRunManifestHash, humanInterventionLogHash
```

`guestProgramKey` is the evaluator-derived key of the settlement guest built
with the candidate feature. The rsp-client key is diagnostic and cannot settle
the reuse escrow.

## States

- candidate: submitted, not yet evaluated
- accepted asset: passed evaluation, registered in ModuleRegistry
- adopted asset: a later job used the unchanged accepted version
