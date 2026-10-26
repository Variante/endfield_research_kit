"""Current Unity curve formatter's bounded stored paths; no curve evaluation claim."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def unity_curve(regions,entry,offsets,s,*,null=False,keys=0):
    if type(keys)is not int or keys not in(-1,0,1,2):raise ValueError('modelViewCurve.path-witness')
    g=BytesPath(regions,entry);b=lambda n:bytes((n,)).hex();cur,rem,adv,used=(b(offsets[n])for n in('currentPtr','bufferLength','advancedCount','consumed'))
    g.take('4053','56','57','4156','4881eca8000000','837a'+rem+'01','4d8bf0','488bda');g.branch('0f8c',False)
    g.take('488b43'+cur,'0fb630','8b7b'+rem,'83ef01');g.branch('0f88',False)
    g.take('48ff43'+cur,'ff43'+adv,'ff43'+used,'897b'+rem,'4080feff');g.branch('0f84',null)
    cells={};allocations={};loop=None
    if null:
        g.take('33f6','498bce','498936','4881c4a8000000','415e','5f','5e','5b')
        if g.relative('e9')!=s['barrier']:raise ValueError('modelViewCurve.null-barrier')
    else:
        g.take('4080fe03');g.branch('0f85',False)
        g.take('4889ac24d0000000','4c89a424e0000000','4c89ac24e8000000','4c89bc24a0000000','837b'+rem+'08');g.branch('0f8c',False)
        g.take('488b43'+cur,'448b20','448b6804','4489642424','44896c2428','8b7b'+rem,'83c7f8');g.branch('0f88',False)
        g.take('488343'+cur+'08','8343'+adv+'08','8343'+used+'08','897b'+rem,'33f6','837b'+rem+'04','8bee');g.branch('0f8c',False)
        g.take('488b43'+cur,'486338','448b7b'+rem,'4183c7fc');g.branch('0f88',False)
        g.take('488343'+cur+'04','8343'+adv+'04','8343'+used+'04','44897b'+rem,'0f29b42490000000','0f29bc2480000000','440f29442470','440f294c2460','440f29542450','440f295c2440','83ffff');g.branch('74',keys==-1,1)
        if keys!=-1:
            allocations['keyArrayUsage']=g.at;cells['keyArray']=g.relative('488b0d');g.take('8bd7');g.call(s['arrayAllocate']);g.take('488be8','85ff');g.branch('0f8f',keys>0)
            if keys>0:
                g.take('48897c2430','488d7828','4c8bff','448be6','4c8bee','4885ed');g.branch('0f84',False);loop=g.at
                for i in range(keys):
                    if g.at!=loop:raise ValueError('modelViewCurve.same-key-loop')
                    g.take('443b6518');g.branch('0f83',False);g.take('837b'+rem+'1c');g.branch('0f8c',False)
                    g.take('488b43'+cur,'8b4810','f30f1030','f30f107804','f3440f104008','f3440f10480c','f3440f105014','f3440f105818','898c24d8000000','8b43'+rem,'83c0e4','89442420');g.branch('0f88',False)
                    g.take('488343'+cur+'1c','8343'+adv+'1c','8343'+used+'1c','8943'+rem,'498977f8','41ffc4','49897704','49ffc5','4989770c','f3450f1107','4983c71c','f30f1177f8','f30f117ffc','f3440f114f04','f3440f11570c','f3440f115f10','894f08','498bff','4c3b6c2430');g.branch('0f8c',i+1<keys)
                g.take('448b642424','448b6c2428');g.jump('e9')
        g.take('493936');g.branch('75',False,1);allocations['curveUsage']=g.at;cells['curve']=g.relative('488b0d');g.call(s['allocate']);g.take('488bd8','4885c0');g.branch('0f84',False)
        cells['create']=g.relative('488b05');g.take('4885c0');g.branch('0f84',False);g.take('33c9','ffd0','48894310','498bce','49891e');g.call(s['barrier'])
        for name,argument in(('wrap0','418bd4'),('wrap1','418bd5'),('keys','488bd5')):
            g.take('498b1e','4885db');g.branch('0f84',False);cells[name]=g.relative('488b05');g.take('4885c0');g.branch('0f84',False);g.take(argument,'488bcb')
            if name!='keys':g.take('ffd0')
        g.take('440f28542450','440f284c2460','440f28442470','0f28bc2480000000','0f28b42490000000','440f285c2440','4c8bac24e8000000','4c8ba424e0000000','488bac24d0000000','4c8bbc24a0000000','4881c4a8000000','415e','5f','5e','5b','48ffe0')
    return dict(selectedBytes=g.seen,null=null,keyCountWitness=keys,memberCount=None if null else 3,headerBytes=1,wrapBytes=0 if null else 8,countBytes=0 if null else 4,keyWireBytes=28,loopEntry=loop,cells=cells,allocations=allocations,wireOrder=['wrap0','wrap1','keys.count','keys[28]'],reader='incoming RDX saved RBX through every wire read and per-key cursor update',output='incoming R8 saved R14, same full reference output slot; normal selected new object/import setter tail',keyLoopInvariant='R12D/R13 start zero, increase once per same28-byte source block; R13 signed64 compares to sign-extended saved positive Int32 count; array stride28, bounds each iteration. For 0<count<=Int32Max, normal matching allocation and sufficient per-step buffer imply exactly count iterations without counter overflow.',condition='Matched current formatter context, buffered disjoint Reader/storage, selected null or MC3, count -1/0/positive, fresh key/curve allocation returns coherent current class/length, nonnull initialized matching icall caches and normally returning ABI-preserving helpers/barriers. Cold refill/error, icall runtime resolution, allocation/import effects and curve evaluation remain conditional; native typed dispatch/field joins are separate.')
