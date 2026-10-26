"""Pure current LevelData43 cursor with explicit reached-child capabilities.

Only the selected source operation may grant provenance or owner authority.
This cursor never scans a suffix, invokes a native opener or falls back to a
historical record layout. A field without a current child capability stops the
single cursor before that child's bytes can be assigned to a later field.
"""
from scripts.game_data.codecs.levelscript.current_collections import Reader as GraphReader
from scripts.game_data.codecs.levelscript.param_graph import ParamGraphDecodeError
from scripts.game_data.codecs.leveldata.current_levelscript import decode_brief_dictionary,decode_spawner_list
from scripts.game_data.leveldata_binary import LEVELDATA_FIELDS

ROOT='Beyond.Gameplay.LevelData'
BRIEF='Beyond.Gameplay.LevelScriptBriefData'
GROUP='Beyond.Gameplay.AirWallGroup'
CHECK='Beyond.Gameplay.AirWallCheckData'
RANGE='Beyond.Gameplay.ThreeDimRange'
POLY='Beyond.Gameplay.PolyLineWall'
TOTAL='Beyond.Gameplay.MissionTotalCheckData'
MISSION='Beyond.Gameplay.MissionCheckData'
LIST=lambda name:'System.Collections.Generic.List`1<'+name+'>'
EMPTY_RECORDS={
    'factoryPredefineData':('Beyond.Gameplay.LevelFactoryPredefineData',('powerGates',)),
    'functionArea':('Beyond.Gameplay.LevelFunctionAreaData',('baseData','functionAreaConditions','ranges','specificDatas')),
    'safeZone':('Beyond.Gameplay.LevelSafeZoneData',('boxes',)),
}
NULL_OBJECTS={
    'blackbox':'Beyond.Gameplay.LevelDataBlackbox',
    'buildableCondition':'Beyond.Gameplay.ConditionRuntimeBase',
    'specificData':'Beyond.Gameplay.LevelSpecificData',
}


