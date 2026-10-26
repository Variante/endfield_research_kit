"""Narrative configuration projected only from current complete typed owners."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.common import read_bytes_cached,rel_path
from scripts.game_data.memorypack.levelscript_current_source import CurrentLevelScriptSource


def _scalar_string(value,*,string_type):
    if type(string_type)is not int:raise ValueError('storyCurrentNarrative.native-string-kind-required')
    if not isinstance(value,dict)or value.get('typeRaw')!=string_type:return None
    array=value.get('valueArray')
    if not isinstance(array,dict)or array.get('count')!=1:return None
    values=array.get('values')
    if not isinstance(values,list)or len(values)!=1:return None
    atom=values[0]
    if not isinstance(atom,dict)or atom.get('valueBit64')!=0:return None
    text=atom.get('valueString')
    return text if isinstance(text,str)and text.strip()else None


def project(frame,*,component_key,string_type,path,data,available_story_keys,reading_rows,interactive_index,reading_popup_path):
    """Projection needs a source-owned complete frame; it grants no framing."""
    if (frame.get('schemaStatus'),frame.get('serializedMemberCount'),frame.get('bytesConsumed'))!=('named_exact',28,len(data)):
        raise ValueError('storyCurrentNarrative.complete-current-owner-eof-required')
    fields=frame['fields'];script_id=str(fields['scriptId']);dictionary=fields['interactives']
    if dictionary.get('status')=='null':return []
    rows=[];object_to_template=interactive_index.get('objectToTemplate')or{};core_paths=interactive_index.get('coreTemplatePaths')or{}
    for entry in dictionary.get('entries')or[]:
        record=entry['value']
        if record is None:continue
        if record.get('serializedMemberCount')!=25:raise ValueError('storyCurrentNarrative.current-interactive-owner-required')
        components=record['componentProperties'].get('entries')or[]
        matches=[r for r in components if r['componentTypeRaw']==component_key]
        if not matches:continue
        if len(matches)!=1:raise ValueError('storyCurrentNarrative.ambiguous-narrative-component')
        properties=matches[0]['properties'];values=properties.get('values')or[]
        typed=[r for r in values if isinstance(r,dict)and r.get('key')=='type_id']
        if len(typed)!=1:continue
        type_id=_scalar_string(typed[0].get('value'),string_type=string_type)
        if type_id is None:continue
        popup=reading_rows.get(type_id);content=str(popup.get('contentId')or'').strip()if isinstance(popup,dict)else''
        if type_id in available_story_keys:story_key=type_id;resolution='direct_story_key'
        elif content in available_story_keys:story_key=content;resolution='reading_popup_content_id'
        else:continue
        detail=record.get('entityDataIdKey');template=str(object_to_template.get(detail)or'')
        if not template.startswith('int_narrative'):continue
        rows.append(dict(storyKey=story_key,rawTypeId=type_id,typeId=type_id,
            storyKeyResolution=resolution,readingPopupId=type_id if resolution=='reading_popup_content_id'else'',
            levelId=path.parent.name,scriptId=script_id,sourceFile=rel_path(path),sourcePath=str(path),
            sourceSha256=hashlib.sha256(data).hexdigest().upper(),ownerMemberCount=28,
            ownerBytesConsumed=len(data),ownerEnvelopeStatus='authenticated-current-levelscript-eof',
            localInteractiveId=entry['key'],entityDetailId=detail,entityType=record['entityTypeRaw'],
            embeddedLogicId=int(record['levelLogicId']),recordOffset=record['startOffset'],
            recordEndOffset=record['endOffset'],serializedMemberCount=25,narrativeComponentKey=component_key,
            componentPropertiesOffset=record['componentProperties'].get('startOffset'),
            componentPropertiesEndOffset=record['componentProperties'].get('endOffset'),
            componentPropertiesCount=record['componentProperties'].get('count'),
            typeIdEntryOffset=typed[0].get('startOffset'),typeIdEntryEndOffset=typed[0].get('endOffset'),
            interactiveMapCount=dictionary.get('count'),interactiveMapCountOffset=dictionary.get('startOffset'),
            interactiveMapEndOffset=dictionary.get('endOffset'),entityTemplateId=template,
            entityTemplatePath=str(core_paths.get(template)or''),
            interactiveTableSourceFile=str(interactive_index.get('sourceFile')or''),
            interactiveTableVerifiedMirrorFile=str(interactive_index.get('verifiedMirrorFile')or''),
            readingPopupTableSourceFile=rel_path(reading_popup_path),nativeMappingId='levelscript-current-pooled-narrative-owner-v1',
            evidenceTier='structuralOnly',storyBinding=True,ownership=False,questActivation=False,
            questPlayback=False,questCompletion=False,runtimeNarrativeConsumerProved=False,
            executionSide='client',serverExchange=False))
    return rows


def build(*,available_story_keys,levelscript_root,reading_popup_path,interactive_table_parser,
        gameassembly,metadata,source_summary_path,source_ledger_path):
    root=Path(levelscript_root);paths=sorted(root.rglob('*.json'))if root.is_dir()else[]
    audit=dict(status='unavailable'if not root.is_dir()else'unresolved',sourceFiles=len(paths),
        ownersClosed=0,failedFiles=0,narrativeConfigurationRows=0,absenceProved=False,
        runtimeNarrativeConsumerProved=False,playbackProved=False,failures=[])
    rows=[]
    def failure(error,path=None,data=None):
        detail=dict(getattr(error,'diagnostic',None)or dict(validator='storyCurrentNarrative',
            gate='current-owner-source',actual=str(error)[:1400]))
        if path is not None:detail['source']=str(path)
        if data is not None:detail['sourceSha256']=hashlib.sha256(data).hexdigest().upper()
        return detail
    if not paths:return rows,audit
    try:
        if gameassembly is None or metadata is None:raise ValueError('storyCurrentNarrative.explicit-native-pair-required')
        if not Path(source_summary_path).is_file()or not Path(source_ledger_path).is_file():
            raise ValueError('storyCurrentNarrative.authenticated-jsondata-receipt-required')
        popup_path=Path(reading_popup_path);popup_before=popup_path.read_bytes()if popup_path.is_file()else None
        reading_rows=json.loads(popup_before)if popup_before is not None else{}
        if not isinstance(reading_rows,dict):raise ValueError('storyCurrentNarrative.reading-popup-table-object-required')
        with CurrentLevelScriptSource(root.parent,gameassembly=gameassembly,metadata=metadata,
                summary_path=Path(source_summary_path),ledger_path=Path(source_ledger_path))as source:
            table_path,table_bytes=source.read_interactive_table()
            interactive_index=interactive_table_parser(table_bytes,strings=source.strings)
            if not isinstance(interactive_index,dict)or not isinstance(interactive_index.get('objectToTemplate'),dict):
                raise ValueError('storyCurrentNarrative.current-interactive-table-required')
            interactive_index=dict(interactive_index,sourceFile=rel_path(table_path))
            for path in paths:
                data=None
                try:
                    data=read_bytes_cached(path);frame=source.frame(path,data)
                    projected=project(frame,component_key=source.narrative_component_key,string_type=source.param_string_type,path=path,data=data,
                        available_story_keys=available_story_keys,reading_rows=reading_rows,
                        interactive_index=interactive_index,reading_popup_path=reading_popup_path)
                except(OSError,ValueError,KeyError,TypeError)as error:
                    audit['failedFiles']+=1
                    if len(audit['failures'])<16:audit['failures'].append(failure(error,path,data))
                    continue
                audit['ownersClosed']+=1;rows.extend(projected)
            audit['sourceAudit']=source.audit()
        if popup_before!=(popup_path.read_bytes()if popup_path.is_file()else None):
            raise ValueError('storyCurrentNarrative.reading-popup-table-drift')
        audit.update(status='partial'if audit['failedFiles']else'stored-configuration-complete',narrativeConfigurationRows=len(rows))
    except(OSError,ValueError,KeyError,TypeError)as error:
        rows=[];audit.update(status='validation_failed',narrativeConfigurationRows=0,
            failedFiles=len(paths),failures=[failure(error)])
        audit.pop('sourceAudit',None)
    rows.sort(key=lambda row:(row['levelId'],row['scriptId'],row['localInteractiveId'],row['storyKey']))
    return rows,audit
