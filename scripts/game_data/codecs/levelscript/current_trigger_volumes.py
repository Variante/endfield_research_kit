"""Finite current Trigger dictionaries, distinct union and record headers."""
import struct

from scripts.game_data.memorypack import levelscript_trigger_components as source
from scripts.game_data.codecs.leveldata.current_kickable_enum_list import require_capability
from scripts.game_data.codecs.levelscript.current_collections import Reader


def need(check,condition):
 if not condition:raise ValueError('currentTriggerVolumes.'+check)


def validate(cap):
 need('exact-finite-current-root',isinstance(cap,dict)and(cap.get('typeName'),cap.get('capability'),cap.get('elementType'))==
  (source.DICTIONARY,source.CAP,source.TYPE)
  and cap.get('admittedRouteTags')==[0,1,2]and all(type(n)is int for n in cap['admittedRouteTags'])
  and cap.get('caseTypes')=={str(k):v for k,v in source.CHILDREN.items()}
  and all(type(cap.get(k))is int and cap[k]==v for k,v in dict(countLimit=source.LIMIT,nodeLimit=source.NODE_LIMIT,nullUnionMarker=255).items())
  and cap.get('reservedMarkersRefused')==[251,252,253,254]
  and all(cap.get(k)is True for k in('canonicalTagEncoding','profileAdmitted','nullAdmitted','positiveAdmitted',
   'ordinaryBaseAdapterAdmitted','initiallyNullOutputsRequired','actualCallbackEqualsCanonicalRequired','actualValueCallbackEqualsProvedChildRequired'))
  and all(cap.get(k)is False for k in('wholeGrammarAdmitted','runtimeFormatterSelectionObserved','runtimeTriggerEvaluationProved')))
 records=cap.get('records');collections=cap.get('collections')
 need('four-exact-records-and-three-independent-lists',isinstance(records,dict)and set(records)==set(source.PLANS)
  and isinstance(collections,dict)and set(collections)=={source.SHAPE_LIST_CAP,source.VECTOR_LIST_CAP,source.ENUM_LIST_CAP,source.ENUM_CAP})
 require_capability(collections[source.ENUM_LIST_CAP],collections[source.ENUM_CAP])
 selected_pins=collections[source.ENUM_LIST_CAP]['nativeInputs']
 for name,plan in source.PLANS.items():
  record=records[name]
  need('own-complete-concrete-record:'+name,isinstance(record,dict)and record.get('typeName')==name
   and type(record.get('memberCount'))is int and record['memberCount']==len(plan)
   and record.get('unsignedFields')==(['slotId']if name!=source.SHAPE else[])
   and all(record.get(k)is True for k in('nullAdmitted','positiveAdmitted','profileAdmitted','finiteSpatialFloatProfile','actualCallbackEqualsProvedChildRequired'))
   and all(record.get(k)is False for k in('wholeGrammarAdmitted','runtimeFormatterSelectionObserved')))
  source.bind_program(dict(wrappedType=name,orderedSourceReads=[dict(fieldName=n,declaredType=t)for n,t,k in plan]),record.get('program'),[])
  if name==source.SHAPE:
   enum=record.get('enumBacking',{})
   need('exact-owned-shape-enum',enum.get('typeName')==source.SHAPE_ENUM and enum.get('backing')in('int','uint')
    and enum.get('field')==[source.SHAPE_ENUM,enum['backing'],16])
  else:need('no-sibling-enum-admission:'+name,record.get('enumBacking')is None)
  for binding in record['program']['childBindings']:
   key=binding['capability'];component=dict(nativeInputs=selected_pins,capabilities={key:collections[key]})
   if key==source.ENUM_LIST_CAP:component['capabilities'][source.ENUM_CAP]=collections[source.ENUM_CAP]
   expected=source.bind_collection(selected_pins,dict(fieldName=binding['fieldName'],typeName=binding['typeName'],
    sourceTargetRva=binding.get('sourceTargetRva'),typedRequest=dict(methodName='ReadPackable',
     methodArguments=[binding['typeName']],methodSpec=[binding.get('readerMethodDefinition'),1,2])),component,key)
   need('same-actual-concrete-list-binding:'+name,binding==expected)
 dictionary=cap.get('dictionary',{})
 expected=source.dictionary.capability(type_name=source.DICTIONARY,value_type=source.TYPE,count_limit=source.LIMIT,
  reader_definition=dictionary.get('packableReaderMethodDefinition'),reader_target=dictionary.get('packableReaderTargetRva'),
  closed_pointer_equivalence=dictionary.get('closedPointerEquivalenceProved'))
 need('own-unsigned-root-dictionary',dictionary==expected)
 parent=cap.get('parentBinding',{})
 expected=dict(ownerType=source.ROOT,fieldName='triggerVolumes',typeName=source.DICTIONARY,elementType=source.TYPE,
  readerMethodDefinition=dictionary['packableReaderMethodDefinition'],sourceTargetRva=dictionary['packableReaderTargetRva'],
  fieldOffset=parent.get('fieldOffset'),initiallyNullOutputRequired=True,
  actualCallbackEqualsCanonicalRequired=True,actualValueCallbackEqualsProvedChildRequired=True)
 need('own-root-call-and-store',parent==expected and type(parent.get('fieldOffset'))is int and 16<=parent['fieldOffset']<4096)


