# Gameplay Activities subpage recovery

## Purpose

Gameplay’s Activities subpage exposes every published ActivityTable entry as a catalog. Supporting tables supply linked details; standalone table
browsing belongs to Text. Its frontend lives under `webui/src/features/gameplay/activities/`, with entry,
language refresh, retry and history routing owned by Gameplay’s `tabs.js`.
The canonical route is `?gameplayKind=activity&activity=<id>#gameplay`; legacy
`#activities` links normalize while retaining activity selection and filters.
The subpage preserves its own search, facets, sort and splitters. List rows
retain their original rounded cards and yellow selection rail, with artwork
on the right filling the card height; details reuse the shared
artwork/title/plain metadata header and body spacing used by Weapons and
Essences. The introductory configuration-boundary paragraph is omitted; the
evidence boundary remains documented here.
Reward, schedule, asset and maintained guide headings reuse Gameplay’s shared
section-title class, including daily check-in and stage/milestone reward titles.
Schedules and activity prerequisites render without a card border or background.
Linked reward cards omit their repeated guide headings while retaining authored
day/stage descriptions and fields below the outer reward section heading.
The final Assets section is visible in normal mode and reuses Gameplay’s shared
asset gallery. It collects only exact published activity and supporting reward
media, including tabImg/bgImg, and displays only the highest pixel-area image for
each authored token. Source alternatives remain published. Previews and links
to the Assets page use the shared Gameplay behavior.
Gameplay reads the ActivityTable total from the shared localized reference index
on entry, so its Activities tab shows the dataset count before selection. Missing
reference publication leaves the count unavailable; it never invents a zero.
Direct entry into Activities also loads the other Gameplay catalog indexes, so
all dataset counts appear together regardless of the initially selected subpage.
Activity details reuse the last Gameplay battle-stage publication for linked
stages and their published scene maps. ActivityDungeon gameMap and ActivityCharTrial
activityId/dungeonId establish direct stored associations. Conditional multi-stage
rows reach completion-condition dungeon references only when the activity and
stage identities agree; these are labelled completion-condition links rather
than activity ownership. A SystemJump SeasonTowerMainHud destination with empty
arguments reaches SeasonTowerTable week group IDs and SeasonTowerGameGroupTable
star game IDs; these appear as season-configuration stages, without selecting
the current season/week or proving live availability. Each stage appears in a
row with its own maps, preserving the stage-to-scene association even when two
difficulty modes share one scene. DungeonTable.sceneId links appear in the
combat-map column; levelId links appear separately as associated area maps.
The levelId field alone does not prove an entrance:
trial dungeons use it for the published simulated training area while their
sceneId is empty. Missing joins create no links.
Stage buttons reuse the shared dataset links and routing.

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
- Supply stages join ActivitySubmitFoodTable by exact `stageId`, then SubmitItem
  by exact `submitItemId`/`submitId`. Stored type-1 parameter pairs expose only
  one resolved ItemTable ID and one positive integer count. Stage submission
  chips remain distinct from reward grants and are excluded from reward totals;
  they do not establish current progress or availability.
- The same exact supply-stage join preserves its localized name, submitDesc
  and noteDesc alongside the stage description and submission quantities.
  Compact mode keeps those stage sections even when the text has no reward.
  Supply stages are grouped by the exact stageList path into separate reading
  cards, with authored stage names, supply text, required items and quantities,
  then rewards and the stored mission reference. Required-item chips reuse
  Gameplay item routing and remain excluded from reward totals. Additional
  task-only stages remain visible rather than being dropped for lacking rewards.
  Mission references survive compact filtering; the shared reference renderer
  also retains introduction and ending quest references from activity configuration,
  while leaving repeated configuration reward previews out of normal details. It
  resolves links through `src/ui/story_links.js` against Story's last localized
  index and mission names. A mission link opens its published Story group; it
  does not assert that the selected conversation belongs to that supply stage.
- Activity details expose narrative mission destinations through the exact `detailJumpId` to
  SystemJumpTable join. Only an identity-matched `Mission` phase with a valid
  JSON `autoSelectList` of mission IDs contributes links, in authored list order.
  Shared Story navigation resolves published destinations; absent destinations
  retain their IDs. This selection list does not establish runtime mission order.
  Task-only stage mission references also survive normal-mode filtering.
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
- Updates publishes `updates/activities.json` schema 3. Individual supporting
  rows retain their identities; each `ActivityTable/<id>` comparison also owns
  the exact related-reward and maintained-guide joins displayed by the page.
  Schedule, conditions, tasks, supply submissions and reward changes can mark
  their owning activity without a change in ActivityTable itself. Related labels
  are terminal and condition parameter strings never create ownership links.
  Lists and detail titles show Added/Modified badges, details show source-field
  comparisons, and Version changes uses the shared filter with other facets.

