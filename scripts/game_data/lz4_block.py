"""Bounded plain LZ4 block decoding with exact input/output consumption."""


def decompress_lz4(source,expected,*,max_output=128*1024*1024):
    if type(expected) is not int or not 0<=expected<=max_output:raise ValueError('LZ4 decoded size exceeds bounds')
    output=bytearray(expected);at=pos=0
    def length(value):
        nonlocal at
        if value==15:
            while True:
                if at>=len(source):raise ValueError('LZ4 length extension truncated')
                byte=source[at];at+=1;value+=byte
                if byte!=255:break
        return value
    while at<len(source):
        token=source[at];at+=1;literal=length(token>>4)
        if at+literal>len(source) or pos+literal>expected:raise ValueError('LZ4 literal exceeds bounds')
        output[pos:pos+literal]=source[at:at+literal];at+=literal;pos+=literal
        if at==len(source):break
        if at+2>len(source):raise ValueError('LZ4 match offset truncated')
        offset=source[at]|source[at+1]<<8;at+=2;match=length(token&15)+4
        if not 0<offset<=pos or pos+match>expected:raise ValueError('LZ4 match offset/length exceeds bounds')
        if match<=offset:output[pos:pos+match]=output[pos-offset:pos-offset+match]
        else:
            pattern=bytes(output[pos-offset:pos]);output[pos:pos+match]=(pattern*((match+offset-1)//offset))[:match]
        pos+=match
    if at!=len(source) or pos!=expected:raise ValueError(f'LZ4 exact byte census differs: input={at}/{len(source)}; output={pos}/{expected}')
    return bytes(output)
