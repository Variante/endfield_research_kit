"""Whole current LevelScript, template and optional LevelData source operation.

All selected families must be decoded and closed before any exit receipt is
available. Source inventory authority and native child grammar remain separate.
"""
from contextlib import contextmanager
from pathlib import Path

from scripts.game_data.memorypack.levelscript_current_source import CurrentLevelScriptSource

from scripts.game_data.memorypack.levelscript_owner_sources import ROOT_FIELDS
from scripts.game_data.leveldata_binary import LEVELDATA_FIELDS

FIELDS = {
    'LevelScriptData': tuple(name for name, _ in ROOT_FIELDS),
    'LevelScriptTemplateData': ('actionMap', 'maxStage', 'properties', 'propertyIdToKeyMap', 'taskMap', 'templateId'),
    'LevelData': LEVELDATA_FIELDS,
}


class CompleteLevelScriptError(ValueError):
    pass


class _CompleteReader:
    def __init__(self, operation, families):
        self.operation = operation; self.families = families; self._receipt = None

    def __call__(self, path, data):
        if not self.operation.active:
            raise CompleteLevelScriptError('completeLevelScript.operation-closed')
        path = Path(path)
        if not path.is_absolute(): path = self.operation.root / path
        key = path.resolve().relative_to(self.operation.root).as_posix()
        family = key.split('/', 1)[0]
        if family not in self.families:
            raise CompleteLevelScriptError('completeLevelScript.unselected-family:' + key)
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise CompleteLevelScriptError('completeLevelScript.bytes-like-input-required')
        data = bytes(data)
        if family == 'LevelData': frame = self.operation.frame_leveldata(path, data)
        elif family == 'LevelScriptTemplateData': frame = self.operation.frame_template(path, data)
        else:
            frame = self.operation.frame(path, data)
            # The sequential root reader retains actionMap beside its other 27
            # fields; normalize the already closed first field, never a suffix.
            ranges = frame.get('ranges', {})
            action_map = ranges.get('actionMap')
            if (not isinstance(action_map, dict) or action_map.get('completeAsset') is not True
                    or action_map.get('startOffset') != 1 or type(action_map.get('endOffset')) is not int
                    or not 1 < action_map['endOffset'] <= len(data)
                    or action_map['endOffset'] != (ranges.get('ownerPrefix') or {}).get('startOffset')):
                raise CompleteLevelScriptError('completeLevelScript.complete-action-map-owner-boundary:' + key)
            frame = dict(frame, fields=dict(actionMap=action_map, **frame['fields']))
        expected = list(FIELDS[family])
        if (frame.get('schemaStatus') != 'named_exact' or frame.get('serializedMemberCount') != len(expected)
                or frame.get('bytesConsumed') != len(data) or list(frame.get('fields', {})) != expected):
            raise CompleteLevelScriptError('completeLevelScript.complete-ordered-owner-EOF:' + key)
        return dict(frame, wholeSchemaExact=True, physicalEOF=True, closedFields=expected,
            openField=None, schemaMappingId='endfield.current-level-owner-operation.v1')

    @property
    def receipt(self):
        if self.operation.active or self._receipt is None:
            raise CompleteLevelScriptError('completeLevelScript.successful-operation-exit-required')
        return self._receipt


@contextmanager
def complete_levelscript_reader(export_root, *, game_root=None, gameassembly=None, metadata=None,
                                families=('LevelScriptData', 'LevelScriptTemplateData')):
    from scripts.common import resolve_installed_native_inputs, native_game_data_root
    from scripts.source_paths import ExportLayout
    layout = ExportLayout(Path(export_root).resolve()).require()
    families = tuple(families)
    if not families or len(set(families)) != len(families) or not set(families) <= set(FIELDS):
        raise CompleteLevelScriptError('completeLevelScript.closed-family-selection')
    if (gameassembly is None) != (metadata is None):
        raise CompleteLevelScriptError('completeLevelScript.both-selected-native-paths-required')
    if gameassembly is None:
        if game_root is None:
            gameassembly, metadata = resolve_installed_native_inputs(export_summary_path=layout.root / 'meta/extraction/summary.json')
        else:
            selected = Path(game_root).resolve()
            gameassembly = selected.parent / 'GameAssembly.dll'; metadata = selected / 'il2cpp_data/Metadata/global-metadata.dat'
    gameassembly, metadata = Path(gameassembly).resolve(), Path(metadata).resolve()
    selected = native_game_data_root(gameassembly=gameassembly, metadata=metadata)
    if game_root is not None and selected != Path(game_root).resolve():
        raise CompleteLevelScriptError('completeLevelScript.explicit-root-and-native-pair-disagree')
    evidence = layout.evidence_dir / 'animestudio'
    with CurrentLevelScriptSource.from_source_inventory(layout.json_dir, gameassembly=gameassembly, metadata=metadata,
            summary_path=evidence / 'jsondata_source_current.json', ledger_path=evidence / 'jsondata_source_files_current.jsonl.gz') as operation:
        if any(family in families for family in ('LevelScriptData','LevelScriptTemplateData')):
            operation.prepare_template()
        decode = _CompleteReader(operation, families)
        yield decode
        audit = operation.audit(); coverage = {}
        for family in families:
            owner = audit if family == 'LevelScriptData' else audit['template' if family == 'LevelScriptTemplateData' else 'leveldata']
            coverage[family] = {key: owner[key] for key in ('sourceUniverse', 'sourcesAttempted', 'ownersClosed', 'allSourcesAttempted', 'allOwnersClosed')}
            if (not owner['sourceUniverse'] or not owner['allSourcesAttempted'] or not owner['allOwnersClosed']
                    or owner['sourcesAttempted'] != owner['sourceUniverse'] or owner['ownersClosed'] != owner['sourceUniverse']):
                raise CompleteLevelScriptError('completeLevelScript.selected-source-family-not-complete:' + family + ':' + str(coverage[family]))
    if operation.native_validation_reuse.get('entryExitBookendsPassed') is not True:
        raise CompleteLevelScriptError('completeLevelScript.native-source-pool-exit-required')
    decode._receipt = dict(schema='endfield.complete-levelscript-operation.v1', status='validated-current-level-owner-operation',
        nativeInputs=dict(operation.proof['nativeInputs']), nativeSources=dict(operation.proof['nativeSources']),
        sourceInventory=audit['summary'], sourceInventoryAuthenticated=audit['sourceInventoryAuthenticated'],
        families=coverage, allSelectedOwnersClosed=True, nativeSourcePoolOwnerExitBookendsPassed=True,
        runtimeActivationProved=False, playbackProved=False)