## Outputs

No generated output of its own. Detail text uses the shared rich-text renderer
with stored size/color tags normalized to ordinary bold emphasis in descriptions
and compact guides. Full debug reference content retains source markup.
The shared raw-tag mode retains the original text.
Root `$.desc` appears below the detail title and official category tags;
the redundant Activity configuration heading is omitted. Normal detail mode uses compact
maintained guides without duplicate description/time fields or technical codes;
source identity and full reference fields/text remain in debug mode; artwork is shown in the final Assets section.
Compact activity and linked-reward guides also hide machine-facing joins,
reference provenance, display settings and unfilled runtime placeholders;
quantified rewards remain visible even without a resolved localized item name.
An intentionally empty compact guide must not trigger the raw field/text
fallback: root Desc and Name already appear in the page header. Full debug
mode still renders the original fields and localized text inventory.
Normal activity details omit the entire Activity configuration guide section;
independent prerequisite and linked reward sections remain visible.
Quantified items from the omitted configuration section are retained separately
in Reward summary when no quantified linked detail is published,
labelled as a preview without treating that overview as a sum of grants.
Otherwise the summary aggregates fixed detail entries by exact ItemTable ID;
each source section/field is counted once and requirements remain applicable.
Reward summary tags and exact ItemTable guide links navigate to Gameplay's
Items catalog by item ID, using the shared catalog URL and navigation helpers.
Reward summary follows prerequisites and precedes stage/check-in/milestone details.
Stage, check-in and milestone rewards use the same wrapping tags as the
summary, sharing Gameplay's chip and icon CSS without page-local sizing overrides.
The stage-rewards block admits only sections containing quantified rewards in
normal mode; stages without rewards remain debug configuration. Milestone and
stage IDs are debug-only, while milestone scores and item quantities stay visible.
Frontend behavior (filters, sorting, list and
detail layout, URL state) is the
[`webui/README.md` Activities contract](../../webui/README.md#activities);
the image lookup belongs to [Assets](assets.md) and the update sidecar to
[Updates](updates.md).

## Evidence boundary

Shows stored configuration, including entries from different versions and
internal/test entries. It does not infer current availability, unlock
execution, player progress, completion or live rewards. Schedule times are
shown verbatim without assigning an unproved time zone to a slot. Exported
Lua `Utils.isCurTimeInTimeIdRange` and `getTimeIdOpenTimeStamp` select
`timeRangeList[CSIndex(Utils.getServerAreaType():GetHashCode())]`, where
`CSIndex` subtracts one. `getServerAreaType` reads the player's
`playerInfoSystem.serverAreaType`; the selected date string is converted with
`DateTimeUtils.SERVER_TIME_ZONE.BaseUtcOffset`. The activity description
popup's `_FormatPhaseTimeRange` uses the same selection and conversion.
Thus the slots are server-area alternatives, not successive activity phases.
This does not prove that every area's dates represent one shared instant,
nor establish the enum-value-to-area or area-to-UTC-offset mapping. The
Permanent/Limited-time labels are a frontend classification from the presence
of a configured closing time, not server availability. Table membership comes
from the published index. Same-name limited-time and permanent activities keep
separate source records, with unfilled amber limited-time and green permanent
tags before list/detail titles, using shared status colors at full opacity
and schedule labels in details. Lists, details, schedule classification and
sorting use the first authored time slot consistently; other variants remain
in source JSON, and no time zone is assigned to the selected slot.
Supporting tables remain separate datasets rather than inferred joins.

## Focused refresh

Official category IDs with the same localized name share one union filter and
total count. Original IDs remain in raw records, and old ID-based filter URLs
are normalized on load. Combat-stage and map destinations reuse Gameplay's
related-link renderer, also used by weapon essence farming destinations.
Overview reward previews display items without quantities, while exact quantified
stage rewards and supply submissions retain counts. The shared Gameplay quantity
predicate also hides unavailable counts in item recipes, uses and chest rewards.

Run `export.bat story` against existing exports to refresh the shared Text
publication and `export.bat assets` to refresh the image lookup. Activities
has no separate extraction scope; installed-client extraction requires an
explicit user request.

## Remaining gaps

- Current availability and runtime progress (completion marks) are outside
  this static evidence.
- Tables without maintained Text guides show only localized text and
  structured fields; the published source JSON is reachable from each record.
