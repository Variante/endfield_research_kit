# FindTarget Empty-Payload Boundary Source Graph Recovery - 2026-07-03

## Scope

The source graph now records the selector replay audit's empty-payload probe
successes for FindTarget selector formatter candidates. This is narrow evidence:
it shows selected formatter candidates accept an empty payload in replay probes,
but it does not prove a full TargetSettings boundary or chain-safe consumption
to a known end offset.

## Graph Evidence Added

New searchable node kinds:

- `findtarget_selector_boundary_probe`
- `findtarget_selector_payload_boundary`
- `findtarget_chain_consumption_verdict`

New evidence edge kinds:

- `findtarget_boundary_probe_matches_shape`
- `findtarget_boundary_probe_uses_selector_tag`
- `findtarget_boundary_probe_calls_formatter`
- `findtarget_selector_candidate_has_boundary_probe`
- `findtarget_boundary_probe_accepts_payload`
- `findtarget_chain_consumption_blocked_by`

The graph intentionally does not emit `findtarget_targetsettings_boundary_exact_end`
or `findtarget_chain_consumption_safe` edges for this slice because the replay
evidence does not establish either condition.

## Validation Counts

Focused validation used a temporary graph with FindTarget selector payload,
replay, and boundary audit ingestion only.

Node counts:

- `findtarget_selector_candidate`: 27
- `findtarget_selector_replay_shape`: 7
- `findtarget_selector_boundary_shape`: 7
- `findtarget_selector_boundary_probe`: 5
- `findtarget_selector_payload_boundary`: 4
- `findtarget_chain_consumption_verdict`: 2
- `findtarget_ambiguous_record`: 30

Edge counts:

- `findtarget_selector_simplest_probe_candidate`: 8
- `findtarget_boundary_probe_matches_shape`: 5
- `findtarget_boundary_probe_uses_selector_tag`: 5
- `findtarget_boundary_probe_calls_formatter`: 5
- `findtarget_selector_candidate_has_boundary_probe`: 5
- `findtarget_boundary_probe_accepts_payload`: 5
- `findtarget_chain_consumption_blocked_by`: 12
- `findtarget_targetsettings_boundary_exact_end`: 0
- `findtarget_chain_consumption_safe`: 0
- `findtarget_ambiguous_record_split_status`: 30

## Accepted Empty-Payload Candidates

- `finder:0x0009:Core_Selector_MainTargetFinder_Data`: 2 probes
- `finder:0x0007:Core_Selector_InFightEnemyFinder_Data`: 1 probe
- `finder:0x0001:Core_Selector_CharacterTeamFinder_Data`: 1 probe
- `postProcessor:0x0001:Core_Selector_ConvertToPosition_Data`: 1 probe

## Blocking Verdicts

- 5 probe instances are blocked by `not-chain-safe:zero-validator-tag`.
- 7 replay shapes are blocked by
  `not-proven: selector formatter payloads are not consumed to a known end offset`.

All 30 ambiguous FindTarget records remain marked with split status evidence.
This graph slice is useful for querying the first concrete empty-payload selector
boundary successes, but future TargetSettings recovery still needs proof that
the surrounding chain consumes to an exact record end.
