"""Finite marker2 physical gaps, separate from native read width and ownership."""
from __future__ import annotations
import collections
import copy
import struct
from typing import Any
from scripts.game_data.streaming import framing as fmt
from scripts.game_data.streaming import marker2_directory as directory_module
from scripts.game_data.streaming import marker2_native as native
from scripts.game_data.streaming.pairs import bind_pair_row

PHYSICAL_GAP_LENGTHS=(4,6)

def _same(label,expected,actual):
    if expected!=actual:raise ValueError(f'{label}: expected {expected!r}, actual {actual!r}')

def _recheck_selected(data,row,source):
    """Re-derive actual field addresses, not only bytes at supplied offsets."""
    label=f'marker2 row {row["outerRowIndex"]} at {row["outerRowOffset"]}'
    outer=fmt._table_layout(data,row['outerRowOffset'])
    actual_selector,selector_slot,selector_status=directory_module._selector(data,outer,2,source,row['outerRowIndex'])
    for field,value in [('rowSelectorU32',actual_selector),('rowSelectorOffset',selector_slot),
                        ('rowSelectorStatus',selector_status),('rowSelectorLowByte',None if actual_selector is None else actual_selector&255)]:
        _same(f'{label} {field}',row[field],value)
    f3=fmt._field_address(outer,3)
    if f3 is None:raise ValueError(f'{label}: expected present field3, actual absent')
    nested_start=fmt._bounded_anonymous_target(data,f3,label+' field3')
    _same(label+' nested table',row['nestedTableOffset'],nested_start)
    nested=fmt._table_layout(data,nested_start)
    vectors,count=directory_module._parallel_vectors(data,nested,source,label+' nested')
    _same(label+' nested count',row['nestedElementCount'],count)
    index=row['elementIndex']
    if type(index) is not int or not 0<=index<count:raise ValueError(f'{label}: expected element index in [0,{count}), actual {index!r}')
    keys=[fmt._u32(data,vectors[3][0]+4+i*4) for i in range(count)]
    key_offset=vectors[3][0]+4+index*4;marker_offset=vectors[4][0]+4+index;slot=vectors[5][0]+4+index*4
    target=fmt._bounded_anonymous_target(data,slot,label+' target')
    for field,value in [('keyOffset',key_offset),('key',keys[index]),('markerOffset',marker_offset),
                        ('marker',data[marker_offset]),('targetSlotOffset',slot),('targetStart',target),
                        ('rawTargetSlotWordU32',fmt._u32(data,slot)),
                        ('keyOccurrenceCountInTable',collections.Counter(keys)[keys[index]])]:
        _same(label+' '+field,row[field],value)
    return target

