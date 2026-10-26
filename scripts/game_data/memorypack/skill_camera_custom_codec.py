"""Finite CustomConfig34 wire fields on the same authenticated parent cursor."""
from scripts.game_data.memorypack import skill_camera_custom_components as source


def need(check,condition):
    if not condition:raise ValueError('skillCameraCustomCodec.'+check)


def require_capability(cap):
    need('own-complete-ordinary34',(cap.get('typeName'),cap.get('wrapperName'))==(source.TYPE,source.WRAPPER)
        and type(cap.get('memberCount'))is int and cap['memberCount']==34
        and cap.get('orderedReads')==source.ordered_reads()and all(type(r.get('memberIndex'))is int for r in cap['orderedReads'])
        and type(cap.get('nullMarker'))is int and cap['nullMarker']==255
        and all(cap.get(k)is True for k in('nullable','nullAdmitted','wholeGrammarAdmitted','ordinaryOriginalReadValueAdmitted',
            'ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved','completeSourceOwnedProgram','opaqueUnityInitializationRequired'))
        and cap.get('originalManagedConstructorInvoked')is False and cap.get('wholeOwnerAdmitted')is False
        and type(cap.get('referenceReaderMethodDefinition'))is int and cap['referenceReaderMethodDefinition']>0
        and type(cap.get('referenceReaderTargetRva'))is int and cap['referenceReaderTargetRva']>0)
    return cap


def preflight(reader):
    """Require all immediate child domains even before the record's FF branch."""
    from scripts.game_data.memorypack import skill_camera_module_codec as modules,skill_camera_transition_codec as transitions
    from scripts.game_data.memorypack.skill_animation_curve_codec import require_capability as curve
    from scripts.game_data.memorypack.skill_enum_list_codec import require_capability as enum
    operation=reader.operation
    curve(operation.child('curve-profile'))
    enum(operation.child(source.ENUM_LIST),operation.child(source.ENUM_ELEMENT),name=source.owner.ENUM)
    modules.require_collection(operation.child(source.module.LIST))
    modules.require_union(operation.child(source.module.CAPABILITY))
    for spec in source.module.RECORDS.values():modules.require_record(operation.child(spec['capability']),spec['capability'])
    transitions.require_collection(operation.child(source.transition.LIST),outer=True)
    transitions.require_collection(operation.child(source.transition.INNER_LIST),outer=False)
    transitions.require_and(operation.child(source.transition.CAPABILITY))
    transitions.require_leaf(operation.child(source.transition.LEAF))


def read(reader,capability=source.CAPABILITY,depth=0):
    need('finite-ordinary-capability',capability==source.CAPABILITY)
    need('depth',type(depth)is int and 0<=depth<=64)
    r=reader;cap=require_capability(r.operation.child(capability));preflight(r)
    start=r.pos;fields=[];null=r.peek()==255
    if null:r.take(1,capability+'.null')
    else:
        r.header(34)
        for field in cap['orderedReads']:
            at=r.pos;kind=field['kind'];child=field['childCapability']
            if child is not None:need('child-depth',depth+1<=64)
            if kind=='curve-profile':r._profile('curve_profile','curve-profile',depth+1)
            elif kind=='camera-enum-list':
                from scripts.game_data.memorypack.skill_enum_list_codec import read as enum
                enum(r,child,depth+1)
            elif kind=='camera-module-list':
                from scripts.game_data.memorypack.skill_camera_module_codec import CameraModuleReader
                CameraModuleReader(r).collection(depth+1)
            elif kind=='camera-transition-list':
                from scripts.game_data.memorypack.skill_camera_transition_codec import CameraTransitionReader
                CameraTransitionReader(r).collection(depth+1,outer=True)
            else:r.take({'bool-byte':1,'float32-bits':4,'scalar32':4,'camera-initial-raw24':24}[kind],capability+'.'+field['fieldName'])
            fields.append(dict(memberIndex=field['memberIndex'],fieldName=field['fieldName'],start=at,end=r.pos))
    row=dict(kind=capability,start=start,end=r.pos,isNull=null,fields=fields)
    r.records.append(row);return row
