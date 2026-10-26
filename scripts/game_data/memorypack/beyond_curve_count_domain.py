"""Integer count domain for the current raw FKeyframe32 array source.

This proves the selected arithmetic/count partition only. A current caller
must independently prove the complete source, typed allocation/empty/data
reference, and actual copy entry through the maximum byte count.
"""


def prove(*, count_limit, copy_max_bytes):
    from scripts.game_data.il2cpp.copy_dispatch_domains import require_interval_partition
    if type(count_limit) is not int or not 1 <= count_limit <= 10000:
        raise ValueError('beyondCurveCount.explicit-finite-count-domain')
    if type(copy_max_bytes) is not int or 32 * count_limit > copy_max_bytes:
        raise ValueError('beyondCurveCount.actual-copy-byte-bound')
    maximum_bytes = count_limit << 5
    if maximum_bytes > (1 << 31) - 1:
        raise ValueError('beyondCurveCount.signed-shift-result')
    partition = require_interval_partition((-1, count_limit), [
        dict(minimum=-1, maximum=-1, program='null'),
        dict(minimum=0, maximum=0, program='typed-empty'),
        dict(minimum=1, maximum=count_limit, program='typed-allocation-copy')], label='beyondCurveCount')
    return dict(countMinimum=-1, countMaximum=count_limit, countPartition=partition,
        positiveCountMinimum=1, positiveCountMaximum=count_limit,
        elementBytes=32, shiftBits=5, sourceCountBits=32, shiftedCountBits=32,
        maximumPayloadBytes=maximum_bytes, copyBoundCoversEveryPayload=True,
        allPositiveShiftResultsExactNonnegativeSignedInt32=True,
        allocationCountUnchanged=True, loopOverElements=False,
        positiveSourceControlSelection='All n in1..limit are unequal to-1 and nonzero; the exact owned source follows the same positive branch. R14D=EDI<<5 is exact n*32 throughout this domain; actual buffered-source sufficiency and no-underflow update predicates remain independently required.',
        counterCondition='Incoming advancedCount and consumed plus32*n fit signed Int32; current pointer plus32*n does not wrap; bufferLength is nonnegative and at least32*n; payload storage is readable and disjoint from output/allocation/frame.',
        childGrammarAdmitted=False, sourceProgramAdmitted=False, copyProgramAdmitted=False,
        unsupportedNegativeCountsAdmitted=False)
