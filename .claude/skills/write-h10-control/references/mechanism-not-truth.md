# Mutate the mechanism, never the ground truth

A check compares something the pipeline PRODUCED (the mechanism) against something the pipeline READ (the truth). A control that mutates the truth changes both sides of the ratio and proves nothing.

| check | mechanism (mutate this) | truth (never mutate) | what went wrong before |
|---|---|---|---|
| check4b capture | node text in docgraph | inventory / geometry lines | first control deleted `ref` rows: ratio stayed 100% |
| check7 refs | `ref.target` | citation text in the source | — |
| check33b completeness | the assembler's bundle (hops, budget) | `dependencies()` set | the original check unioned truth into mechanism: 100.0000% identically |
| check31 evalset | question text | target provisions | gate read the `kind` label, not measured overlap |
| check24 MR1 | node text per page | page text per page | corpus-wide multiset with 71% surplus: 100% blanking read as 0.14% |

Parameter mutations (`hops=0`, `budget=200`) are the cleanest: they cannot touch the truth at all.

Any corpus-wide aggregate where one side has surplus is vacuous. Compare per unit (per page, per node) so the surplus leaves the denominator.
