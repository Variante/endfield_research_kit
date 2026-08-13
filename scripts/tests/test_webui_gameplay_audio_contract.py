from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GAMEPLAY = ROOT / "webui" / "src" / "features" / "gameplay" / "index.js"


@unittest.skipUnless(shutil.which("node"), "Node.js is required for WebUI JavaScript tests")
class GameplayAudioContractTests(unittest.TestCase):
    def run_node(self, source: str) -> None:
        completed = subprocess.run(
            ["node", "-e", source],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            completed.returncode,
            0,
            msg=f"Node test failed:\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}",
        )

    def test_duplicate_page_end_events_merge_without_losing_candidates_or_evidence(self) -> None:
        source = GAMEPLAY.read_text(encoding="utf-8")
        body = source.split("  function mergeGameplaySoundEvents", 1)[1].split(
            "\n  function renderGameplaySoundEvidence", 1
        )[0]
        function_source = "function mergeGameplaySoundEvents" + body
        self.run_node(
            f"""
const assert = require("node:assert/strict");
{function_source}
const merged = mergeGameplaySoundEvents([
  {{
    id: "au_test",
    audio: [{{src: "/a.flac", mediaId: 1}}],
    sourceSkillIds: ["skill_a"],
    triggerBindings: [{{groupId: "group_a"}}],
    evidence: [{{skillId: "skill_a"}}],
    playRootActionIds: [10],
    mediaRelationTypes: ["randomAlternative"],
    triggerRelationTypes: ["skillDataEventReference"],
    selectorEvidence: {{
      bankDefinitionCount: 1,
      rootStopActionCount: 0,
      containers: {{randomAlternative: {{nodeCount: 1, childEdgeCount: 2}}}},
    }},
    possibleMediaCount: 1,
  }},
  {{
    id: "AU_TEST",
    audio: [{{src: "/b.flac", mediaId: 2}}],
    sourceSkillIds: ["skill_b"],
    triggerBindings: [{{groupId: "group_b"}}],
    evidence: [{{skillId: "skill_b"}}],
    playRootActionIds: [20],
    mediaRelationTypes: ["switchCandidate"],
    triggerRelationTypes: ["skillBuffChain"],
    selectorEvidence: {{
      bankDefinitionCount: 2,
      rootStopActionCount: 1,
      containers: {{
        randomAlternative: {{nodeCount: 3, childEdgeCount: 4}},
        switchCandidate: {{nodeCount: 5, childEdgeCount: 6}},
      }},
    }},
    possibleMediaCount: 2,
  }},
]);
assert.equal(merged.length, 1);
assert.deepEqual(merged[0].audio.map((row) => row.src), ["/a.flac", "/b.flac"]);
assert.deepEqual(merged[0].sourceSkillIds, ["skill_a", "skill_b"]);
assert.deepEqual(merged[0].triggerBindings.map((row) => row.groupId), ["group_a", "group_b"]);
assert.deepEqual(merged[0].playRootActionIds, [10, 20]);
assert.deepEqual(merged[0].mediaRelationTypes, ["randomAlternative", "switchCandidate"]);
assert.deepEqual(merged[0].triggerRelationTypes, ["skillDataEventReference", "skillBuffChain"]);
assert.equal(merged[0].selectorEvidence.bankDefinitionCount, 2);
assert.equal(merged[0].selectorEvidence.rootStopActionCount, 1);
assert.deepEqual(merged[0].selectorEvidence.containers, {{
  randomAlternative: {{nodeCount: 3, childEdgeCount: 4}},
  switchCandidate: {{nodeCount: 5, childEdgeCount: 6}},
}});
assert.equal(merged[0].possibleMediaCount, 2);
"""
        )

    def test_projectile_audio_sidecar_joins_by_id_field_and_unsigned_hash(self) -> None:
        source = GAMEPLAY.read_text(encoding="utf-8")
        projectile_helpers = source.split("  function projectileEventHash", 1)[1].split(
            "\n  function projectileFriendlyName", 1
        )[0]
        sound_rows = source.split("  function projectileSoundRows", 1)[1].split(
            "\n  function renderProjectileAudio", 1
        )[0]
        indexes = source.split("  function buildIntegrationIndexes", 1)[1].split(
            "\n  function integrationNodeCandidates", 1
        )[0]
        self.run_node(
            f"""
const assert = require("node:assert/strict");
const PROJECTILE_SOUND_PHASES = ["launchSound", "loopSound", "reachSound", "hitSound", "blockSound", "finishedSound", "sizzleSound"];
const STATE = {{integration: {{
  combat: null,
  projectiles: {{entries: []}},
  projectileAudio: {{links: [{{
    projectileId: "projectile_fixture",
    field: "launchSound",
    eventHash: 0xffffffff,
    event: {{foundInWwise: true, canonicalEventIds: ["au_fixture"]}},
    audio: [{{src: "/fixture.flac", mediaId: 7}},],
  }}]}},
}}}};
function projectileEventHash{projectile_helpers}
function projectileSoundRows{sound_rows}
function buildIntegrationIndexes{indexes}
STATE.integration.indexes = buildIntegrationIndexes();
const projectile = {{
  id: "projectile_fixture",
  sounds: {{launchSound: {{value: -1, event: {{foundInWwise: false}}, audio: [{{src: "/embedded.flac"}}]}}}},
}};
let rows = projectileSoundRows(projectile);
assert.equal(rows.length, 1);
assert.equal(rows[0].event.foundInWwise, true);
assert.deepEqual(rows[0].event.canonicalEventIds, ["au_fixture"]);
assert.deepEqual(rows[0].audio.map((row) => row.src), ["/fixture.flac"]);
STATE.integration.projectileAudio = {{links: []}};
STATE.integration.indexes = buildIntegrationIndexes();
rows = projectileSoundRows(projectile);
assert.equal(rows[0].event.hash, 0xffffffff);
assert.equal(rows[0].event.foundInWwise, undefined);
assert.deepEqual(rows[0].audio, []);
"""
        )
        self.assertIn("data/lang/${code}/gameplay/projectile_audio.json", source)

    def test_audio_placement_and_flat_event_contract(self) -> None:
        source = GAMEPLAY.read_text(encoding="utf-8")
        inline = source.split("  function renderActiveSkillSoundEffects", 1)[1].split(
            "\n  function renderEnemySoundEffects", 1
        )[0]
        trailing = source.split("  function renderCharacterSkillSounds", 1)[1].split(
            "\n  function renderActiveSkillSoundEffects", 1
        )[0]
        enemy = source.split("  function renderEnemySoundEffects", 1)[1].split(
            "\n  function renderCharacterAnimationSounds", 1
        )[0]

        self.assertIn(".filter(gameplaySoundHasExactSkillTrigger)", inline)
        self.assertIn("!gameplaySoundHasExactSkillTrigger(event)", trailing)
        self.assertIn("mergeGameplaySoundEvents(events)", trailing)
        self.assertIn("flattenGroups: true", enemy)
        self.assertIn(
            'gp$("#gameplay-detail-body").innerHTML = `${rendered.body || ""}${integrated}${trailingAudio}`;',
            source,
        )
        self.assertIn('<audio controls preload="none" src="${escapeHtml(candidate.src)}"></audio>', source)
        self.assertIn('<article class="gameplay-sfx-event">', source)
        self.assertNotIn('<details class="gameplay-sfx-action">', source)
        self.assertNotIn('<details class="gameplay-projectile-audio-phase"><summary><strong>${escapeHtml(gameplaySoundEventName(event.id)', source)
        self.assertNotIn('details[data-gameplay-sfx-src]', source)
        self.assertNotIn('<details class="gameplay-related-sfx">', source)
        self.assertNotIn('data-gameplay-sfx-list-toggle', source)
        self.assertNotIn('data-gameplay-sfx-play', source)
        self.assertNotIn('data-gameplay-sfx-list', source)
        self.assertNotIn('bindCandidatePlayers', source)
        self.assertNotIn('container.querySelectorAll("[data-gameplay-sfx-src]', source)
        self.assertIn('details.addEventListener("toggle"', source)
        self.assertIn("renderGameplaySoundEvidence(event, audio)", source)
        self.assertIn('text("soundPlayBranches")', source)
        self.assertIn("selectorEvidence.containers", source)
        self.assertIn("const GAMEPLAY_INLINE_AUDIO_LIMIT = 20;", source)
        self.assertIn(
            'row.audio.length > 0 && row.audio.length <= GAMEPLAY_INLINE_AUDIO_LIMIT ? " open" : ""',
            source,
        )

    def test_related_audio_uses_flat_event_cards_and_keeps_action_labels(self) -> None:
        source = GAMEPLAY.read_text(encoding="utf-8")
        groups = source.split("  function renderGameplaySoundActionGroups", 1)[1].split(
            "\n  function gameplayResolvedSoundEvents", 1
        )[0]
        related = source.split("  function renderGameplaySoundGroup", 1)[1].split(
            "\n  function renderCharacterSkillSounds", 1
        )[0]
        self.assertIn(
            'renderGameplaySoundEvents(group.events, { showActionLabel: true })',
            groups,
        )
        self.assertNotIn('<section class="gameplay-sfx-action">', groups)
        self.assertNotIn("flattenGroups: true", related)
        self.assertIn("gameplay-sfx-inline", related)
        self.assertIn(".filter(gameplaySoundHasExactSkillTrigger)", source)

    def test_gameplay_audio_counts_associations_and_unique_files_separately(self) -> None:
        source = GAMEPLAY.read_text(encoding="utf-8")
        count = source.split("  function gameplaySoundCountText", 1)[1].split(
            "\n  function gameplaySoundIsSharedAnimation", 1
        )[0]
        self.assertIn("const mediaKeys = new Set();", count)
        self.assertIn("soundUniqueFiles", count)
        labels = (ROOT / "webui" / "src" / "features" / "gameplay" / "labels.js").read_text(encoding="utf-8")
        self.assertIn("possible media associations", labels)
        self.assertIn("unique decoded files", labels)


if __name__ == "__main__":
    unittest.main()
