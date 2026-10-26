"""Conservative lane-aware dependencies for straight-line DXBC outputs.

This proves syntactic dependencies only. It neither evaluates floating point
instructions nor claims control-flow, texture contents or runtime bindings.
Unsupported instructions on the slice and any control flow fail closed.
"""
import re

LANES='xyzw'
COMPONENTWISE={'mov','add','mul','mad','div','min','max','sqrt','rsq','exp','log','frc','round_ne','round_ni','round_pi','round_z',
    'lt','ge','eq','ne','movc','and','or','xor','not','iadd','imad','ishl','ishr','ushr','itof','utof','ftoi','ftou','f16tof32','f32tof16','deriv_rtx','deriv_rty'}
DUAL_DESTINATIONS={'imul','umul','udiv','sincos'}
FLOW={'if_nz','if_z','else','endif','loop','endloop','switch','case','default','endswitch','break','breakc_nz','breakc_z',
    'continue','continuec_nz','continuec_z','call','callc_nz','callc_z','retc_nz','retc_z','discard_nz','discard_z'}


def operands(text):
    result=[];start=0;depth=0
    for i,c in enumerate(text):
        if c in '([':depth+=1
        elif c in ')]':depth-=1
        elif c==',' and not depth:result.append(text[start:i].strip());start=i+1
        if depth<0:raise ValueError('instruction operand delimiter differs')
    if depth:raise ValueError('instruction operand delimiter unclosed')
    result.append(text[start:].strip());return result


def instruction_parts(line):
    depth=0
    for i,c in enumerate(line):
        if c=='(':depth+=1
        elif c==')':depth-=1
        elif c.isspace() and depth==0:return line[:i],line[i:].strip()
        if depth<0:raise ValueError('instruction opcode delimiter differs')
    if depth:raise ValueError('instruction opcode delimiter unclosed')
    return line,''


def output_dependencies(executable,output):
    match=re.fullmatch(r'(o\d+)\.([xyzw]+)',output)
    if not match or len(set(match[2]))!=len(match[2]):raise ValueError('unsupported output slice')
    live={(match[1],c) for c in match[2]};selected=[];buffers={};resources=set();failure=None
    def source(token,positions):
        token=token.strip('-|')
        if token.startswith('l('):return
        m=re.fullmatch(r'(r\d+|v\d+|cb\d+\[[^\]]+\]|[tsu]\d+)(?:\.([xyzw]+))?',token)
        if m is None:raise ValueError('unsupported dependency operand '+token)
        register,swizzle=m[1],m[2] or LANES
        if len(swizzle) not in (1,4):raise ValueError('unsupported dependency source swizzle '+token)
        lanes={swizzle[0] if len(swizzle)==1 else swizzle[p] for p in positions}
        cb=re.fullmatch(r'(cb\d+)\[([^\]]+)\]',register)
        if cb:
            key=(cb[1],cb[2]);buffers.setdefault(key,set()).update(lanes)
            if not cb[2].isdecimal():
                for reg,lane in re.findall(r'\b(r\d+)\.([xyzw])',cb[2]):live.add((reg,lane))
        elif register[0] in 'tsu':resources.add(register)
        else:live.update((register,c) for c in lanes)
    try:
        returns=[i for i,line in enumerate(executable['instructions']) if line.split()[0]=='ret']
        if returns!=[len(executable['instructions'])-1]:raise ValueError('output slice requires one terminal return')
        for ordinal,line in reversed(list(enumerate(executable['instructions']))):
            token,tail=instruction_parts(line);opcode=token.split('(')[0];base=opcode.removesuffix('_sat')
            if base in FLOW:raise ValueError('control flow requires a separate dependency reader')
            if base in ('ret','nop'):continue
            args=operands(tail) if tail else []
            destinations=args[:2] if base in DUAL_DESTINATIONS else args[:1]
            needed=set()
            for token in destinations:
                if token=='null' and base in DUAL_DESTINATIONS:continue
                dst=re.fullmatch(r'(r\d+|o\d+)(?:\.([xyzw]+))?',token)
                if dst is None:raise ValueError('unsupported dependency destination '+line)
                needed.update((dst[1],c) for c in dst[2] or LANES if (dst[1],c) in live)
            if not needed:continue
            selected.append(ordinal);live.difference_update(needed)
            positions={LANES.index(c) for reg,c in needed}
            if base in COMPONENTWISE or base in DUAL_DESTINATIONS:
                for arg in args[len(destinations):]:source(arg,positions)
            elif base in ('dp2','dp3','dp4'):
                for arg in args[1:]:source(arg,set(range(int(base[-1]))))
            elif base=='sample_b_indexable':
                if len(args)!=5:raise ValueError('unsupported biased texture sample')
                # Dimension is checked from the executable declaration, not a
                # texture name. Only the selected 2D form is supported here.
                tex=re.match(r'(t\d+)',args[2]);decl=executable['declarations'].get(tex[1]) if tex else None
                if not decl or not decl['declaration'].startswith('dcl_resource_texture2d '):raise ValueError('unsupported sampled texture dimension')
                source(args[1],{0,1});source(args[2],positions);source(args[3],{0});source(args[4],{0})
            else:raise ValueError('unsupported dependency opcode '+base)
        if any(reg.startswith(('r','o')) for reg,lane in live):raise ValueError('output depends on an undefined register lane')
    except ValueError as e:failure=str(e)
    if failure:return dict(status='unresolved',output=output,reason=failure)
    return dict(status='structuralOnly',output=output,instructionOrdinals=sorted(selected),
        inputLanes=[dict(register=r,lanes=''.join(c for c in LANES if (r,c) in live)) for r in sorted({r for r,c in live})],
        resourceRegisters=sorted(resources),constantBufferReads=[dict(register=r,address=a,
            byteOffsets=sorted(int(a)*16+LANES.index(c)*4 for c in lanes) if a.isdecimal() else None,
            lanes=''.join(c for c in LANES if c in lanes)) for (r,a),lanes in sorted(buffers.items())],
        evidenceBoundary='Conservative straight-line instruction dependencies, preserving source swizzles and destination masks. Syntactic reads can be canceled by actual values. No execution, uploaded-value, resource-content or final-image claim.')
