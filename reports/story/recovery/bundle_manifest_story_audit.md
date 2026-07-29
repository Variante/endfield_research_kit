# BundleManifest Story audit

- classification: **resource_routing_only**
- mission-graph action: **none**
- effective source: **persistent**
- StreamingAssets version: 22,097,503
- Persistent version: 22,764,515
- compressed / decompressed bytes: 46,476,082 / 137,818,624

## Validated content

- manifest hash: `5f521eb8-5202-dcdf-2412-02d992d0d771`
- hash version: `d8a7b49e0f157b6793ac5f7ac77c8da0`
- assets: 327,584 in 327,584 buckets
- bundles: 237,800 in both the dictionary and array
- data pool: 102,604,548 bytes with matching prefix/suffix lengths
- exact encoded target hits: 0

## Typed reader boundary

AssetInfo fields: `pathHashHead`, `path`, `bundleIndex`, `assetSize`.

Bundle fields: `bundleIndex`, `name`, `dependencies`, `directReverseDependencies`, `directDependencies`, `bundleFlags`, `hashName`, `hashVersion`, `category`.

The complete effective manifest is a validated asset-path to bundle routing index plus bundle dependency metadata. Its typed records expose no mission, quest, LevelScript, phase, playback selector, or owner field. None of the unresolved Story roots occurs in compressed or decompressed ASCII/UTF-16LE.

Bundle membership and dependency co-location are resource-loader relations, not authored Story ownership or chronology. Future builds, runtime/server selection, and consumers outside this hash-gated manifest reader remain separate evidence surfaces.
