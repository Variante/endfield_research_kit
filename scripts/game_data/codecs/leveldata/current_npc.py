"""Current-owner NPC extension; historical NPC v1 never selects these wires."""
import math
import struct

from scripts.game_data.codecs.leveldata.npc_runtime import _Reader,LevelNpcCodecError
from scripts.game_data.memorypack.skill_root_children_codec import RootChildrenReader


class CurrentNpcReader(_Reader):
    def __init__(self,strings,layout,profile,require):
        super().__init__(strings,layout)
        self.profile,self.require=profile,require

    def value(self,data,cursor,field,plan):
        if plan['wire']=='u32':
            return self.number(data,cursor,field,lambda b,o:(struct.unpack_from('<I',b,o)[0],o+4)
                if 0<=o<=len(b)-4 else None)
        if plan['wire']!='current-data-pair':return super().value(data,cursor,field,plan)
        self.require();outer=self
        class Operation:
            def child(self,key):
                outer.require()
                if key!='skill-root-data-pair':raise ValueError('currentNpcBattle.unknown-value-child')
                return outer.profile['dataPairChild']
        class Bridge:
            pos=cursor;limit=len(data);operation=Operation()
            def __init__(self):self.data=data;self.records=[];self.pooled={}
            def peek(self):
                if not 0<=self.pos<self.limit:raise LevelNpcCodecError(field,self.pos,'DataPair header','truncated')
                return data[self.pos]
            def take(self,size,label):
                if type(size)is not int or size<0 or not 0<=self.pos<=self.limit-size:
                    raise LevelNpcCodecError(field,self.pos,label,'truncated')
                self.pos+=size
            def header(self,count):
                actual=self.peek()
                if actual!=count:raise LevelNpcCodecError(field,self.pos,count,actual)
                self.take(1,field+'.memberCount')
            def byte_payload(self):
                at=self.pos;value,self.pos=outer.string(data,self.pos,field+'.pool')
                self.pooled[at]=value
        bridge=Bridge();row=RootChildrenReader(bridge).record('skill-root-data-pair')
        value=dict(startOffset=cursor,endOffset=bridge.pos,returnsDefaultValue=row.get('returnsDefaultValue',False))
        if row['isNull']:
            value.update(isDynamic=False,key=None,valueDouble=0.0,valueDoubleBits='0000000000000000',valueStr=None)
            return value,bridge.pos
        spans={r['fieldName']:r['start']for r in row['fields']};boolean=data[spans['isDynamic']]
        if boolean not in(0,1):raise LevelNpcCodecError(field+'.isDynamic',spans['isDynamic'],'0 or 1',boolean)
        number=struct.unpack_from('<d',data,spans['valueDouble'])[0]
        value.update(isDynamic=bool(boolean),key=bridge.pooled[spans['key']],
            valueDouble=number if math.isfinite(number)else None,
            valueDoubleBits=f"{struct.unpack_from('<Q',data,spans['valueDouble'])[0]:016X}",
            valueStr=bridge.pooled[spans['valueStr']])
        return value,bridge.pos
