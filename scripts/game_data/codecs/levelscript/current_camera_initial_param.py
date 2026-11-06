"""Own raw camera initial-state value inside its nullable reference Param.

The complete selected native source proves the raw copy. Only the matching
selected-image layout names its fields; all padding and scalar bits survive.
"""
from scripts.game_data.codecs.levelscript.current_condition_param import _validate_shape

TYPE='Beyond.Gameplay.View.CameraControlStateInitialParam'


def validate(cap):
    _validate_shape(cap,'camera-initial-raw24',24)
    fields=cap.get('constantFields')
    if(cap.get('valueType')!=TYPE or cap.get('rawValueBitsPreserved')is not True
            or cap.get('runtimeCameraExecutionProved')is not False
            or not isinstance(fields,list)or not fields):
        raise ValueError('currentCameraInitial.own-raw24-fields')
    occupied=[];names=[]
    for row in fields:
        if(not isinstance(row,list)or len(row)!=3 or not isinstance(row[0],str)or not row[0]
                or row[1]not in('bool','float')or type(row[2])is not int):
            raise ValueError('currentCameraInitial.named-field-layout')
        width=1 if row[1]=='bool'else 4
        if not 0<=row[2]<=24-width:raise ValueError('currentCameraInitial.field-extent')
        occupied.extend(range(row[2],row[2]+width));names.append(row[0])
    if len(set(occupied))!=len(occupied)or len(set(names))!=len(names):
        raise ValueError('currentCameraInitial.disjoint-fields')


def read(reader,field,cap,*,layouts):
    validate(cap)
    layout=layouts.layout(TYPE,24)
    observed=[[r['fieldName'],r['layout']['typeName'],r['offset']]for r in layout.get('fields',[])]
    if observed!=cap['constantFields']:
        raise ValueError('currentCameraInitial.same-selected-native-field-layout')
    marker=reader.number('<B',field+'.memberCount')
    if marker==255:return None
    if marker!=4:raise ValueError(field+':camera-initial-Param-member-count')
    at=reader.offset;reader.need(24,field+'.constValue');reader.offset+=24
    constant=layouts.read(TYPE,bytes(reader.data[at:reader.offset]))
    return dict(constValue=constant,idRef=reader.number('<i',field+'.idRef'),
        paramSource=reader.number('<i',field+'.paramSource'),path=reader.string(field+'.path'))
