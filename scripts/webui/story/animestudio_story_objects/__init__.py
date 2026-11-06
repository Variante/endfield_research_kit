"""Builder-owned AnimeStudio Story-object evidence stages and artifacts."""
from pathlib import Path


from scripts.repo_paths import REPO_ROOT
from scripts.source_paths import configured_animestudio_cli

ROOT = REPO_ROOT
REPORT_ROOT = ROOT / 'webui/data/_build/story/recovery'
DEFAULT_ANIMESTUDIO_CLI = configured_animestudio_cli()
CARRIER_REPORT_PATH = REPORT_ROOT / "animestudio_story_carrier_audit.json"
HIERARCHY_REPORT_PATH = REPORT_ROOT / "animestudio_story_gameobject_audit.json"
REVERSE_REPORT_PATH = REPORT_ROOT / "animestudio_story_reverse_pptr_audit.json"

REVERSE_SCHEMA = "animestudioStoryReversePPtrAudit.v4"
REVERSE_NATIVE_MAPPING_ID = (
    "gameassembly-2026-07-28-cutscene-root-director-playback-v1"
)
# The CutsceneRoot/TimelineHandle playback claims, checked on the installed
# build: contracts/story_native_consumers.json.
REVERSE_NATIVE_GROUP = "cutsceneRootDirectorPlayback"

STAGES = ("carrier", "hierarchy", "reverse")
