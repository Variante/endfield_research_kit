"""Only the independently proved empty Enemy dictionary states."""
from scripts.game_data.memorypack import leveldata_enemy_dictionary_sources as source


def validate(cap):
 if(not isinstance(cap,dict)or cap.get('typeName')!=source.TYPE or cap.get('closedDictionaryType')!=source.TYPE
  or(cap.get('keyType'),cap.get('valueType'))!=('string','object')
  or cap.get('allowedCounts')!=[-1,0]or cap.get('countRange')!=[-1,0]
  or any(type(cap.get(k))is not int or cap[k]!=v for k,v in dict(countLimit=0,headerBytes=4,outputBytes=8).items())
  or cap.get('sourceWitnessClassArguments')!=['object','object']
  or any(cap.get(k)is not True for k in('nullable','profileAdmitted','actualCallbackEqualsCanonicalRequired','typedConstructorAndHelperCompatibilityRequired'))
  or any(cap.get(k)is not False for k in('positiveCountsAdmitted','keyGrammarAdmitted','valueGrammarAdmitted','wholeGrammarAdmitted',
   'closedPointerEquivalenceProved','actualCallbackSelectionObserved','providerFactorySelectionObserved','parentFieldAdmitted','wholeOwnerAdmitted'))):
  raise ValueError('currentEnemyDictionary.exact-conditional-empty-profile')
 for key in('packableReaderMethodDefinition','packableReaderTargetRva'):
  if type(cap.get(key))is not int or cap[key]<(1 if key=='packableReaderTargetRva'else 0):raise ValueError('currentEnemyDictionary.literal-parent-source')


def read(reader,field,cap):
 validate(cap);start=reader.offset;count=reader.number('<i',field+'.count')
 if count not in(-1,0):raise ValueError(field+':positive-object-dictionary-unproved')
 return dict(startOffset=start,endOffset=reader.offset,count=count,entries=None if count==-1 else[],
  conditionalChildSources=[dict(typeName=source.TYPE,sourceWitnessClassArguments=['object','object'],closedPointerEquivalenceProved=False,
   actualCallbackEqualsCanonicalRequired=True,typedConstructorAndHelperCompatibilityRequired=True,
   typedConstructorCompatibilityRequired=count==0,providerFactorySelectionObserved=False,actualCallbackSelectionObserved=False,
   positiveObjectValuesAdmitted=False)])
