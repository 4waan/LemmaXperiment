# bridge: keep the release manifest with each purchase

**Open after:** `bridge/apply-and-verify` (P11), with the payment work's `lemma_buy_resolution` merges.
**Lane:** non-chain, touches the payment seam.

## Problem

Apply and verify need a purchase's release manifest: for its capability when the purchase was not previewed here, for the profile check, and for the acceptance recipe. The bridge fetches it by digest and caches it. When the server no longer has it (a dev server was swapped for another, or the release was removed), the purchase is left out and the answer says there is no purchase, which is misleading.

## Proposal

- Fetch and store the manifest when the delivery is stored (`inbox.put`, used by the paid tool and by recovery), in the same step, so every stored purchase has one.
- Answer a purchase whose manifest is missing with its own text, naming what to do.

## Done when

- A purchase stored while the server had its release keeps working after the server loses it.
- A purchase with no manifest gets a specific answer, not "no purchased resolution".
