"""Fresh current LevelScript owners tied to their selected export and pool.

This operation never reads historical route sourceReceipts or searches a tail
for an interactive map. Every successful owner reaches physical EOF through
the maintained sequential source cursor.
"""
from __future__ import annotations

from contextlib import ExitStack
import gzip
import hashlib
import json
from pathlib import Path
import sys
import struct

from scripts.game_data import levelscript_current_owner_native as native
from scripts.game_data.jsondata_source_provenance import (
    authenticate_current_jsondata_receipt, authenticate_current_jsondata_source_inventory)
from scripts.game_data.levelscript_reader_inputs import (
    snapshot_complete_reader_inputs,snapshot_string_pool_inputs,reader_input_changes)
from scripts.game_data.memorypack import pooled_source_helper
from scripts.game_data.string_pool import export_string_pool

COLLECTIONS={
    'interactiveActiveRiskEntityIdList':'System.Collections.Generic.List`1<ulong>',
    'refWorldEntityIdList':'System.Collections.Generic.List`1<ulong>',
    'properties':'System.Collections.Generic.List`1<Beyond.Gameplay.ParamKeyValue>',
    'propertyIdToKeyMap':'System.Collections.Generic.Dictionary`2<int,string>',
    'interactives':'System.Collections.Generic.Dictionary`2<uint,Beyond.Gameplay.LevelInteractiveData>',
}


class CurrentLevelScriptSourceError(ValueError):
    def __init__(self,gate,source,expected=None,actual=None):
        self.diagnostic=dict(validator='currentLevelScriptSource',gate=gate,source=str(source),
            expected=expected,actual=actual)
        super().__init__(json.dumps(self.diagnostic,sort_keys=True))


def _reviewed_native_identity(*,gameassembly,metadata):
    """Cheap selected-pair gate; it supplies no native owner capability."""
    try:fact=json.loads(native.CONTRACT_PATH.read_bytes())
    except(OSError,ValueError)as error:
        raise CurrentLevelScriptSourceError('reviewed-native-contract-read',native.CONTRACT_PATH,
            'readable reviewed JSON contract',dict(error=type(error).__name__,detail=str(error)[:1600]))from error
    pins=fact.get('nativeInputs')if isinstance(fact,dict)else None
    if (not isinstance(fact,dict)or fact.get('schema')!=native.SCHEMA or fact.get('status')!='exact-current-build'
            or not isinstance(pins,dict)or set(pins)!={'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'}
            or any(not isinstance(v,str)or len(v)!=64 or any(c not in '0123456789abcdefABCDEF'for c in v)for v in pins.values())):
        raise CurrentLevelScriptSourceError('reviewed-native-identity',native.CONTRACT_PATH)
    selected=native._gate(pins,gameassembly=gameassembly,metadata=metadata)
    paths={'GameAssembly.dll':str(Path(getattr(selected,'gameassembly',gameassembly)).resolve()),
        'global-metadata.dat':str(Path(getattr(selected,'metadata',metadata)).resolve())}
    measured={name:value for name,attribute in(('GameAssembly.dll','gameassembly_sha256'),
        ('global-metadata.dat','metadata_sha256'))if(value:=getattr(selected,attribute,''))}
    actual=dict(status=selected.status,detail=str(getattr(selected,'detail',''))[:1600],
        selectedPaths=paths,measuredHashes=measured)
    expected=dict(status='validated',nativeInputs=pins)
    if selected.status!='validated':
        raise CurrentLevelScriptSourceError('selected-native-preflight','selected-native-pair',expected,actual)
    if failure:=pooled_source_helper.check_unity_input(selected.gameassembly,pins):
        unity=Path(selected.gameassembly).parent/'UnityPlayer.dll';paths['UnityPlayer.dll']=str(unity.resolve())
        if unity.is_file():measured['UnityPlayer.dll']=pooled_source_helper.sha256_file_upper(unity)
        actual.update(status=failure.get('status'),detail=str(failure.get('detail',''))[:1600])
        raise CurrentLevelScriptSourceError('selected-native-preflight',unity,expected,actual)
    return dict(nativeInputs=pins,nativeSources={'GameAssembly.dll':str(Path(selected.gameassembly).resolve()),
        'global-metadata.dat':str(Path(selected.metadata).resolve())})


