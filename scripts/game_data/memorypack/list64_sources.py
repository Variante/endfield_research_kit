"""Selected current raw 64-bit list normal paths; nominal signedness is independently gated."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

def positive_list(regions,entry,o,s,*,count,count_limit):
 if type(count_limit)is not int or not 1<=count_limit<=256 or type(count)is not int or not 1<=count<=count_limit:raise ValueError('list64-list-count')
 g=BytesPath(regions,entry);cur,rem,adv,used,total=(bytes((o[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed','totalLength'))
 g.take('4c89442418','53','55','57','4154','4155','4156','4883ec28','4533ed','4d8be1','837a'+rem+'04','4d8bf0','488bda','4c896c2468');g.branch('0f8c',False)
 g.take('488b43'+cur,'8b28','8b7b'+rem,'83c7fc');g.branch('0f88',False);g.take('488343'+cur+'04','8343'+adv+'04','8343'+used+'04','897b'+rem,'486343'+used,'488b4b'+total,'482bc8','4863c5','483bc8');g.branch('0f8c',False);g.take('83fdff');g.branch('0f84',False)
 g.take('4889742460','4c897c2420','4d392e');g.branch('0f85',False);g.take('498b4c2420','33d2','488b89c0000000');g.call(s['context']);g.take('488bc8');g.call(s['allocate']);g.take('488bf8','4885c0');g.branch('0f84',False)
 g.take('498b4c2420','488b91c0000000','488b4a08','4c396920');g.branch('0f84',False);g.take('85ed');g.branch('0f88',False);g.take('498b442420','488b88c0000000','488b7108','488b4620','488b88c0000000');g.branch('0f84',False)
 g.take('ba01000000');g.call(s['context']);g.take('488bd5','488bc8');g.call(s['arrayAllocate']);g.take('488d4f10','48894710');g.call(s['barrier']);g.take('498bce','49893e');g.call(s['barrier'])
 owner=g.relative('488b0d');g.take('4439a9e0000000');g.branch('0f84',False);g.take('498b442420','488b88c0000000','488b4918');g.call(s['provider']);g.take('4c8bf8','418bf5','85ed');g.branch('0f8e',False)
 if g.relative('488d3d')!=s['callback']:raise ValueError('list64-callback')
 for index in range(count):
  g.take('4c896c2468','4d85ff');g.branch('0f84',False);g.take('498b0f');g.call(s['prepare']);g.take('498b07','4c8b9090010000','4c8b8898010000','4c3bd7');g.branch('0f85',False)
  g.take('837b'+rem+'08');g.branch('0f8c',False);g.take('488b43'+cur,'488b00','4889442468','8b7b'+rem,'83c7f8');g.branch('0f88',False);g.take('488343'+cur+'08','8343'+adv+'08','8343'+used+'08','897b'+rem)
  g.take('498b3e','4c8b742468','4885ff');g.branch('0f84',False);g.take('498b442420','488b88c0000000','488b4130','4883782000');g.branch('0f84',False);g.take('498b442420','488b5710','488b88c0000000','4c8b6930','ff471c','4885d2');g.branch('0f84',False)
  g.take('48634f18','3b4a18');g.branch('0f83',False);g.take('8d4101','894718','3b4a18');g.branch('0f83',False);g.take('4c8974ca20','4c8b742470')
  if g.relative('488d3d')!=s['callback']:raise ValueError('list64-callback-reload')
  g.take('ffc6','41bd00000000','3bf5');g.branch('0f8c',index+1<count)
 g.take('488b742460','4c8b7c2420','4883c428','415e','415d','415c','5f','5d','5b','c3')
 return dict(selectedBytes=g.seen,count=count,wireCountBytes=4,elementWireBytes=8,elementCallbacks=0,inlineSlot=5,selectedCallback=s['callback'],providerOwnerCell=owner,initialList='null',arrayStride=8,storedBits=64,normalFrameAndReturn=True,condition='Sufficient contiguous input; nonoverflowing coherent reader counters; initialized selected typed contexts; ordinary noninterfering normal context/allocation/barrier/provider/preparation helpers; new zeroed List with typed array capacity at least count; returned formatter slot5 equals the independently authenticated selected 64-bit callback. Other callbacks, existing populated lists, growth and live/default provider selection are unproved.')

def formatter(regions,entry,o):
 g=BytesPath(regions,entry);cur,rem,adv,used=(bytes((o[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed'))
 g.take('48895c2408','57','4883ec20','837a'+rem+'08','498bf8','488bda');g.branch('0f8c',False);g.take('488b42'+cur,'488b00','488907','8b7b'+rem,'83c7f8');g.branch('0f88',False)
 g.take('488343'+cur+'08','8343'+adv+'08','8343'+used+'08','897b'+rem,'488b5c2430','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,storedBits=64,wireBytes=8,output='incoming R8',reader='incoming RDX',normalFrameAndReturn=True,condition='Valid disjoint buffered Reader/output and coherent nonoverflowing counters; nominal closed element, slot5 identity and provider choice are separate.')

