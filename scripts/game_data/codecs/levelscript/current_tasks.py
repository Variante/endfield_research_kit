"""Pure pooled Task cursors; the source operation supplies current authority."""
from scripts.game_data.codecs.levelscript.current_collections import Reader
from scripts.game_data.codecs.levelscript.param_graph import ParamGraphDecodeError


def decode(data,offset,*,strings,capability):
    if (not isinstance(capability,dict)or type(capability.get('countLimit'))is not int
            or capability['countLimit']!=16384 or capability.get('headerBytes')!=4
            or capability.get('taskMemberCount')!=4 or capability.get('conditionMemberCount')!=3
            or capability.get('gameConditionNullOnly')is not True
            or capability.get('positiveGameConditionAdmitted')is not False
            or capability.get('gameConditionNullMarker')!=255
            or capability.get('wholeGrammarAdmitted')is not False or capability.get('profileAdmitted')is not True
            or capability.get('recordGrammar')!='MC4-or-FF;TaskCondition-MC3-or-FF;GameCondition-FF-only'
            or capability.get('sourceWitnessClassArguments')!=['object','object']
            or capability.get('actualCallbackEqualsCanonicalRequired')is not True):
        raise ParamGraphDecodeError('currentTaskMap:complete-current-child-capability-required')
    reader=Reader(data,offset,strings,'taskMap')
    def dictionary(field,read):
        start=reader.offset;count=reader.count(field);entries=[];seen=set()
        for index in range(max(0,count)):
            child=f'{field}[{index}]';at=reader.offset;key=reader.string(child+'.key')
            if key is None:raise ParamGraphDecodeError(f'{child}:null-dictionary-key,offset={at}')
            if key in seen:raise ParamGraphDecodeError(f'{child}:duplicate-key,offset={at},actual={key!r}')
            seen.add(key);value=read(child+'.value')
            entries.append(dict(keyOffset=at,endOffset=reader.offset,key=key,value=value))
        return dict(startOffset=start,endOffset=reader.offset,status='null'if count==-1 else'present',
            count=None if count==-1 else count,entries=None if count==-1 else entries)
    def condition(field):
        start=reader.offset
        if not reader.member(field,3):return None
        at=reader.offset;marker=reader.number('<B',field+'.condition')
        if marker!=255:raise ParamGraphDecodeError(f'{field}.condition:current-positive-GameCondition-unproved,offset={at},actual={marker}')
        main=reader.boolean(field+'.isMainObjective');objective=reader.number('<i',field+'.objectiveEnum')
        return dict(startOffset=start,endOffset=reader.offset,serializedMemberCount=3,
            condition=None,isMainObjective=main,objectiveEnumRaw=objective)
    def task(field):
        start=reader.offset
        if not reader.member(field,4):return None
        tracked=reader.boolean(field+'.canBeTracked');conditions=dictionary(field+'.conditionDict',condition)
        manual=reader.boolean(field+'.needManualCheck');kind=reader.number('<i',field+'.taskType')
        return dict(startOffset=start,endOffset=reader.offset,serializedMemberCount=4,canBeTracked=tracked,
            conditionDict=conditions,needManualCheck=manual,taskTypeRaw=kind)
    row=dictionary('taskMap',task)
    row.update(sourceBoundary='conditional',sourceWitnessClassArguments=['object','object'],
        actualCallbackEqualsCanonicalRequired=True,runtimeSelectionObserved=False,
        positiveGameConditionAdmitted=False)
    return row,reader.offset