class Reader(GraphReader):
    def __init__(self,data,strings,capabilities,npc_decoder=None):
        condition_cap=capabilities.get('records',{}).get(NULL_OBJECTS['buildableCondition'])
        if isinstance(condition_cap,dict)and condition_cap.get('profileAdmitted')is not True:condition_cap=None
        super().__init__(data,0,strings,ROOT,condition_cap=condition_cap);self.caps=capabilities;self.npc_decoder=npc_decoder

    def refuse(self,field,gate,actual=None):
        raise ParamGraphDecodeError(f'{field}:{gate},offset={self.offset},actual={actual}')

    def cap(self,kind,name):
        cap=self.caps.get(kind,{}).get(name)
        if not isinstance(cap,dict):self.refuse(name,'missing-current-child-capability')
        return cap

    def header(self,name,count,field):
        cap=self.cap('records',name)
        if type(cap.get('memberCount'))is not int or cap['memberCount']!=count:self.refuse(field,'current-record-member-capability',cap)
        self.need(1,field+'.memberCount');marker=self.data[self.offset]
        if marker==255:
            if cap.get('nullAdmitted')is not True:self.refuse(field,'current-record-null-unproved')
            self.offset+=1;return False
        if cap.get('positiveAdmitted')is not True:self.refuse(field,'current-positive-record-unproved')
        if marker!=count:self.refuse(field,'member-count',marker)
        self.offset+=1;return True

    def count_for(self,owner,name,*,type_name=None):
        field=owner+'::'+name;cap=self.cap('collections',field)
        if cap.get('headerBytes')!=4 or type(cap.get('countLimit'))is not int or cap['countLimit']<0:
            self.refuse(field,'current-count-capability',cap)
        if type_name is not None and cap.get('typeName')!=type_name:
            self.refuse(field,'current-closed-collection-type',cap.get('typeName'))
        start=self.offset;count=self.number('<i',field+'.count')
        allowed=cap.get('allowedCounts')
        if (count < -1 or count>cap['countLimit']or(allowed is not None and count not in allowed)):
            self.refuse(field,'current-count-refused',count)
        return start,count

    def list(self,owner,name,child=None,*,type_name=None):
        start,count=self.count_for(owner,name,type_name=type_name);rows=[]
        if count>0 and child is None:self.refuse(owner+'::'+name,'positive-elements-unproved',count)
        for index in range(max(0,count)):rows.append(child(f'{owner}::{name}[{index}]'))
        return dict(startOffset=start,endOffset=self.offset,count=count,rows=None if count==-1 else rows)

    def range(self,field):
        start=self.offset
        if not self.header(RANGE,2,field):return None
        center=[self.single(field+'.m_center.'+axis)for axis in'xyz']
        size=[self.single(field+'.m_size.'+axis)for axis in'xyz']
        return dict(startOffset=start,endOffset=self.offset,center=center,size=size)

    def mission_check(self,field):
        start=self.offset
        if not self.header(MISSION,4,field):return None
        row=dict(startOffset=start,detailStateRaw=self.number('<i',field+'.detailState'),
            id=self.string(field+'.id'),isQuest=self.boolean(field+'.isQuest'),isSame=self.boolean(field+'.isSame'))
        row['endOffset']=self.offset;return row

    def mission_total(self,field):
        start=self.offset
        if not self.header(TOTAL,4,field):return None
        down=self.list(TOTAL,'downReason',self.mission_check,type_name=LIST(MISSION))
        down_any=self.boolean(field+'.isDownAny');rise_any=self.boolean(field+'.isRiseAny')
        rise=self.list(TOTAL,'riseReason',self.mission_check,type_name=LIST(MISSION))
        return dict(startOffset=start,endOffset=self.offset,downReason=down,isDownAny=down_any,
            isRiseAny=rise_any,riseReason=rise)

    def airwall_check(self,field):
        start=self.offset
        if not self.header(CHECK,2,field):return None
        kind=self.number('<i',field+'.checkType');mission=self.mission_total(field+'.missionData')
        return dict(startOffset=start,endOffset=self.offset,checkTypeRaw=kind,missionData=mission)

    def vector2(self,field):
        return [self.single(field+'.'+axis)for axis in'xy']

    def polyline(self,field):
        start=self.offset
        if not self.header(POLY,10,field):return None
        bounds=self.range(field+'.bounds');disabled=self.boolean(field+'.disableDefaultEffect')
        nav=self.boolean(field+'.enableNavObstacle');height=self.vector2(field+'.heightRange')
        effect=self.string(field+'.overrideEffectId')
        positions=self.list(POLY,'posList',self.vector2,type_name=LIST('UnityEngine.Vector2'))
        push=self.single(field+'.pushDis');warn=self.single(field+'.pushWarnDis')
        usage=self.number('<i',field+'.usage');visual=self.vector2(field+'.visualHeightRange')
        return dict(startOffset=start,endOffset=self.offset,bounds=bounds,disableDefaultEffect=disabled,
            enableNavObstacle=nav,heightRange=height,overrideEffectId=effect,posList=positions,
            pushDis=push,pushWarnDis=warn,usageRaw=usage,visualHeightRange=visual)

    def airwall(self,field):
        start=self.offset
        if not self.header(GROUP,8,field):return None
        bounds=self.range(field+'.bounds');check=self.airwall_check(field+'.checkData')
        default=self.boolean(field+'.defaultOn');identity=self.number('<Q',field+'.groupId')
        walls=self.list(GROUP,'polyLineWalls',self.polyline,type_name=LIST(POLY))
        radio=self.string(field+'.pushBackRadioId');script=self.number('<Q',field+'.scriptId')
        slot=self.number('<I',field+'.slotId')
        return dict(startOffset=start,endOffset=self.offset,bounds=bounds,checkData=check,defaultOn=default,
            groupId=str(identity),polyLineWalls=walls,pushBackRadioId=radio,scriptId=str(script),slotId=slot)

    def empty_record(self,name):
        original,fields=EMPTY_RECORDS[name];start=self.offset
        if name in('safeZone','factoryPredefineData'):
            selected=self.cap('records',original)
            if 'profileAdmitted'in selected or 'capability'in selected:
                from scripts.game_data.codecs.leveldata import current_auxiliary_container as auxiliary
                auxiliary.validate(selected)
                if selected['typeName']!=original or selected['parentBinding']['fieldName']!=name:
                    self.refuse(name,'current-positive-auxiliary-parent-profile')
                return auxiliary.read(self,ROOT+'::'+name,selected)
        base_child=range_child=condition_child=specific_child=None
        base_factory_hide=None
        if name=='functionArea':
            from scripts.game_data.memorypack import leveldata_function_area_sources as area
            from scripts.game_data.codecs.leveldata.current_function_area import read,validate
            selected=self.cap('collections',original+'::baseData')
            if selected.get('profileAdmitted')is True:
                parent=self.cap('records',original);child=self.cap('records',area.TYPE)
                validate(child);binding=selected.get('childBinding',{})
                if child['positiveFactoryHideDescAdmitted']:base_factory_hide=child['factoryHideCapability']
                ranges=self.cap('collections',original+'::ranges');positive_ranges=ranges.get('profileAdmitted')is True
                condition_list=self.cap('collections',original+'::functionAreaConditions')
                positive_conditions=condition_list.get('profileAdmitted')is True
                specific_list=self.cap('collections',original+'::specificDatas')
                positive_specific=specific_list.get('profileAdmitted')is True
                if (selected.get('typeName')!=LIST(area.TYPE)or selected.get('headerBytes')!=4
                        or type(selected.get('countLimit'))is not int or selected['countLimit']!=area.LIMIT
                        or selected.get('allowedCounts')is not None or selected.get('wholeGrammarAdmitted')is not False
                        or selected.get('actualCallbackEqualsProvedChildRequired')is not True
                        or selected.get('liveFormatterSelectionObserved')is not False
                        or parent.get('positiveChildFields')!=['baseData']+(['functionAreaConditions']if positive_conditions else[])+(['ranges']if positive_ranges else[])+(['specificDatas']if positive_specific else[])
                        or parent.get('otherPositiveChildElementsAdmitted')is not False
                        or (binding.get('fieldName'),binding.get('typeName'),binding.get('capability'))!=('baseData',LIST(area.TYPE),area.CAP)
                        or type(binding.get('readerMethodDefinition'))is not int or binding['readerMethodDefinition']<0
                        or type(binding.get('sourceTargetRva'))is not int or binding['sourceTargetRva']<=0):
                    self.refuse(name,'current-function-area-base-parent-profile')
                base_child=lambda field,selected_child=child:read(self,field,selected_child)
                if positive_conditions:
                    from scripts.game_data.memorypack import leveldata_condition_components as condition_source
                    from scripts.game_data.codecs.leveldata.current_condition import read_area,validate_area
                    condition=self.cap('records',condition_source.TYPE);record=self.cap('records',condition_source.AREA_RECORD)
                    validate_area(record,condition);binding=condition_list.get('childBinding',{})
                    if (condition_list.get('typeName')!=LIST(condition_source.AREA_RECORD)or condition_list.get('headerBytes')!=4
                            or type(condition_list.get('countLimit'))is not int or condition_list['countLimit']!=condition_source.COUNT_LIMIT
                            or condition_list.get('allowedCounts')is not None or condition_list.get('wholeGrammarAdmitted')is not False
                            or condition_list.get('actualCallbackEqualsProvedChildRequired')is not True
                            or condition_list.get('liveFormatterSelectionObserved')is not False
                            or(binding.get('fieldName'),binding.get('typeName'),binding.get('capability'))!=(
                                'functionAreaConditions',LIST(condition_source.AREA_RECORD),'story-function-area-condition')
                            or type(binding.get('readerMethodDefinition'))is not int or binding['readerMethodDefinition']<0
                            or type(binding.get('sourceTargetRva'))is not int or binding['sourceTargetRva']<=0):
                        self.refuse(name,'current-function-area-condition-parent-profile')
                    condition_child=lambda field,record=record,condition=condition:read_area(self,field,record,condition)
                elif condition_list.get('countLimit')!=0 or condition_list.get('allowedCounts')!=[-1,0]:
                    self.refuse(name,'current-function-area-condition-profile-required')
                if positive_ranges:
                    binding=ranges.get('childBinding',{});child=self.cap('records',RANGE)
                    if (ranges.get('typeName')!=LIST(RANGE)or ranges.get('headerBytes')!=4
                            or type(ranges.get('countLimit'))is not int or ranges['countLimit']!=area.LIMIT
                            or ranges.get('allowedCounts')is not None or ranges.get('wholeGrammarAdmitted')is not False
                            or ranges.get('actualCallbackEqualsProvedChildRequired')is not True
                            or ranges.get('liveFormatterSelectionObserved')is not False
                            or (binding.get('fieldName'),binding.get('typeName'),binding.get('capability'))!=('ranges',LIST(RANGE),'story-function-area-range')
                            or type(binding.get('readerMethodDefinition'))is not int or binding['readerMethodDefinition']<0
                            or type(binding.get('sourceTargetRva'))is not int or binding['sourceTargetRva']<=0
                            or type(child.get('memberCount'))is not int or child['memberCount']!=2
                            or child.get('nullAdmitted')is not True or child.get('positiveAdmitted')is not True):
                        self.refuse(name,'current-function-area-range-parent-profile')
                    range_child=self.range
                elif ranges.get('countLimit')!=0 or ranges.get('allowedCounts')!=[-1,0]:
                    self.refuse(name,'current-function-area-range-profile-required')
                if positive_specific:
                    from scripts.game_data.memorypack import leveldata_function_specific_components as specific_source
                    from scripts.game_data.memorypack.leveldata_function_specific_complex_sources import ENTRY_CAP
                    from scripts.game_data.memorypack.leveldata_condition_components import CAP as CONDITION_CAP
                    from scripts.game_data.codecs.leveldata import current_function_specific as specific_codec
                    specific=self.cap('records',specific_source.TYPE);specific_codec.validate(specific)
                    binding=specific_list.get('childBinding',{});proved=specific['listParent']
                    if (specific.get('profileId')not in('complex4','all18')or specific.get('owningConditionGraphJoined')is not True
                            or specific_list.get('typeName')!=specific_source.LIST or specific_list.get('headerBytes')!=4
                            or type(specific_list.get('countLimit'))is not int or specific_list['countLimit']!=specific_source.COUNT_LIMIT
                            or specific_list.get('allowedCounts')is not None or specific_list.get('wholeGrammarAdmitted')is not False
                            or specific_list.get('actualCallbackEqualsProvedChildRequired')is not True
                            or specific_list.get('liveFormatterSelectionObserved')is not False
                            or(binding.get('fieldName'),binding.get('typeName'),binding.get('capability'))!=(
                                'specificDatas',specific_source.LIST,specific_source.LIST_CAP)
                            or type(binding.get('readerMethodDefinition'))is not int or type(binding.get('sourceTargetRva'))is not int
                            or(binding['readerMethodDefinition'],binding['sourceTargetRva'])!=(proved['readerMethodDefinition'],proved['sourceTargetRva'])):
                        self.refuse(name,'current-function-area-specific-parent-profile')
                    if self.condition_cap is None:self.refuse(name,'current-function-area-owning-condition-profile-required')
                    entry=specific['routes']['14']['capability']['childCapabilities'][ENTRY_CAP]
                    from scripts.game_data.codecs.leveldata.current_function_specific_complex import condition_for_reader
                    condition_for_reader(self,entry['childCapabilities'][CONDITION_CAP])
                    specific_child=lambda field,cap=specific:specific_codec.read(self,field,cap)
                elif specific_list.get('countLimit')!=0 or specific_list.get('allowedCounts')!=[-1,0]:
                    self.refuse(name,'current-function-area-specific-profile-required')
            elif selected.get('countLimit')!=0 or selected.get('allowedCounts')!=[-1,0]:
                self.refuse(name,'current-function-area-base-profile-required')
            elif self.cap('collections',original+'::ranges').get('profileAdmitted')is True:
                self.refuse(name,'current-function-area-base-profile-required')
            elif self.cap('collections',original+'::functionAreaConditions').get('profileAdmitted')is True:
                self.refuse(name,'current-function-area-base-profile-required')
            elif self.cap('collections',original+'::specificDatas').get('profileAdmitted')is True:
                self.refuse(name,'current-function-area-base-profile-required')
        if not self.header(original,len(fields),ROOT+'::'+name):return None
        children={field:self.list(original,field,base_child if field=='baseData'else range_child if field=='ranges'else condition_child if field=='functionAreaConditions'else specific_child if field=='specificDatas'else None,
            type_name=LIST(area.TYPE)if field=='baseData'and base_child is not None else LIST(RANGE)if field=='ranges'and range_child is not None
            else LIST(condition_source.AREA_RECORD)if field=='functionAreaConditions'and condition_child is not None
            else specific_source.LIST if field=='specificDatas'and specific_child is not None else None)for field in fields}
        result=dict(startOffset=start,endOffset=self.offset,fields=children)
        if base_child is not None:
            result['conditionalChildSources']=[dict(typeName=area.TYPE,actualCallbackEqualsProvedChildRequired=True,
                positiveFactoryHideDescAdmitted=base_factory_hide is not None,runtimeFormatterSelectionObserved=False)]
            if base_factory_hide is not None:
                from scripts.game_data.memorypack import leveldata_factory_hide_sources as hide_source
                callback=base_factory_hide['enumCallback'];enum_list=base_factory_hide['enumList']
                result['conditionalChildSources'].append(dict(typeName=hide_source.TYPE,
                    actualCallbackEqualsProvedChildRequired=True,actualNominalEnumCallbackRequired=True,
                    runtimeFormatterSelectionObserved=False,nominalEnumType=hide_source.ENUM,
                    callbackConditions=callback['conditions'],listConditions=enum_list['conditions'],
                    actualRuntimeSelectionObserved=callback['actualRuntimeSelectionObserved'],
                    unconditionalCallbackSelectionProved=callback['unconditionalCallbackSelectionProved']))
            if range_child is not None:result['conditionalChildSources'].append(dict(typeName=RANGE,
                actualCallbackEqualsProvedChildRequired=True,runtimeFormatterSelectionObserved=False))
            if condition_child is not None:result['conditionalChildSources'].append(dict(typeName=condition_source.TYPE,
                admittedRouteTags=condition['admittedRouteTags'],countLimit=condition['countLimit'],nodeLimit=condition['nodeLimit'],
                depthLimit=condition['depthLimit'],actualCallbackEqualsProvedChildRequired=True,runtimeFormatterSelectionObserved=False))
            if specific_child is not None:result['conditionalChildSources'].append(dict(typeName=specific_source.TYPE,
                profileId=specific['profileId'],admittedRouteTags=specific['admittedRouteTags'],countLimit=specific['countLimit'],
                nodeLimit=specific['nodeLimit'],actualCallbackEqualsProvedChildRequired=True,runtimeFormatterSelectionObserved=False))
        return result

    def null_object(self,name):
        original=NULL_OBJECTS[name];cap=self.cap('records',original)
        if name=='blackbox'and cap.get('profileAdmitted')is True:
            return self.factory_config(name)
        if name=='buildableCondition'and cap.get('profileAdmitted')is True:
            from scripts.game_data.codecs.leveldata.current_condition import read,validate_parent
            validate_parent(cap,ROOT,name);return read(self,ROOT+'::'+name,cap)
        if name=='specificData'and cap.get('profileAdmitted')is True:
            from scripts.game_data.codecs.leveldata.current_specific import read
            return read(self,ROOT+'::'+name,cap)
        if cap.get('nullAdmitted')is not True or cap.get('positiveAdmitted')is not False:
            self.refuse(name,'exact-current-null-only-capability',cap)
        marker=self.number('<B',ROOT+'::'+name)
        if marker!=255:self.refuse(name,'positive-object-unproved',marker)
        return None

    def brief_dictionary(self):
        # Capabilities are required even for an FF/null value. The independent
        # source operation supplies the root parent and all three child kinds.
        cap=self.cap('records',BRIEF)
        if (type(cap.get('memberCount'))is not int or cap['memberCount']!=9
                or cap.get('nullAdmitted')is not True or cap.get('positiveAdmitted')is not True):
            self.refuse(BRIEF,'complete-current-Brief-capability',cap)
        for name in('interactiveActiveRiskEntityIdList','properties','propertyIdToKeyMap','refWorldEntityIdList'):
            child=self.cap('collections',BRIEF+'::'+name)
            if child.get('wholeGrammarAdmitted')is not True or child.get('countLimit')!=16384:
                self.refuse(BRIEF+'::'+name,'complete-current-Brief-child',child)
        start=self.offset;self.count_for(ROOT,'levelScriptBriefDataDict',
            type_name='System.Collections.Generic.Dictionary`2<ulong,'+BRIEF+'>')
        row=decode_brief_dictionary(self.data,start,strings=self.strings);self.offset=row['endOffset'];return row

    def string_dictionary(self):
        start,count=self.count_for(ROOT,'levelScriptDataPathDict',
            type_name='System.Collections.Generic.Dictionary`2<ulong,string>')
        rows=[];seen=set()
        for index in range(max(0,count)):
            at=self.offset;key=self.number('<Q','levelScriptDataPathDict.key')
            if key in seen:self.refuse('levelScriptDataPathDict','duplicate-key',key)
            seen.add(key);value=self.string('levelScriptDataPathDict.value')
            rows.append(dict(keyOffset=at,endOffset=self.offset,key=str(key),value=value))
        return dict(startOffset=start,endOffset=self.offset,count=count,entries=None if count==-1 else rows)

    def ulong_list(self):
        return self.list(ROOT,'autoSpawnedInteractives',lambda field:str(self.number('<Q',field)),type_name=LIST('ulong'))

    def interactives(self):
        record=self.cap('records','Beyond.Gameplay.LevelInteractiveData')
        grammar=record.get('recordGrammar')
        if grammar=='MC25-or-FF;bounded-condition-runtime':
            from scripts.game_data.codecs.leveldata.current_condition import validate_parent
            if record.get('conditionCapability')!='story-condition-runtime' or self.condition_cap is None:
                self.refuse('interactives','current-interactive-condition-profile-required')
            validate_parent(self.condition_cap,'Beyond.Gameplay.LevelInteractiveData','progressLockCondition')
        elif grammar!='MC25-or-FF;condition-FF-only'or self.condition_cap is not None:
            self.refuse('interactives','current-interactive-grammar',record)
        return self.list(ROOT,'interactives',self.record,type_name=LIST('Beyond.Gameplay.LevelInteractiveData'))

    def spawners(self):
        cap=self.cap('records','Beyond.Gameplay.LevelSpawnerInstData')
        if (type(cap.get('memberCount'))is not int or cap['memberCount']!=6
                or cap.get('nullAdmitted')is not True or cap.get('positiveAdmitted')is not True):
            self.refuse('spawners','complete-current-spawner-capability',cap)
        start=self.offset;self.count_for(ROOT,'spawners',type_name=LIST('Beyond.Gameplay.LevelSpawnerInstData'))
        row=decode_spawner_list(self.data,start,strings=self.strings);self.offset=row['endOffset'];return row

    def npc_patrol(self):
        from scripts.game_data.codecs.leveldata.patrol import _decode_npc_patrol_list
        original='Beyond.Gameplay.AI.Config.NpcPatrolData'
        cap=self.cap('collections',ROOT+'::npcPatrol');layout=self.caps.get('patrolLayout')
        if (not isinstance(layout,dict)or layout.get('root')!=original
                or type(layout.get('countLimit'))is not int or layout['countLimit']!=4096
                or cap.get('wholeGrammarAdmitted')is not True or cap.get('countLimit')!=4096):
            self.refuse('npcPatrol','current-nominal-Patrol-layout')
        start=self.offset;self.count_for(ROOT,'npcPatrol',type_name=LIST(original))
        row=_decode_npc_patrol_list(self.data,start,strings=self.strings,layout=layout)
        self.offset=row['endOffset'];return row

    def core_patrol(self):
        from scripts.game_data.memorypack import leveldata_core_patrol_sources as source
        from scripts.game_data.codecs.leveldata import current_core_patrol as codec
        selected=self.cap('collections',ROOT+'::patrols')
        if selected.get('countLimit')==0 and selected.get('allowedCounts')==[-1,0]:return self.list(ROOT,'patrols')
        cap=self.cap('records',source.ROOT);codec.validate(cap)
        if (selected.get('typeName')!=source.LIST(source.ROOT)or type(selected.get('headerBytes'))is not int or selected['headerBytes']!=4
                or type(selected.get('countLimit'))is not int or selected['countLimit']!=source.LIMIT
                or selected.get('allowedCounts')is not None or selected.get('profileAdmitted')is not True
                or selected.get('wholeGrammarAdmitted')is not False or selected.get('liveFormatterSelectionObserved')is not False
                or selected.get('actualCallbackEqualsProvedChildRequired')is not True or selected.get('initiallyNullListRequired')is not True
                or selected.get('childBinding')!=cap['parentBinding']):
            self.refuse('patrols','current-Core-Patrol-parent-profile')
        row=codec.read(self,'patrols',cap)
        row['conditionalChildSources']=[dict(typeName=name,actualCallbackEqualsProvedChildRequired=True,
            initiallyNullListsRequired=True,runtimeFormatterSelectionObserved=False,
            controllerConversionProved=False,actionDispatchProved=False,checkpointProducerProved=False,
            playbackProved=False)for name in(source.ROOT,source.ACTION,source.SUBACTION)]
        row['conditionalChildSources'].append(dict(typeName=source.LIST(source.VECTOR),countLimit=source.LIMIT,
            elementWireBytes=12,elementRecordHeaderBytes=0,initiallyNullListRequired=True,
            actualCallbackEqualsProvedChildRequired=True,runtimeFormatterSelectionObserved=False))
        row['conditionalChildSources'].append(dict(typeName='Beyond.Blackboard+DataPair',managedBytes=32,
            positiveWireBytes=18,nullWireBytes=1,nullReturnsDefaultValue=True,
            actualCallbackEqualsProvedChildRequired=True,runtimeFormatterSelectionObserved=False))
        return row

    def factory_config(self,name):
        from scripts.game_data.memorypack import leveldata_factory_config_sources as source
        from scripts.game_data.codecs.leveldata import current_factory_config as codec
        if name not in('blackbox','predefinedParams'):self.refuse(name,'closed-current-factory-config-host')
        if name=='predefinedParams':
            selected=self.cap('collections',ROOT+'::'+name)
            if selected.get('countLimit')==0 and selected.get('allowedCounts')==[-1,0]:return self.list(ROOT,name)
        cap=self.cap('records',source.BLACKBOX);codec.validate(cap)
        if name=='predefinedParams':
            if (selected.get('typeName')!=source.LIST(source.PREDEFINED_HOST)
                    or type(selected.get('headerBytes'))is not int or selected['headerBytes']!=4
                    or type(selected.get('countLimit'))is not int or selected['countLimit']!=source.LIMIT
                    or selected.get('allowedCounts')is not None or selected.get('profileAdmitted')is not True
                    or selected.get('wholeGrammarAdmitted')is not False or selected.get('liveFormatterSelectionObserved')is not False
                    or selected.get('actualCallbackEqualsProvedChildRequired')is not True or selected.get('initiallyNullListRequired')is not True
                    or selected.get('childBinding')!=cap['parentBindings']['predefinedParams']):
                self.refuse(name,'current-factory-config-parent-profile')
        return codec.read(self,ROOT+'::'+name,cap,host_field=name)

    def factory_regions(self):
        from scripts.game_data.memorypack import leveldata_factory_region_sources as source
        from scripts.game_data.codecs.leveldata import current_factory_region as codec
        selected=self.cap('collections',ROOT+'::factoryRegions')
        if selected.get('profileAdmitted')is not True:
            if selected.get('countLimit')!=0 or selected.get('allowedCounts')!=[-1,0]:
                self.refuse('factoryRegions','complete-current-factory-region-profile-required')
            return self.list(ROOT,'factoryRegions')
        cap=self.cap('records',source.REGION);codec.validate(cap)
        if (selected.get('typeName')!=source.LIST(source.REGION)
                or type(selected.get('headerBytes'))is not int or selected['headerBytes']!=4
                or type(selected.get('countLimit'))is not int or selected['countLimit']!=source.LIMIT
                or selected.get('allowedCounts')is not None or selected.get('wholeGrammarAdmitted')is not False
                or selected.get('liveFormatterSelectionObserved')is not False
                or selected.get('actualCallbackEqualsProvedChildRequired')is not True
                or selected.get('initiallyNullListRequired')is not True or selected.get('childBinding')!=cap['parentBinding']):
            self.refuse('factoryRegions','current-factory-region-parent-profile')
        row=codec.read(self,ROOT+'::factoryRegions',cap)
        row['conditionalChildSources']=codec.conditional_sources(cap)
        return row

    def enemy_groups(self):
        from scripts.game_data.memorypack import leveldata_enemy_group_sources as source
        from scripts.game_data.codecs.leveldata import current_enemy_group as codec
        selected=self.cap('collections',ROOT+'::enemyGroup')
        cap=self.cap('records',source.GROUP)if source.GROUP in self.caps.get('records',{})else{}
        full=('profileAdmitted'in selected or'childBinding'in selected
            or'profileAdmitted'in cap or cap.get('capability')==source.CAP)
        if not full:
            if selected.get('countLimit')!=0 or selected.get('allowedCounts')!=[-1,0]:
                self.refuse('enemyGroup','complete-current-enemy-group-profile-required')
            return self.list(ROOT,'enemyGroup')
        codec.validate(cap)
        if (selected.get('typeName')!=source.LIST(source.GROUP)
                or type(selected.get('headerBytes'))is not int or selected['headerBytes']!=4
                or type(selected.get('countLimit'))is not int or selected['countLimit']!=source.LIMIT
                or selected.get('allowedCounts')is not None or selected.get('profileAdmitted')is not True
                or selected.get('wholeGrammarAdmitted')is not False or selected.get('liveFormatterSelectionObserved')is not False
                or selected.get('actualCallbackEqualsProvedChildRequired')is not True
                or selected.get('initiallyNullListRequired')is not True or selected.get('childBinding')!=cap['parentBinding']):
            self.refuse('enemyGroup','current-enemy-group-parent-profile')
        row=codec.read(self,ROOT+'::enemyGroup',cap);row['conditionalChildSources']=codec.conditional_sources(cap)
        return row

    def mission_areas(self):
        from scripts.game_data.memorypack import leveldata_mission_area_sources as source
        from scripts.game_data.codecs.leveldata import current_mission_area as codec
        selected=self.cap('collections',ROOT+'::'+source.FIELD)
        cap=self.cap('records',source.TYPE)if source.TYPE in self.caps.get('records',{})else{}
        full=('profileAdmitted'in selected or'childBinding'in selected
            or'profileAdmitted'in cap or cap.get('capability')==source.CAP)
        if not full:
            if selected.get('countLimit')!=0 or selected.get('allowedCounts')!=[-1,0]:
                self.refuse(source.FIELD,'complete-current-mission-area-profile-required')
            return self.list(ROOT,source.FIELD)
        codec.validate(cap)
        if (selected.get('typeName')!=source.LIST
                or type(selected.get('headerBytes'))is not int or selected['headerBytes']!=4
                or type(selected.get('countLimit'))is not int or selected['countLimit']!=source.LIMIT
                or selected.get('allowedCounts')is not None or selected.get('profileAdmitted')is not True
                or selected.get('wholeGrammarAdmitted')is not False or selected.get('liveFormatterSelectionObserved')is not False
                or selected.get('actualCallbackEqualsProvedChildRequired')is not True
                or selected.get('initiallyNullListRequired')is not True or selected.get('childBinding')!=cap['parentBinding']):
            self.refuse(source.FIELD,'current-mission-area-parent-profile')
        row=codec.read(self,ROOT+'::'+source.FIELD,cap);row['conditionalChildSources']=codec.conditional_sources(cap)
        return row

    def level_wide(self):
        from scripts.game_data.codecs.leveldata import current_levelwide as codec
        name='levelWideConfigs';selected=self.cap('collections',ROOT+'::'+name)
        cap=self.cap('records',codec.TYPE)if codec.TYPE in self.caps.get('records',{})else{}
        full=('profileAdmitted'in selected or'childBinding'in selected
            or'profileAdmitted'in cap or cap.get('capability')==codec.CAP)
        if full:
            codec.validate(cap)
            if (selected.get('typeName')!=codec.TYPE or type(selected.get('headerBytes'))is not int
                    or selected['headerBytes']!=4 or type(selected.get('countLimit'))is not int
                    or selected['countLimit']!=codec.LIMIT or selected.get('allowedCounts')is not None
                    or selected.get('profileAdmitted')is not True or selected.get('wholeGrammarAdmitted')is not False
                    or selected.get('initiallyNullDictionariesRequired')is not True
                    or selected.get('actualCallbackEqualsCanonicalRequired')is not True
                    or selected.get('runtimeFormatterSelectionObserved')is not False
                    or selected.get('childBinding')!=cap['parentBinding']):
                self.refuse(name,'current-levelwide-parent-profile')
            row=codec.read(self,ROOT+'::'+name,cap)
            row['conditionalChildSources']=codec.conditional_sources(cap)
            return row
        if (selected.get('closedPointerEquivalenceProved')is not False
                or selected.get('actualCallbackEqualsCanonicalRequired')is not True
                or selected.get('sourceWitnessClassArguments')!=['object','object']
                or selected.get('typedConstructorAndHelperCompatibilityRequired')is not True
                or selected.get('actualEnumCallbackSelectionObserved')is not False
                or selected.get('providerFactorySelectionObserved')is not False):
            self.refuse(name,'conditional-enum-dictionary-source-required',selected)
        start,count=self.count_for(ROOT,name)
        if count>0:self.refuse(name,'positive-dictionary-unproved',count)
        return dict(startOffset=start,endOffset=self.offset,count=count,conditionalChildSources=[dict(
            typeName=selected['typeName'],count=count,sourceWitnessClassArguments=list(selected['sourceWitnessClassArguments']),
            closedPointerEquivalenceProved=False,actualCallbackEqualsCanonicalRequired=True,
            typedConstructorCompatibilityRequired=count==0,normalHelperCompatibilityRequired=True,
            actualEnumCallbackSelectionObserved=False,providerFactorySelectionObserved=False)])

    def npcs(self):
        original='Beyond.Gameplay.Core.NpcRuntimeProxyData'
        cap=self.cap('collections',ROOT+'::npcs')
        # The earlier independently proved empty profile remains available;
        # the positive profile requires the lexical NPC source gate even for
        # null/empty input and never opens a gate from this pure cursor.
        if cap.get('countLimit')==0 and cap.get('allowedCounts')==[-1,0]:return self.list(ROOT,'npcs')
        if (cap.get('typeName')!=LIST(original)or cap.get('profileAdmitted')is not True
                or cap.get('wholeGrammarAdmitted')is not False or cap.get('requiresFreshNpcSemanticGate')is not True
                or cap.get('countLimit')!=16384 or cap.get('elementType')!=original
                or not callable(getattr(self.npc_decoder,'collection',None))
                or not isinstance(self.caps.get('npcLayout'),dict)
                or type(cap.get('memberCount'))is not int or cap['memberCount']<=0
                or self.caps['npcLayout'].get('memberCount')!=cap['memberCount']
                or getattr(self.npc_decoder,'native_layout',None)!=self.caps['npcLayout']):
            self.refuse('npcs','current-scoped-NPC-profile-required')
        start=self.offset;_,count=self.count_for(ROOT,'npcs',type_name=LIST(original))
        row=self.npc_decoder.collection(self.data,start)
        if (row.get('startOffset')!=start or type(row.get('endOffset'))is not int
                or not self.offset<=row['endOffset']<=len(self.data)
                or type(row.get('count'))is not int or row['count']!=count
                or not isinstance(row.get('rows'),list)or len(row['rows'])!=max(0,count)):
            self.refuse('npcs','current-NPC-child-range',row)
        self.offset=row['endOffset'];return row

    def simple_plan(self,original,field):
        from scripts.game_data.memorypack.leveldata_simple_record_sources import PLANS
        from scripts.game_data.memorypack import leveldata_extended_record_sources as extended
        cap=self.cap('records',original);program=cap.get('program',{})
        positive_polyline=original==extended.ENV and cap.get('positivePolylineProfile')is True
        plan=PLANS.get(original,extended.plan_for(original,positive_polyline)if original in extended.PLANS else None)
        if plan is None:self.refuse(field,'closed-current-record-type',original)
        requirements=sorted({'byte-payload'if kind=='byte-payload'else extended.NULL_CAP if kind=='null-reference'
            else extended.POLY_CAP if kind=='record'else extended.STRING_CAP
            for _,_,kind in plan if kind in('byte-payload','null-reference','pooled-string-list','record')})
        child=lambda kind:'byte-payload'if kind=='byte-payload'else extended.NULL_CAP if kind=='null-reference'else extended.STRING_CAP if kind=='pooled-string-list'else extended.POLY_CAP if kind=='record'else None
        if (cap.get('typeName')!=original or cap.get('profileAdmitted')is not True
                or cap.get('wholeGrammarAdmitted')is not False or cap.get('finiteFloatProfile')is not True
                or cap.get('actualCallbackEqualsProvedChildRequired')is not True
                or cap.get('liveFormatterSelectionObserved')is not False
                or program.get('memberCount')!=len(plan)
                or any(type(r.get('memberIndex'))is not int for r in program.get('reads',[]))
                or [(r.get('memberIndex'),r.get('fieldName'),r.get('kind'),r.get('childCapability'))for r in program.get('reads',[])]!=[
                    (i,n,k,child(k))for i,(n,_,k)in enumerate(plan)]
                or program.get('requiredCapabilities')!=requirements):
            self.refuse(field,'current-finite-record-program',cap)
        bindings=program.get('childBindings')
        expected=[(name,declared,child(kind))for name,declared,kind in plan if kind in('null-reference','pooled-string-list','record')]
        if (not isinstance(bindings,list)or[(r.get('fieldName'),r.get('typeName'),r.get('capability'))for r in bindings]!=expected
                or any(type(r.get('readerMethodDefinition'))is not int or type(r.get('sourceTargetRva'))is not int
                    or r['readerMethodDefinition']<0 or r['sourceTargetRva']<=0 for r in bindings)):
            self.refuse(field,'current-finite-record-child-bindings')
        for binding in bindings:
            if binding['capability']==extended.NULL_CAP:
                if (binding.get('positiveAdmitted'),binding.get('nullMarker'),binding.get('consumedBytes'))!=(False,255,1):
                    self.refuse(field,'current-FF-reference-source')
            elif binding['capability']==extended.POLY_CAP:
                from scripts.game_data.codecs.leveldata.current_polyline import validate
                selected=self.cap('records',extended.POLY);validate(selected)
                if (binding.get('profileAdmitted')is not True or binding.get('wholeGrammarAdmitted')is not(selected.get('wholeGrammarAdmitted')is True)
                        or binding.get('actualCallbackEqualsProvedChildRequired')is not True
                        or (binding['readerMethodDefinition'],binding['sourceTargetRva'])!=(
                            selected.get('referenceReaderMethodDefinition'),selected.get('referenceReaderTargetRva'))):
                    self.refuse(field,'current-positive-polyline-parent-source')
            elif binding.get('countLimit')!=extended.COUNT_LIMIT or binding.get('actualCallbackEqualsPooledStringRequired')is not True:
                self.refuse(field,'current-pooled-list-source')
        if original in extended.PLANS:
            enums=cap.get('enumBackings',{});wanted={n:t for n,t,k in plan if k=='scalar32'and t not in('int','uint')}
            if (cap.get('countLimit')!=extended.COUNT_LIMIT or set(enums)!=set(wanted)
                    or cap.get('nullReferenceTypes')!=([extended.POLY]if original==extended.ENV and not positive_polyline else[])
                    or cap.get('pooledStringListTypes')!=([extended.STRINGS]if any(k=='pooled-string-list'for _,_,k in plan)else[])):
                self.refuse(field,'current-finite-record-child-profile')
            for name,typename in wanted.items():
                enum=enums[name]
                if (enum.get('typeName')!=typename or enum.get('backing')not in('int','uint')
                        or enum.get('field')!=[typename,enum.get('backing'),16]):
                    self.refuse(field,'current-nominal-enum-backing',enum)
        return plan

    def simple_record(self,original,field):
        plan=self.simple_plan(original,field)
        start=self.offset
        if not self.header(original,len(plan),field):return None
        result=dict(startOffset=start,recordType=original,memberCount=len(plan));spans={}
        for name,declared,kind in plan:
            path=field+'.'+name;at=self.offset
            if kind=='byte-payload':value=self.string(path)
            elif kind=='scalar32':
                backing=declared if declared in('int','uint')else self.cap('records',original)['enumBackings'][name]['backing']
                value=self.number('<i'if backing=='int'else'<I',path)
            elif kind=='scalar64-bits'and declared in('long','ulong'):
                value=self.number('<q'if declared=='long'else'<Q',path)
                if declared=='ulong':value=str(value)
            elif kind=='float32-bits'and declared=='float':value=self.single(path)
            elif kind=='unity-vector3-raw12'and declared=='UnityEngine.Vector3':
                value={axis:self.single(path+'.'+axis)for axis in'xyz'}
            elif kind=='bool-byte'and declared=='bool':value=self.boolean(path)
            elif kind=='null-reference':
                marker=self.number('<B',path)
                if marker!=255:self.refuse(path,'current-positive-reference-unproved',marker)
                value=None
            elif kind=='record':
                from scripts.game_data.memorypack.leveldata_extended_record_sources import POLY
                from scripts.game_data.codecs.leveldata.current_polyline import read
                if declared!=POLY:self.refuse(path,'closed-current-positive-child-type',declared)
                value=read(self,path,self.cap('records',POLY))
            elif kind=='pooled-string-list':
                from scripts.game_data.memorypack.leveldata_extended_record_sources import COUNT_LIMIT
                at=self.offset;count=self.number('<i',path+'.count')
                if not -1<=count<=COUNT_LIMIT:self.refuse(path,'current-pooled-list-count',count)
                self.need(max(count,0)*4,path+'.indices')
                values=[self.string(path+f'[{index}]')for index in range(max(0,count))]
                value=dict(startOffset=at,endOffset=self.offset,count=count,rows=None if count==-1 else values)
            else:self.refuse(path,'closed-record-operation',kind)
            result[name]=value;spans[name]=[at,self.offset]
        result.update(endOffset=self.offset,fieldRanges=spans);return result

    def simple_list(self,name):
        from scripts.game_data.memorypack.leveldata_simple_record_sources import FIELDS,COUNT_LIMIT
        from scripts.game_data.memorypack.leveldata_extended_record_sources import FIELDS as EXTENDED
        original={**FIELDS,**EXTENDED}[name];cap=self.cap('collections',ROOT+'::'+name)
        if cap.get('countLimit')==0 and cap.get('allowedCounts')==[-1,0]:return self.list(ROOT,name)
        if (cap.get('countLimit')!=COUNT_LIMIT or cap.get('allowedCounts')is not None
                or cap.get('wholeGrammarAdmitted')is not False or cap.get('profileAdmitted')is not True
                or cap.get('actualCallbackEqualsProvedChildRequired')is not True
                or cap.get('liveFormatterSelectionObserved')is not False):
            self.refuse(name,'current-finite-record-list-profile',cap)
        # A reached current profile requires its child program even for -1/0.
        self.simple_plan(original,name)
        return self.list(ROOT,name,lambda field:self.simple_record(original,field),type_name=LIST(original))

    def composed_list(self,name):
        """Each finite owner has its independent complete child program."""
        from scripts.game_data.memorypack import leveldata_occlusion_sources as occlusion
        from scripts.game_data.codecs.leveldata import current_occlusion
        from scripts.game_data.memorypack import leveldata_factory_mine_sources as mines
        from scripts.game_data.codecs.leveldata import current_factory_mine
        from scripts.game_data.memorypack import leveldata_enemy_sources as enemies
        from scripts.game_data.codecs.leveldata import current_enemy
        from scripts.game_data.memorypack import leveldata_spline_sources as spline,leveldata_lock_sources as lock,leveldata_water_sources as water,leveldata_map_region_sources as maps,leveldata_attract_point_sources as attract,leveldata_npc_group_sources as groups,leveldata_waypoint_sources as waypoints,leveldata_integer_host_sources as integer_hosts,leveldata_authored_patrol_sources as authored
        from scripts.game_data.codecs.leveldata import current_spline,current_locks,current_water,current_map_region,current_attract_point,current_npc_group,current_waypoint,current_integer_hosts,current_authored_patrol
        original,key={'splines':(spline.TYPE,spline.CAP),'interactiveLockData':(lock.TYPE,lock.CAP),
            'waterVolumes':(water.TYPE,water.CAP),'riftVolumes':(water.TYPE,water.CAP),'mapVolumeDatas':(maps.REGION,maps.CAP),
            'npcAttractPointData':(attract.TYPE,attract.CAP),'npcGroup':(groups.GROUP,groups.CAP),
            'worldWayPointData':(waypoints.TYPE,waypoints.CAP),'dynamicOccludeAreas':(occlusion.AREA,occlusion.AREA_CAP),
            'factoryMines':(mines.MINE,mines.KEYS[mines.MINE]),
            'enemies':(enemies.TYPE,enemies.CAP),
            **{field:(original,integer_hosts.CAPS[original])for field,original in integer_hosts.FIELDS.items()},
            **{field:(original,authored.record_key(original))for field,original in authored.FIELDS.items()}}[name]
        selected=self.cap('collections',ROOT+'::'+name)
        if selected.get('profileAdmitted')is not True:
            if selected.get('countLimit')!=0 or selected.get('allowedCounts')!=[-1,0]:
                self.refuse(name,'complete-current-composed-profile-required')
            return self.list(ROOT,name)
        binding=selected.get('childBinding',{})
        if (selected.get('typeName')!=LIST(original)or selected.get('headerBytes')!=4
                or type(selected.get('countLimit'))is not int or selected['countLimit']!=4096
                or selected.get('allowedCounts')is not None or selected.get('wholeGrammarAdmitted')is not False
                or selected.get('actualCallbackEqualsProvedChildRequired')is not True
                or selected.get('liveFormatterSelectionObserved')is not False
                or(binding.get('fieldName'),binding.get('typeName'),binding.get('capability'))!=(name,LIST(original),key)
                or type(binding.get('readerMethodDefinition'))is not int or binding['readerMethodDefinition']<0
                or type(binding.get('sourceTargetRva'))is not int or binding['sourceTargetRva']<=0):
            self.refuse(name,'exact-current-composed-list-parent')
        cap=self.cap('records',original)
        if name=='splines':
            current_spline.validate(cap);child=lambda path:current_spline.read(self,path,cap)
        elif name=='interactiveLockData':
            single=self.cap('records',lock.SINGLE);lang=self.cap('records',lock.LANG)
            current_locks.validate(cap,single,lang);child=lambda path:current_locks.read(self,path,cap,single,lang)
        else:
            if name in water.PARENT_FIELDS:current_water.validate(cap)
            elif name=='mapVolumeDatas':current_map_region.validate(maps.REGION,cap)
            elif name=='npcAttractPointData':current_attract_point.validate(cap)
            elif name=='npcGroup':current_npc_group.validate(groups.GROUP,cap)
            elif name in integer_hosts.FIELDS:current_integer_hosts.validate(original,cap)
            elif name in authored.FIELDS:current_authored_patrol.validate(original,cap)
            elif name==occlusion.FIELD:current_occlusion.validate(original,cap,self.condition_cap)
            elif name==mines.FIELD:current_factory_mine.validate(original,cap)
            elif name==enemies.FIELD:current_enemy.validate(cap)
            else:current_waypoint.validate(cap)
            parent=current_water.parent_binding(cap,name)if name in water.PARENT_FIELDS else cap['parentBinding']
            if any(binding.get(k)!=parent.get(k)for k in('fieldName','typeName','capability','readerMethodDefinition','sourceTargetRva')):
                self.refuse(name,'same-current-finite-host-parent')
            if name in integer_hosts.FIELDS:child=lambda path:current_integer_hosts.read(self,path,cap,name=original)
            elif name in authored.FIELDS:child=lambda path:current_authored_patrol.read(self,path,original,cap)
            elif name==occlusion.FIELD:child=lambda path:current_occlusion.read(self,path,original,cap,self.condition_cap)
            elif name==mines.FIELD:child=lambda path:current_factory_mine.read(self,path,original,cap)
            elif name==enemies.FIELD:child=lambda path:current_enemy.read(self,path,cap)
            else:
                codec={'waterVolumes':current_water,'riftVolumes':current_water,'mapVolumeDatas':current_map_region,'npcAttractPointData':current_attract_point,
                    'npcGroup':current_npc_group,'worldWayPointData':current_waypoint}[name]
                child=lambda path:codec.read(self,path,cap)
        return self.list(ROOT,name,child,type_name=LIST(original))


