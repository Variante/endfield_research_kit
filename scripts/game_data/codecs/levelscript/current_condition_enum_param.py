"""Nominal enum Param grammar, separate from primitive Param selection."""
from scripts.game_data.codecs.levelscript.current_condition_param import _validate_shape,_read_record

SCHEMA='endfield.story-condition-enum-param-capability.v1'


def validate(cap):
 from scripts.game_data.memorypack.levelscript_condition_enum_param_sources import require_nominal
 if not isinstance(cap,dict):raise ValueError('currentConditionEnumParam.missing-capability')
 identity=require_nominal(cap.get('typeName'),cap.get('enumCarrier',{}),cap.get('enumDeclaration',{}))
 if(cap.get('schema')!=SCHEMA or cap.get('enumSourceAdmitted')is not True
    or cap.get('enumBackingType')!=identity['backingType']or cap.get('valueType')!=identity['valueType']
    or cap.get('genericHeapLayoutInferred')is not False):
  raise ValueError('currentConditionEnumParam.exact-own-enum-source')
 _validate_shape(cap,identity['constantWireKind'],identity['constantWireBytes'])


def read(reader,field,cap):
 validate(cap);return _read_record(reader,field,cap)
