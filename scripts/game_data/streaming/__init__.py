"""The block-15 Streaming lane: framing, marker parsers, native validators and corpus gates.

``framing`` reads a Streaming file exactly; ``pairs`` binds Init/Streaming
witnesses; ``marker2``, ``marker13`` and ``marker17`` parse the bounded
marker payloads; the ``*_native`` modules authenticate their reviewed
contracts against the selected build; and the ``*_corpus`` gates sweep the
authenticated block-15 corpus and write the reports. Nothing outside this
lane imports it; its conclusions live in ``memory/game_data/world_chunk_*.md``.
"""
