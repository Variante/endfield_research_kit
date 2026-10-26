"""Conditional ordinary EventArgs value transfers; no live provider selection."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

def read_value(regions,entry,s):
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20','48837a3800','488bda','488bf9');g.branch('74',False,1)
 g.relative('488b0d');g.take('48c744243800000000','83b9e000000000');g.branch('74',False,1)
 g.take('488b4b38','488b09');g.call(s['provider']);g.take('4885c0');g.branch('74',False,1)
 g.take('4c8d4c2438','4c8bc7','488bd0');g.call(s['dispatch']);g.take('488b442438','488b5c2430','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,result='Same eight output bytes returned in RAX',providerContextSlot=0)

def peek(regions,entry,offsets):
 g=BytesPath(regions,entry);g.take('4053','4883ec20','8379'+bytes((offsets['bufferLength'],1)).hex(),'488bd9');g.branch('0f8c',False)
 g.take('488b43'+bytes((offsets['currentPtr'],)).hex(),'8038ff','0f94c0','4883c420','5b','c3')
 return dict(selectedBytes=g.seen,result='AL iff next byte is FF; reader unchanged')

def read_is_null(regions,entry,s):
 g=BytesPath(regions,entry);g.take('4053','4883ec20','488bd9','c644243000');g.call(s['peek']);g.take('84c0');g.branch('0f85',False)
 g.take('4883c420','5b','c3');return dict(selectedBytes=g.seen,result='Non-FF byte remains unconsumed; AL zero')

def original_dispatch(regions,entry,s):
 g=BytesPath(regions,entry);g.take('48895c2408','4889742410','48897c2418','4156','4883ec20','488b0a','4d8bf1','498bf0','488bda');g.call(s['prepare'])
 g.take('488b3b')
 if g.relative('488d0d')!=s['adapter']:raise ValueError('eventBridge.canonical-fast-target')
 g.take('488b8790010000','488bbf98010000','483bc1');g.branch('0f85',False)
 g.take('803d');g.read(4);g.take('00');g.branch('0f84',False)
 g.take('488b4720','488bce','488b90c0000000','488b12');g.call(s['readNull']);g.take('84c0');g.branch('0f85',False)
 g.take('488b4720');g.relative('488b0d');g.take('488b98c0000000','83b9e000000000','488b5b50');g.branch('74',False,1)
 g.take('33d2','488bcb');g.call(s['typeHandle']);g.take('4885c0');g.branch('74',False,1)
 g.take('33d2','488bc8');g.call(s['isAbstract']);g.take('84c0');g.branch('75',False,1)
 g.take('488b4720','488b88c0000000','488b4958');g.call(s['activate'])
 g.take('488b4f20','4c8bc0','498bd6','4c8b89c0000000','488bce','4d8b4918');g.call(s['deserializeNotNull'])
 g.take('488b5c2430','488b742438','488b7c2440','4883c420','415e','c3')
 return dict(selectedBytes=g.seen,callbackSlot=5,contextSlots=dict(readNull=0,wrapperType=10,activate=11,deserializeNotNull=3),sameReaderAndOutput=True)

def deserialize_not_null(regions,entry,s):
 g=BytesPath(regions,entry);g.take('48895c2408','4889742410','4c89442418','57','4883ec20','803d');g.read(4);g.take('00','498bf9','488bf2','488bd9');g.branch('0f84',False)
 g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False)
 g.take('488b4f20');g.call(s['resolve']);g.take('488b88c0000000','488b4920');g.call(s['wrapperProvider']);g.take('4885c0');g.branch('0f84',False)
 g.take('b905000000','4c8d4c2440','4c8bc3','488bd0');g.call(s['wrapperInvoke'])
 g.take('488b5c2440','4885db');g.branch('74',False,1)
 g.take('488b4f20');g.call(s['resolve']);g.take('ba08000000','488b88c0000000');g.call(s['contextSlot'])
 g.take('488bd0','33c9','4c8bc3');g.call(s['getValueInvoke']);g.take('488bce','488906');g.call(s['barrier'])
 g.take('488b5c2430','488b742438','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,contextSlots=dict(wrapperProvider=4,wrapperInterface=8),wrapperReferenceSlot='entrySP+24',sameReaderAndOutput=True,output='Unchanged GetValue RAX stored as QWORD')

def get_value_interface(regions,entry,*,prepare,match_index=1):
 if match_index!=1:raise ValueError('eventBridge.wrapper-interface-index')
 g=BytesPath(regions,entry);g.take('48895c2408','48896c2410','4889742418','57','4883ec20','498b38','498bf0','0fb7e9','488bda','488bcf');g.call(prepare)
 g.take('440fb78730010000','33c0','66413bc0');g.branch('73',False,1);g.take('488b97b0000000')
 for i in range(2):
  g.take('0fb7c8','4803c9','48391cca');g.branch('74',i==1,1)
  if not i:g.take('66ffc0','66413bc0');g.branch('72',True,1)
 g.take('0fb7d0','488b87b0000000','4803d2','8b44d008','03c5','4898','4883c014','48c1e004','4803c7')
 g.take('4c8b00','488bce','488b5008','488b5c2430','488b6c2438','488b742440','4883c420','5f','49ffe0')
 return dict(selectedBytes=g.seen,matchedInterfaceIndex=1,slotSelector=0,receiver='Original updated wrapper',result='Unchanged callback RAX')
