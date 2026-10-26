"""Keep complete bounded generated-owner refusals in Story diagnostics."""
import json


class GeneratedSourceRefusal(ValueError):
 def __init__(self,validator,type_name,row):
  self.diagnostic=dict(validator=validator,check='complete-generated-reader-source',typeName=type_name,
   wrapperName=row.get('wrapperName'),expected='complete-reader-source-proved',actual=row.get('status'),
   sourcePath='scripts/game_data/memorypack/generated_reader_sources.py',reason=row.get('reason','missing-generated-owner-reason'))
  super().__init__(json.dumps(self.diagnostic,ensure_ascii=False,separators=(',',':')))


def require_complete(row,*,validator,type_name):
 if row.get('status')!='complete-reader-source-proved':raise GeneratedSourceRefusal(validator,type_name,row)
 return row['proof']
