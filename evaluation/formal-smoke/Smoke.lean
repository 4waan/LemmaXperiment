/-!
Evaluator smoke project for evaluation-formal.yml. It exercises the frozen
Lean procedure (toolchain pin, `lake build`, `#print axioms`, `leanchecker`)
on a theorem with the shape the policy expects from a candidate: a cached
lookup refines the uncached function under an explicit invariant. It is not
evidence about any candidate.
-/

namespace Smoke

/-- The cache invariant: anything the cache holds is what the uncached
resolver returns for that key. -/
def Sound (f : Nat → Nat) (cache : Nat → Option Nat) : Prop :=
  ∀ k v, cache k = some v → v = f k

/-- Resolution through the cache: a hit is served, a miss falls back. -/
def resolve (f : Nat → Nat) (cache : Nat → Option Nat) (k : Nat) : Nat :=
  (cache k).getD (f k)

/-- Under the invariant, resolving through the cache equals resolving without it. -/
theorem resolve_refines (f : Nat → Nat) (cache : Nat → Option Nat)
    (h : Sound f cache) (k : Nat) : resolve f cache k = f k := by
  unfold resolve
  cases hc : cache k with
  | none => rfl
  | some v => exact h k v hc

/-- The empty cache satisfies the invariant. -/
theorem empty_sound (f : Nat → Nat) : Sound f (fun _ => none) := by
  intro k v h
  cases h

end Smoke