def frame(data,*,strings,capabilities,npc_decoder=None):
    """Return a whole frame only after every field and physical EOF closes."""
    reader=Reader(data,strings,capabilities,npc_decoder)
    if capabilities.get('orderedFields')!=list(LEVELDATA_FIELDS):reader.refuse(ROOT,'complete-current-field-capability')
    if reader.number('<B',ROOT+'.memberCount')!=43:reader.refuse(ROOT,'member-count')
    fields={};conditions=[]
    for name in LEVELDATA_FIELDS:
        start=reader.offset
        if name=='airWalls':row=reader.list(ROOT,name,reader.airwall,type_name=LIST(GROUP))
        elif name in EMPTY_RECORDS:row=reader.empty_record(name)
        elif name in NULL_OBJECTS:row=reader.null_object(name)
        elif name=='autoSpawnedInteractives':row=reader.ulong_list()
        elif name=='levelScriptBriefDataDict':row=reader.brief_dictionary()
        elif name=='levelScriptDataPathDict':row=reader.string_dictionary()
        elif name=='interactives':row=reader.interactives()
        elif name=='spawners':row=reader.spawners()
        elif name=='npcPatrol':row=reader.npc_patrol()
        elif name=='patrols':row=reader.core_patrol()
        elif name=='predefinedParams':row=reader.factory_config(name)
        elif name=='factoryRegions':row=reader.factory_regions()
        elif name=='enemyGroup':row=reader.enemy_groups()
        elif name=='missionAreas':row=reader.mission_areas()
        elif name=='npcs':row=reader.npcs()
        elif name in('splines','interactiveLockData','waterVolumes','riftVolumes','mapVolumeDatas','npcAttractPointData','npcGroup','worldWayPointData','doodadGroup','guideHints','charPatrol','enemyPatrol','dynamicOccludeAreas','factoryMines','enemies'):row=reader.composed_list(name)
        elif name in('aiTransData','cameraPoses','sludgeDatas','environmentVolumes','levelUIs','npcClusters'):row=reader.simple_list(name)
        elif name=='levelIdNum':row=reader.number('<i',ROOT+'::'+name)
        elif name=='sceneId':row=reader.string(ROOT+'::'+name)
        elif name=='levelWideConfigs':row=reader.level_wide()
        else:row=reader.list(ROOT,name)
        if isinstance(row,dict)and isinstance(row.get('conditionalChildSources'),list):
            conditions.extend(dict(field=name,**condition)for condition in row['conditionalChildSources'])
        if name in('buildableCondition','interactives')and reader.condition_cap is not None:
            condition=reader.condition_cap
            conditions.append(dict(field=name,typeName=condition['typeName'],admittedRouteTags=condition['admittedRouteTags'],
                countLimit=condition['countLimit'],nodeLimit=condition['nodeLimit'],depthLimit=condition['depthLimit'],
                actualCallbackEqualsProvedChildRequired=True,runtimeFormatterSelectionObserved=False))
        if name=='specificData':
            specific=capabilities.get('records',{}).get(NULL_OBJECTS[name],{})
            if specific.get('profileAdmitted')is True:
                from scripts.game_data.codecs.leveldata.current_specific import conditional_sources
                conditions.extend(dict(field=name,**condition)for condition in conditional_sources(specific))
        if name in('blackbox','predefinedParams'):
            factory=capabilities.get('records',{}).get(NULL_OBJECTS['blackbox'],{})
            if factory.get('profileAdmitted')is True:
                from scripts.game_data.codecs.leveldata.current_factory_config import conditional_sources
                conditions.extend(dict(field=name,**condition)for condition in conditional_sources(factory))
        if name in('safeZone','factoryPredefineData'):
            auxiliary=capabilities.get('records',{}).get(EMPTY_RECORDS[name][0],{})
            if auxiliary.get('profileAdmitted')is True:
                from scripts.game_data.codecs.leveldata.current_auxiliary_container import conditional_sources
                conditions.extend(dict(field=name,**condition)for condition in conditional_sources(auxiliary))
        cap=capabilities.get('collections',{}).get(ROOT+'::'+name,{})
        if cap.get('profileAdmitted')is True and cap.get('actualCallbackEqualsProvedChildRequired')is True:
            conditions.append(dict(field=name,typeName=cap['typeName'],
                actualCallbackEqualsProvedChildRequired=True,runtimeFormatterSelectionObserved=False))
            if name=='interactiveLockData':
                conditions.append(dict(field=name,typeName='Beyond.LangKey',managedBytes=16,referenceLaneOffsets=[0,8],
                    rawTextSerialized=False,actualCallbackEqualsProvedChildRequired=True,runtimeFormatterSelectionObserved=False))
            elif name=='splines':
                conditions.append(dict(field=name,typeName='UnityEngine.Splines.BezierKnot',inlineElementSource=True,elementWireBytes=56,
                    closedElementRegistrationEquivalenceProved=False,standaloneElementAdmitted=False,
                    actualCallbackEqualsProvedChildRequired=True,runtimeFormatterSelectionObserved=False))
            elif name in('waterVolumes','riftVolumes'):
                conditions.append(dict(field=name,typeName='Beyond.LangKey',managedBytes=16,referenceLaneOffsets=[0,8],
                    rawTextSerialized=False,actualCallbackEqualsProvedChildRequired=True,runtimeFormatterSelectionObserved=False))
                conditions.append(dict(field=name,typeName='System.Collections.Generic.List`1<UnityEngine.Vector3>',
                    countLimit=4096,initiallyNullListRequired=True,actualCallbackEqualsProvedChildRequired=True,
                    runtimeFormatterSelectionObserved=False))
            elif name=='enemies':
                from scripts.game_data.memorypack import leveldata_enemy_sources as enemies
                record=capabilities['records'][enemies.TYPE]
                conditions.append(dict(field=name,typeName=enemies.TYPE,coherentOriginalCacheRequired=True,
                    compatibleRefreshOnly=True,coldInitializationObserved=False,runtimeEnemyActivationProved=False))
                dictionary=record['childCapabilities'][enemies.dictionary.CAP]
                conditions.append(dict(field=name,typeName=dictionary['typeName'],allowedCounts=[-1,0],
                    sourceWitnessClassArguments=list(dictionary['sourceWitnessClassArguments']),closedPointerEquivalenceProved=False,
                    actualCallbackEqualsCanonicalRequired=True,typedConstructorAndHelperCompatibilityRequired=True,
                    actualCallbackSelectionObserved=False,providerFactorySelectionObserved=False,positiveObjectValuesAdmitted=False))
                conditions.append(dict(field=name,typeName=enemies.nullable.TYPE,wireBytes=8,rawBitsPreserved=True,
                    hasValueByteNormalized=False,paddingSerialized=True,actualCallbackEqualsProvedChildRequired=True,
                    runtimeFormatterSelectionObserved=False))
                pending=list(record['childCapabilities'].values());seen=set()
                while pending:
                    current=pending.pop();type_name=current['typeName']if 'typeName'in current else current['closedListType']
                    if type_name in seen:continue
                    seen.add(type_name)
                    if 'childCapabilities'in current:pending.extend(current['childCapabilities'].values())
                    if current.get('initiallyNullListRequired')is True or current.get('initiallyNullArrayRequired')is True:
                        conditions.append(dict(field=name,typeName=type_name,countLimit=4096,
                            runtimeFormatterSelectionObserved=False,
                            **{k:current[k]for k in('initiallyNullListRequired','initiallyNullArrayRequired',
                                'actualCallbackEqualsProvedChildRequired','actualCallbackEqualsPooledStringRequired',
                                'nullElementIndex','emptyElementIndex')if k in current}))
            elif name=='factoryMines':
                from scripts.game_data.memorypack import leveldata_factory_mine_sources as mines
                for type_name,axes,width in(('UnityEngine.Vector2Int',['x','y'],8),('UnityEngine.Vector3Int',['x','y','z'],12)):
                    conditions.append(dict(field=name,typeName=type_name,rawInt32Axes=axes,wireBytes=width,
                        integerVectorSourceProved=True,runtimeFormatterSelectionObserved=False))
                conditions.append(dict(field=name,typeName=mines.integers.TYPE,countLimit=mines.LIMIT,rawBitsPreserved=True,
                    actualCallbackEqualsProvedChildRequired=True,runtimeFormatterSelectionObserved=False))
            elif name=='dynamicOccludeAreas':
                from scripts.game_data.memorypack import leveldata_occlusion_sources as occlusion
                condition=reader.condition_cap
                conditions.append(dict(field=name,typeName=condition['typeName'],admittedRouteTags=condition['admittedRouteTags'],
                    countLimit=condition['countLimit'],nodeLimit=condition['nodeLimit'],depthLimit=condition['depthLimit'],
                    actualCallbackEqualsProvedChildRequired=True,runtimeFormatterSelectionObserved=False))
                for type_name in(occlusion.GRID_LIST,occlusion.lines.LIST):
                    conditions.append(dict(field=name,typeName=type_name,countLimit=occlusion.LIMIT,initiallyNullListRequired=True,
                        actualCallbackEqualsProvedChildRequired=True,runtimeFormatterSelectionObserved=False))
                conditions.append(dict(field=name,typeName=occlusion.lines.TYPE,managedBytes=12,rawInt32Axes=['x','y'],
                    defaultValueOnFF=True,actualCallbackEqualsCanonicalRequired=True,runtimeFormatterSelectionObserved=False))
            elif name in('charPatrol','enemyPatrol'):
                from scripts.game_data.memorypack import leveldata_authored_patrol_sources as authored
                record=capabilities['records'][authored.FIELDS[name]]
                conditions.append(dict(field=name,typeName=record['typeName'],nodeLimit=authored.NODE_LIMIT,
                    authoredRecordOnly=True,controllerConversionProved=False,runtimeActivationProved=False,playbackProved=False))
                pending=[record];seen=set()
                while pending:
                    current=pending.pop()
                    for child in current['childCapabilities'].values():
                        if child['typeName']in seen:continue
                        seen.add(child['typeName'])
                        if 'childCapabilities'in child:pending.append(child)
                        elif child.get('initiallyNullListRequired')is True:
                            conditions.append(dict(field=name,typeName=child['typeName'],countLimit=authored.LIMIT,
                                initiallyNullListRequired=True,actualCallbackEqualsProvedChildRequired=True,
                                runtimeFormatterSelectionObserved=False))
            elif name in('doodadGroup','guideHints'):
                from scripts.game_data.memorypack import leveldata_integer_host_sources as integer_hosts
                record=capabilities['records'][integer_hosts.FIELDS[name]]
                conditions.append(dict(field=name,typeName=integer_hosts.VECTOR,rawInt32Axes=['x','y','z'],wireBytes=12,
                    integerVectorSourceProved=True,runtimeFormatterSelectionObserved=False))
                for child in record['childCapabilities'].values():
                    conditions.append(dict(field=name,typeName=child['typeName'],countLimit=4096,
                        actualCallbackEqualsProvedChildRequired=True,runtimeFormatterSelectionObserved=False,
                        **{key:child[key]for key in('initiallyNullListRequired','initiallyNullOutputRequired','rawBitsPreserved',
                            'elementType','elementWireBytes','rawInt32Axes')if key in child}))
            elif name=='npcAttractPointData':
                conditions.append(dict(field=name,typeName='System.Collections.Generic.List`1<ulong>',countLimit=4096,
                    initiallyNullOutputRequired=True,actualCallbackEqualsProvedChildRequired=True,
                    runtimeFormatterSelectionObserved=False))
                conditions.append(dict(field=name,typeName='System.Collections.Generic.List`1<string>',countLimit=4096,
                    initiallyNullListRequired=True,actualCallbackEqualsPooledStringRequired=True,
                    runtimeFormatterSelectionObserved=False))
            elif name=='npcGroup':
                conditions.append(dict(field=name,typeName='System.Collections.Generic.List`1<UnityEngine.Vector3>',countLimit=4096,
                    initiallyNullListRequired=True,actualCallbackEqualsProvedChildRequired=True,
                    runtimeFormatterSelectionObserved=False))
            elif name=='worldWayPointData':
                from scripts.game_data.memorypack import leveldata_waylane_list_sources as lanes
                value=capabilities['records']['Beyond.Gameplay.AI.WayPointInEditorData']['childCapabilities'][lanes.VALUE_CAP]
                array=value['arrayCapability']
                conditions.append(dict(field=name,typeName=lanes.LIST,countLimit=4096,initiallyNullListRequired=True,
                    managedElementBytes=16,paddingByteRanges=[[4,8]],paddingSerialized=False,
                    actualCallbackEqualsCanonicalRequired=True,runtimeFormatterSelectionObserved=False))
                conditions.append(dict(field=name,typeName='uint[]',countLimit=array['countLimit'],rawBitsPreserved=True,
                    actualOwningSourceJoinProved=True,actualSourceAuthentication=array['actualSourceAuthentication'],
                    canonicalEntryPointerMatched=array['canonicalEntryPointerMatched'],
                    closedPointerEquivalenceProved=array['closedPointerEquivalenceProved'],runtimeFormatterSelectionObserved=False))
                conditions.append(dict(field=name,typeName='System.Collections.Generic.List`1<ulong>',countLimit=4096,
                    initiallyNullOutputRequired=True,actualCallbackEqualsProvedChildRequired=True,runtimeFormatterSelectionObserved=False))
        if name=='environmentVolumes':
            from scripts.game_data.memorypack.leveldata_extended_record_sources import ENV,POLY
            if capabilities.get('records',{}).get(ENV,{}).get('positivePolylineProfile')is True:
                selected=capabilities['records'][POLY]
                conditions.append(dict(field=name,typeName=POLY,actualCallbackEqualsProvedChildRequired=True,
                    **{key:selected.get(key)is True for key in('positiveBvhNodesAdmitted','positiveConvexPolygonsAdmitted','positiveTreeAdmitted')},
                    runtimeFormatterSelectionObserved=False))
        fields[name]=dict(startOffset=start,endOffset=reader.offset,value=row)
    if reader.offset!=len(data):reader.refuse(ROOT,'physical-eof-required',len(data)-reader.offset)
    return dict(status='exact_current_leveldata_owner',schemaStatus='named_exact',serializedMemberCount=43,
        bytesConsumed=reader.offset,fields=fields,reader=__name__+'.frame',evidenceBoundary='structuralOnly',
        sourceBoundary='conditional',conditionalChildSources=conditions,
        runtimeActivationProved=False,playbackProved=False)
