"""MC2 EnemyShake value cursor; FF returns its separately proved default8."""
from scripts.game_data.memorypack.animation_enemy_shake_value_components import CAPABILITY,TYPE,require_capability


def read(reader,*,depth=0,budget=None):
    from scripts.game_data.memorypack.animation_extra_record_codec import budget_node,need
    need('bounded-enemy-shake-depth',type(depth)is int and 0<=depth<=64);budget_node(budget)
    cap=require_capability(reader.operation.child(CAPABILITY));start=reader.pos;default=reader.peek()==255
    fields=[]
    if default:
        reader.take(1,'EnemyShake.default8')
        fields=[dict(fieldName=name,rawHex='00000000')for name in cap['orderedFieldNames']]
    else:
        reader.header(2)
        fields=[dict(fieldName=name,rawHex=reader.take(4,name).hex())for name in cap['orderedFieldNames']]
    result=dict(kind=CAPABILITY,typeName=TYPE,start=start,end=reader.pos,isNull=False,defaultValue=default,
        defaultManagedValueHex='0000000000000000'if default else None,fields=fields,
        runtimeAnimationProved=False,containingRouteClaimed=False)
    reader.records.append(result);return result
