"""Finite ordinary Story leaves behind complete actual-source capabilities."""
from scripts.game_data.memorypack import leveldata_ordinary_leaf_sources as source


def validate(name,cap):
 plan=source.PLANS.get(name)
 if (plan is None or not isinstance(cap,dict)or cap.get('typeName')!=name
   or type(cap.get('memberCount'))is not int or cap['memberCount']!=len(plan)
   or any(cap.get(k)is not True for k in('nullAdmitted','positiveAdmitted','ordinaryAdapterAdmitted','finiteFloatProfile',
    'profileAdmitted','actualCallbackEqualsProvedChildRequired'))
   or any(cap.get(k)is not False for k in('wholeGrammarAdmitted','liveFormatterSelectionObserved','parentFieldAdmitted','wholeOwnerAdmitted'))):
  raise ValueError('currentOrdinaryLeaf.exact-finite-profile:'+str(name))
 source.bind_program(name,dict(wrappedType=name,orderedSourceReads=[dict(fieldName=n,declaredType=t)for n,t,k in plan]),cap.get('program'),[])


def read(reader,field,name,cap):
 validate(name,cap);start=reader.offset;marker=reader.number('<B',field+'.memberCount')
 if marker==255:return None
 if marker!=len(source.PLANS[name]):raise ValueError(field+':ordinary-leaf-member-count')
 result=dict(startOffset=start,recordType=name,memberCount=marker);ranges={}
 for member,declared,kind in source.PLANS[name]:
  at=reader.offset;path=field+'.'+member
  if kind=='float32-bits':value=reader.single(path)
  elif kind=='bool-byte':value=reader.boolean(path)
  elif kind=='byte-payload':value=reader.string(path)
  elif kind=='unity-vector3-raw12':value={axis:reader.single(path+'.'+axis)for axis in'xyz'}
  else:raise ValueError(field+':ordinary-leaf-closed-kind')
  result[member]=value;ranges[member]=[at,reader.offset]
 result.update(endOffset=reader.offset,fieldRanges=ranges)
 return result
