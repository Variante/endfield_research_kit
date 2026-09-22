"""Loaders for the reviewed native contracts that Story, Mission Pipeline and Map consume.

The contract JSON itself lives in ``scripts/game_data/contracts``; each module
here pins one file's digest, gates on the installed native inputs, and hands
its rows to the builders.
"""
