"""Two explicit source programs; equal widths never select an enum variant."""


def select(value):
    if value is None:
        return dict(backingType='int',underlyingKind=8,placeholderType='System.Int32Enum',
            placeholderName=b'Int32Enum',wireBytes=4,
            formatterTypes=('MemoryPack.Formatters.ListFormatter`1','MemoryPack.Formatters.UnmanagedFormatter`1'))
    if type(value)is str and value=='byte':
        return dict(backingType='byte',underlyingKind=5,placeholderType='System.ByteEnum',
            placeholderName=b'ByteEnum',wireBytes=1,
            formatterTypes=('MemoryPack.Formatters.UnmanagedFormatter`1',))
    raise ValueError('enumSourceVariants.explicit-int32-default-or-byte-only')


BYTE_CONDITION='Explicit byte-backed nominal variant: fresh ordinary enum/value__ metadata, actual original nominal requests and source-selected ByteEnum class/code registrations. Coherent initialized original class/MethodInfo/contexts, canonical interner/method-key/registry state, normal helpers and no replacement are required. No Int32Enum or primitive-byte alias is inferred.'
