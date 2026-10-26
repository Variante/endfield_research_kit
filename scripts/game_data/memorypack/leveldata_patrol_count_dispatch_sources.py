"""Actual Patrol ICollection slot-zero Count dispatcher and nominal joins.

The selected runtime interface table must be the coherent inflated closed
List<Point> table matching the independently read static declarations.  Its
selected callback must equal the independently source-proved object-shared
Count entry.  Those are explicit runtime/key-construction obligations; the
dispatcher proves their argument/result flow without inventing a closed
Point native registration or an observed MethodInfo/class pointer.
"""
import json,struct

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.story-patrol-Count-dispatch-source.v1'


def need(check,condition):
 if not condition:raise ValueError('storyPatrolCountDispatch.'+check)


def program(regions,entry,*,callback,interface_ordinal=1):
 need('exact-owned-List-ICollection-interface-ordinal',interface_ordinal==1 and type(interface_ordinal)is int)
 need('literal-independently-selected-Count-callback',type(callback)is int and callback>0)
 g=BytesPath(regions,entry)
 g.take('48895c2408','48896c2410','4889742418','48897c2420','4156','4883ec30',
  '498b30','498bf8','0fb7e9','488bda','488bce');prepare=g.relative('e8')
 g.take('440fb78630010000','4533f6','410fb7c6','66453bf0');g.branch('73',False,1)
 g.take('488b96b0000000')
 for ordinal in (0,1):
  g.take('0fb7c8','4803c9','48391cca');g.branch('74',ordinal==1,1)
  if ordinal==0:g.take('66ffc0','66413bc0');g.branch('72',True,1)
 g.take('0fb7d0','488b86b0000000','4803d2','8b44d008','03c5','4898','4883c014','48c1e004','4803c6','4c8b00','488b5008')
 excluded=[]
 for ordinal in range(3):
  target=g.relative('488d05');need('Count-callback-not-an-unproved-inline-alternative',target!=callback);excluded.append(target)
  g.take('4c3bc0');g.branch('0f84'if ordinal==2 else'74',False,4 if ordinal==2 else 1)
 g.take('488bcf','41ffd0','8bd8','488b6c2448','8bc3','488b5c2440','488b742450','488b7c2458','4883c430','415e','c3')
 return dict(selectedBytes=g.seen,entry=entry,prepareTarget=prepare,interfaceOrdinal=interface_ordinal,
  requestedInterfaceFromIncomingRdx=True,receiverFromIncomingR8Preserved=True,selectorLow16Required=0,
  classInterfaceCountOffset=304,classInterfaceTableOffset=176,interfaceEntryBytes=16,interfaceVtableOffsetField=8,
  classVtableOffset=320,vtableEntryBytes=16,callbackOffset=0,methodInfoOffset=8,
  selectedCallbackRequired=callback,excludedInlineTargets=excluded,
  callbackArguments=dict(rcx='unchanged incoming collection receiver',rdx='selected same-slot MethodInfo'),
  returnedInt32Unchanged=True,entryRspRestored=True,nonvolatilesRestored=['rbx','rbp','rsi','rdi','r14'],normalReturn=True,
  runtimeInflatedInterfaceTableOrCallbackIdentityObserved=False,callbackSelectionProved=False)