def _count(reader,field,budget):
 reader.need(4,field+'.count');count=struct.unpack_from('<i',reader.data,reader.offset)[0]
 need('list-count-domain',-1<=count<=source.LIMIT);need('subtree-budget',max(count,0)<=budget[0]);reader.offset+=4
 return count


def _record(reader,field,name,cap,budget):
 need('record-budget',budget[0]>0);budget[0]-=1;start=reader.offset
 marker=reader.number('<B',field+'.memberCount')
 if marker==255:return None
 plan=source.PLANS[name];need('own-concrete-member-count:'+name,marker==len(plan));out=dict(startOffset=start,recordType=name,memberCount=marker);ranges={}
 record=cap['records'][name]
 for member,declared,kind in plan:
  at=reader.offset;path=field+'.'+member
  if kind=='bool-byte':value=reader.boolean(path)
  elif kind=='scalar32':
   unsigned=member in record['unsignedFields']or(name==source.SHAPE and record['enumBacking']['backing']=='uint')
   value=reader.number('<I'if unsigned else'<i',path)
  elif kind=='float32-bits':value=reader.single(path)
  elif kind=='unity-vector3-raw12':value={axis:reader.single(path+'.'+axis)for axis in'xyz'}
  elif kind=='byte-payload':value=reader.string(path)
  elif kind in('trigger-shape-list','trigger-vector2-list','trigger-kickable-list'):
   begin=reader.offset;count=_count(reader,path,budget);rows=[]
   reader.need(max(count,0)*(1 if kind=='trigger-shape-list'else 8 if kind=='trigger-vector2-list'else 4),path+'.elements')
   if kind!='trigger-shape-list':budget[0]-=max(count,0)
   for index in range(max(count,0)):
    if kind=='trigger-shape-list':child=_record(reader,path+'['+str(index)+']',source.SHAPE,cap,budget)
    elif kind=='trigger-vector2-list':child={axis:reader.single(path+'['+str(index)+'].'+axis)for axis in'xy'}
    else:
     offset=reader.offset;bits=bytes(reader.data[offset:offset+4]);reader.offset+=4
     child=dict(rawHex=bits.hex().upper())
    rows.append(child)
   value=dict(startOffset=begin,endOffset=reader.offset,count=count,rows=None if count==-1 else rows)
  else:raise ValueError(path+':unproved-current-trigger-operation')
  out[member]=value;ranges[member]=[at,reader.offset]
 out.update(endOffset=reader.offset,fieldRanges=ranges);return out


def _union(reader,field,cap,budget):
 need('union-budget',budget[0]>0);budget[0]-=1;start=reader.offset;marker=reader.number('<B',field+'.unionTag')
 if marker==255:return None
 if marker<250:tag=marker
 elif marker==250:
  tag=reader.number('<H',field+'.extendedTag');need('canonical-extended-tag',tag>=250)
 else:raise ValueError(field+':reserved-union-marker:'+str(marker))
 need('proved-union-route',tag in source.CHILDREN)
 name=source.CHILDREN[tag];value=_record(reader,field+'.'+name.rsplit('.',1)[-1],name,cap,budget)
 return dict(startOffset=start,endOffset=reader.offset,unionTag=tag,recordType=name,value=value)


def conditional_sources(cap):
 validate(cap)
 return [dict(typeName=source.DICTIONARY,sourceWitnessClassArguments=['uint','object'],countLimit=source.LIMIT,
  initiallyNullOutputRequired=True,actualCallbackEqualsCanonicalRequired=True,actualKeyCallbackEqualsProvedUInt32Required=True,
  actualValueCallbackEqualsProvedChildRequired=True,typedConstructorAndHelperCompatibilityRequired=True,
  closedPointerEquivalenceProved=cap['dictionary']['closedPointerEquivalenceProved'],actualCallbackSelectionObserved=False),
  dict(typeName=source.TYPE,admittedRouteTags=[0,1,2],initiallyNullOutputRequired=True,
   actualCallbackEqualsCanonicalRequired=True,runtimeTriggerEvaluationProved=False),
  *[dict(typeName=source.LIST(name),countLimit=source.LIMIT,initiallyNullListRequired=True,
   actualCallbackEqualsProvedChildRequired=True,runtimeFormatterSelectionObserved=False)
   for name in(source.SHAPE,'UnityEngine.Vector2',source.ENUM)],
  dict(typeName=source.ENUM,actualNominalEnumCallbackRequired=True,actualRuntimeSelectionObserved=False)]


def decode(data,offset,*,strings,capability):
 validate(capability);need('literal-offset',type(offset)is int and 0<=offset<=len(data))
 reader=Reader(data,offset,strings,'triggerVolumes');budget=[source.NODE_LIMIT];count=_count(reader,'triggerVolumes',budget)
 reader.need(max(count,0)*5,'triggerVolumes.minimumEntries');rows=[];seen=set()
 for index in range(max(count,0)):
  key=reader.number('<I','triggerVolumes['+str(index)+'].key')
  need('unique-UInt32-key',key not in seen);seen.add(key)
  value=_union(reader,'triggerVolumes['+str(key)+']',capability,budget);rows.append(dict(key=key,value=value))
 return dict(startOffset=offset,endOffset=reader.offset,status='null'if count==-1 else'present',count=None if count==-1 else count,
  entries=None if count==-1 else rows,parseStatus='decoded',conditionalChildSources=conditional_sources(capability)),reader.offset
