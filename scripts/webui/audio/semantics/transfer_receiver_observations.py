"""Local transfer and receiver entry snapshots; never pair allocation lifetimes."""
from collections import Counter

from scripts.webui.audio.semantics.package_read_observations import checked_transform_fields
from scripts.webui.audio.semantics.observation_sampling import StratifiedSamples


SCHEMA = "endfield.audio-transfer-receiver-entry-observations.v1"
BOUNDARY = (
    "Non-atomic same-entry user-data/block and receiver/node comparisons under selected native gates. "
    "Address points select reviewed interface families only. The dispatcher recycles the block before "
    "receiver calls: later carrier block fields are raw observations, not the original transfer or its "
    "allocation generation. Only the dispatch flag's low byte is interpreted. No cross-entry pairing, "
    "decoder instance, codec selection, decoded PCM or audibility is established. "
    "All observed strata are counted before bounded representative selection; this is not corpus prevalence."
)
DISPATCH = "anonymousTransferCompletionDispatcher"
PRIMARY = "anonymousPrimaryReceiverTransferCompletion"
QUEUED = "anonymousQueuedReceiverTransferCompletion"
TRANSFORM = "anonymousPackageReadTransform"


def summarize(rows, hooks, read_gate):
    """Consume only audited rows and the mandatory transfer recipe companion."""
    transform_gate = read_gate.get("packageTransformGate", {})
    failed = next((gate for gate in (read_gate, transform_gate) if gate.get("status") != "validated"), None)
    if failed:
        return {"schema": SCHEMA, "status": failed.get("status", "missing"),
                "detail": failed.get("detail", "transfer native companion unavailable")}
    contract = transform_gate["contract"]
    points = {"primaryProviderInterface": int(contract["primaryReceiverSlot"]["addressPointRva"], 16),
              "queuedReceiverInterface": int(contract["queuedReceiverInterface"]["addressPointRva"], 16)}
    dispatcher = next(group for group in contract["nativeGroups"] if group["key"] == "transferCompletionDispatcher")
    call = next(witness for witness in dispatcher["instructionWitnesses"] if witness["role"] == "callReceiver")
    caller_return = int(call["rva"], 16) + len(bytes.fromhex(call["instructionHex"]))
    counts, families, statuses, observed = Counter(), Counter(), Counter(), 0
    sampler = StratifiedSamples(24)

    def retain(sample, interface_family):
        label = {"sourceKind": sample["sourceKind"], "interfaceFamily": interface_family,
                 "checkOutcome": sample["checkOutcome"]}
        sampler.add(label, {key:value for key,value in sample.items() if key != "captureId"}, sample, label=label)

    def family(pointer, base):
        if pointer is None:
            return "unreadableAddressPoint"
        return next((name for name, rva in points.items() if pointer == base + rva), "unreviewedAddressPoint")

    for row in rows:
        hook = hooks[row["hook"]]
        kind = hook["sourceKind"]
        if kind not in (DISPATCH, PRIMARY, QUEUED, TRANSFORM):
            continue
        # Historical read recipes cannot supply these fields.
        if kind == TRANSFORM and not any(field["name"] == "transferUserDataPointer" for field in hook["memory"]):
            continue
        observed += 1; counts[kind] += 1
        fields = {field["name"]: value if state == 1 else None
                  for field, value, state in zip(hook["memory"], row["values"], row["states"])}
        arg = lambda name: row["args"][hook["args"][name]["index"]]
        sample = {"captureId": row["captureId"], "sourceKind": kind}
        if kind in (PRIMARY, QUEUED):
            receiver = arg("receiverPointer")
            selected = family(fields.get("receiverAddressPointPointer"), row["moduleBase"])
            families[kind + ":" + selected] += 1
            local_match = bool(receiver and fields.get("nodeReceiverPointer") == receiver)
            reviewed_caller = row["returnAddress"] - row["moduleBase"] == caller_return
            expected_family = "primaryProviderInterface" if kind == PRIMARY else "queuedReceiverInterface"
            checked_receiver = local_match and reviewed_caller and selected == expected_family
            counts["receiverLocalNodeMatches"] += local_match
            counts["receiverReviewedDispatcherCallers"] += reviewed_caller
            counts["receiverCheckedFamilyEntries"] += checked_receiver
            status = arg("completionStatus") & 0xffffffff
            statuses[str(status)] += 1
            sample.update(receiverFamily=selected, localNodeReceiverMatch=local_match,
                          reviewedDispatcherCaller=reviewed_caller, completionStatus=status,
                          dispatchFlagByte=arg("dispatchFlagRegister") & 255,
                          checkOutcome="checkedReviewedReceiver" if checked_receiver else
                          "unreviewedDispatcherCaller" if not reviewed_caller else
                          "nodeReceiverMismatch" if not local_match else "unexpectedReceiverFamily")
            sampled_family = selected
            # These are deliberately not labelled a transfer join: the block was recycled.
            for name in ("nodeBufferCarrierPointer", "carrierTransferBlockPointer", "carrierTransferBlockOwnerPointer"):
                value = fields.get(name)
                sample[name] = hex(value) if value is not None else None
        else:
            if kind == TRANSFORM:
                checked, comparison = checked_transform_fields(row, hook, read_gate["observerSpec"])
                counts[comparison] += 1
                if checked is None:
                    sample["checkOutcome"] = comparison
                    retain(sample, "notChecked")
                    continue
            transfer = arg("transferPointer")
            user_data = fields.get("transferUserDataPointer")
            back_pointer = bool(transfer and user_data and
                                user_data + contract["transferBlockLayout"]["transferOffset"] == transfer)
            callback_match = fields.get("transferCallbackPointer") == row["moduleBase"] + int(dispatcher["entryRva"], 16)
            counts["embeddedBlockBackPointerMatches"] += back_pointer
            counts["reviewedTransferCallbackMatches"] += callback_match
            owner = fields.get("transferBlockOwnerPointer")
            owner_family = family(fields.get("transferBlockOwnerAddressPointPointer"), row["moduleBase"])
            families[kind + ":" + owner_family] += 1
            local_receiver_match = bool(owner and fields.get("firstCompletionReceiverPointer") == owner)
            counts["ownerEqualsFirstCompletionReceiver"] += local_receiver_match
            sample.update(blockBackPointerMatch=back_pointer, transferCallbackMatch=callback_match,
                          blockOwnerFamily=owner_family, ownerEqualsFirstCompletionReceiver=local_receiver_match,
                          checkOutcome="blockBackPointerMismatch" if not back_pointer else
                          "transferCallbackMismatch" if not callback_match else
                          "ownerFirstReceiverMismatch" if not local_receiver_match else
                          "unreviewedBlockOwnerFamily" if owner_family not in points else "checkedLocalTransfer",
                          descriptorKeyLow=fields.get("descriptorKeyLow"),
                          descriptorByteLength=str(fields["descriptorByteLength"]) if fields.get("descriptorByteLength") is not None else None,
                          transferFilePosition=str(fields["transferFilePosition"]) if fields.get("transferFilePosition") is not None else None,
                          transferRequestedBytes=fields.get("transferRequestedBytes"))
            sampled_family = owner_family
            if kind == DISPATCH:
                status = arg("completionStatus") & 0xffffffff
                statuses[str(status)] += 1
                sample["completionStatus"] = status
                default_io = bool(fields.get('cookieDescriptorPointer') and
                    fields.get('cookiePrimaryIoAddressPointPointer') == row['moduleBase'] +
                    int(read_gate['observerSpec']['primaryIoAddressPointRva'], 16))
                counts['dispatcherLocalDefaultIoMatches'] += default_io
                sample['defaultIoAddressPointMatch'] = default_io
                word = fields.get("bufferFirstWord")
                requested = fields.get("transferRequestedBytes")
                sample["dispatcherEntryBufferWord"] = f"{word:08x}" if word is not None and requested is not None and requested >= 4 else None
        retain(sample, sampled_family)
    samples, selection = sampler.finish()
    return {"schema": SCHEMA, "status": "validated", "entryCount": observed, "counts": dict(counts),
            "hookCounts": {kind:counts[kind] for kind in (TRANSFORM, DISPATCH, PRIMARY, QUEUED)},
            "interfaceFamilyCounts": dict(families), "completionStatusCounts": dict(statuses),
            "samples": samples, "samplesTruncated": selection["samplesTruncated"],
            "sampleSelection": selection, "evidenceBoundary": BOUNDARY}
