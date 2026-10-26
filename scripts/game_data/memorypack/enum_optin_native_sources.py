"""Explicit nominal enum domains outside the default Skill list declaration.

The domain contract declares only exact nominals and a bounded collection
scope. The existing reviewed callback profile supplies the helper anchors;
neither declaration is a saved proof. Every selected callback, original nominal
context, formatter registration and list body is freshly derived. The default
Skill enum set and its proof remain unchanged. Int32-backed source selection
is deliberately separate from byte-backed enums.
"""
import copy
import json

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp import enum_nominal_callback_sources as callbacks
from scripts.game_data.memorypack import enum_list_native_sources as lists

SCHEMA='endfield.enum-optin-sources.v1'
PROFILE_SCHEMA='endfield.enum-optin-domains.v1'
CONTRACT_PATH=CONTRACTS_DIR/'enum_optin_domains_native.json'
LABEL='enumOptinSources'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def domain_profile(declaration,pins,domain,*,reviewed=True):
    need('profile-schema',declaration.get('schema')==PROFILE_SCHEMA)
    need('profile-review-state',declaration.get('status')in(('reviewed',)if reviewed else('reviewed','pendingReview')))
    need('same-selected-native-inputs',declaration.get('nativeInputs')==pins)
    domains=declaration.get('domains')
    need('finite-domain-declarations',type(domains)is dict and 0<len(domains)<=32
        and all(type(k)is str and k for k in domains))
    need('explicit-selected-domain',type(domain)is str and domain in domains)
    selected=domains[domain]
    need('exact-domain-shape',type(selected)is dict
        and set(selected)=={'nominalEnums','collectionEnums','countLimit'})
    names=selected['nominalEnums'];collections=selected['collectionEnums']
    need('finite-unique-nominals',type(names)is list and 0<len(names)<=32
        and all(type(n)is str and n for n in names)and names==sorted(set(names)))
    need('explicit-collection-subset',type(collections)is list and collections==sorted(set(collections))
        and all(type(n)is str and n in names for n in collections))
    need('finite-count-limit',type(selected['countLimit'])is int and 0<selected['countLimit']<=10000)
    need('explicit-evidence-boundary',type(declaration.get('evidenceBoundary'))is dict
        and set(declaration['evidenceBoundary'])=={'exact','conditional','structuralOnly','unresolved'})
    return selected


def _derive_on_domain(image,pins,*,declaration,profile,domain):
    """A candidate declaration is re-proved; it never bypasses source gates."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    _publication_gate(image,pins)
    selected=domain_profile(declaration,pins,domain,reviewed=False)
    callbacks.validate_profile(profile,pins)
    own_profile=copy.deepcopy(profile);own_profile['nominalEnums']=selected['nominalEnums'][:]
    callback_source=callbacks._derive_on_profile(image,pins,own_profile)
    need('exact-fresh-callback-scope',set(callback_source['capabilities'])==set(selected['nominalEnums']))
    listing=None;caps={'skill-enum-callback:'+name:cap for name,cap in callback_source['capabilities'].items()}
    if selected['collectionEnums']:
        listing=lists._derive_with_callbacks(image,pins,callback_source,
            enum_types=tuple(selected['collectionEnums']),count_limit=selected['countLimit'])
        for key,cap in listing['capabilities'].items():
            need('equal-overlapping-callback',key not in caps or caps[key]==cap)
            caps[key]=cap
    _publication_gate(image,pins)
    return dict(schema=SCHEMA,status='validated-conditional-optin-enum-domain',nativeInputs=pins,
        domain=domain,domainDeclaration=copy.deepcopy(selected),capabilities=caps,
        proof=dict(callbackSources=callback_source,listSources=listing),
        defaultSkillDomainChanged=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=copy.deepcopy(declaration['evidenceBoundary']))


def _load(path,label):
    try:return json.loads(path.read_bytes())
    except OSError as error:raise ValueError(LABEL+'.'+label+'-missing')from error


def derive(image,pins,*,domain):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    _publication_gate(image,pins)
    declaration=_load(CONTRACT_PATH,'reviewed-domain-profile')
    domain_profile(declaration,pins,domain)
    profile=_load(callbacks.CONTRACT_PATH,'reviewed-callback-profile')
    return _derive_on_domain(image,pins,declaration=declaration,profile=profile,domain=domain)


def bind_request(image,pins,source,*,typed_request,call_target,enum_type):
    """Bind the actual collection request; enclosing transfers remain unproved."""
    need('same-fresh-domain-source',source.get('schema')==SCHEMA
        and source.get('status')=='validated-conditional-optin-enum-domain'
        and source.get('nativeInputs')==pins and source.get('defaultSkillDomainChanged')is False
        and source.get('parentFieldAdmitted')is False and source.get('wholeOwnerAdmitted')is False)
    domain=source.get('domainDeclaration',{})
    need('explicit-actual-collection-nominal',enum_type in domain.get('collectionEnums',[]))
    listing=source.get('proof',{}).get('listSources')
    need('exact-selected-list-capabilities',type(listing)is dict and all(
        source.get('capabilities',{}).get(key)==cap for key,cap in listing.get('capabilities',{}).items()))
    return lists._bind_request(image,pins,listing,typed_request=typed_request,call_target=call_target,
        enum_type=enum_type,enum_types=tuple(domain['collectionEnums']),count_limit=domain['countLimit'])
