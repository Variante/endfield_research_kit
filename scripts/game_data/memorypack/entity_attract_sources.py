"""Current owning EntityAttract setters; native identity is checked by the caller."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

def setter(regions,entry,*,field,kind,instance,null_throw,barrier):
 if type(field)is not int or not 16<=field<128 or type(instance)is not int or not 16<=instance<128 or kind not in('reference','dword','qword'):raise ValueError('entityAttract.setter-profile')
 g=BytesPath(regions,entry);g.take('4883ec28')
 if kind=='reference':
  g.take('488b49'+bytes((instance,)).hex(),'4885c9');target=g.relative('74',1);g.take('488951'+bytes((field,)).hex(),'4883c1'+bytes((field,)).hex(),'4883c428')
  if g.relative('e9')!=barrier:raise ValueError('entityAttract.setter-barrier')
  cold=BytesPath(regions,target);cold.call(null_throw);cold.take('cc')
 else:
  g.take('488b41'+bytes((instance,)).hex(),'4885c0');store=g.relative('75',1);cold=BytesPath(regions,g.at);cold.call(null_throw);cold.take('cc')
  if cold.at!=store:raise ValueError('entityAttract.setter-null-join')
  g.at=store;g.take(('8950'if kind=='dword'else'488950')+bytes((field,)).hex(),'4883c428','c3')
 return dict(selectedBytes=g.seen,nullFailureBytes=cold.seen,ownedInstanceSlot=instance,fieldOffset=field,storedBits=32 if kind=='dword'else 64,normalReturn=True,condition='Nonnull coherent generated wrapper instance; reference barrier has ordinary normal return effects.')