def parse_marker2_gaps(data: bytes, *, source: str, family: str, parsed: dict[str,Any],
                      certified_ranges=None, native_layout_validated: bool=False,
                      pair_context: dict[str,Any]|None=None) -> dict[str,Any]:
    """Collect once internally; caller authenticates VFS inputs and paired corpus.

    Unsupported clusters publish no scalar/read projection. Exclusive gaps must
    match the finite4/6 structural profile; their end is not native EOF/sizeof.
    The exact pair-row byte binding is required only for a finite read candidate.
    """
    try:
        if native_layout_validated is not True:
            raise ValueError(f'marker2 native gate: expected exact True, actual {native_layout_validated!r}')
        if family not in ('streaming','init'):
            raise ValueError(f'marker2 family: expected streaming/init, actual {family!r}')
        if not isinstance(parsed,dict):
            raise ValueError(f'marker2 parsed root: expected mapping, actual {type(parsed).__name__}')
        _same('parser family',family,parsed.get('kind'))
        directory=directory_module.collect_marker2_directory(data,source=source,family=family,parsed=parsed,certified_ranges=certified_ranges)
        output=[]
        summary=dict(references=len(directory['rows']),framed=0,unsupported=0,ambiguous=0,
                     physicalGapBytes=0,nativeReadWindowBytes=0,opaqueBytes=0,targetOwnedBytes=0)
        statuses=collections.Counter()
        for row in directory['rows']:
            item={**row,'source':source,'family':family,'targetOwnedBytes':0,'runtimeReceipt':'unresolved'}
            def append(status,reason):
                item.update(status=status,reason=reason)
                output.append(item);statuses[status]+=1
                summary['ambiguous' if status.startswith('ambiguous-') else 'unsupported']+=1
            if not(family=='streaming' and row['rootMarker']==2 and row['rowSelectorU32']==6 and row['key']==0x09020000):
                append('unsupported-context','not selected family/root2/explicit raw6/fullkey09020000');continue
            target=_recheck_selected(data,row,source)
            if row['keyOccurrenceCountInTable']!=1:
                append('ambiguous-key','full key is duplicated in complete nested field3 vector');continue
            if not row['targetOccupancyComplete']:
                append('unsupported-occupancy','unknown marker representation prevents complete target occupancy');continue
            if target>len(data)-4:
                raise ValueError(f'marker2 target at {target}: expected4 readable bytes, actual {max(0,len(data)-target)}')
            gap=row['candidateOpaqueGap'];previous=row['previousCertifiedRange'];following=row['nextCertifiedRange']
            if row['containingCertifiedRanges']:
                raise ValueError(f'marker2 target at {target}: expected disjoint certified structures, actual {row["containingCertifiedRanges"]}')
            if gap is None or previous is None or following is None:
                raise ValueError(f'marker2 target at {target}: expected two independent certified neighbours, actual {previous!r}/{following!r}')
            _same(f'marker2 target at {target} gap start',target,gap['start'])
            if target+4>gap['end']:
                raise ValueError(f'marker2 target at {target}: expected4-byte read not crossing certified start {gap["end"]}, actual end {target+4}')
            occupants=row['gapTargetReferences']
            starts=[]
            for occupant in occupants:
                marker_offset=occupant['markerOffset'];key_offset=occupant['keyOffset'];slot=occupant['targetSlotOffset']
                _same(f'marker2 occupancy marker at {marker_offset}',occupant['marker'],data[marker_offset])
                _same(f'marker2 occupancy key at {key_offset}',occupant['key'],fmt._u32(data,key_offset))
                actual=fmt._bounded_anonymous_target(data,slot,'marker2 occupancy')
                _same(f'marker2 occupancy target at {slot}',occupant['targetStart'],actual)
                starts.append(actual)
            if not starts or target not in starts:raise ValueError(f'marker2 target at {target}: expected own reference in complete occupancy, actual {starts}')
            if len(starts)!=len(set(starts)) or row['targetReferenceCountInFile']!=1:
                append('ambiguous-target','aliased target identity in complete file/gap occupancy');continue
            if any(target<p<target+4 for p in starts):
                append('ambiguous-target','another target starts inside the selected4-byte read window');continue
            if len(starts)>1:
                append('unsupported-cluster','multiple distinct targets in independently bounded opaque cluster');continue
            length=gap['end']-target
            if length not in PHYSICAL_GAP_LENGTHS:
                raise ValueError(f'marker2 target at {target}: expected exclusive physical gap length4 or6, actual {length}; unknown exclusive profile')
            if not isinstance(pair_context,dict):raise ValueError(f'marker2 target at {target}: expected structured current source-pair context, actual {pair_context!r}')
            _same('marker2 pair source',source,pair_context.get('source'))
            pair_row=bind_pair_row(data,row,pair_context)
            item.update(status='framed',pairRow=pair_row,
                physicalGapRange={'start':target,'end':gap['end'],'length':length},
                nativeReadWindowRange={'start':target,'end':target+4,'length':4},
                anonymousU32=struct.unpack_from('<I',data,target)[0],
                residualOpaqueRange=({'start':target+4,'end':gap['end'],'length':2,
                    'bytesHex':data[target+4:gap['end']].hex().upper(),'classification':'opaque-not-padding'} if length==6 else None),
                serializedSizeStatus='unknown',nativeEofStatus='unresolved')
            output.append(item);statuses['framed']+=1;summary['framed']+=1
            summary['physicalGapBytes']+=length;summary['nativeReadWindowBytes']+=4;summary['opaqueBytes']+=length-4
        _same('marker2 classification reconciliation',summary['references'],summary['framed']+summary['unsupported']+summary['ambiguous'])
        return dict(status='ambiguous' if summary['ambiguous'] else 'partial' if summary['unsupported'] else 'exact-anonymous-physical-gaps',
            source=source,family=family,profile={**copy.deepcopy(native.PROFILE),'physicalGapLengths':list(PHYSICAL_GAP_LENGTHS)},
            directory=directory,rows=output,summary=summary,statusCounts=dict(statuses),targetOwnedBytes=0,
            evidenceBoundary='Physical gap profile is independently certified geometry, not serialized sizeof/native EOF. Opaque2 bytes allow arbitrary values. Runtime receipt remains unresolved; all other clusters/contexts stay unowned.')
    except (KeyError,TypeError,ValueError,IndexError,struct.error) as exc:
        raise ValueError(f'{source}: {exc}') from exc
