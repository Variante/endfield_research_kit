"""Builder-owned AnimeStudio Story-object evidence stages and artifacts."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REPORT_ROOT = ROOT / "reports" / "story" / "recovery"
DEFAULT_ANIMESTUDIO_CLI = (
    ROOT
    / "tools"
    / "AnimeStudio"
    / "AnimeStudio.CLI"
    / "bin"
    / "Release"
    / "net9.0-windows"
    / "AnimeStudio.CLI.exe"
)
CARRIER_REPORT_PATH = REPORT_ROOT / "animestudio_story_carrier_audit.json"
HIERARCHY_REPORT_PATH = REPORT_ROOT / "animestudio_story_gameobject_audit.json"
REVERSE_REPORT_PATH = REPORT_ROOT / "animestudio_story_reverse_pptr_audit.json"

REVERSE_SCHEMA = "animestudioStoryReversePPtrAudit.v4"
REVERSE_NATIVE_MAPPING_ID = (
    "gameassembly-2026-07-28-cutscene-root-director-playback-v1"
)
REVERSE_GAMEASSEMBLY_SHA256 = (
    "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE"
)
REVERSE_METADATA_SHA256 = (
    "90C58E26E87C7227A85DDA3FEDF6CE5ED0B06DC1F76E0ABBE75AB20750ADF97E"
)

STAGES = ("carrier", "hierarchy", "reverse")
