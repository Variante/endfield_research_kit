"""Private missing-route bridge for one authenticated Story operation.

No constructor or decoder accepts retained native proof. The operation's pool,
source epoch and selected native inputs own every lazily derived route.
"""
import json

from scripts.game_data.codecs.levelscript import current_generated_action_route as codec


def _need(check, condition):
    if not condition:
        raise ValueError('currentActionMapRoute.'+check)


def _owned_audit(current_owner, audit, family, tag):
    _need('same-operation-native-source', isinstance(audit, dict) and audit.get('status') == 'validated'
          and audit.get('schema') == 'endfield.generated-actionmap-route-components.v1'
          and audit.get('nativeInputs') == current_owner.proof.get('nativeInputs')
          and audit.get('nativeSources') == current_owner.proof.get('nativeSources')
          and (audit.get('family'), audit.get('tag')) == (family, tag)
          and audit.get('wholeOwnerAdmitted') is False)
    cap = codec.validate(audit.get('capability'))
    _need('same-current-native-route', (cap['family'], cap['tag']) == (family, tag)
          and audit.get('wrapperName') == cap['wrapperName'])
    return cap


def decode(data, offset, *, family, tag, field, current_owner, strings):
    from scripts.game_data.memorypack.levelscript_current_source import require_framing_owner
    from scripts.game_data.memorypack.operation_native_validation import validate_native
    from scripts.game_data import levelscript_action_routes_native as native
    require_framing_owner(current_owner, strings=strings)
    _need('explicit-operation-native-root', current_owner.game_root is not None)
    # The lexical validator cache owns successful reuse. Mutable attributes on
    # an operation cannot introduce a saved audit or survive its source epoch.
    audit = validate_native(native.validate, family=family, tag=tag, game_root=current_owner.game_root)
    if not isinstance(audit, dict) or audit.get('status') != 'validated':
        detail = {k: audit[k] for k in ('status', 'detail', 'reason', 'pending', 'diagnostic') if k in audit} if isinstance(audit, dict) else type(audit).__name__
        raise ValueError('currentActionMapRoute.fresh-source-required:'+json.dumps(detail, sort_keys=True)[:2400])
    cap = _owned_audit(current_owner, audit, family, tag)
    return codec.decode(data, offset, field=field, capability=cap, strings=strings)
