"""Authenticate the static generic request independently of its physical target."""
from scripts.game_data.damage_snapshot_cache_flow import _require
from scripts.game_data.damage_snapshot_abi import require_ordinary_type,require_ordinary_type_var,require_ordinary_pointer
from scripts.game_data.il2cpp.context import method_spec_usage_index,method_spec_record
from scripts.game_data.il2cpp.protocol import runtime_type_name
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext


def require_request_shape(owner,name,flags,method_inst,parameter_count,argument_count,spec):
    _require(owner==spec['collectionType'] and name==spec['getterMethod'] and not flags&0x10 and method_inst==-1 and parameter_count==1 and argument_count==1,
             'process-context-request-shape','instance unary closed class getter without method instantiation',
             [owner,name,flags,method_inst,parameter_count,argument_count])


def check_process_context(index,loop_proof,provider_proof,spec):
    _require(loop_proof.get('claim')=='snapshotProcessLocalIncrementGuardAndProviderRequest' and provider_proof.get('claim')=='snapshotProcessActualProviderEightByteNormalReturn',
             'process-context-fresh-dependencies','fresh actual request and physical provider',[loop_proof.get('claim'),provider_proof.get('claim')])
    _require(loop_proof['guard']['providerTarget']==int(provider_proof['actualProviderEntry'],16),
             'process-context-same-target','same independently proved physical target',provider_proof['actualProviderEntry'])
    cell=loop_proof['guard']['anonymousContextQword'];r=index.image.registration
    si=method_spec_usage_index(index.pe.bytes_at_va(cell,8),r['methodSpecsCount'],source='processProviderRequest',offset=cell)
    va=int(r['methodSpecs'],16)+si*12
    di,ci,mi=method_spec_record(index.pe.bytes_at_va(va,12),len(index.metadata.methods),r['genericInstsCount'],source='processProviderRequest',offset=va)
    method=index.metadata.methods[di];owner=index.metadata.type_full_name(index.metadata.types[method.declaring_type]);name=index.metadata.string(method.name_index)
    arguments=index.image.instantiations.resolve(ci).arguments;parameters=index.metadata.parameters_for(method)
    require_request_shape(owner,name,method.flags,mi,len(parameters),len(arguments),spec)
    selected=NativeReferenceContext(index.image,index=index)
    require_ordinary_type(selected,parameters[0].type_index,'int','Process.provider.request.index')
    require_ordinary_type_var(selected,method.return_type,method.declaring_type,0,'Process.provider.request.resultVAR0')
    argument=arguments[0];actual=runtime_type_name(index.pe,index.metadata,argument.type_pointer_va)
    require_ordinary_pointer(selected,argument.type_pointer_va,actual,spec['unitType'],'Process.provider.request.classArg0',reference_kind=0x12)
    entries=sorted(p for p,aliases in index.names_by_pointer.items() if any(a.get('methodSpecIndex')==si for a in aliases))
    physical=loop_proof['guard']['providerTarget']
    return {'symbol':loop_proof['symbol'],'claim':'snapshotProcessStaticClosedUnitGetterRequest',
            'staticUsageCell':hex(cell),'methodSpecIndex':si,'requestedOwner':owner,'requestedMethod':name,'requestedClassArgument':actual,
            'registeredRequestEntries':[hex(p) for p in entries],'physicalTargetIsRegisteredRequestedEntry':physical in entries,
            'physicalTarget':hex(physical),'physicalClosedUnitSemanticsProved':False,
            'boundary':'The exact fresh caller RIP-loaded R8 usage cell authenticates a static instance List<Unit> getter MethodSpec request with ordinary Int32 parameter, reciprocal ordinary type VAR0 return owner/ordinal and ordinary Unit reference class argument. Physical target and registered requested entries are recorded independently; an empty registration set does not equate the folded compiled Object entry with the requested closed Unit entry. Initialized/live-resolved compatible context, receiver/array layout, returned bits being a Unit reference and runtime generic ABI remain conditions or unresolved. This typed request descriptor does not upgrade the physical eight-byte read into actual Unit semantics or prove continuous Process frame/cache compact-index equality.'}
