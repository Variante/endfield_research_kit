"""NPC child decoding selected only by an active current LevelScript owner."""
import copy
import hashlib
import struct
from pathlib import Path

from scripts.game_data.codecs.leveldata.npc_runtime import _Reader,LevelNpcCodecError
from scripts.game_data.memorypack.leveldata_npc_child_sources import PLANS,PARENTS


def _layout(base,declared,capability,battle=None,extra=None):
    if (not isinstance(capability,dict)or capability.get('profileId')!='current-owner-npc-children'
            or capability.get('positiveReferenceFields')!=PARENTS or capability.get('nullMarker')!=255
            or capability.get('profileAdmitted')is not True or capability.get('wholeGrammarAdmitted')is not False
            or capability.get('requiresFreshCurrentOwnerScope')is not True
            or capability.get('liveFormatterSelectionObserved')is not False):
        raise LevelNpcCodecError('current-owner-npc-child-capability',None,'fresh independent child profile',capability)
    expected=copy.deepcopy(base)
    for name,plan in PLANS.items():
        if name in expected['records']:raise LevelNpcCodecError('current-owner-npc-old-record-collision',None,None,name)
        expected['records'][name]=[dict(name=field,type=type_name,wire=wire)for field,type_name,wire in plan]
    for field,type_name in PARENTS.items():
        rows=[r for r in expected['root']if r['name']==field]
        if len(rows)!=1 or (rows[0]['type'],rows[0]['wire'])!=(type_name,'null'):
            raise LevelNpcCodecError('current-owner-npc-old-null-profile',None,field,rows)
        rows[0].update(wire='record',nullable=True)
    if battle is not None:
        from scripts.game_data.memorypack.leveldata_npc_battle_layout import extend_layout
        expected=extend_layout(expected,battle)
    if extra is not None:
        from scripts.game_data.memorypack.leveldata_npc_extra_sources import extend_layout
        expected=extend_layout(expected,extra)
    if declared!=expected:raise LevelNpcCodecError('current-owner-npc-exact-layout')
    return expected


def _current_npc_decoder(owner,original):
    """Internal pure reader; its authority is the active opaque owner operation."""
    from scripts.game_data.memorypack.levelscript_current_source import require_framing_owner
    def require():require_framing_owner(owner,strings=owner.strings)
    require()
    if any(not hasattr(original,key)for key in('pool_root','native_inputs','native_sources','native_layout')):
        raise LevelNpcCodecError('current-owner-npc-base-operation')
    if (Path(original.pool_root).resolve()!=Path(owner.strings.root).resolve()
            or original.native_inputs!=owner.proof['nativeInputs']
            or original.native_sources!=owner.proof['nativeSources']):
        raise LevelNpcCodecError('current-owner-npc-base-operation')
    caps=owner.host_caps
    if not isinstance(caps,dict):raise LevelNpcCodecError('current-owner-npc-host-capabilities')
    cap=caps.get('npcChildProfile');declared=caps.get('npcLayout');battle=caps.get('npcBattleProfile');extra=caps.get('npcExtraProfile')
    if cap is None:
        if declared!=original.native_layout or battle is not None or extra is not None:raise LevelNpcCodecError('current-owner-npc-missing-child-capability')
        return original
    layout=_layout(original.native_layout,declared,cap,battle,extra)
    if battle is None and extra is None:reader=_Reader(owner.strings,layout)
    else:
        from scripts.game_data.codecs.leveldata.current_npc import CurrentNpcReader
        reader=CurrentNpcReader(owner.strings,layout,battle or{},require)
    conditions=[dict(typeName=name,actualCallbackEqualsProvedChildRequired=True,
        runtimeFormatterSelectionObserved=False)for name in PLANS]
    if battle is not None:
        conditions.extend(dict(typeName=row['typeName'],actualCallbackEqualsProvedChildRequired=True,
            runtimeFormatterSelectionObserved=False)for row in battle['records'].values())
        conditions.append(dict(typeName=battle['dataPairChild']['typeName'],
            actualCallbackEqualsProvedChildRequired=True,runtimeFormatterSelectionObserved=False))
    if extra is not None:
        conditions.extend(dict(typeName=name,actualCallbackEqualsProvedChildRequired=True,
            runtimeFormatterSelectionObserved=False)for name in extra['records'])
    def decode(data,offset,index=0):
        require()
        try:return reader.row(data,offset,index)
        except LevelNpcCodecError as error:
            error.diagnostic['sourceSha256']=hashlib.sha256(data).hexdigest().upper();raise
    def count(data,offset,kind):
        require()
        if not isinstance(data,bytes):raise LevelNpcCodecError('immutable-source-required',offset,'bytes',type(data).__name__)
        if kind not in layout['containerKinds']:raise LevelNpcCodecError('current-owner-npc-container',offset,None,kind)
        value,end=reader.number(data,offset,kind+'.count',lambda b,o:(struct.unpack_from('<i',b,o)[0],o+4)
            if 0<=o<=len(b)-4 else None)
        if value < -1 or value>16384 or value>len(data)-end:
            raise LevelNpcCodecError(kind+'.count',offset,'-1 or bounded count <=16384',value)
        return value,end
    def collection(data,offset):
        start=offset;n,offset=count(data,offset,'list');rows=[]
        for i in range(max(n,0)):
            row,offset=decode(data,offset,i);rows.append(row)
        return dict(startOffset=start,endOffset=offset,count=n,value=None if n==-1 else rows,rows=rows,
            memberPartition=layout['memberPartition'],conditionalChildSources=copy.deepcopy(conditions),
            evidenceBoundary='Conditional current owner NPC child profile; stored values only.')
    def dictionary(data,offset,*,key_wire):
        start=offset;n,offset=count(data,offset,key_wire+'-dictionary');entries=[];seen=set()
        try:
            for i in range(max(n,0)):
                key_at=offset
                if key_wire=='pool':key,offset=reader.string(data,offset,f'npcs[{i}].key')
                elif key_wire=='uint':key,offset=reader.number(data,offset,f'npcs[{i}].key',lambda b,o:
                    (struct.unpack_from('<I',b,o)[0],o+4)if 0<=o<=len(b)-4 else None)
                else:raise LevelNpcCodecError('dictionary-key-wire',offset,None,key_wire)
                if key is None or key in seen:raise LevelNpcCodecError('npc-dictionary-key',key_at,'nonnull unique key',key)
                seen.add(key);row,offset=decode(data,offset,i)
                entries.append(dict(key=key,keyOffset=key_at,valueOffset=row['startOffset'],value=row))
        except LevelNpcCodecError as error:error.partial_entries=entries;error.entry_count=n;raise
        return dict(startOffset=start,endOffset=offset,count=n,entries=None if n==-1 else entries,
            status='null'if n==-1 else'present',conditionalChildSources=copy.deepcopy(conditions)),offset
    decode.collection=collection;decode.dictionary=dictionary
    decode.pool_root=original.pool_root;decode.native_inputs=original.native_inputs
    decode.native_sources=original.native_sources;decode.native_layout=layout
    decode.current_profile_conditions=copy.deepcopy(conditions)
    return decode
