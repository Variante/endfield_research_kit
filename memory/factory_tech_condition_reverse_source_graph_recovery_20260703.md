# Factory Tech Condition Reverse Source Graph Recovery - 2026-07-03

## Context

Factory tech condition parameters can reference authored level, item, domain,
or machine ids. The graph already emitted forward edges such as
`factory_tech_condition_references_level` and
`factory_tech_condition_references_machine`, but referenced nodes could not
directly traverse back to the conditions that used them.

## Implementation

`tools/endfield_source_graph.py` now adds reverse edges in
`add_factory_condition_parameter_refs`:

- `level_used_by_factory_tech_condition`
- `item_used_by_factory_tech_condition`
- `domain_used_by_factory_tech_condition`
- `factory_machine_used_by_factory_tech_condition`

The current export has level and machine references; item/domain reverse kinds
are present for future data with the same schema.

## Validation

Focused validation graph:

```text
factory_tech_condition_references_level 6 level_used_by_factory_tech_condition 6
factory_tech_condition_references_machine 1 factory_machine_used_by_factory_tech_condition 1
factory_tech_condition_references_item 0 item_used_by_factory_tech_condition 0
factory_tech_condition_references_domain 0 domain_used_by_factory_tech_condition 0
```

Sample reverse evidence:

```text
level:map01_lv001
  level_used_by_factory_tech_condition -> factory_tech_condition:cond_tech_group_tundra_1
  level_used_by_factory_tech_condition -> factory_tech_condition:tech_tundra_2_diffuser_connectable_1
  level_used_by_factory_tech_condition -> factory_tech_condition:tech_tundra_3_pole_supply_1

factory_machine:f1m26_q#3
  factory_machine_used_by_factory_tech_condition -> factory_tech_condition:tech_tundra_2_field_1
```

CLI smoke queries:

```bat
python tools\endfield_source_graph.py query map01_lv001 --kind level --db tmp\factory_tech_condition_reverse_validation.sqlite --limit 12
python tools\endfield_source_graph.py query f1m26_q#3 --kind factory_machine --db tmp\factory_tech_condition_reverse_validation.sqlite --limit 12
```

Both queries showed the existing forward condition references and the new
reverse edges from referenced level/machine nodes.
