"""Named AirWall raw24 values under their independently proved Param source."""
from scripts.game_data.codecs.levelscript.current_condition_param import _validate_shape

TYPE='Beyond.Gameplay.Core.AirWallPtr'


def validate(cap):
    _validate_shape(cap,'airwall-raw24',24)
    fields=cap.get('constantFields')
    if(cap.get('valueType')!=TYPE or cap.get('rawValueBitsPreserved')is not True
            or cap.get('runtimeAirWallResolutionProved')is not False
            or not isinstance(fields,list)or len(fields)!=3):
        raise ValueError('currentAirWall.own-raw24-fields')
    kinds=[('useSlotId','bool'),('logicId','ulong'),('slotId','uint')]
    widths={'bool':1,'ulong':8,'uint':4};occupied=[]
    for row,(name,kind)in zip(fields,kinds,strict=True):
        if(not isinstance(row,list)or len(row)!=3 or row[:2]!=[name,kind]
                or type(row[2])is not int or not 0<=row[2]<=24-widths[kind]):
            raise ValueError('currentAirWall.named-field-layout')
        occupied.extend(range(row[2],row[2]+widths[kind]))
    if len(set(occupied))!=len(occupied):raise ValueError('currentAirWall.disjoint-fields')


def read(reader,field,cap,*,layouts):
    validate(cap)
    layout=layouts.layout(TYPE,24)
    observed=[[r['fieldName'],r['layout']['typeName'],r['offset']]for r in layout.get('fields',[])]
    if observed!=cap['constantFields']:
        raise ValueError('currentAirWall.same-selected-native-field-layout')
    marker=reader.number('<B',field+'.memberCount')
    if marker==255:return None
    if marker!=4:raise ValueError(field+':AirWall-Param-member-count')
    at=reader.offset;reader.need(24,field+'.constValue');reader.offset+=24
    constant=layouts.read(TYPE,bytes(reader.data[at:reader.offset]))
    return dict(constValue=constant,idRef=reader.number('<i',field+'.idRef'),
        paramSource=reader.number('<i',field+'.paramSource'),path=reader.string(field+'.path'))
