"""Current Lock2/SingleLock18 cursor; no native opener or owner authority."""
from scripts.game_data.memorypack import leveldata_lock_sources as source
from scripts.game_data.memorypack.leveldata_extended_record_sources import STRING_CAP
from scripts.game_data.memorypack.leveldata_lang_key_components import CAP as LANG_CAP
from scripts.game_data.codecs.leveldata import current_lang_key


def _program(cap,name,plan):
    program=cap.get('program',{});child=lambda t:LANG_CAP if t==source.LANG else STRING_CAP if t==source.STRINGS else source.SINGLE_CAP if t==source.SINGLES else None
    if (cap.get('typeName')!=name or type(cap.get('memberCount'))is not int or cap['memberCount']!=len(plan)
            or any(cap.get(k)is not True for k in('nullAdmitted','positiveAdmitted','profileAdmitted','actualCallbackEqualsProvedChildRequired'))
            or cap.get('wholeGrammarAdmitted')is not False or cap.get('liveFormatterSelectionObserved')is not False
            or type(cap.get('countLimit'))is not int or cap['countLimit']!=source.LIMIT
            or program.get('memberCount')!=len(plan)
            or any(type(r.get('memberIndex'))is not int for r in program.get('reads',[]))
            or[(r.get('memberIndex'),r.get('fieldName'),r.get('kind'),r.get('childCapability'))for r in program.get('reads',[])]!=[
                (i,n,k,child(t)or('byte-payload'if k=='byte-payload'else None))for i,(n,t,k)in enumerate(plan)]
            or program.get('requiredCapabilities')!=sorted({child(t)or'byte-payload'for n,t,k in plan if child(t)or k=='byte-payload'})):
        raise ValueError('currentLocks.exact-finite-record-program:'+name)
    bindings=program.get('childBindings',[])
    if ([(b.get('fieldName'),b.get('typeName'),b.get('capability'))for b in bindings]!=[(n,t,child(t))for n,t,k in plan if child(t)]
            or any(type(b.get('readerMethodDefinition'))is not int or b['readerMethodDefinition']<0
                or type(b.get('sourceTargetRva'))is not int or b['sourceTargetRva']<=0 for b in bindings)):
        raise ValueError('currentLocks.exact-child-bindings:'+name)
    return bindings


def validate(lock,single,lang):
    current_lang_key.validate(lang)
    for binding in _program(single,source.SINGLE,source.SINGLE_PLAN):
        if binding['typeName']==source.LANG:
            if ((binding['readerMethodDefinition'],binding['sourceTargetRva'])!=(lang['readerMethodDefinition'],lang['sourceTargetRva'])
                    or type(binding.get('managedBytes'))is not int or binding['managedBytes']!=16 or binding.get('referenceLaneOffsets')!=[0,8]
                    or any(type(binding.get(k))is not int for k in('wireMemberCount','positiveWireBytes','nullWireBytes'))
                    or(binding.get('wireMemberCount'),binding.get('positiveWireBytes'),binding.get('nullWireBytes'))!=(1,5,1)
                    or any(binding.get(k)is not True for k in('nonserializedRawText','actualCallbackEqualsProvedChildRequired','completeFieldTransferAndFrameProved'))):
                raise ValueError('currentLocks.exact-LangKey-parent')
        else:
            strings=single.get('collections',{}).get(STRING_CAP,{})
            if (strings.get('closedListType')!=source.STRINGS or strings.get('elementType')!='string'
                    or strings.get('elementValueType')is not False
                    or any(strings.get(k)is not True for k in('nullable','positiveCountsAdmitted','elementGrammarAdmitted','actualCallbackEqualsPooledStringRequired'))
                    or type(strings.get('countLimit'))is not int or strings['countLimit']!=source.LIMIT
                    or(strings.get('packableReaderMethodDefinition'),strings.get('packableReaderTargetRva'))!=(binding['readerMethodDefinition'],binding['sourceTargetRva'])
                    or binding.get('countLimit')!=source.LIMIT or binding.get('actualCallbackEqualsPooledStringRequired')is not True):
                raise ValueError('currentLocks.exact-pooled-string-list-parent')
    enum=single.get('enumBackings',{}).get('unlockType',{});typename=source.SINGLE_PLAN[-1][1]
    if (set(single.get('enumBackings',{}))!={'unlockType'}or enum.get('typeName')!=typename or enum.get('backing')not in('int','uint')
            or enum.get('field')!=[typename,enum.get('backing'),16]):
        raise ValueError('currentLocks.exact-unlock-enum')
    binding,=_program(lock,source.TYPE,source.PLAN);listing=lock.get('collections',{}).get(source.SINGLE_CAP,{})
    if (listing.get('typeName')!=source.SINGLES or listing.get('elementType')!=source.SINGLE
            or any(listing.get(k)is not True for k in('nullable','positiveCountsAdmitted','actualCallbackEqualsProvedChildRequired'))
            or type(listing.get('countLimit'))is not int or listing['countLimit']!=source.LIMIT
            or(listing.get('readerMethodDefinition'),listing.get('sourceTargetRva'))!=(binding['readerMethodDefinition'],binding['sourceTargetRva'])
            or binding.get('countLimit')!=source.LIMIT or binding.get('actualCallbackEqualsProvedChildRequired')is not True):
        raise ValueError('currentLocks.exact-single-lock-list-parent')


def read_single(reader,field,cap,lang):
    # Full parent validation happens before any enclosing FF/empty marker.
    start=reader.offset
    if not reader.header(source.SINGLE,18,field):return None
    result=dict(startOffset=start,memberCount=18,recordType=source.SINGLE);spans={}
    for name,declared,kind in source.SINGLE_PLAN:
        path=field+'.'+name;at=reader.offset
        if kind=='scalar64-bits':value=str(reader.number('<Q',path))
        elif kind=='byte-payload':value=reader.string(path)
        elif kind=='bool-byte':value=reader.boolean(path)
        elif kind=='lang-key':value=current_lang_key.read(reader,path,lang)
        elif kind=='scalar32':value=reader.number('<i'if cap['enumBackings']['unlockType']['backing']=='int'else'<I',path)
        elif kind=='pooled-string-list':
            count=reader.number('<i',path+'.count')
            if not -1<=count<=source.LIMIT:reader.refuse(path,'current-lock-string-count-limit',count)
            reader.need(max(count,0)*4,path+'.indices')
            value=dict(startOffset=at,count=count,rows=None if count==-1 else[reader.string(path+f'[{i}]')for i in range(count)],endOffset=reader.offset)
        else:reader.refuse(path,'closed-current-lock-operation',kind)
        result[name]=value;spans[name]=[at,reader.offset]
    result.update(endOffset=reader.offset,fieldRanges=spans);return result


def read(reader,field,cap,single,lang):
    validate(cap,single,lang);start=reader.offset
    if not reader.header(source.TYPE,2,field):return None
    count_start=reader.offset;count=reader.number('<i',field+'.locks.count')
    if not -1<=count<=source.LIMIT:reader.refuse(field,'current-single-lock-count-limit',count)
    reader.need(max(count,0),field+'.locks.elements')
    rows=None if count==-1 else[read_single(reader,field+f'.locks[{i}]',single,lang)for i in range(count)]
    locks=dict(startOffset=count_start,endOffset=reader.offset,count=count,rows=rows)
    identity=str(reader.number('<Q',field+'.logicIdGlobal'))
    return dict(startOffset=start,endOffset=reader.offset,memberCount=2,recordType=source.TYPE,locks=locks,logicIdGlobal=identity)
