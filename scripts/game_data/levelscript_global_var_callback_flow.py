"""Whole callback partition and selected normal transfer program."""

from scripts.game_data import levelscript_param_value_bridge as bridge
from scripts.game_data.memorypack.scalar_param_native import need


def check_callback(rows, fields, targets):
    label = 'globalVarCallback'
    raw = lambda n: bytes.fromhex(rows[n]['bytes'])
    normalized = [[int(r['va'], 16), bytes.fromhex(r['bytes']).hex()] for r in rows]
    forms = ['48895c2408','4889742410','57','4883ec20',None,'488bda','488bf1',None,
             None,None,None,None,None,None,'33d2','8bcf',None,'84c0',None,None,
             '41b001','488b8e'+fields['_comparer'].to_bytes(4,'little').hex(),'33d2','488b7b08',None,
             None,'41b001','488b8e'+fields['_targetValue'].to_bytes(4,'little').hex(),'33d2','8bd8',None,
             '0f57d2','0f57c9','f3480f2ad0','4533c9','8bcb','f3480f2acf',None,
             '0fb6d0','4533c0','488bce',None,None,'33d2','8bcf',None,'4885c0',None,None,
             'cc','4533c9','4c8bc3','488bd6','488bc8',None,'488b5c2430','488b742438','4883c420','5f','c3']
    bridge.shape(normalized, forms, label)
    need(label, 'wholePrimaryBytes', 228, sum(len(bytes.fromhex(r['bytes'])) for r in rows))
    for n, prefix, suffix in [(4,b'\x80\x3d',b'\x00'),(8,b'\x48\x8d\x0d',b''),
                             (10,b'\x48\x8d\x0d',b''),(12,b'\xc6\x05',b'\x01'),
                             (19,b'\x4c\x8b\x0d',b''),(25,b'\x4c\x8b\x0d',b'')]:
        need(label, 'ripInstructionSize'+str(n), 7, len(raw(n)))
        need(label, 'ripInstructionPrefix'+str(n), prefix, raw(n)[:len(prefix)])
        if suffix: need(label, 'ripInstructionSuffix'+str(n), suffix, raw(n)[-len(suffix):])
    def rip(n, tail=0):
        return normalized[n][0]+len(raw(n))+int.from_bytes(raw(n)[len(raw(n))-4-tail:len(raw(n))-tail if tail else None], 'little', signed=True)
    need(label,'sameInitFlag',rip(4,1),rip(12,1))
    need(label,'sameEnumUsageCell',rip(8),rip(19))
    need(label,'sameLongUsageCell',rip(10),rip(25))
    need(label,'patchLiteralEncoding',b'\xbf',raw(13)[:1]);need(label,'patchLiteralWidth',5,len(raw(13)))
    for at, role in [(16,'patch'),(24,'enumValue'),(30,'longValue'),(37,'compare'),(41,'resultSetter')]:
        need(label,'actualCall.'+role,targets[role],bridge.target(normalized[at],b'\xe8'))
    need(label,'sameOpaqueInitializer',bridge.target(normalized[9],b'\xe8'),bridge.target(normalized[11],b'\xe8'))
    for n in (45,48,54): bridge.target(normalized[n],b'\xe8')
    for at, opcode, destination in [(7,b'\x75',13),(18,b'\x75',43),(42,b'\xeb',55),(47,b'\x75',50)]:
        need(label,'ownedEdge'+str(at),normalized[destination][0],bridge.target(normalized[at],opcode))
    paths=[]
    def walk(n,path):
        need(label,'acyclicSelectedCFG',True,n not in path and len(path)<61)
        path=path+[n]
        if n==59: paths.append(path);return
        if n==7:
            walk(13,path);walk(8,path)
        elif n==18:walk(19,path)  # actual patch AL=0 is the selection
        elif n==42:walk(55,path)
        else:
            need(label,'excludedReplacementPath',True,n<43 or n>=55)
            walk(n+1,path)
    walk(0,[]);need(label,'selectedNormalPaths',2,len(paths))
    for path in paths:
        need(label,'fullFrame',True,all(n in path for n in (0,1,2,3,5,6,23,29,30,33,36,37,38,40,41,55,56,57,58,59)))
    return {'wholePrimaryBytes':228,'wholeInstructions':60,'selectedNormalPaths':2,'frameDelta':40,
            'eventLane':{'input':'original explicit byref argument','offset':8,'bytes':8,'namedFieldPlacementProved':False},
            'comparisonArguments':{'a':'signed Int64 event-lane conversion to Single in XMM1',
                                   'b':'signed Int64 current GetValue return conversion to Single in XMM2',
                                   'operator':'current enum GetValue EAX retained through EBX into ECX'},
            'resultRequest':'current comparison AL zero-extended to EDX for ConditionResult setter',
            'normalizationOrConcreteResultProved':False,'setterBodyEffectsProved':False,
            'conditions':['patch request returns AL=0','normal ABI returns and retained nonvolatile registers',
                          'selected initialized usage cells and compatible loaded generic contexts',
                          'valid compatible receiver and anonymous byref QWORD lane',
                          'MXCSR rounding/exception conditions for both signed conversions']}
