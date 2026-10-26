"""Finite FactoryHide7 syntax with nominal FCNode raw bits, no enum alias."""
from scripts.game_data.memorypack import leveldata_factory_hide_sources as source
from scripts.game_data.memorypack.skill_enum_list_codec import require_capability


def validate(cap):
 if(not isinstance(cap,dict)or cap.get('typeName')!=source.TYPE or type(cap.get('memberCount'))is not int or cap['memberCount']!=7
  or type(cap.get('countLimit'))is not int or cap['countLimit']!=source.LIMIT
  or any(cap.get(k)is not True for k in('nullAdmitted','positiveAdmitted','profileAdmitted','ordinaryAdapterAdmitted',
   'actualCallbackEqualsProvedChildRequired','actualNominalEnumCallbackRequired'))
  or cap.get('wholeGrammarAdmitted')is not False or cap.get('runtimeFormatterSelectionObserved')is not False
  or type(cap.get('referenceReaderMethodDefinition'))is not int or cap['referenceReaderMethodDefinition']<0
  or type(cap.get('referenceReaderTargetRva'))is not int or cap['referenceReaderTargetRva']<=0):raise ValueError('factoryHide.exact-ordinary-profile')
 source.bind_program(dict(wrappedType=source.TYPE,orderedSourceReads=[dict(fieldName=n,declaredType=t)for n,t,k in source.PLAN]),cap.get('program'),[])
 enum=cap.get('enumBacking',{})
 if(enum.get('typeName')!=source.PLAN[5][1]or enum.get('backing')not in('int','uint')
  or enum.get('field')!=[enum['typeName'],enum['backing'],16]):raise ValueError('factoryHide.exact-nominal-Owner-enum')
 require_capability(cap.get('enumList',{}),cap.get('enumCallback',{}),name=source.ENUM)
 binding,=cap['program']['childBindings']
 expected=source.bind_enums(cap['enumList']['nativeInputs'],dict(fieldName='showFacBuildingTypes',typeName=source.LIST,
  sourceTargetRva=binding.get('sourceTargetRva'),typedRequest=dict(methodName='ReadPackable',methodArguments=[source.LIST],methodSpec=[binding.get('readerMethodDefinition')])),
  dict(nativeInputs=cap['enumList']['nativeInputs'],capabilities={source.LIST_CAP:cap['enumList'],source.ELEMENT_CAP:cap['enumCallback']}),source.LIST_CAP)
 if binding!=expected:raise ValueError('factoryHide.exact-enum-parent-binding')
 if cap.get('parentBinding')!=dict(ownerType=source.PARENT,fieldName='factoryHideDesc',typeName=source.TYPE,capability=source.CAP,
  readerMethodDefinition=cap['referenceReaderMethodDefinition'],sourceTargetRva=cap['referenceReaderTargetRva'],actualCallbackEqualsProvedChildRequired=True):
  raise ValueError('factoryHide.exact-BaseData-parent-binding')


def read(reader,field,cap):
 validate(cap);start=reader.offset;marker=reader.number('<B',field+'.memberCount')
 if marker==255:return None
 if marker!=7:raise ValueError(field+':factory-hide-member-count')
 out=dict(startOffset=start,recordType=source.TYPE,memberCount=7);spans={}
 for member,declared,kind in source.PLAN:
  at=reader.offset;path=field+'.'+member
  if kind=='bool-byte':value=reader.boolean(path)
  elif kind=='scalar32':value=reader.number('<I'if cap['enumBacking']['backing']=='uint'else'<i',path)
  elif kind=='factory-hide-enum-list':
   count=reader.number('<i',path+'.count')
   if not -1<=count<=source.LIMIT:raise ValueError(path+':factory-hide-count-limit')
   reader.need(max(count,0)*4,path+'.values');rows=[]
   for j in range(max(0,count)):
    offset=reader.offset;bits=reader.number('<I',path+'['+str(j)+']').to_bytes(4,'little')
    rows.append(dict(startOffset=offset,endOffset=reader.offset,rawHex=bits.hex().upper()))
   value=dict(startOffset=at,endOffset=reader.offset,count=count,elementType=source.ENUM,rows=None if count==-1 else rows)
  else:raise ValueError(path+':closed-factory-hide-operation')
  out[member]=value;spans[member]=[at,reader.offset]
 out.update(endOffset=reader.offset,fieldRanges=spans);return out
