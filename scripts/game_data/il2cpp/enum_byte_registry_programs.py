"""Byte registration's actual closed reference-registry setter source."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

LABEL='enumByteRegistryPrograms'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def setter_program(regions,entry,*,cold_insertion=False):
    need('literal-insertion-context-case',type(cold_insertion)is bool)
    g=BytesPath(regions,entry)
    g.take('48895c2418','55','57','4156','4883ec40','48c744246800000000',
        '498be9','4d8bf0','488bda','488bf9','4885d2');g.branch('0f84',False)
    g.take('4889742460','488b7118','4885f6');g.branch('0f84',False)
    g.take('498b4920','ba0c000000','488b89c0000000');resolver=g.relative('e8')
    g.take('488bd0','b901000000','4c8bcb','4c8bc6');hashing=g.relative('e8')
    g.take('488b4d20','8bf0','488b91c0000000','488b4a78','4883792000');g.branch('0f84',cold_insertion)
    if cold_insertion:
        g.take('488b4d20','488b91c0000000','488b4a78','ff11','90');g.jump('e9')
    g.take('488b4d20','4d8bce','448bc6','488b91c0000000','488bcf','488b4278','488bd3',
        '4889442438','488d442468','4889442430','c644242801','c644242001')
    insertion=g.relative('e8')
    g.take('488b742460','488b5c2470','4883c440','415e','5f','5d','c3')
    return dict(selectedBytes=g.seen,entry=entry,coldInsertion=cold_insertion,
        incomingArguments=dict(rcx='actual reference registry dictionary',rdx='actual nominal System.Type key',
            r8='unchanged actual formatter reference',r9='actual closed set_Item MethodInfo'),
        actualClassContextSlotResolver=resolver,actualHashHelper=hashing,actualInsertion=insertion,
        dictionaryTablesFieldOffset=24,dictionaryHashContextSlot=12,dictionaryInsertionContextSlot=15,
        insertionArguments=dict(rcx='same actual registry dictionary',rdx='same nominal System.Type key',
            r8d='actual hash result',r9='same original formatter reference',stack32=True,stack40=True,
            stack48='address of owned zeroed output reference',stack56='actual own context slot15 MethodInfo'),
        sameIncomingKeyAndFormatterPreserved=True,normalInsertionReturnRequired=True,
        entryRspRestored=True,nonvolatilesRestored=['rbx','rbp','rdi','rsi','r14'],normalReturn=True,
        registryPublicationOrLookupProved=False)
