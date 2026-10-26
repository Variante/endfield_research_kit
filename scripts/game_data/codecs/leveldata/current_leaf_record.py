"""Finite stored Story leaves under explicit fresh ordinary-source capabilities."""
from scripts.game_data.memorypack import leveldata_leaf_record_sources as source


def validate(name,cap):
 if (name not in source.PLANS or not isinstance(cap,dict)or cap.get('typeName')!=name
  or type(cap.get('memberCount'))is not int or cap['memberCount']!=len(source.PLANS[name])
  or any(cap.get(k)is not True for k in('nullAdmitted','positiveAdmitted','ordinaryAdapterAdmitted','finiteFloatProfile',
   'profileAdmitted','actualCallbackEqualsProvedChildRequired'))
  or any(cap.get(k)is not False for k in('wholeGrammarAdmitted','liveFormatterSelectionObserved','parentFieldAdmitted','wholeOwnerAdmitted'))):
  raise ValueError('currentLeafRecord.exact-finite-profile:'+str(name))
 source.bind_program(name,dict(wrappedType=name,orderedSourceReads=[dict(fieldName=n,declaredType=t)for n,t,k in source.PLANS[name]]),cap.get('program'),[])
 expected={n:t for n,t,k in source.PLANS[name]if k=='scalar32'and t!='int'};enums=cap.get('enumBackings',{})
 if not isinstance(enums,dict)or set(enums)!=set(expected):raise ValueError('currentLeafRecord.exact-enum-set')
 for member,typename in expected.items():
  enum=enums[member]
  if (not isinstance(enum,dict)or enum.get('typeName')!=typename or enum.get('backing')not in('int','uint')
   or enum.get('field')!=[typename,enum['backing'],16]):raise ValueError('currentLeafRecord.nominal-enum')


def read(reader,field,name,cap):
 validate(name,cap);start=reader.offset;marker=reader.number('<B',field+'.memberCount')
 if marker==255:return None
 if marker!=len(source.PLANS[name]):raise ValueError(field+':leaf-record-member-count')
 out=dict(startOffset=start,recordType=name,memberCount=marker);ranges={}
 for member,declared,kind in source.PLANS[name]:
  at=reader.offset;path=field+'.'+member
  if kind=='scalar32':value=reader.number('<I'if cap['enumBackings'].get(member,{}).get('backing')=='uint'else'<i',path)
  elif kind=='scalar64-bits':value=str(reader.number('<q'if declared=='long'else'<Q',path))
  elif kind=='bool-byte':value=reader.boolean(path)
  elif kind=='float32-bits':value=reader.single(path)
  elif kind=='byte-payload':value=reader.string(path)
  elif kind=='unity-vector3-raw12':value={axis:reader.single(path+'.'+axis)for axis in'xyz'}
  else:raise ValueError(path+':closed-leaf-record-operation')
  out[member]=value;ranges[member]=[at,reader.offset]
 out.update(endOffset=reader.offset,fieldRanges=ranges);return out
