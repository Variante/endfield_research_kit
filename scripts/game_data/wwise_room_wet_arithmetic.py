"""Original first-vector RoomVerb wet operations, with recorded SSE controls."""
from __future__ import annotations
from scripts.game_data.wwise_room_input_arithmetic import _history_binary,UnsupportedArithmetic


def operations(mxcsr):
    if type(mxcsr) is not int or not 0<=mxcsr<2**16 or mxcsr&0x6000 or mxcsr&0x1f80!=0x1f80:raise UnsupportedArithmetic('roomWetRoundingUnsupported')
    add=lambda a,b:_history_binary(a,b,'add',mxcsr)
    mul=lambda a,b:_history_binary(a,b,'mul',mxcsr)
    sub=lambda a,b:add(a,b^0x80000000)
    return add,mul,sub


def fdn_prefix_modes(lengths,indices,frames,words=4):
    """Native segment headroom determines vector lanes versus scalar remainder."""
    if len(lengths)!=4 or len(indices)!=4 or type(frames) is not int or frames<4 or type(words) is not int or not 4<=words<=frames or any(type(n) is not int or n<4 or type(p) is not int or not 0<=p<n for n,p in zip(lengths,indices)):raise UnsupportedArithmetic('roomFdnGeometryNotSelected')
    modes=[];position=list(indices);remaining=frames
    while len(modes)<words:
        segment=min(remaining,*(n-p for n,p in zip(lengths,position)));vector=segment//4*4
        modes.extend([False]*min(vector,words-len(modes)))
        modes.extend([True]*min(segment-vector,words-len(modes)))
        position=[(p+segment)%n for n,p in zip(lengths,position)];remaining-=segment
    return modes


def fdn_prefix(rings,history,b0,a1,inputs,output,scale,mxcsr,scalar=None):
    if len(rings)!=4 or any(len(v)!=4 for v in rings) or any(len(v)!=4 for v in (history,b0,a1,inputs,output)):raise ValueError('four complete ring/filter/sample vectors required')
    if scalar is None:scalar=[False]*4
    if len(scalar)!=4 or any(type(v) is not bool for v in scalar):raise ValueError('four native path selections required')
    add,mul,sub=operations(mxcsr);h=list(history);filtered=[]
    for i in range(4):
        h=[add(mul(rings[j][i],b0[j]),mul(h[j],a1[j]^0x80000000)) for j in range(4)];filtered.append(h)
    actual=[];new=[[] for _ in range(4)]
    for i,u in enumerate(filtered):
        if scalar[i]:
            actual.append(add(add(add(u[1]^0x80000000,u[0]),add(u[3]^0x80000000,u[2])),output[i]))
            scaled=[mul(v,scale) for v in u];total=add(add(scaled[1],scaled[0]),add(scaled[3],scaled[2]))
            for j in range(4):new[j].append(add(add(total,u[(j+1)%4]),inputs[i]))
        else:
            actual.append(sub(add(add(u[2],u[0]),output[i]),add(u[3],u[1])))
            total=add(add(add(u[1],u[0]),u[2]),u[3]);z=add(mul(total,scale),inputs[i])
            for j in range(4):new[j].append(add(z,u[(j+1)%4]))
    return actual,new,h


def damping_prefix(inputs,previous_input,previous_output,pole,gain,mxcsr):
    if len(inputs)!=4:raise ValueError('four wet input words required')
    add,mul,sub=operations(mxcsr);result=[]
    for x in inputs:
        scaled=mul(gain,x);previous_output=add(sub(scaled,previous_input),mul(previous_output,pole));previous_input=scaled;result.append(previous_output)
    return result,previous_input,previous_output


def early_prefix(projection,inputs,mxcsr):
    """First native vector block writes current input before reading any taps."""
    if len(inputs)!=4:raise ValueError('four early input words required')
    add,mul,_=operations(mxcsr);length=projection['length'];index=projection['ringIndex']
    if length<4 or index+4>length or not 0<=index<length:raise UnsupportedArithmetic('roomEarlyFirstVectorNotSelected')
    results=[]
    for bank in projection['banks']:
        output=[0]*4
        for tap in bank:
            position=tap['index']
            if not 0<=position<=length-4:raise UnsupportedArithmetic('roomEarlyTapVectorNotSelected')
            values=[inputs[position+i-index] if index<=position+i<index+4 else tap['words'][i] for i in range(4)]
            output=[add(y,mul(tap['gainBits'],x)) for y,x in zip(output,values)]
        results.append(output)
    return results
