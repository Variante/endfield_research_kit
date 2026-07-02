# Equipment enhance reverse source graph recovery - 2026-07-02

## Context

`EquipEnhanceCostTable` has only one current row, but it carries direct
progression economy evidence: the equipment enhance domain, consumed item, and
refund item. The graph already exposed the forward relationships from the
enhancement-cost node. This slice adds target-centric reverse lookup edges.

## Graph Change

`tools/endfield_source_graph.py` now emits:

- `domain_has_equipment_enhance_cost`
- `item_consumed_by_equipment_enhance_cost`
- `item_refunded_by_equipment_enhance_cost`

These edges mirror existing forward edges and preserve item count metadata. The
change is table evidence only; it does not model enhancement success rates,
guarantee-rule behavior, or runtime economy flow.

## Validation

Focused build command:

```bat
python tools\endfield_source_graph.py build --db tmp\equipment_enhance_reverse_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

- graph size: 1,688,009 nodes, 3,144,088 edges, 2,277,554 aliases
- `equipment_enhance_cost`: 1 node
- `equipment_enhance_guarantee_rule`: 3 nodes
- `equipment_enhance_cost_domain`: 1 edge
- `domain_has_equipment_enhance_cost`: 1 edge
- `equipment_enhance_cost_consumes_item`: 1 edge
- `item_consumed_by_equipment_enhance_cost`: 1 edge
- `equipment_enhance_cost_refund_item`: 1 edge
- `item_refunded_by_equipment_enhance_cost`: 1 edge

Resolved target evidence:

- `domain_2` has the equipment enhance cost node.
- `item_equip_enhance_wuling` is consumed with count `1`.
- `item_domain_jinlong_coupon` is the refund item with count `0`.
