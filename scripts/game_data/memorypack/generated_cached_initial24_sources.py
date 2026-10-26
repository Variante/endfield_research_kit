"""Exact cached-getter InitialParam24 pointer transfer.

The nominal padded layout and declaring field are separate obligations. This
program proves the incoming pointer survives the actual getter and every one
of its 24 bytes is copied, including padding, before the frame returns.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

TYPE = 'Beyond.Gameplay.View.CameraControlStateInitialParam'
LABEL = 'generatedCachedInitial24'


def need(key, condition, detail=None):
    if not condition:
        raise ValueError(LABEL + '.' + key + ':' + str(detail)[:600])


def program(regions, entry, *, getter, field):
    from scripts.game_data.memorypack.generated_inline_constructor_sources import _nonnull
    from scripts.game_data.memorypack.generated_member_sources import _displacement

    need('literal-owned-getter-field', type(getter) is int and getter > 0
         and type(field) is int and 16 <= field < 2 ** 31 - 24)
    g = BytesPath(regions, entry)
    g.take('4053', '4883ec20', '488bda', '33d2')
    getter_call = g.at
    g.call(getter)
    g.take('4885c0')
    null = _nonnull(g)
    null['bytes'] = bytes(g.bytes[null['nullTargetVa'] + i] for i in range(6)).hex().upper()
    g.take('0f1003', 'f20f104b10', _displacement('0f1140', field),
           _displacement('f20f1148', field + 16), '4883c420', '5b', 'c3')
    return dict(selectedBytes=g.seen, getterTarget=getter, getterCallVa=getter_call,
                fieldOffset=field, storedBytes=24, sourceSlices=[[0, 16], [16, 8]],
                incomingPointerRegister='rdx', preservedPointerRegister='rbx',
                getterResultRegister='rax', ownedNullExit=null,
                completeSourceBitsStoredUnchanged=True, normalFrameAndReturn=True,
                entryRspRestored=True, nonvolatileRbxRestored=True,
                paddingBitsPreserved=True, boolBytesNormalized=False,
                nominalLayoutAdmitted=False, metadataFieldOwnershipProved=False,
                childGrammarAdmitted=False,
                condition='The independently nominally bound getter returns the compatible nonnull closed Original and preserves Win64 nonvolatiles. Source24 and destination are disjoint and stable. All incoming bytes are copied without normalization; no source framing, constructor, closed field metadata or runtime outcome is inferred.')