def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.initializer_control import control_transfer
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
 from scripts.game_data.il2cpp.formatter_composition import _vtable
 from scripts.game_data.memorypack import pointer_param as pointer,leveldata_patrol_point_sources as points
 from scripts.game_data.memorypack import leveldata_patrol_count_sources as count_owner,leveldata_patrol_object_key_sources as key_owner
 _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
 point=points.derive(image,pins);usage=point['proof']['typedUsages']['points-safe-count'];target=base+point['proof']['actualTargets']['points-safe-count']
 sites={(c['instructionVa'],c['targetVa'])for c in point['proof']['programs'][1]['calls']if c['role']=='points-safe-count'}
 need('one-actual-count-loop-callsite-and-target',len(sites)==1);site,actual_target=next(iter(sites))
 need('same-actual-count-helper-target',actual_target==target)
 source_instruction=[site-base,image.pe.bytes_at_va(site,5).hex().upper()]
 count=count_owner.derive(image,pins,typed_request=usage,source_target=target,source_instruction=source_instruction)
 key=key_owner.derive(image,pins);selection=key['proof']['ObjectLookupSource']['proof']['selectionSource']
 registration=selection['proof']['independentObjectRegistration'];callback=registration['pointer']
 cloned=pointer.owned(image,target);tail=control_transfer(cloned['rows'][18])
 need('same-independently-proved-SafeCount-dispatch-tail',tail['kind']=='jump'
  and cloned['rows'][18]['va']==count['proof']['selectedCloneEquivalence']['cloneDispatchVa'])
 body=pointer.owned(image,tail['target']);selected=program(body['regions'],body['pointer'],callback=callback)
 td=ctx.index.types[points.LIST];symbols=ContextSymbols(image);section=md.sections['interfaceOffsets'];rows=[]
 start=section.offset+td.interface_offsets_start*8
 for ordinal,(index,offset)in enumerate(struct.iter_unpack('<ii',md.buf[start:start+td.interface_offsets_count*8])):
  rows.append(dict(ordinal=ordinal,carrier=symbols.type(ctx.type_pointer(index)),vtableOffset=offset))
 first,matched=rows[:2];variable,=matched['carrier']['classArguments']
 need('fresh-List-first-two-distinct-owned-interface-declarations',first['carrier']['definition']['name']=='System.Collections.Generic.IList`1'
  and matched['carrier']['definition']['name']=='System.Collections.Generic.ICollection`1'
  and first['carrier']['classArguments']==[variable]and variable.get('parameterOwner',{}).get('typeIndex')==td.index
  and variable['parameterOwner']['ordinal']==0 and bytes.fromhex(variable['rawHex'])[10:12]==bytes((19,0)))
 getter=selection['proof']['countMethodDefinition'];_vtable(image,td.index,matched['vtableOffset'],getter,'storyPatrolCountDispatch.ListCount')
 # Static closed argument pointers are compared, never inflated class pointers.
 actual,=image.instantiations.resolve(usage['methodSpec'][2]).arguments
 receiver=point['proof']['closedReceiverJoins']['point-get-item'];field_argument,=receiver['receiver']['classArguments']
 need('same-actual-nominal-Point-argument-in-SafeCount-and-field',actual.type_pointer_va==field_argument['typePointerVa']
  and actual.raw_type_record_hex==field_argument['rawHex'])
 leaf=selection['proof']['countProgram'];item=point['proof']['item']['program']
 need('same-byte-derived-operational-List-count-storage',leaf['receiverOffset']==item['listSizeOffset']and leaf['loadBytes']==4)
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-actual-Count-dispatch-source',nativeInputs=pins,
  proof=dict(pointTransfer=point,SafeCountSource=count,ObjectKeySource=key,dispatcherWindows=body['windows'],
   dispatcherRegions=[[a,h.hex().upper()]for a,h in body['regions']],selectedInterfacePath=selected,
   staticListInterfaces=rows,staticCountVtableSlot=matched['vtableOffset'],countMethodDefinition=getter,
   sameNominalPointArgument=dict(typePointerVa=actual.type_pointer_va,rawHex=actual.raw_type_record_hex)),
  completeSlotZeroCountCallerArgumentAndReturnSourceProved=True,
  CountReturnsSameOperationalListSizeConditional=True,actualRuntimeCallbackSelectionProved=False,
  normalizedMethodKeyConstructionSourceProved=False,wholeConversionProved=False,
  runtimeInvocationObserved=False,playbackProved=False,evidenceBoundary=dict(exact='Actual SafeCount clone to owned interface dispatcher, complete slot-zero second-interface/fallback callback program/full frame, own reciprocal List/ICollection declarations and exact Count definition token, same raw Point argument and byte-derived size DWORD.',
   conditional=__doc__,unresolved=['actual method-key construction/table population source','initialized inflated class/MethodInfo/interface/callback identity',
    'full conversion/initializer/checkpoint and playback']))))
