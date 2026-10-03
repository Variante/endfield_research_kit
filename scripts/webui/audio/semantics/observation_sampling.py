"""Deterministic bounded representatives; aggregate every observed stratum first."""
import json


def _key(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


class StratifiedSamples:
    """Keep at most ``limit`` objects per stratum and round-robin at publication.

    Exact distinct signatures and stratum counts are retained separately. Keys
    only group local observations; they never establish allocation identity.
    """

    def __init__(self, limit):
        if type(limit) is not int or limit <= 0:
            raise ValueError("positive sample limit required")
        self.limit = limit
        self.strata = {}

    def add(self, stratum, identity, sample, *, label=None):
        bucket = self.strata.setdefault(_key(stratum), {
            "entryCount": 0, "seen": set(), "samples": {}, "label": label or {}})
        bucket["entryCount"] += 1
        key = _key(identity)
        bucket["seen"].add(key)
        kept = bucket["samples"]
        if key in kept:
            kept[key]["entryCount"] += 1
            if "captureId" in sample:
                kept[key]["captureId"] = min(kept[key]["captureId"], sample["captureId"])
        elif len(kept) < self.limit or key < max(kept):
            if len(kept) == self.limit:
                del kept[max(kept)]
            kept[key] = {**sample, "entryCount": 1}

    def finish(self):
        buckets = sorted(self.strata.items())
        ordered = [sorted(bucket["samples"].items()) for _, bucket in buckets]
        selected, per_stratum = [], [0] * len(buckets)
        for depth in range(self.limit):
            for index, samples in enumerate(ordered):
                if depth < len(samples) and len(selected) < self.limit:
                    selected.append({**samples[depth][1], "sampleStratum": index})
                    per_stratum[index] += 1
            if len(selected) == self.limit:
                break
        counts = [{"sampleStratum": index, **bucket["label"],
                   "entryCount": bucket["entryCount"], "distinctSampleCount": len(bucket["seen"]),
                   "sampleCount": per_stratum[index]}
                  for index, (_, bucket) in enumerate(buckets)]
        distinct = sum(row["distinctSampleCount"] for row in counts)
        represented = sum(value > 0 for value in per_stratum)
        return selected, {
            "strategy": "deterministicStratumRoundRobin", "sampleLimit": self.limit,
            "observedEntryCount": sum(row["entryCount"] for row in counts),
            "distinctSampleCount": distinct, "stratumCount": len(buckets),
            "representedStratumCount": represented, "omittedStratumCount": len(buckets) - represented,
            "samplesTruncated": distinct > len(selected), "strata": counts}
