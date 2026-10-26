"""Current direct ModelView union callback's fresh-child short-tag routes."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def branch(g,short,near,taken):
    if g.bytes.get(g.at)==int(short,16):g.branch(short,taken,1)
    else:g.branch(near,taken,4)


def new_child(regions,entry,s,*,tag,count,table,selected,special,existing=True):
    if type(tag)is not int or not 0<=tag<count<=128 or not 0<=special<count:raise ValueError('modelViewUnion.scope')
    g=BytesPath(regions,entry);g.take('48895c2408','4889742418','57','4883ec20');g.relative('803d');g.take('00','498bf8','488bda');g.branch('0f84',False,4);g.take('33f6','488d542438','488bcb','6689742438');g.call(s['header']);g.take('84c0');g.branch('0f84',False,4);g.take('0fb7742438','8bc6','83fe'+bytes((special,)).hex());g.branch('75',tag!=special,1)
    if tag==special:
        if g.at!=selected:raise ValueError('modelViewUnion.special-target')
        image_base=None
    else:
        g.take('83f8'+bytes((count-1,)).hex());g.branch('0f87',False,4);image_base=g.relative('488d15');g.take('8b8cb2'+(table-image_base).to_bytes(4,'little').hex(),'4803ca','ffe1');g.at=selected
        if selected not in g.bytes:raise ValueError('modelViewUnion.unowned-case')
    g.take('488b0f','4885c9');branch(g,'74','0f84',not existing);cast_usage=None
    if existing:
        site=g.at;cell=g.relative('488b15');cast_usage=dict(instruction=site,cell=cell);g.take('488b09');g.call(s['assignable']);g.take('84c0')
        if g.bytes.get(g.at)==0x75 or g.bytes.get(g.at)==0x0f and g.bytes.get(g.at+1)==0x85:branch(g,'75','0f85',False)
        else:branch(g,'74','0f84',True)
    context_site=g.at;context=g.relative('488b15');g.take('488bcb');g.call(s['packable'])
    if g.bytes.get(g.at+2)==0xcf:g.take('488bcf','488907')
    else:
        g.take('488907')
        if g.bytes.get(g.at)in(0xeb,0xe9):g.jump('eb',1)if g.bytes[g.at]==0xeb else g.jump('e9',4)
        g.take('488bcf')
    g.call(s['barrier'])
    if g.bytes.get(g.at)in(0xeb,0xe9):g.jump('eb',1)if g.bytes[g.at]==0xeb else g.jump('e9',4)
    g.take('488b5c2430','488b742440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,tag=tag,entryCount=count,imageBase=image_base,table=table,selected=selected,special=special,existingBaseWrapper=existing,castUsage=cast_usage,childContext=dict(instruction=context_site,cell=context),sameReader=True,sameOutput=True,normalReturn=True,condition='Initialized direct default-formatter callback, short header returns exact selected tag. Incoming output is null or contains the freshly selected coherent Abstract BaseW; current class predicate returns false for selected distinct derived ChildW. Actual typed ReadPackable<ChildW> returns normal fullref8; exact same Reader and output store/barrier/frame return, disjoint stable storage and Win64 helper ABI. Compatible existing-child byref route and live/runtime/provider/factory/predicate effects remain conditional and unadmitted.')
