"""Initialized EntityAttract reference wrapper prefix and allocation paths."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def prefix(regions,entry,s,*,created=False,null=False):
    g=BytesPath(regions,entry);g.take('48895c2418','57','4883ec20');g.relative('803d');g.take('00','488bda','488bf9');g.branch('0f84',False)
    g.take('488d542430','c644243000','488bcf');g.call(s['header']);g.take('84c0');g.branch('0f84',null);allocation=None
    if null:
        g.take('488bcb','48c70300000000');g.call(s['barrier']);g.take('90');g.jump('e9')
        g.take('488b5c2440','4883c420','5f','c3')
    else:
        g.take('4889742438','48833b00');g.branch('0f84',created)
        if created:
            allocation=g.relative('488b0d');g.call(s['allocate']);g.take('488bf0','4885c0');g.branch('0f84',False)
            g.take('33d2','488bc8');g.call(s['constructor']);g.take('488bcb','488933');g.call(s['barrier']);g.take('90');g.jump('e9')
        g.take('0fb6742430','4080fe04');g.branch('0f85',False)
    return dict(selectedBytes=g.seen,nextAddress=g.at,allocationClassCellVA=allocation,created=created,null=null,
                selectedMemberCount=None if null else 4,sameReaderAndOutput=True,normalReturn=null,
                condition='Initialized header source; normal typed zeroed wrapper allocation, constructor and barrier. Positive prefix composes only at nextAddress with independently proved exact ordered four-field suffix.')


def constructor(regions,entry,s,*,factory=False):
    g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20');g.relative('803d');g.take('00','488bf9');g.branch('75'if factory else'74',factory,1)
    allocation=g.relative('488b0d');g.call(s['allocate']);g.take('488bd8','4885c0');g.branch('75'if factory else'74',factory,1)
    g.take('33d2','488bcb'if factory else'488bc8');g.call(s['originalConstructor'])
    g.take('488d4f10','48895f10','488b5c2430','4883c420','5f')
    if g.relative('e9')!=s['barrier']:raise ValueError('NPC entity constructor barrier tail')
    return dict(selectedBytes=g.seen,allocationClassCellVA=allocation,wrapperSlot=16,source='same normally returned original allocation in RBX',
                factory=factory,normalTail=True,condition='Initialized exact original allocation and current original constructor returns normally with same original reference; ordinary barrier tail effects remain conditional.')


def positive(regions,entry,reads,setters):
    if len(reads)!=4 or len(setters)!=4:raise ValueError('NPC entity exact four field transfers')
    g=BytesPath(regions,entry)
    for i,(reader,setter) in enumerate(zip(reads,setters,strict=True)):
        if i<3:
            cell=g.relative('488b15');g.take('488bcf','488b33');g.call(reader)
            g.take('4885f6');g.branch('0f84'if i==0 else'74',False,4 if i==0 else 1)
            g.take('4533c0','488bd0'if i==0 else'8bd0','488bce');g.call(setter)
        else:
            g.take('488b1b','488bcf');g.call(reader);g.take('4885db');g.branch('74',False,1)
            g.take('4533c0','488bd0','488bcb');g.call(setter)
    g.take('488b742438','488b5c2440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,normalReturn=True,readResultsToOwnedSetters=True,sameReaderAndHolder=True,
                condition='Selected initialized MC4 wrapper and exact child reader/setter helpers return normally; null-holder failures excluded.')
