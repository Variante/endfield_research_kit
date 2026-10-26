"""ScriptTaskPtr MC1 pooled key/default8 inside its separately nullable Param."""

CAP_SCHEMA='endfield.story-condition-script-task-param-capability.v1'
VALUE='Beyond.Gameplay.Core.ScriptTaskPtr'


def validate(cap):
 if not isinstance(cap,dict):raise ValueError('currentScriptTaskParam.missing-owned-capability')
 expected=dict(schema=CAP_SCHEMA,typeName='Beyond.Gameplay.Actions.Param`1<'+VALUE+'>',valueType=VALUE,
  memberCount=4,fieldOrder=['constValue','idRef','paramSource','path'],constantWireKind='script-task-ptr-value',
  constantWireBytes=None,positiveWireBytes=None,positiveWireBytesRange=[14,18],nullWireBytes=1,nullOutput='reference-null',
  idRefWireKind='i32',paramSourceWireKind='i32',pathEncoding='int32-pool-index',sourceReferenceKind=21,referenceOutputBytes=8,
  constantMemberCount=1,constantField='key',constantFieldEncoding='int32-pool-index',constantManagedBytes=8,constantDefaultZeroBytes=8)
 if(any(cap.get(k)!=v for k,v in expected.items())or any(type(cap.get(k))is not int for k in('memberCount','nullWireBytes',
   'sourceReferenceKind','referenceOutputBytes','constantMemberCount','constantManagedBytes','constantDefaultZeroBytes'))
  or any(cap.get(k)is not True for k in('nullAdmitted','positiveAdmitted','wholeGrammarAdmitted','closedCarrierProved',
   'actualCallbackEqualsProvedChildRequired','actualValueCallbackEqualsCanonicalRequired'))
  or cap.get('runtimeTaskResolutionProved')is not False or cap.get('liveFormatterSelectionObserved')is not False
  or type(cap.get('readerMethodDefinition'))is not int or cap['readerMethodDefinition']<0
  or any(type(cap.get(k))is not int or cap[k]<=0 for k in('sourceTargetRva','canonicalCallbackTargetRva'))):
  raise ValueError('currentScriptTaskParam.own-MC1-key-and-four-field-Param')


def read(reader,field,cap):
 validate(cap);start=reader.offset;marker=reader.number('<B',field+'.memberCount')
 if marker==255:return None
 if marker!=4:raise ValueError(field+':ScriptTask-Param-member-count')
 marker=reader.number('<B',field+'.constValue.memberCount')
 if marker==255:constant=dict(key=None,defaultValue=True)
 elif marker==1:constant=dict(key=reader.string(field+'.constValue.key'),defaultValue=False)
 else:raise ValueError(field+':ScriptTask-value-member-count')
 result=dict(startOffset=start,typeName=cap['typeName'],constValue=constant,
  idRef=reader.number('<i',field+'.idRef'),paramSource=reader.number('<i',field+'.paramSource'),path=reader.string(field+'.path'))
 result['endOffset']=reader.offset;return result