class CurrentLevelScriptSource:
    def __init__(self,json_root,*,gameassembly,metadata,
            summary_path=Path('reports/animestudio/jsondata_current_latest.json'),
            ledger_path=Path('reports/animestudio/jsondata_current_files_latest.jsonl.gz')):
        self.root=Path(json_root).resolve();self.gameassembly=gameassembly;self.metadata=metadata
        self.summary=Path(summary_path);self.ledger=Path(ledger_path);self.active=False
        self._source_inventory=False

    @classmethod
    def from_source_inventory(cls,json_root,*,gameassembly,metadata,summary_path,ledger_path):
        """Use an explicit full source inventory; native/EOF gates stay fresh."""
        if cls is not CurrentLevelScriptSource:
            raise CurrentLevelScriptSourceError('exact-current-source-type-required',json_root)
        operation=cls(json_root,gameassembly=gameassembly,metadata=metadata,
            summary_path=summary_path,ledger_path=ledger_path)
        operation._source_inventory=True
        return operation

    def _authenticate_source(self,identity):
        authenticate=(authenticate_current_jsondata_source_inventory if self._source_inventory
                      else authenticate_current_jsondata_receipt)
        receipt=authenticate(summary_path=self.summary,ledger_path=self.ledger,
            expected_summary_sha256=self.summary_sha,native_sources=identity['nativeSources'],
            native_inputs=identity['nativeInputs'])
        if self._source_inventory and Path(receipt['jsonRoot']).resolve()!=self.root:
            raise CurrentLevelScriptSourceError('source-inventory-selected-json-root',self.root,
                receipt['jsonRoot'],str(self.root))
        return receipt

    def _receipt(self):
        return self._authenticate_source(self.proof)

    def _open_source_rows(self,identity):
        self.summary_raw=self.summary.read_bytes();self.summary_sha=hashlib.sha256(self.summary_raw).hexdigest().upper()
        self.receipt_before=self._authenticate_source(identity)
        self.rows={}
        with gzip.open(self.ledger,'rt',encoding='utf-8')as stream:
            for line in stream:
                row=json.loads(line);key=row.get('exportRelativePath','')
                if not key.startswith(('LevelScriptData/','LevelData/','StringPool/'))and key!='Interactive/InteractiveTable.json':continue
                if key in self.rows:raise CurrentLevelScriptSourceError('duplicate-logical-source',key)
                self.rows[key]=row

    def _confirm_source_rows(self):
        if self.summary.read_bytes()!=self.summary_raw or self.receipt_before!=self._receipt():
            raise CurrentLevelScriptSourceError('source-receipt-drift',self.root)

    def _check_source_exit(self):
        self._confirm_source_rows()

    def _source_audit(self):
        if self._source_inventory:
            return dict(status='conditional-current-levelscript-source-inventory',
                summary=dict(path=str(self.summary),sha256=self.summary_sha),
                sourceInventoryAuthenticated=True,currentCensusAuthenticated=False,
                sourceReceiptAuthority=True,namedSchemaFromSourceReceipt=False)
        return dict(status='conditional-current-levelscript-source',summary=dict(path=str(self.summary),sha256=self.summary_sha))

    def __enter__(self):
        from scripts.game_data.memorypack.operation_native_validation import (
            _native_validation_scope,_suspend_native_validation)
        if self.active:raise CurrentLevelScriptSourceError('operation-active',self.root)
        if hasattr(self,'native_validation_reuse'):del self.native_validation_reuse
        # Keep an outer operation suspended until this entire operation exits,
        # including failed entry cleanup and every independent child exit.
        self._native_validation_ambient=_suspend_native_validation()
        self._native_validation_ambient.__enter__()
        try:
            self._enter_fresh_source()
            self._native_validation_context=_native_validation_scope(gameassembly=self.gameassembly,
                metadata=self.metadata,native_inputs=self.proof['nativeInputs'],reader_inputs=self.reader_inputs)
            self._native_validation_state=self._native_validation_context.__enter__()
            return self
        except BaseException:
            try:
                if self.active:self._exit_fresh_source(*sys.exc_info())
            finally:self._native_validation_ambient.__exit__(*sys.exc_info())
            raise

    def _enter_fresh_source(self):
        if self.active:raise CurrentLevelScriptSourceError('operation-active',self.root)
        if self.gameassembly is None or self.metadata is None:
            raise CurrentLevelScriptSourceError('explicit-native-pair-required',self.root)
        self.stack=ExitStack()
        try:
            self.reader_inputs=snapshot_complete_reader_inputs();self.pool_inputs=snapshot_string_pool_inputs(self.root)
            identity=_reviewed_native_identity(gameassembly=self.gameassembly,metadata=self.metadata)
            self._open_source_rows(identity)
            self.strings=export_string_pool(self.root)
            if self.strings is None:raise CurrentLevelScriptSourceError('matching-string-pool-required',self.root)
            self.proof=native.validate_current_native_contract(gameassembly=self.gameassembly,metadata=self.metadata)
            if self.proof.get('status')!='validated':
                raise CurrentLevelScriptSourceError('selected-owner-source',self.root,'validated',self.proof)
            if any(self.proof.get(k)!=identity[k]for k in('nativeInputs','nativeSources')):
                raise CurrentLevelScriptSourceError('selected-native-identity-drift',self.root)
            self._confirm_source_rows()
            self.narrative_component_key=self.proof['narrativeComponent']['id']
            string_kind=self.proof.get('paramStringType')
            if (not isinstance(string_kind,dict)or string_kind.get('typeName')!='Beyond.GEnums.ParamRealType'
                    or string_kind.get('name')!='String'or type(string_kind.get('id'))is not int):
                raise CurrentLevelScriptSourceError('native-param-string-kind',self.root,actual=string_kind)
            self.param_string_type=string_kind['id']
            self.child_caps=self.proof.get('children',{})
            self.host_caps=self.proof.get('leveldata')
            self.condition_caps=(self.host_caps or{}).get('records',{}).get('Beyond.Gameplay.ConditionRuntimeBase')
            if isinstance(self.condition_caps,dict)and self.condition_caps.get('profileAdmitted')is not True:
                self.condition_caps=None
            self.task_caps=self.proof.get('tasks');self.root_empty_caps=self.proof.get('rootEmpty');self.module_caps=self.proof.get('modules')
            self.root_record_caps=self.proof.get('rootRecords')
            self.trigger_caps=self.proof.get('triggers')
            self.game_root=Path(self.proof['nativeSources']['global-metadata.dat']).parents[2]
            self.files={};self.closed=set();self.attempted=set()
            self.host_closed=set();self.host_attempted=set();self.host_conditions={}
            self.root_conditions={}
            for row in self.pool_inputs['files']:
                path=Path(row['path']);self._join(path,path.read_bytes())
            self.universe={key for key in self.rows if key.startswith('LevelScriptData/')}
            self.host_universe={key for key in self.rows if key.startswith('LevelData/')}
            from scripts.game_data.levelscript_null_list_param_native import current_null_list_params
            from scripts.game_data.levelscript_numeric_list_param_native import current_numeric_list_params
            from scripts.game_data.levelscript_camera_shake_param_native import current_camera_shake_params
            from scripts.game_data.levelscript_buff_ptr_param_native import current_buff_ptr_params
            from scripts.game_data.levelscript_entity_list_param_native import current_entity_list_params
            from scripts.game_data.memorypack.npc_runtime import npc_runtime_decoder
            self.leaves={name:self.stack.enter_context(factory(game_root=self.game_root,strings=self.strings))
                for name,factory in(('null_list_params',current_null_list_params),
                    ('numeric_list_params',current_numeric_list_params),
                    ('camera_shake_params',current_camera_shake_params),('buff_ptr_params',current_buff_ptr_params),
                    ('entity_list_params',current_entity_list_params))}
            self.npc_decoder=self.stack.enter_context(npc_runtime_decoder(strings=self.strings,
                gameassembly=self.gameassembly,metadata=self.metadata))
            self.active=True
            if isinstance(self.host_caps,dict):
                from scripts.game_data.memorypack.levelscript_current_npc import _current_npc_decoder
                self.npc_decoder=_current_npc_decoder(self,self.npc_decoder)
            return self
        except BaseException:
            self.active=False
            self.stack.__exit__(*sys.exc_info());raise

    def _join(self,path,data):
        try:key=Path(path).resolve().relative_to(self.root).as_posix()
        except ValueError as error:raise CurrentLevelScriptSourceError('source-outside-selected-json-root',path)from error
        row=self.rows.get(key);actual=[len(data),hashlib.sha256(data).hexdigest().upper()]
        expected=None if row is None else[row['length'],row['logicalSha256'].upper()]
        if expected!=actual:raise CurrentLevelScriptSourceError('logical-source-byte-join',key,expected,actual)
        return key

    def frame(self,path,data):
        if not self.active:raise CurrentLevelScriptSourceError('operation-closed',self.root)
        path=Path(path).resolve();key=self._join(path,data)
        if key not in self.universe:raise CurrentLevelScriptSourceError('owner-family',key,'LevelScriptData')
        if self.files.setdefault(path,data)!=data:raise CurrentLevelScriptSourceError('mixed-source-versions',key)
        self.attempted.add(key)
        from scripts.game_data.levelscript_binary import frame_levelscript_named
        frame=frame_levelscript_named(data,source=key,strings=self.strings,game_root=self.game_root,
            npc_decoder=self.npc_decoder,current_owner=self,**self.leaves)
        expected_fields=self.proof['owners'][native.source.ROOT]['orderedFields'][1:]
        if (frame.get('schemaStatus'),frame.get('serializedMemberCount'),frame.get('bytesConsumed'))!=('named_exact',28,len(data)):
            raise CurrentLevelScriptSourceError('complete-sequential-owner-eof',key,
                dict(schemaStatus='named_exact',serializedMemberCount=28,bytesConsumed=len(data)),
                {name:frame.get(name)for name in('schemaStatus','serializedMemberCount','bytesConsumed','stopField','stopDetail','readerRefusals')})
        if list(frame.get('fields',{}))!=expected_fields:
            raise CurrentLevelScriptSourceError('complete-current-field-order',key,expected_fields,list(frame.get('fields',{})))
        if frame.get('reader','').rsplit('.',1)[-1]not in('frame_levelscript_empty_action_map_sequential',
                'frame_levelscript_null_action_map_sequential','frame_levelscript_current_action_sequence_leader_enter'):
            raise CurrentLevelScriptSourceError('sequential-owner-reader',key,actual=frame.get('reader'))
        conditions=[]
        from scripts.game_data.memorypack.levelscript_module_graph_sources import CAP_SCHEMA as MODULE_SCHEMA
        for field in('enemies','interactiveLocks','modules','triggerVolumes'):
            child=frame['fields'].get(field)or{};count=child.get('count')
            if field=='triggerVolumes'and self.trigger_caps is not None:
                from scripts.game_data.codecs.levelscript.current_trigger_volumes import conditional_sources
                cap=self._trigger_cap()
                if count is None and child.get('status')=='null':count=-1
                if (type(count)is not int or not -1<=count<=cap['countLimit']
                        or(count>=0 and len(child.get('entries')or[])!=count)):
                    raise CurrentLevelScriptSourceError('current-trigger-count',key,field,count)
                conditions.extend(dict(field=field,**row)for row in conditional_sources(cap))
                continue
            if field in('enemies','interactiveLocks')and self.root_record_caps is not None:
                from scripts.game_data.codecs.levelscript.current_root_records import conditional_sources
                cap=self._root_record_cap(field)
                if count is None and child.get('status')=='null':count=-1
                if (type(count)is not int or not -1<=count<=cap['dictionary']['countLimit']
                        or(count>=0 and len(child.get('entries')or[])!=count)):
                    raise CurrentLevelScriptSourceError('current-root-record-count',key,field,count)
                conditions.extend(dict(field=field,**row)for row in conditional_sources(field,cap))
                continue
            if field=='modules'and isinstance(self.module_caps,dict)and self.module_caps.get('schema')==MODULE_SCHEMA:
                from scripts.game_data.memorypack.levelscript_module_public import conditional_sources
                cap=self._module_cap()
                if count is None and child.get('status')=='null':count=-1
                if (type(count)is not int or not -1<=count<=cap['dictionary']['countLimit']
                        or(count>=0 and len(child.get('entries')or[])!=count)
                        or child.get('storedModuleGrammarAdmitted')is not True):
                    raise CurrentLevelScriptSourceError('current-module-profile-count',key,actual=child)
                conditions.extend(dict(field=field,**row)for row in conditional_sources(cap))
                continue
            if field=='modules'and type(count)is int and count>0:
                cap=self._module_cap()
                if count>cap['countLimit']or len(child.get('entries')or[])!=count:
                    raise CurrentLevelScriptSourceError('current-module-profile-count',key,actual=child)
                conditions.append(dict(field=field,count=count,sourceWitnessClassArguments=['ulong','object'],
                    actualCallbackEqualsCanonicalRequired=True,concreteRuntimeSelectionObserved=False,
                    allowedModuleTags=cap['allowedModuleTags'],finiteFloatProfile=True))
                continue
            cap=self._root_empty_cap(field)
            if count is None and child.get('status')=='null':count=-1
            if type(count)is not int or count not in(-1,0):
                raise CurrentLevelScriptSourceError('current-root-empty-child',key,field,child)
            conditions.append(dict(field=field,count=count,sourceWitnessClassArguments=cap['sourceWitnessClassArguments'],
                actualCallbackEqualsCanonicalRequired=True,concreteRuntimeSelectionObserved=False,
                typedConstructorAndHelperCompatibilityRequired=True))
        from scripts.game_data.memorypack.levelscript_task_game_condition_sources import CAP_SCHEMA as TASK_SCHEMA
        if isinstance(self.task_caps,dict)and self.task_caps.get('schema')==TASK_SCHEMA:
            from scripts.game_data.codecs.levelscript.current_task_game_conditions import conditional_sources
            child=frame['fields'].get('taskMap')or{};count=child.get('count')
            if count is None and child.get('status')=='null':count=-1
            if (type(count)is not int or not -1<=count<=self.task_caps['countLimit']
                    or(count>=0 and len(child.get('entries')or[])!=count)
                    or child.get('positiveGameConditionAdmitted')is not True):
                raise CurrentLevelScriptSourceError('current-Task-game-condition-count',key,actual=child)
            conditions.extend(dict(field='taskMap',**row)for row in conditional_sources(self.task_caps))
        # A complete structural reader does not manufacture an independently
        # current source capability for a positive child it happened to parse.
        for field in('activeShapeList','startShapeList','triggerVolumes'):
            child=frame['fields'].get(field)or{}
            if type(child.get('count'))is int and child['count']>0:
                if field=='triggerVolumes'and self.trigger_caps is not None:continue
                if field in('activeShapeList','startShapeList'):
                    cap=self.child_caps.get('System.Collections.Generic.List`1<Beyond.Gameplay.Core.LevelScriptShape>')
                    if isinstance(cap,dict)and cap.get('wholeGrammarAdmitted')is True and (
                            cap.get('headerBytes'),cap.get('countLimit'),cap.get('managedElementBytes'),
                            cap.get('recordWireBytes'))==(4,64,44,45)and child['count']<=64:
                        continue
                raise CurrentLevelScriptSourceError('current-positive-child-source',key,
                    'independent current '+field+' source/grammar',child['count'])
        task=frame['fields'].get('taskMap')or{}
        if task.get('sourceBoundary')=='conditional'and not(isinstance(self.task_caps,dict)and self.task_caps.get('schema')==TASK_SCHEMA):
            conditions.append(dict(field='taskMap',sourceWitnessClassArguments=task['sourceWitnessClassArguments'],
                actualCallbackEqualsCanonicalRequired=True,runtimeSelectionObserved=False,
                positiveGameConditionAdmitted=False))
        conditions.extend(dict(field='npcs',**condition)for condition in
            getattr(self.npc_decoder,'current_profile_conditions',[]))
        conditions.extend(dict(field='interactives',**condition)for condition in
            (frame['fields'].get('interactives')or{}).get('conditionalChildSources',[]))
        self.root_conditions[key]=conditions
        self.closed.add(key)
        return frame

    def _root_empty_cap(self,field):
        cap=self.root_empty_caps.get(field)if isinstance(self.root_empty_caps,dict)else None
        witness={'enemies':['uint','object'],'interactiveLocks':['uint','object'],
            'modules':['ulong','object'],'triggerVolumes':['uint','object']}.get(field)
        if (not isinstance(cap,dict)or cap.get('headerBytes')!=4 or type(cap.get('countLimit'))is not int or cap['countLimit']!=0
                or cap.get('allowedCounts')!=[-1,0]or cap.get('positiveChildrenAdmitted')is not False
                or cap.get('actualCallbackEqualsCanonicalRequired')is not True
                or cap.get('sourceWitnessClassArguments')!=witness
                or cap.get('concreteRuntimeSelectionObserved')is not False
                or cap.get('typedConstructorAndHelperCompatibilityRequired')is not True):
            raise CurrentLevelScriptSourceError('current-empty-root-source',field,actual=cap)
        return cap

    def empty_root_collection(self,field,data,offset,*,strings):
        require_framing_owner(self,strings=strings)
        if field not in('enemies','interactiveLocks','modules','triggerVolumes'):
            raise CurrentLevelScriptSourceError('closed-empty-root-field',field)
        self._root_empty_cap(field)
        if type(offset)is not int or not 0<=offset<=len(data)-4:
            raise CurrentLevelScriptSourceError('truncated-current-empty-root',field,actual=offset)
        count=struct.unpack_from('<i',data,offset)[0]
        if count not in(-1,0):raise CurrentLevelScriptSourceError('current-positive-root-child',field,[-1,0],count)
        return dict(startOffset=offset,endOffset=f'0x{offset+4:x}',status='null'if count==-1 else'present',
            count=None if count==-1 else count,parseStatus='decoded'),offset+4

    def _root_record_cap(self,field):
        from scripts.game_data.codecs.levelscript.current_root_records import validate
        cap=self.root_record_caps.get(field)if isinstance(self.root_record_caps,dict)else None
        try:validate(field,cap)
        except(ValueError,KeyError,TypeError)as error:
            raise CurrentLevelScriptSourceError('current-root-record-source',field,actual=str(error)[:1200])from error
        return cap

    def root_record_map(self,field,data,offset,*,strings):
        require_framing_owner(self,strings=strings)
        if field not in('enemies','interactiveLocks'):
            raise CurrentLevelScriptSourceError('closed-current-root-record-field',field)
        if self.root_record_caps is None:
            return self.empty_root_collection(field,data,offset,strings=strings)
        from scripts.game_data.codecs.levelscript.current_root_records import decode
        return decode(data,offset,field,strings=self.strings,capability=self._root_record_cap(field))

    def task_map(self,data,offset,*,strings):
        require_framing_owner(self,strings=strings)
        from scripts.game_data.memorypack.levelscript_task_game_condition_sources import CAP_SCHEMA
        if isinstance(self.task_caps,dict)and self.task_caps.get('schema')==CAP_SCHEMA:
            from scripts.game_data.codecs.levelscript.current_task_game_conditions import decode
        else:
            from scripts.game_data.codecs.levelscript.current_tasks import decode
        return decode(data,offset,strings=self.strings,capability=self.task_caps)

    def _trigger_cap(self):
        from scripts.game_data.codecs.levelscript.current_trigger_volumes import validate
        try:validate(self.trigger_caps)
        except(ValueError,KeyError,TypeError)as error:
            raise CurrentLevelScriptSourceError('current-trigger-source','triggerVolumes',actual=str(error)[:1200])from error
        return self.trigger_caps

    def trigger_map(self,data,offset,*,strings):
        require_framing_owner(self,strings=strings)
        if self.trigger_caps is None:
            return self.empty_root_collection('triggerVolumes',data,offset,strings=strings)
        from scripts.game_data.codecs.levelscript.current_trigger_volumes import decode
        return decode(data,offset,strings=self.strings,capability=self._trigger_cap())

    def _module_cap(self):
        from scripts.game_data.memorypack.levelscript_module_graph_sources import CAP_SCHEMA
        from scripts.game_data.codecs.levelscript.current_module_graph import validate
        cap=self.module_caps;declared='System.Collections.Generic.Dictionary`2<ulong,Beyond.Gameplay.LevelScriptModuleData>'
        if isinstance(cap,dict)and cap.get('schema')==CAP_SCHEMA:
            try:validate(cap)
            except(ValueError,KeyError,TypeError)as error:
                raise CurrentLevelScriptSourceError('current-module-source-capability','modules',actual=str(error)[:1200])from error
            return cap
        tags=cap.get('allowedModuleTags')if isinstance(cap,dict)else None
        if (not isinstance(cap,dict)or cap.get('typeName')!=declared or cap.get('headerBytes')!=4
                or type(cap.get('countLimit'))is not int or cap['countLimit']!=16384
                or cap.get('profileAdmitted')is not True or cap.get('wholeGrammarAdmitted')is not False
                or cap.get('moduleType')!='Beyond.Gameplay.RollingStoneControllerData'
                or (cap.get('positiveRecordMemberCount'),cap.get('launcherMemberCount'))!=(3,7)
                or not isinstance(tags,list)or len(tags)!=1 or type(tags[0])is not int or not 0<=tags[0]<=65535
                or cap.get('nullUnionMarker')!=255 or cap.get('canonicalTagEncoding')is not True
                or cap.get('reservedMarkersRefused')!=[251,252,253,254]
                or cap.get('finiteFloatProfile')is not True or cap.get('actualCallbackEqualsCanonicalRequired')is not True
                or cap.get('sourceWitnessClassArguments')!=['ulong','object']
                or cap.get('concreteRuntimeSelectionObserved')is not False):
            raise CurrentLevelScriptSourceError('current-module-source-capability','modules',actual=cap)
        return cap

    def module_map(self,data,offset,*,strings,diagnostics=None):
        require_framing_owner(self,strings=strings)
        cap=self._module_cap()
        from scripts.game_data.memorypack.levelscript_module_graph_sources import CAP_SCHEMA
        if cap.get('schema')==CAP_SCHEMA:
            from scripts.game_data.memorypack.levelscript_module_public import decode
            return decode(data,offset,strings=self.strings,capability=cap)
        from scripts.game_data.codecs.levelscript.modules import _decode_module_dictionary
        return _decode_module_dictionary(data,offset,cap['allowedModuleTags'][0],diagnostics,
            count_limit=cap['countLimit'],canonical=True)

    def frame_leveldata(self,path,data):
        """Close a current host only through the independently composed cursor."""
        if not self.active:raise CurrentLevelScriptSourceError('operation-closed',self.root)
        path=Path(path).resolve();key=self._join(path,data)
        if key not in self.host_universe:
            raise CurrentLevelScriptSourceError('owner-family',key,'LevelData')
        if not isinstance(self.host_caps,dict):
            raise CurrentLevelScriptSourceError('current-LevelData-capabilities',key,
                'independently current host source and reached-child composition',self.host_caps)
        if self.files.setdefault(path,data)!=data:raise CurrentLevelScriptSourceError('mixed-source-versions',key)
        self.host_attempted.add(key)
        from scripts.game_data.codecs.leveldata.current_owner import frame
        try:framed=frame(data,strings=self.strings,capabilities=self.host_caps,npc_decoder=self.npc_decoder)
        except ValueError as error:
            raise CurrentLevelScriptSourceError('complete-current-LevelData-owner',key,
                'all43 source-backed fields and physical EOF',str(error)[:2400])from error
        if (framed.get('schemaStatus'),framed.get('serializedMemberCount'),framed.get('bytesConsumed'))!=('named_exact',43,len(data)):
            raise CurrentLevelScriptSourceError('complete-current-LevelData-eof',key,actual=framed)
        self.host_conditions[key]=framed.get('conditionalChildSources',[])
        self.host_closed.add(key);return framed

    def collection(self,field,data,offset,*,strings):
        require_framing_owner(self,strings=strings)
        from scripts.game_data.codecs.levelscript.current_collections import decode
        name=COLLECTIONS.get(field)
        if name is None:raise CurrentLevelScriptSourceError('closed-collection-field',field)
        cap=self.child_caps.get(name)
        if not isinstance(cap,dict)or cap.get('countLimit')!=16384 or cap.get('headerBytes')!=4:
            raise CurrentLevelScriptSourceError('current-child-capability',field,name,cap)
        if name.endswith('LevelInteractiveData>'):
            if cap.get('recordGrammar')!='MC25-or-FF;condition-FF-only':
                raise CurrentLevelScriptSourceError('interactive-reached-child-capability',field,actual=cap)
            record=(self.host_caps or{}).get('records',{}).get('Beyond.Gameplay.LevelInteractiveData',{})
            if record.get('recordGrammar')=='MC25-or-FF;bounded-condition-runtime'and self.condition_caps is None:
                raise CurrentLevelScriptSourceError('interactive-current-condition-capability',field)
        elif cap.get('wholeGrammarAdmitted')is not True:
            raise CurrentLevelScriptSourceError('whole-child-grammar',field,actual=cap)
        if field=='interactives'and self.condition_caps is not None:
            return decode(data,offset,name,strings=self.strings,condition_cap=self.condition_caps)
        return decode(data,offset,name,strings=self.strings)

    def read_interactive_table(self):
        if not self.active:raise CurrentLevelScriptSourceError('operation-closed',self.root)
        path=self.root/'Interactive/InteractiveTable.json';data=path.read_bytes();self._join(path,data)
        if self.files.setdefault(path,data)!=data:raise CurrentLevelScriptSourceError('mixed-source-versions',path)
        return path,data

    def audit(self):
        if not self.active:raise CurrentLevelScriptSourceError('operation-closed',self.root)
        return dict(self._source_audit(),nativeValidationReuse=self._native_validation_state.statistics(),sourceUniverse=len(self.universe),
            sourcesAttempted=len(self.attempted),ownersClosed=len(self.closed),
            allSourcesAttempted=len(self.attempted)==len(self.universe),allOwnersClosed=len(self.closed)==len(self.universe),
            conditionalChildSources={key:self.root_conditions[key]for key in sorted(self.root_conditions)},
            leveldata=dict(sourceUniverse=len(self.host_universe),sourcesAttempted=len(self.host_attempted),
                ownersClosed=len(self.host_closed),allSourcesAttempted=len(self.host_attempted)==len(self.host_universe),
                allOwnersClosed=len(self.host_closed)==len(self.host_universe),
                conditionalChildSources={key:self.host_conditions[key]for key in sorted(self.host_conditions)}),
            runtimeActivationProved=False,playbackProved=False,absenceProved=False)

    def __exit__(self,*error):
        try:
            self._native_validation_context.__exit__(*error)
            self._exit_fresh_source(*error)
            if not error or error[0]is None:
                self.native_validation_reuse=dict(self._native_validation_state.statistics(),entryExitBookendsPassed=True)
        finally:self._native_validation_ambient.__exit__(*error)

    def _exit_fresh_source(self,*error):
        try:
            self._check_source_exit()
            for path,raw in self.files.items():
                if path.read_bytes()!=raw:raise CurrentLevelScriptSourceError('owner-source-drift',path)
            if self.pool_inputs!=snapshot_string_pool_inputs(self.root):raise CurrentLevelScriptSourceError('string-pool-drift',self.root)
            changed=snapshot_complete_reader_inputs()
            if self.reader_inputs!=changed:raise CurrentLevelScriptSourceError('reader-source-drift',self.root,'unchanged',reader_input_changes(self.reader_inputs,changed))
            selected=self.proof['nativeSources'];pins=self.proof['nativeInputs']
            after=native._gate(pins,gameassembly=Path(selected['GameAssembly.dll']),metadata=Path(selected['global-metadata.dat']))
            if after.status!='validated'or pooled_source_helper.check_unity_input(selected['GameAssembly.dll'],pins):
                raise CurrentLevelScriptSourceError('selected-native-exit',self.root,'validated',after.status)
        finally:
            self.active=False;self.stack.__exit__(*error)


def require_current_owner(operation,*,strings):
    if type(operation)is not CurrentLevelScriptSource or not operation.active:
        raise CurrentLevelScriptSourceError('active-selected-owner-required','<operation>')
    if operation.strings is not strings:
        raise CurrentLevelScriptSourceError('matching-operation-pool','<operation>')


def require_framing_owner(operation,*,strings):
    """Native-backed framing authority; existing bytes confer no census receipt."""
    from scripts.game_data.memorypack.levelscript_existing_source import ExistingLevelScriptSource
    if type(operation)not in(CurrentLevelScriptSource,ExistingLevelScriptSource)or not operation.active:
        raise CurrentLevelScriptSourceError('active-selected-owner-required','<operation>')
    if operation.strings is not strings:
        raise CurrentLevelScriptSourceError('matching-operation-pool','<operation>')
