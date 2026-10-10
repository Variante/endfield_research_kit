# Activities page recovery

## Purpose

Activities exposes every published ActivityTable entry plus the exported
Activity-prefixed supporting tables as a catalog. It follows Gameplay in
navigation (Story, Gameplay, Activities, ...).

## Inputs and recovery flow

Reads the last published localized `reference/index.json` and its declared
Activity table shards; it builds nothing of its own. Story/Text owns discovery,
localization, structured fields and activity guides, and Activities reuses
Text's maintained row renderers.

- TimeRangeTable and ActivityTagTable rows are joined by exact authored IDs
  from rawRows. Tag names are the exported ActivityTagTable `name` values
  selected by each activity's authored `tagIds`.
- Supporting rows inherit tags/schedules only through an explicit
  `activityId`; otherwise they keep their own configuration.
- Activity details expand the exact activity-keyed CheckInRewardTable days and
  stage, task and milestone rows. Every check-in child's `activityId` must
  match; the conditional-stage row must match by key and stored `activityId`.
  Days and stages keep their own reward quantities and icons; grants are never
  aggregated.
- The optional Assets-owned `activity_media.json` supplies exact artwork,
  InstructionBook images (via `instructionId`) and fixed RewardTable
  itemBundle ItemTable icons. It follows only exact authored asset fields; no
  asset-name prefix is treated as an activity ownership link. Assets publishes
  it from the same complete asset scan as its index, so it adds no extraction
  input.
- Updates publishes an `activities.json` row-diff sidecar over Activity*Table
  and CheckInRewardTable using the Reference comparison and freshness gate.

## Outputs

No generated output of its own. Frontend behavior (filters, sorting, list and
detail layout, URL state) is the
[`webui/README.md` Activities contract](../../webui/README.md#activities);
the image lookup belongs to [Assets](assets.md) and the update sidecar to
[Updates](updates.md).

## Evidence boundary

Shows stored configuration, including entries from different versions and
internal/test entries. It does not infer current availability, unlock
execution, player progress, completion or live rewards. Schedule times are
shown verbatim with no inferred time zone or meaning for range variants. The
Permanent/Limited-time labels are a frontend classification from the presence
of a configured closing time, not server availability. Table membership comes
from the published index; supporting tables remain separate datasets rather
than inferred joins.

## Focused refresh

Run `export.bat story` against existing exports to refresh the shared Text
publication and `export.bat assets` to refresh the image lookup. Activities
has no separate extraction scope; installed-client extraction requires an
explicit user request.

## Remaining gaps

- Current availability and runtime progress (completion marks) are outside
  this static evidence.
- Tables without maintained Text guides show only localized text and
  structured fields; the published source JSON is reachable from each record.
