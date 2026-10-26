"""Native-backed diagnostic framing of exact existing export bytes.

This operation authenticates the current native contract and the selected local
bytes. It neither authenticates a current VFS census nor consumes source-export
receipts, and cannot publish or establish absence from the installed corpus.
"""
import hashlib
from pathlib import Path

from scripts.game_data.memorypack.levelscript_current_source import (
    CurrentLevelScriptSource,CurrentLevelScriptSourceError)
from scripts.game_data.string_pool import export_string_pool

SCHEMA='endfield.levelscript-existing-inputs.v1'


def _authority():
    return dict(diagnosticOnly=True,publicationEligible=False,currentVfsCorpus=False,currentVfsAuthority=False,
        currentCensusAuthenticated=False,sourceReceiptAuthority=False,absenceProved=False)


def _inside(path,root):
    resolved=path.resolve()
    if not resolved.is_relative_to(root):
        raise CurrentLevelScriptSourceError('source-outside-selected-json-root',path)
    # Shared byte joins use resolved names. Do not silently collapse a second
    # logical input onto an existing file through a symlink or junction.
    if resolved!=path.absolute():
        raise CurrentLevelScriptSourceError('existing-input-path-alias',path,str(path.absolute()),str(resolved))
    return resolved


def snapshot_existing_inputs(json_root):
    """Re-enumerate owner JSON, all pool files and conditional InteractiveTable.

    No image is opened. The table's absence is bound, but is permitted until a
    cursor actually requests it. Pool page-set/header checks run before native
    validation; individual payloads are decoded by the same pool/framing code.
    """
    root=Path(json_root).resolve()
    if not root.is_dir():raise CurrentLevelScriptSourceError('existing-json-root-required',root)
    paths=set()
    for family in('LevelScriptData','LevelData'):
        folder=_inside(root/family,root)
        if folder.exists():
            for path in folder.rglob('*.json'):
                if not path.is_file():raise CurrentLevelScriptSourceError('existing-input-file-required',path)
                paths.add(_inside(path,root))
    pool=_inside(root/'StringPool',root)
    if not pool.is_dir():raise CurrentLevelScriptSourceError('matching-string-pool-required',pool)
    for path in pool.rglob('*'):
        if path.is_file():paths.add(_inside(path,root))
        elif path.is_symlink():_inside(path,root)
    # Always perform fresh page/header validation, with no injected pool.
    if export_string_pool(root)is None:raise CurrentLevelScriptSourceError('matching-string-pool-required',root)
    table=_inside(root/'Interactive/InteractiveTable.json',root)
    if table.is_file():paths.add(table)
    rows=[]
    for path in sorted(paths):
        raw=path.read_bytes();rows.append(dict(path=str(path),exportRelativePath=path.relative_to(root).as_posix(),
            length=len(raw),logicalSha256=hashlib.sha256(raw).hexdigest().upper()))
    return dict(schema=SCHEMA,root=str(root),files=rows,
        interactiveTable=dict(path=str(table),present=table.is_file(),requiredWhen='read_interactive_table'),**_authority())


def _changes(before,after):
    old={r['exportRelativePath']:r for r in before['files']};new={r['exportRelativePath']:r for r in after['files']}
    changed=[dict(path=k,expected=old.get(k),actual=new.get(k))for k in sorted(old.keys()|new.keys())if old.get(k)!=new.get(k)]
    return dict(changedFiles=len(changed),changes=changed[:8],
        expectedInteractiveTable=before['interactiveTable'],actualInteractiveTable=after['interactiveTable'])


class ExistingLevelScriptSource(CurrentLevelScriptSource):
    """Same source-backed cursors over an exact existing export, diagnostic only."""
    def __init__(self,json_root,*,gameassembly,metadata):
        self.root=Path(json_root).resolve();self.gameassembly=gameassembly;self.metadata=metadata;self.active=False

    def _receipt(self):
        raise CurrentLevelScriptSourceError('existing-export-no-source-receipt-authority',self.root)

    def _open_source_rows(self,identity):
        self.existing_inputs=snapshot_existing_inputs(self.root)
        self.rows={row['exportRelativePath']:row for row in self.existing_inputs['files']}

    def _confirm_source_rows(self):
        after=snapshot_existing_inputs(self.root)
        if self.existing_inputs!=after:
            raise CurrentLevelScriptSourceError('existing-export-input-drift',self.root,'unchanged',_changes(self.existing_inputs,after))

    def _check_source_exit(self):
        self._confirm_source_rows()

    def _source_audit(self):
        return dict(status='conditional-existing-levelscript-source-diagnostic',existingInputs=self.existing_inputs,**_authority())

    def read_interactive_table(self):
        if not self.active:raise CurrentLevelScriptSourceError('operation-closed',self.root)
        key='Interactive/InteractiveTable.json'
        if key not in self.rows:raise CurrentLevelScriptSourceError('required-existing-interactive-table',self.root/key)
        return super().read_interactive_table()
