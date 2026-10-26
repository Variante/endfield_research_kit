"""Validate explicit synchronous call pairs; never infer nesting from proximity."""
from __future__ import annotations
import re

PAIRED_ABI = re.compile(r'win64\.(?:(?:scoped_)?paired_gp_|paired_double_slot2_(?=void_4\.v1\Z))(void|bool|float|double|int|pointer)_([1-5])\.v1\Z')


class InvocationError(ValueError):
    pass


class Invocations:
    def __init__(self):
        self.stacks = {}
        self.seen = set()
        self.completed = self.abandoned = self.maximum_depth = 0

    def observe(self, row, hook):
        def need(condition, message):
            if not condition:
                raise InvocationError('mission_trace.invocation: '+message)
        def unsigned(name):
            value = row.get(name)
            need(type(value) is int and 0 <= value < 2**64, 'invalid '+name)
            return value
        identity, parent, depth = (unsigned(k) for k in ('invocationId', 'parentInvocationId', 'depth'))
        stack = self.stacks.setdefault(row['threadId'], [])
        phase = row.get('phase')
        abi = PAIRED_ABI.fullmatch(hook['abiId'])
        if hook.get('captureScope') == 'paired-ancestor':
            need(bool(abi) and bool(stack),'scoped observer lacks recorded paired ancestor')
        need(phase in ('enter', 'return', 'unwind') if abi else phase == 'entry', 'ABI/phase mismatch')
        result = row.get('returnValue')
        if phase in ('entry', 'enter'):
            need(depth == len(stack) and parent == (stack[-1]['invocationId'] if stack else 0), 'parent/depth mismatch')
            need(result is None, 'entry has return value')
            if phase == 'entry':
                need(identity == 0, 'entry-only hook has invocation ID')
            else:
                need(0 < identity and identity not in self.seen and depth < 64, 'duplicate ID or depth overflow')
                self.seen.add(identity)
                stack.append({k: row[k] for k in ('invocationId','parentInvocationId','depth','hookIndex','args','returnAddress','qpc','sequence')})
                self.maximum_depth = max(self.maximum_depth, len(stack))
        else:
            need(bool(stack) and identity == stack[-1]['invocationId'], 'unmatched or crossing return')
            entered = stack.pop()
            need(all(row[k] == entered[k] for k in ('parentInvocationId','depth','hookIndex','args','returnAddress')),
                 'return entry identity/arguments differ')
            need(row['qpc'] >= entered['qpc'] and row['sequence'] > entered['sequence'], 'return precedes entry')
            if phase == 'unwind':
                need(result is None and row.get('fields') == [], 'unwind must not read freed fields or return values')
                self.abandoned += 1
            else:
                valid = (result is None if abi[1] == 'void' else
                         type(result) is int and result in (0, 1) if abi[1] == 'bool' else
                         type(result) is int and 0 <= result < 2**(32 if abi[1] in {'float','int'} else 64))
                need(valid,
                     'invalid typed return value')
                self.completed += 1
            return {'entrySequence': entered['sequence'], 'entryQpc': entered['qpc'],
                    'durationQpc': row['qpc']-entered['qpc'], 'returnedNormally': phase == 'return'}
        return None

    def finish(self, complete):
        open_ids = [item['invocationId'] for stack in self.stacks.values() for item in stack]
        if complete and (open_ids or self.abandoned):
            raise InvocationError('mission_trace.invocation: complete receipt has unfinished or unwound calls')
        return {'entered': len(self.seen), 'completed': self.completed, 'unwound': self.abandoned,
                'openCount': len(open_ids), 'openIds': open_ids[:64], 'maximumDepth': self.maximum_depth,
                'boundary': 'Explicit same-thread observed synchronous enclosure only; no async ownership or total mission order.'}
