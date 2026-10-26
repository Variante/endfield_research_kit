"""Project freshly authenticated NPC declarations into one bounded read plan."""


def layout(root,records,profile):
    primitive=dict(string='pool',bool='bool',int='i32',long='i64',ulong='u64',float='f32')
    def value(member):
        name,kind=member['declaredType'],member['kind'];plan=dict(name=member['name'],type=name)
        if name in primitive:plan['wire']=primitive[name]
        elif kind=='enum':plan['wire']='i32'
        elif name in profile['inlineInt32Types']:plan['wire']='i32'
        elif name=='UnityEngine.Vector3':plan['wire']='vector3'
        elif name==profile['aiDictionaryType']:plan['wire']='ai-dictionary'
        elif name in records:plan.update(wire='record',nullable=name in profile['nullableRecords'])
        elif name in profile['collections']:
            selected=profile['collections'][name];plan.update(wire='items',countLimit=selected['countLimit'],element=selected['element'])
        elif name in profile['nullOnlyTypes']:plan['wire']='null'
        else:raise ValueError('npcLayout.unproved-type:'+member['name']+':'+name)
        return plan
    plans={name:[value(m)for m in members]for name,members in records.items()}
    fields=[]
    for member in root:
        row=value(member);row['group']=profile['groups'][member['declaringWrapper']];fields.append(row)
    return dict(memberCount=len(fields),root=fields,records=plans,tagType=profile['tagType'],aiType=profile['aiType'],aiDictionaryCounts=[0,1],memberPartition=[14,79,28],stringEncoding='int32-pool-index')
