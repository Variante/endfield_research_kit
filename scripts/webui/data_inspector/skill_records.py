"""Complete stored SkillData values from selected source-bound native replay."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.memorypack import current_family_evidence as current
from scripts.game_data.memorypack.corpus_gate import _fingerprint
from scripts.game_data.memorypack.skill_values import SkillValueSchema
from scripts.webui.data_inspector.current_receipts import select_current_family_report


def load_skill_values(export_root, *, registry, definition, context):
    current.need('Skill-values-active-current-context', context is not None)
    export_root = Path(export_root).resolve()
    path, selection = select_current_family_report('SkillData', export_root)
    report = json.loads(path.read_bytes()); pin = _fingerprint(path)
    current.need('Skill-values-selected-export', context['layout'].root.resolve() == export_root
        and Path(report['exportRoot']).resolve() == export_root)
    current.need('Skill-values-selected-report', all(selection['familyReport'][k] == pin[k]
        for k in ('path','length','sha256')))
    root = context['gameRoot']
    image = open_native_image(root.parent/'GameAssembly.dll', root/'il2cpp_data/Metadata/global-metadata.dat')
    schema = SkillValueSchema(operation=context['operation'], registry=registry, image=image)
    result = {}
    selected = current.family_sources(context, 'SkillData')
    def collect(row):
        raw = current.source_bytes(context, row['identity'])
        value, facts = schema.decode(raw, definition=definition, source=row['virtualPath'], receipt=row['rootReceipt'])
        current.need('Skill-values-exact-source-id', value.get('skillId') == Path(row['exportRelativePath']).stem,
                     row['virtualPath'])
        key = 'game/' + row['virtualPath'].removeprefix('Data/')
        current.need('Skill-values-unique-source', key not in result, key)
        result[key] = (value, dict(facts, sourceSha256=hashlib.sha256(raw).hexdigest().upper(),
                                  bytesConsumed=len(raw), serializedMemberCount=49))
    current.load_evidence(path, family='SkillData',
        expected_input_set_sha256=selection['currentSourceReceipt']['inputSetSha256'],
        expected_paths={r['virtualPath'] for r in selected}, loaded_report=(report,pin),
        context=context, on_row=collect)
    current.need('Skill-values-full-source-roster', len(result) == len(selected))
    current.need('Skill-values-registry-bookend', select_current_family_report('SkillData', export_root) == (path,selection))
    return result, dict(currentNativeRoot=True, currentSourceReceipt=selection,
        familyReport=pin, namedValueTypes=sorted(schema.types),
        storedValueLayouts=[v for _,v in sorted(schema.layouts.layouts.items())],
        allStoredValuesExact=True, runtimeExecutionProved=False)
