# Intro And Planting Microcopy Source Graph Recovery - 2026-07-02

## Scope

Recovered first-class source graph coverage for two compact text-rich tables
that were still outside the named semantic ingestion groups:

- `IntroTable`
- `PlantingStepConstTable`

These tables are small, but they preserve original onboarding and workflow
microcopy that helps explain how game systems are presented to players.

## Recovered Semantics

`IntroTable` defines guide topics and ordered guide pages. The graph now emits:

- `intro_topic` nodes for each guide topic.
- `intro_page` nodes for each page entry, keyed by topic plus page order so
  repeated page ids do not collapse distinct pages.
- `defines_intro_topic` and `intro_topic_has_page` edges.
- `intro_page_title_text` and `intro_page_desc_text` edges to i18n text.
- `asset_stem` aliases for page `imagePath` guide images.

`PlantingStepConstTable` defines UI text for planting workflow step types. The
graph now emits:

- `planting_step_type` nodes.
- `defines_planting_step_type` edges.
- Text edges for button, hint, progress, and description fields.

## Validation

Built a focused temporary graph:

```bat
python tools\endfield_source_graph.py build --db tmp\intro_planting_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

```text
Source graph: 1628734 nodes, 3057881 edges, 2235267 aliases
```

Focused semantic counts:

```text
NODE intro_topic 12
NODE intro_page 44
NODE planting_step_type 4
EDGE defines_intro_topic 12
EDGE intro_topic_has_page 44
EDGE intro_page_title_text 44
EDGE intro_page_desc_text 44
EDGE defines_planting_step_type 4
EDGE planting_step_type_button_text 4
EDGE planting_step_type_hint_text 4
EDGE planting_step_type_progress_text 4
EDGE planting_step_type_description_text 4
```

The first validation pass intentionally caught a modeling issue: page ids repeat
within `IntroTable` topics, so keying only by topic and page id collapsed 44
page edges into 12 page nodes. The final implementation includes the page order
in the node key and validates all 44 guide pages.
