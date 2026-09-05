"""Exact-build, read-only generic-instantiation audit; JSON is emitted to stdout.

No runtime MethodInfo or serialized source cursor is inferred. Native tables
are referenced PE extents, not a claim to consume the entire PE to EOF.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import struct
import sys
from pathlib import Path

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp_context import ContextError, GenericInstantiationTable, method_parameter_owner, type_image_owners, match_image_modules, method_spec_usage_index, generic_type_carrier, select_rgctx_range, unresolved_usage_index, rip_qword_load_target
from scripts.game_data.memorypack.skill_corpus import verify_current_report_inputs
from scripts.game_data.il2cpp_context import class_sharing_branch
from scripts.game_data.il2cpp_context import named_top_level_type
from scripts.game_data.il2cpp_context import object_type_comparison_key
from scripts.game_data.il2cpp_context import method_pointer_indices, generic_method_candidates
from scripts.game_data.il2cpp_context import type_parameter_owner, rgctx_range_entries
from scripts.game_data.il2cpp_context import method_spec_record, usage_method_spec, relative_branch_target, method_token_pointer
from scripts.game_data.il2cpp_context import literal_record

ROOT = Path(__file__).resolve().parents[2]
GA_SHA = 'C24495E51B406F03B03890C4788EE618AE022C991405BE5D5B8B787CB775AE89'
MD_SHA = '0076743397ACADF03D3B0064343A963C7C88863B8160526D397E4B3EFB96F02E'
CORPUS_SHA = '3B2B96545D1A17FFA4F7770B2BA7AF6045E4BDE701465AD42E2AFB0FA6D05943'
CONSUMER_WINDOWS = (
    (0x2DF4460, 0x2DF4684, 'AC887FDEF479D755A8389CCF34DE243A1C762D32ABD70CE699DC2297985D01D9'),
    (0x4C5DC40, 0x4C5DD38, '594A25EE92B3F5F9C4BAE27D83336887CDA9124D0779F6EB9DF94044B91AFBF6'),
    (0x2D8DE0, 0x2D8EAC, '88A126F8A51C4D39BE8C73B8E5594A436A41066417A841C66EEA5DB04D8CC67A'),
    (0x2DF2AA0, 0x2DF3271, 'AF49BFE87E68E091E58848935F5BEA3CC32DC280704D2235CD48D6DFCA3B753C'),
    (0x2D72FA0, 0x2D731F5, '445859C5F6E56B6F1C0987ABEABED40E5AF217F7FE42353A95DA117D4FB2B2E2'),
    (0x2D7F770, 0x2D7F914, 'DAE488218AC934D0C9CF68F33BAAB9B1659D3F57DA158D7A0834A6B1F7BE810B'),
    (0x2D7AE60, 0x2D7AF28, 'CF2651FC76E186FE5D6DF8E34163A75EC3A3F37ED40560B3F2324E60059A41A2'),
    (0x2D7F920, 0x2D7FE68, 'D6A7ABB1AE1DCCFA30BA942968FC9E89671FB36578BAABDB0E347753D565E6E0'),
    (0x2D7DBF0, 0x2D7E3BC, 'BD887872DEB0E1D5939A3ECDB53DB9059E0AF27AE072B1A8F72311EE8800C150'),
    (0x2D7E480, 0x2D7E6C8, 'C5A0B6BAA857B336A99B7BEF8A5B59D62CD8776A651F11C718A40122493385E8'),
    (0x2FCA460, 0x2FCA768, 'A8F70CDC62487F47713F7540310DF6F3D6F388D0B9289C13C4B98ABFF3D82CD7'),
    (0x3AFCB00, 0x3AFCC8E, '1AE31F3A846C775B877BC41FC7D0DFDE947C52AA726F5EF559C4E7B5FF7DD885'),
    (0x318BC00, 0x318BD14, '8AD4D7E061F64FA7627B5A55141CE2094E3D75116A467637D3C36F43A19C28D9'),
    (0x318BD20, 0x318BE14, '034D24CE15719BC3DE0F4759195E066B7F6BE1F90820C4E72FBA87C905BAEECE'),
    (0x318BFA0, 0x318C0B6, 'B8AFE09CFE1B3D58237F4DAA075BE3EA90281DCA9B6C80EE8AF9DEFD7E5DBDEF'),
    (0x318C0C0, 0x318C214, '96DA74FCCB3AEA554D97FD30502F8233D88BC5D0BDEC1844FD92C55A42CD4C19'),
    (0x318C220, 0x318C489, 'AA82FB39E35A4D9F1ACCEDFBE1B902C534879F8ABA6685204C78C5CA068FCFDD'),
    (0x318B640, 0x318BA9C, '4C0DC2B5628149EC93FDAB7D280B3AE0B05E373E6C124F8E1B737E722D5BBAE3'),
    (0x507D3C4, 0x507D3E8, '8859615A9572203BEB3922A248068B3C790543DFEEA14930BC3C1B815875C3D2'),
    (0x2C97EF0, 0x2C97FF9, '50637A88FDE993EC5A257E43D3CCB904A397EEB21FB97CA9747CDFF3CEF50EAB'),
    (0x33AF150, 0x33AF45D, '3EF2B07F92BEFA88B2176CC85AED55F46631C40221C8855C39147B80B2E80819'),
    (0x2D76170, 0x2D763EF, '1C22EC661AEB8FF271F3F6DCC867025A0045808F7EA9BD7EC1BD5CFCA4F1490E'),
    (0x449AEB0, 0x449AF12, 'A29D6DE8B297DB1A9EDC50AFF7B73DC946FBA6F02BD7BA15341F07B1BB91EC73'),
    (0x4D86E0C, 0x4D86ED8, '247C2A7B2E2B9926079FAEDAE02FC2056595D51924EDA7424CA7796814452BBE'),
    (0x2D76D10, 0x2D780D7, 'DA75F628478837F4C1B6C6E142B9218243F17775265D233F0276CE8B83043437'),
    (0x2D78240, 0x2D783B6, 'C72E36C1E1A1643708DBAD591A96C705E39A0BB8DE55BB6C7E678486C52FD015'),
    (0x2D755E0, 0x2D7590C, '56D2ECAC18B1C514E38AC00F3ED5920E04E53A389C168758F1B0DDE0A6A1CCA2'),
    (0x4C48A42, 0x4C48A77, 'FB76990B4CFD1E0485A0D5EC5B413D1E7E5378D3B1E422B18217FBBBE6117581'),
    (0x2D75510, 0x2D755DF, '8AB413FBC0531BFFEC188D2D97F92212E74BA7E8E811F2CBBA49A54831645B00'),
    (0x2D751D0, 0x2D753A1, '1E0BB4C935C862C3FDB667BA3DE791A5B3F7D310BD14D8EE775541D1D8FD1CEB'),
    (0x2D7A040, 0x2D7A43B, 'D960CF4CBD48D4E3D111DA83A56D3564157F0164A64CA93D1465962C6A30A535'),
    (0x2D7A640, 0x2D7ACA8, '5CFC59429A62052363B2F6B44F9B1AF16484C431FE9803067328438C3C8845CC'),
    (0x2D7ACD0, 0x2D7AE5B, 'F28DFB721F739050378D152E8B86757C6A9F03C837D96912387C693056056D22'),
    (0x5BBB52C, 0x5BBB6A8, '63A3C18739E138374BF02B556FA7C526777DC2CA7DB2BD10E6AE67C2207C0B06'),
    (0x51D80, 0x51DDC, 'B2CF8E434864F9AE7C9883709C4E0267E7BA2AEFF4C32BBF71DB249F6A47FC54'),
    (0x508E0, 0x50926, '2071A23E23E45FBCA162759BF197902A6D6B9C5587F6F71FADE172F2CBA92618'),
    (0x2D7A4C0, 0x2D7A633, '65CD048E5A09DE0A04F21C01679BC1B31D085665530236F5CAF2FA0F7520387B'),
    (0x2D076C0, 0x2D07B84, '84F4B8575E52FD2AAE54A6A05BCFABC141B8497D9C6AD37F17B7DA794E70420D'),
    (0x2D06B70, 0x2D06D61, '996028190AEED096CCF29CDDAB8526D6E6D2D875B485632E36E7BF59228577CB'),
    (0x4A490D0, 0x4A49131, '1169F77B12C05437AE9F62438BCC597F5C6E07B242C64FADD4176E2818A69850'),
    (0x3DBBDC0, 0x3DBBE37, '1657ED5BBC390F4DFE0289B223AD316D6704BFC5AF7773F8CCB34E3F6645D48D'),
    (0x4C36012, 0x4C36118, 'A30083FD47A8AAD5C85B522ED3005C611E3D33C55D1FC9769754B01CF82276DA'),
    (0x2D36380, 0x2D36994, '85D41B9FE1654F6F92A646B7A964873F1F7FE0CD00D141C4F83008F8829E5030'),
    (0x3AF70, 0x3AFBF, '72BD36DFB1B0E26BACC5934A9DD0C0CE1F0DBC3B7D651C979A4D519F0898C5B3'),
    (0x3B188A0, 0x3B189ED, 'BBF441134BEE6360DE2E40A3EF134DB920D8DE9FED8231EEBF0602101B5E389D'),
    (0x3B677B0, 0x3B67D18, '57AD13123C926CC835193BAE0A9636F201B74EDF5D23F87121E7DA2D332555DB'),
    (0x970BFBC, 0x970BFF0, 'AB34067513E25C40E3C0BE6EAF9A085B4C48438CDB435512C1B2BF2AE24A34F3'),
    (0x9711078, 0x9711A57, 'CEA35CF8D73D0B319BD52DE7BA66202EB93CA5559EF0083F14EF01ED1D2D9963'),
    (0x970AD30, 0x970AE65, 'B1587FA587E6E160B00DEF0116FD0B7C1BEC5D7670AD8CA059E22489904F20EA'),
    (0x3B67E30, 0x3B67EC4, 'E20940F2F7B39A3BB1806DA04749C66E3B2CF514FF8CA0658B5F690C18EB0279'),
    (0x970C4A8, 0x970C672, 'EEFD3592C95C7366380F47A0890632F54ED8EC2B521D81014852BA045BFC610C'),
    (0x970BFF0, 0x970C1F5, 'AE39953E1E6D1C4C8531CE5206EA5DCE70CD82DBB8093111E669103CC2B80A7F'),
    (0x970915C, 0x9709454, 'AB0D5C7A12E463100AF920A8CB6A52001B52B15A51AB7EC11C1D006D04EC7363'),
    (0x5AD2140, 0x5AD227B, 'DF6D3A33414236CA22AD342A51DA9DF5B759B250EFB98B40BBD8816E6992C5E5'),
    (0x838223C, 0x8382292, '44086E7E4E68ABB7828C536B227D14046E427D6EA13E39C4396A66E0854F090D'),
    (0x837EC68, 0x837ED6A, '1FCA33902F53C293A266896CEDA59F4DE806A98E5B8FDF0A2F6FB10CA4ACD65D'),
    (0x8381FF0, 0x8382066, '7CD14312228390425009C7437524BCCAF7E52B39A40AB030D62AA197819998CF'),
    (0x83761A0, 0x837633C, '0178C8AB8E92ACFCBC58B294EC2800840F2EF46C86927FBFB5AB969AC9724DF9'),
    (0x8375FBC, 0x83761A0, 'EFA324973C53A29ED5926C04777AA94EF9E39DBB0CE12218B26E18E9BB97C41C'),
    (0x381F8F0, 0x381FDF6, '5917DCD09ACBA635492A0F3A751C3940EDEA02D5E0F38B977F3DADEFDC672279'),
    (0x37DF620, 0x37DF67D, '6901FC137F0D874FDFBDED47658B6B8BFA718E0BF2AE7EFD480EF8152DEEE72A'),
    (0x37DF680, 0x37DF77C, 'FBF5D3CF070494A3BE4FF265779AEEDE8B5CA95A2DE61EDFE215DB72640A1AA1'),
    (0x4E3B21E, 0x4E3B2B9, '4C1C33561E4C1011B637FF320D49C0DDF625396AEE89C8BB88414F9C97A048B5'),
    (0x8D20, 0x8F52, '48868BF56BEC2C84D6EEF44AE342E3CB5ABC1D54A62494733BE2703CA6A206B3'),
    (0x84B0, 0x8C74, 'A29F9BB8993244FF7D7571D39282EFA4A8B88736E71FAA18492B7AA4D90A706A'),
    (0xB010, 0xB995, '10231D49EEBCEAD16CF4142DF20F38407783C9D3DA55196125D305F23785D238'),
    (0x10000, 0x10019, 'AB93A915D9FB7495ADE419CB253425EEF1EED86E69495C824F19B157AD12C7F1'),
    (0xF4E0, 0xFF04, '0A71E5B9F7995F00CAF05B63F8FC5D3081CCD7614346A27057A329171072D89E'),
    (0x2DA8DA0, 0x2DA9898, 'C8A0697BE4093DAAA327F0D8202C33F900B6FB3857C270DFD6AD5F0E5386FFAF'),
    (0x2CC6B0, 0x2CC78C, '24344F6D00D7721765E78CF8141E2D1645B867A92FCBC657A54A7447C58303EC'),
    (0x2CC840, 0x2CC87C, '5E938881C79B911A1B1ACFE6BC3C4D3ABCC63D2552F05F0033FC67D0D49BEEF9'),
    (0x438F0, 0x43943, '33FF46D3B9C40354CAA46CC41E0F5174C2A87AAF69638F4A90B0E858F2DD56B1'),
    (0x9890, 0x9C67, '3764C631545FC23232AD4EBB109D0CC0415C1F5951531B840C207A4339749B34'),
    (0x13170, 0x134AF, '982687620B62840A318F9822B52C6F856D9FA5192337B1660007FD0306F52DD1'),
    (0x9C70, 0x9E6C, '0E56CE95E514F299C8F4D717C397811C7F1D16AC4E512C2955B23CCD05EA6F25'),
    (0x6A1E0, 0x6A39A, 'D9128C8BAB9B54797E0A0627E477F13A66063B5AB05932F0F9BB08475FE14E2B'),
    (0x2B2D70, 0x2B2E09, 'A9E38FAA7FB63E0C143C42798EB01AD09814F1639E04045E5EFDC776698B3080'),
    (0x69D60, 0x69D81, 'B585984BD43C174908671417D61F619A5BC3D0F083DF75AF691CF5EB218D4743'),
    (0x69D81, 0x69E9D, '8957659F01CF49BBFD5E7626A35F48B3E967880F6CEDF73B79C9AF5786E45276'),
    (0x69E9D, 0x69EAA, '05C4EF4266710A20641E22FDD6F964EE9C4A7ED76C4A98645B15F4D4780C4333'),
    (0x69EAA, 0x69F99, '98E219B3323AAF0B639E2B25E8AAB6AB135092CB0324F94C5F2F35299748ED86'),
    (0x4A560, 0x4A6A9, '5F21000E0A7DC7AD2B6AE4B29D79964839FEBBBD524762D6F8E4C0EA67618FE9'),
    (0x1C850, 0x1CCD6, 'E05B2B74811C4CCCCA4C95A3FACDFE804C037BB56FBBA41EB28EC1545265F70F'),
    (0x3CF20, 0x3D364, 'E1629CA701FE3C68029C4FA2207449CF615DC38E9EB43F4B3DFDA8319A41F48F'),
    (0x2C6C10, 0x2C6E20, 'D0C37020DB6E3FA5F5D8429326495F7C63157F0A731EE3DC070E1CB3F8BC05B4'),
    (0x2C7550, 0x2C75D3, 'CE47EA89E1466DA991434EB620A2DCFDF25D50F80A8D2A7A67CE87E70D73B13A'),
    (0x2DA4770, 0x2DA4842, 'E485B80DE7EB384A0656711FE57395E813FA3DA7981EED3171080ACCC0D40507'),
    (0x2DA4842, 0x2DA4CB6, 'B62863C4ECF8EED5095302277B77F5AF56FB6EEFD6BF69E53A249B99132231F7'),
    (0x2A5B3B0, 0x2B25E5F, 'FF4949FACDD976369EA9D9008FC74EAD1A384AA4F0A699585810DC65AEFB0B7B'),
    (0x38003F0, 0x380047D, 'A31994FE88EFC8CBC3666CEBCB71FDD8CA317233F38D1EF5727110E6879631B5'),
    (0xA790, 0xAE47, 'F9E448ECD6162E73ED4282F551F1F19A763854F6D99031A45EA61612AF292A09'),
    (0x9230, 0x962A, 'B11CC37279D6BD65872B4E6CC22339543A84B005FE4B65F424081417C0C57214'),
    (0x3850, 0x3995, '4C5BF32B3BDC82C200BC2D88CFD0698694249C52C68BE5B71E87CC596F713C23'),
    (0x281B0, 0x28367, '4A5FE0579AFAF220617B572015648A598472D8F86A163A8EBE9E4F06282C02CB'),
    (0x64EA0, 0x64FB9, '5432E86CB6E16C4659B2FAC1EDAD6F805331B1638BFF96C6103192AF46543F9E'),
    (0x37DE060, 0x37DE0BB, '0926899BA44C601CEBAC2B4E70580B397CDDAB4FC60060C1E8DC0EF99A2555FB'),
    (0x37DE9C5, 0x37DEB23, 'C6A761532672A5700D9FEEB980F66BAF88B6F1F2CEAC48688680CF4158C1F285'),
    (0x37DE884, 0x37DE9C5, '853722D03CBFE915CFB92DD372A7C85BE072576C8FEB4CB35912E766BBDE9BCA'),
    (0x41260, 0x4138C, '910E29E41F01BE05DE60EF70F0D95CA521E103889A596DA577F10AF50840B2F2'),
    (0x4127B, 0x412D2, 'EC737048F208A7BF568C342D1630E506203A591F88E5497D2D93A9DD31B04D06'),
    (0x412D2, 0x412E0, '65F69D9450DCBB01DF08A592D62CFD560557C9B84E8662F49E421AEC07C15E91'),
    (0x2D8D10, 0x2D8D6A, '1D69558B9C9CBC2E7868E2A5895269966FB40E86B3E36B7B020BCC5C948ED5AC'),
    (0x2D8BF0, 0x2D8C12, '58AEECD1D6787DA519A37F3857FB40F3950BED75D3A9A0A6AEC81DEE32569AA4'),
    (0x2D8C12, 0x2D8C79, 'F1D27E8325CBBCF568E89D23C9280969ADAB6DEE2CEDE13E0FD1F1CBCB762470'),
    (0x2D8C79, 0x2D8C83, '087CD1A1ECF2C15B53BC8CA47F008DFACD7DB6E1579D1AD1C3A77D500224D68C'),
    (0x9630, 0x9850, 'F1F3F2471B2DDA9F3BC2E3505293D5658E04D9F25225CA8EF648EC4CC786388F'),
    (0x2C0E50, 0x2C0ED3, '16DD44242597B807F5729A2DD6AE5EF4BA7CB0B825BF9303F259407BB8A53A36'),
    (0x12BD0, 0x12C74, '90390C80AEFAF2A371E43E9491A557C87A6F168EFE73D8A7A089B7447C61EAAC'),
    (0x12CC0, 0x13169, 'BE122CAACEC77957916E5CC541FF0055ABFD9264303F7ACEB8BC48832933DCF3'),
    (0x2D7820, 0x2D7BBF, 'BFB975F36A64975240720253EB1391D00D2DFBD48317ED38291DAB6683EA00F0'),
    (0x9E70, 0xA500, '1B9824C30A36C141691EC195D8D3052B50A497722679DA9BAA2BC8194F68C19B'),
    (0x15C90, 0x16F71, 'EDCF30D6AEC6E2E98B7329DCA27C14DB36C754FADC8841648EDC02ADF5726023'),
)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest().upper()


def require(actual, expected, source, offset=0):
    if actual != expected:
        raise ContextError(str(source), offset, expected, actual)


def native_gate():
    gate = check_installed_native_inputs(GA_SHA, MD_SHA)
    require(gate.status, 'validated', 'selected native inputs: ' + gate.detail)
    return gate


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sweep(table):
    rows, failures = [], []
    for index in range(table.count):
        try:
            rows.append(table.resolve(index).as_dict())
        except ContextError as error:
            failures.append({'index': index, **error.diagnostics})
    return {'success': len(rows), 'failed': len(failures), 'unsupported': 0}, rows, failures


def validate_selected_method_spec(row, records, base, method_count, instantiation_count, *, source):
    """Verify emitted identity against raw records, independently of loop locals."""
    if not isinstance(row,dict) or len(records)%12:
        raise ContextError(source,base,'MethodSpec evidence object and exact record array',type(row).__name__)
    index=row.get('index')
    if type(index) is not int or not 0<=index<len(records)//12:
        raise ContextError(source,base,'bounded reported MethodSpec index',index)
    offset=base+index*12
    raw=records[index*12:(index+1)*12]
    definition,_,method_inst=method_spec_record(raw,method_count,instantiation_count,source=source,offset=offset)
    for key,expected in (('va',offset),('rawHex',raw.hex().upper()),('definition',definition)):
        if row.get(key)!=expected:
            raise ContextError(source,offset,f'reported {key} matches raw MethodSpec',
                               {'expected':expected,'actual':row.get(key)})
    inst=row.get('methodInstantiation')
    if not isinstance(inst,dict) or inst.get('index')!=method_inst:
        raise ContextError(source,offset+8,'reported method instantiation matches raw MethodSpec',
                           {'expected':method_inst,'actual':inst})


def serializer_return_consumers(pe, *, source):
    """Selected exact post-call windows, not exhaustive caller/EOF analysis."""
    edges=[]
    for rva,target in ((0x970BFE1,0x970C4A8),(0x97112AB,0x970C4A8),
                       (0x971179A,0x970C4A8),(0x97112BF,0x51D80)):
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+target,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'rawHex':raw.hex().upper(),'targetRva':target})
    windows=[]
    for rva,expected in ((0x970BFE6,'488B4424504883C448C3'),
                         (0x97112B0,'4C63C0B920000000448D49E1488BD7'),
                         (0x971179F,'488B742430488D8C24A0000000')):
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(expected)))
        require(raw,bytes.fromhex(expected),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    return {'edges':edges,'postCallWindows':windows,
            'level':'direct selected consumer dataflow',
            'objectReturnWrapper':{'rva':0x970BFBC,
                                   'boundary':'Copies entry RDX 16-byte input, supplies a zero-initialized output slot to the reader-owning entry, then overwrites RAX with that output slot and returns. The returned consumed count in EAX is discarded without comparison in this entire wrapper.'},
            'stateMachineCallsites':[
                {'rva':0x97112AB,'boundary':'Sign-extends returned consumed EAX into R8 and forwards it with ECX=0x20, R9D=1, RDX=the source object to another dispatcher. This is use of consumption, not an EOF comparison; the dispatched operation and source identity remain unresolved.'},
                {'rva':0x971179A,'boundary':'Loads the local output result into RSI and prepares cleanup, discarding returned consumed EAX. Buffer-fill counts and completion branches elsewhere in this owner do not themselves establish equality with this parser consumption.'}],
            'boundary':'No claim that these are all callers, that SkillData selects any of them, or that successful object return certifies EOF. Initial authenticated logical-file identity and the actual selected formatter remain missing.'}


def module_methods(pe, md, modules, image_owners, selections, *, source, expected_image='MemoryPack.dll'):
    """Join each selected definition through its own owner/image/token identity."""
    selected=[]
    pointer_tables={}
    for index,type_name,name,expected in selections:
        require(0<=index<len(md.methods),True,source,index)
        method=md.methods[index]
        require(0<=method.declaring_type<len(md.types),True,source,index)
        owner=md.types[method.declaring_type]
        require(md.type_full_name(owner),type_name,source,index)
        require(md.string(method.name_index),name,source,index)
        image_name=md.string(md.images[image_owners[method.declaring_type]].name_index)
        require(image_name,expected_image,source,index)
        module=modules[image_name]
        if module not in pointer_tables:
            count=pe.u32_at_va(module+8)
            require(count<=1_000_000,True,source,module+8)
            base=pe.u64_at_va(module+16)
            pointer_tables[module]=(base,pe.bytes_at_va(base,count*8))
        base,pointers=pointer_tables[module]
        row=method_token_pointer(method.token,pointers,source=source,offset=base)
        require(row['pointerVa'],0 if expected is None else pe.image_base+expected,source,row['slotVa'])
        selected.append(dict(row,methodIndex=index,declaringType=type_name,name=name,image=image_name,moduleVa=module))
    return selected


def reader_construction(pe, md, modules, image_owners, *, source):
    """Exact method-token identities plus independently reviewed native bodies."""
    selected=module_methods(pe,md,modules,image_owners,
        [(index,'MemoryPack.MemoryPackReader',name,rva) for index,name,rva in
         ((428422,'get_Consumed',0x4A46420),(428423,'get_Remaining',0x4A655D0),
          (428426,'.ctor',0x970AD30),(428427,'.ctor',0x3B67E30))],source=source)
    getters=[]
    for rva,hex_bytes in ((0x4A46420,'8B4144C3'),(0x4A655D0,'48635144488B4118482BC2C3')):
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(hex_bytes)))
        require(raw,bytes.fromhex(hex_bytes),source,rva)
        getters.append({'rva':rva,'rawHex':raw.hex().upper(),'rangeKind':'bounded explicit-return leaf; no pdata extent'})
    edges=[]
    for rva,target in ((0x970AE04,0x8381FF0),(0x970AE34,0x838223C),(0x970AE4C,0x3F779C0),
                       (0x970C5BB,0x3B67E30),(0x970C605,0x3F300),(0x970C0FD,0x970AD30)):
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+target,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'rawHex':raw.hex().upper(),'targetRva':target})
    return {'methods':selected,'getterLeaves':getters,'edges':edges,
            'level':'exact module/token identity; direct conditional native construction',
            'spanConstructor':{'rva':0x3B67E30,'inputWindowBytes':16,'stateWindowBytes':0x58,
                               'boundary':'RDX points to a 16-byte carrier copied to reader+0x20. Its signed dword+8 is stored at reader+0x30 and sign-extended into +0x18; +0x38 and both +0x40/+0x44 counters are cleared. Nonzero carrier length selects its pointer for +0x50; zero selects null. The first 24 state bytes come from static storage. Input validity and allocation bounds are not checked by this constructor.'},
            'sequenceConstructor':{'rva':0x970AD30,'inputWindowBytes':24,
                                   'boundary':'RDX points to a 24-byte endpoint descriptor. Equal endpoints use the static descriptor in reader+0; otherwise the input descriptor is copied. First-segment and length helpers still receive the original input, supplying +0x20/+0x30, total +0x18 and cursor +0x50. Both counters are cleared. Static descriptor contents and multi-segment ABI remain unresolved.'},
            'accessors':{'consumedOffset':0x44,'totalLengthOffset':0x18,
                         'boundary':'get_Consumed returns the dword at +0x44; get_Remaining returns qword+0x18 minus sign-extended dword+0x44. This independently names these state roles, not serialized field meanings.'},
            'caller':{'rva':0x970C4A8,'readerStackOffset':0x50,'returnedCounterStackOffset':0x94,
                      'boundary':'Copies the entry RDX 16-byte input, initializes a 0x58-byte stack reader, invokes the span constructor, dispatches with that reader, and returns its +0x44 counter after cleanup. The sequence caller similarly copies a constructed 0x58-byte state and returns +0x44. Neither reviewed owner compares that counter against original length. Caller selection for SkillData, initial file identity, and outer EOF enforcement remain unknown.'},
            'boundary':'A conditional source-length/consumed ABI exists, but no authenticated VFS allocation or observed SkillData invocation joins it. Do not prune terminal candidates.'}


def reader_cursor_consumers(pe, *, source):
    """Bound reviewed edges; caller authenticates complete selected native build."""
    edges=[]
    for rva,opcode,target in (
        (0x4E3B229,0xE8,0x970915C),(0x4E3B23C,0xE8,0x5AD2140),
        (0x5AD21C3,0xE8,0x838223C),(0x838228D,0xE9,0x83761A0),
        (0x5AD21F5,0xE8,0x837EC68),(0x5AD221C,0xE8,0x8381FF0),
        (0x8382045,0xE8,0x8375FBC),(0x5AD2236,0xE8,0x3F779C0),
        (0x9709289,0xE8,0x837EC68),(0x97092D8,0xE8,0x8381FF0),
        (0x9709421,0xE8,0x3F779C0),(0x381FAD4,0xE8,0x2DA4770),
        (0x381FB1D,0xE8,0x3F300)):
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        actual=relative_branch_target(raw,pe.image_base+rva,source=source)
        require(raw[0],opcode,source,rva)
        require(actual,pe.image_base+target,source,rva)
        edges.append({'instructionRva':rva,'instructionHex':raw.hex().upper(),'targetRva':target})
    # This leaf has no pdata row: certify only its two explicit return paths,
    # not a guessed function extent or the following aligned function.
    leaf=pe.bytes_at_va(pe.image_base+0x3F779C0,13)
    require(leaf,bytes.fromhex('837908007404488B01C333C0C3'),source,0x3F779C0)
    return {'edges':edges,'pointerLeaf':{'rva':0x3F779C0,'rawHex':leaf.hex().upper(),
                                       'rangeKind':'bounded instruction window; no pdata extent'},
            'level':'direct conditional native reader state transitions',
            'advance':{'rva':0x5AD2140,'normalReturn':True,'localCounterResetOffset':0x40,
                       'accumulatedCounterOffset':0x44,'cursorReplacementOffset':0x50,
                       'boundary':'The only normal return sets AL=1, resets +0x40, adds the signed-extended request via a 32-bit addition at +0x44, and replaces +0x30/+0x50 from helper outputs. Caller false-return fallback is not a second normal path in this pinned body. Helpers may throw; counter overflow and runtime descriptor validity are not certified.'},
            'ensure':{'rva':0x970915C,'sourceDescriptorPrefixBytes':24,
                      'boundary':'Uses +0x18 minus signed-extended +0x44 as a requested-length guard, resets +0x40 after a delegated 24-byte descriptor transformation, and selects an existing or copied segment before replacing +0x30/+0x50. The cursor can change allocations; a pointer delta is not an absolute source offset. The descriptor transform/copy/type-context helpers are not fully closed.'},
            'descriptorLength':{'rva':0x83761A0,'prefixBytes':24,
                                'boundary':'For equal endpoint objects at +0/+8, masks bit 31 from the +0x10/+0x14 words and returns end minus start. Unequal endpoints use type-context conversions and object +0x28 values; their ABI remains conditional, not a certified source length.'},
            'nestedRead':{'rva':0x381F8F0,'readerRegister':'R15',
                          'boundary':'Entry RCX is saved in R15 and passed to dispatch as R8; the local output is returned after formatter dispatch. This body is another provider/dispatch layer, not the list count or element consumer. Its cold cache paths, live MethodInfo and selected list formatter are unresolved.'},
            'boundary':'No authenticated logical-file allocation, initial descriptor, complete helper ABI, final cursor or EOF join. Keep both terminal candidates.'}


def wrapper_consumer(pe, md, reg, table, *, source):
    """Reviewed conditional wrapper path, not a source/EOF or dispatch receipt."""
    instruction=pe.bytes_at_va(pe.image_base+0x37DF6EC,7)
    require(instruction[:3],bytes.fromhex('488B15'),source,0x37DF6EC)
    cell=rip_qword_load_target(instruction,pe.image_base+0x37DF6EC,source=source)
    initializer=pe.bytes_at_va(pe.image_base+0x37DF752,7)
    require(initializer[:3],bytes.fromhex('488D0D'),source,0x37DF752)
    require(pe.image_base+0x37DF759+struct.unpack_from('<i',initializer,3)[0],cell,source,0x37DF752)
    records_base=int(reg['methodSpecs'],16)
    spec=usage_method_spec(pe.bytes_at_va(cell,8),pe.bytes_at_va(records_base,reg['methodSpecsCount']*12),
                          len(md.methods),reg['genericInstsCount'],source=source,
                          usage_offset=cell,records_offset=records_base)
    require((spec['index'],spec['definition'],spec['classInstantiationIndex'],spec['methodInstantiationIndex']),
            (610730,428462,-1,8486),source,spec['va'])
    inst=table.resolve(spec['methodInstantiationIndex'])
    require(len(inst.arguments),1,source,inst.record_va)
    arg=inst.arguments[0]
    raw=bytes.fromhex(arg.raw_type_record_hex)
    carrier_raw=pe.bytes_at_va(struct.unpack_from('<Q',raw)[0],32)
    base_raw=pe.bytes_at_va(struct.unpack_from('<Q',carrier_raw)[0],16)
    carrier=generic_type_carrier(raw,carrier_raw,base_raw,type_pointer=arg.type_pointer_va,
                                 type_count=len(md.types),source=source)
    require(carrier['baseDefinitionIndex'],37521,source)
    require(md.type_full_name(md.types[37521]),'System.Collections.Generic.List`1',source)
    element_inst=table.resolve_pointer(carrier['classInstantiationPointerVa'])
    require(element_inst.index,816,source,element_inst.record_va)
    require(len(element_inst.arguments),1,source,element_inst.record_va)
    require(element_inst.arguments[0].raw_type_record_hex,'A22D0000000000000000118000000000',source)
    call=pe.bytes_at_va(pe.image_base+0x37DF6F9,5)
    require(call[0],0xE8,source,0x37DF6F9)
    require(pe.image_base+0x37DF6FE+struct.unpack_from('<i',call,1)[0],pe.image_base+0x381F8F0,source,0x37DF6F9)
    return {'methodSpec':spec,'methodInstantiation':inst.as_dict(),
            'listCarrier':carrier,'elementInstantiation':element_inst.as_dict(),
            'formatterEntryRva':0x37DF620,'readerEntryRva':0x37DF680,'nestedCallRva':0x37DF6F9,
            'level':'direct conditional consumer; exact static usage/type relation',
            'boundary':'The formatter forwards its reader unchanged to the wrapper reader. The fast path consumes one byte using remaining+0x30, cursor+0x50 and counters+0x40/+0x44. Header 0xFF clears the output; non-null header 1 reaches the nested call with the same reader and the recorded List instantiation. Other headers reach a helper then INT3. Cold ensure/advance transitions are described separately in selectedReaderCursorConsumers; their descriptor helpers are not fully closed. No list element layout, actual provider selection, authenticated source allocation, source extent or final cursor is established.'}


def resource_carrier_consumers(pe, *, source):
    """Reviewed native carrier/state path, separate from actual resource selection."""
    edges=[]
    for rva,target in ((0x3B18966,0x3B677B0),(0x3B67C9C,0x2DA4260),
                       (0x3B67CBB,0x3F300),(0x3B67CD3,0x1F0450)):
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+target,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'targetRva':target,'rawHex':raw.hex().upper()})
    windows=[]
    for rva,hex_bytes in (
        (0x3B188B5,'483972387508488BCAE8CD6653FC'),
        (0x3B1896B,'488B9C249800000048899C24A0000000'),
        (0x3B67CA6,'B9050000004C8B8C24080100004C8D442440488BD0'),
        (0x3B67CC0,'8B9C2484000000899C2410010000488D4C2430'),
        (0x3B67CEB,'8BC34881C4C0000000415F415E415D415C5F5E5BC3')):
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(hex_bytes)))
        require(raw,bytes.fromhex(hex_bytes),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    switch=pe.bytes_at_va(pe.image_base+0x3B67D18,28)
    require(switch,struct.pack('<7I',0x3B67A26,0x3B67A35,0x3B67A44,0x3B67AA7,
                               0x3B67AB6,0x3B67A44,0x3B67B79),source,0x3B67D18)
    return {'edges':edges,'instructionWindows':windows,
            'switchData':{'rva':0x3B67D18,'rawHex':switch.hex().upper()},
            'level':'direct conditional native carrier/state consumption',
            'outer':{'rva':0x3B188A0,'inputCarrierBytes':16,
                     'boundary':'Null MethodInfo+0x38 invokes initialization; non-null skips it. Rebuilds a 16-byte local from input qword+0 and dword+8, with last dword zero. Supplies the local, output slot, zero R8 and context slot 0 to the inner entry. Returned EAX is discarded; the output slot is returned after cleanup. No EOF comparison in this wrapper.'},
            'inner':{'rva':0x3B677B0,'stateStackOffset':0x40,'counterOffset':0x44,
                     'boundary':'Inlines state construction: input carrier at state+0x20, dword length at +0x30, signed length at +0x18, zero +0x38/+0x40/+0x44, and pointer-or-null cursor at +0x50. State+0x48 comes from the thread-local storage/allocation path, not the plain constructor. Conditional non-null helper result reaches dispatch slot 5 with R8=&state and R9=output. Returns state dword+0x44 after cleanup, matching the independently identified consumed accessor offset. This is not a proof of helper success or input allocation validity.'},
            'boundary':'MethodSpec-based names and declared stream input are separately joined in selectedStreamSourceIdentity. Live contexts, complete upstream resource selection, path/hash, carrier allocation length and final authenticated-file cursor are not joined. The switch data is excluded from the code window. Both terminal layouts remain ambiguous.'}


def skill_resource_context(pe, md, modules, image_owners, table, reg, code,
                          spec_records, specs_raw, methods_raw, *, source):
    """Exact selected static relations; no live generic sharing or file receipt."""
    identity=named_top_level_type(md.buf,b'Gameplay.Beyond.dll',b'Beyond.Gameplay.Core',
                                 b'SkillData',source=source)
    require(identity['typeDefinitionIndex'],9060,source)
    inst=table.resolve(16656)
    require(len(inst.arguments),1,source,inst.record_va)
    raw=bytes.fromhex(inst.arguments[0].raw_type_record_hex)
    require(raw,bytes.fromhex('64230000000000000000120000000000'),source,inst.arguments[0].type_pointer_va)
    require(struct.unpack_from('<Q',raw)[0],identity['typeDefinitionIndex'],source)
    object_inst=table.resolve(75)
    require(len(object_inst.arguments),1,source,object_inst.record_va)
    require(object_inst.arguments[0].raw_type_record_hex,'068E00000000000000001C0000000000',source)
    identities=module_methods(pe,md,modules,image_owners,
        [(248580,'Beyond.Resource.ResourceManager','DeserializeFromJson',None),
         (248574,'Beyond.Resource.ResourceManager','DeserializeFromJsonAsyncByCoroutine',None)],
        source=source,expected_image='Common.Beyond.dll')
    for row,token in zip(identities,(0x06001251,0x0600124B)):
        require(row['token'],token,source,row['slotVa'])
    selected=[]
    for index,definition in ((621380,248580),(621385,248574)):
        require(spec_records[index],(definition,-1,inst.index),source,int(reg['methodSpecs'],16)+index*12)
        selected.append({'index':index,'definition':definition,'classInstantiationIndex':-1,
                         'methodInstantiationIndex':inst.index,'rawHex':specs_raw[index*12:(index+1)*12].hex().upper()})
    matching={i for i,(definition,_,_) in enumerate(spec_records) if definition in (248580,248574)}
    candidates=generic_method_candidates(methods_raw,reg['genericMethodTableCount'],len(spec_records),
        matching,code['genericMethodPointersCount'],code['invokerPointersCount'],
        source=source,offset=int(reg['genericMethodTable'],16))
    for row in candidates:
        method,invoker,_=row['indices']
        row['methodPointerVa']=pe.u64_at_va(int(code['genericMethodPointers'],16)+method*8)
        row['invokerPointerVa']=pe.u64_at_va(int(code['invokerPointers'],16)+invoker*8)
        require(row['methodPointerVa']!=0 and row['invokerPointerVa']!=0,True,source,row['va'])
    # Pins validate the current complete candidate set, without selecting a live one.
    require([(r['methodSpecIndex'],r['methodPointerVa']) for r in candidates],
            [(521437,pe.image_base+0x36A7AD0),(521443,pe.image_base+0x45BA810)],source)
    for index,definition in ((521437,248580),(521443,248574)):
        require(spec_records[index],(definition,-1,object_inst.index),source,int(reg['methodSpecs'],16)+index*12)
    return {'typeIdentity':identity,'methodIdentities':identities,'concreteInstantiation':inst.as_dict(),
            'objectInstantiation':object_inst.as_dict(),'concreteMethodSpecs':selected,
            'sameDefinitionMethodSpecs':[{'index':i,'indices':list(spec_records[i]),
                                         'rawHex':specs_raw[i*12:(i+1)*12].hex().upper()} for i in sorted(matching)],
            'codeCandidates':candidates,
            'tableFraming':{'records':reg['genericMethodTableCount'],'byteLength':len(methods_raw),
                             'sha256':hashlib.sha256(methods_raw).hexdigest().upper(),
                             'boundary':'All 16-byte records and MethodSpec keys bounded; only selected triples decoded. Other triples remain opaque.'},
            'level':'exact static type/MethodSpec/code-table relations',
            'boundary':'Core.SkillData, not the same-named AI nested type. Generic definition module slots are null; code candidates come from the separate generic method table. Same-definition Object MethodSpecs do not establish actual sharing selection, method invocation, resource path/hash, reader ABI, consumed length or EOF. Preserve both terminal candidates.'}


def stream_source_identity(pe,md,modules,image_owners,reg,code,spec_records,methods_raw,*,source):
    """Join selected generic bodies and declared stream slots, not live overrides."""
    identities=module_methods(pe,md,modules,image_owners,
        [(249865,'Beyond.MemoryPack.MemoryPackManager','DeSerialize',None),
         (249853,'Beyond.MemoryPack.MemoryPackManager','_DeSerialize',None),
         (248587,'Beyond.Resource.ResourceManager','_MemoryPackDeserializeFromJson',None)],
        source=source,expected_image='Common.Beyond.dll')
    identities+=module_methods(pe,md,modules,image_owners,
        [(428652,'MemoryPack.MemoryPackSerializer','Deserialize',None)],source=source)
    stream=named_top_level_type(md.buf,b'mscorlib.dll',b'System.IO',b'Stream',source=source)
    require(stream['typeDefinitionIndex'],37639,source)
    method=md.methods[249853]
    require((method.parameter_start,method.parameter_count),(237944,1),source)
    require(method.parameter_start<len(md.parameters),True,source)
    parameter=md.parameters[method.parameter_start]
    require(parameter.type_index,143204,source)
    require(parameter.type_index<reg['typesCount'],True,source)
    type_pointer=pe.u64_at_va(int(reg['types'],16)+parameter.type_index*8)
    type_raw=pe.bytes_at_va(type_pointer,16)
    require(type_raw,bytes.fromhex('07930000000000000000120000000000'),source,type_pointer)
    require(struct.unpack_from('<Q',type_raw)[0],stream['typeDefinitionIndex'],source,type_pointer)
    stream_methods=module_methods(pe,md,modules,image_owners,
        [(287486,'System.IO.Stream','get_Length',None),(287526,'System.IO.Stream','Read',0x2FC6D40)],
        source=source,expected_image='mscorlib.dll')
    for row,slot,return_index,raw_hex in zip(stream_methods,(11,35),(126199,126157),
        ('3C8D00000000000000000A8000000000','3B8D0000000000000000088000000000')):
        method=md.methods[row['methodIndex']]
        require((method.slot,method.return_type),(slot,return_index),source)
        require(return_index<reg['typesCount'],True,source)
        pointer=pe.u64_at_va(int(reg['types'],16)+return_index*8)
        raw=pe.bytes_at_va(pointer,16)
        require(raw,bytes.fromhex(raw_hex),source,pointer)
        row.update(virtualSlot=slot,returnTypeIndex=return_index,returnTypeRawHex=raw.hex().upper())
    expected=((517109,249865,0x3B188A0),(517125,249853,0x2D36380),
              (517721,428652,0x3B677B0),(521492,248587,0x3187EB0))
    definitions={definition for _,definition,_ in expected}
    matching={i for i,(definition,_,_) in enumerate(spec_records) if definition in definitions}
    rows=generic_method_candidates(methods_raw,reg['genericMethodTableCount'],len(spec_records),matching,
        code['genericMethodPointersCount'],code['invokerPointersCount'],source=source,
        offset=int(reg['genericMethodTable'],16))
    for row in rows:
        row['methodPointerVa']=pe.u64_at_va(int(code['genericMethodPointers'],16)+row['indices'][0]*8)
    require([(row['methodSpecIndex'],row['methodPointerVa']) for row in rows],
            [(index,pe.image_base+rva) for index,_,rva in expected],source)
    for index,definition,_ in expected:
        require(spec_records[index],(definition,-1,75),source,int(reg['methodSpecs'],16)+index*12)
    return {'methodIdentities':identities,'genericBodyCandidates':rows,'streamType':stream,
            'streamParameter':{'methodIndex':249853,'parameterIndex':237944,'typeIndex':parameter.type_index,
                               'typePointerVa':type_pointer,'typeRawHex':type_raw.hex().upper()},
            'declaredStreamMethods':stream_methods,
            'level':'exact static method/type/virtual-slot relation',
            'boundary':'Declared input is System.IO.Stream. Metadata virtual slots 11 and 35 name get_Length and Read, with signed 64-bit and 32-bit return records. This does not identify the concrete stream subclass or override, its successful initialization, bytes, position, full-read behavior or EOF. Shared Object method contexts do not prove actual SkillData invocation.'}


def stream_carrier_consumer(pe,*,source):
    """Exact reviewed calls and discarded read result; length is not a receipt."""
    edges=[]
    for rva,target in ((0x2D363DC,0x3AF70),(0x2D36425,0x3AF70),(0x2D36470,0x3AF70),
                       (0x2D365F1,0x3AF70),(0x2D36448,0x3150DD0),
                       (0x2D3659E,0x3B188A0),(0x2D36961,0x3B188A0)):
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+target,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'targetRva':target,'rawHex':raw.hex().upper()})
    windows=[]
    for rva,hex_bytes in (
        (0x3AF78,'0FB7D9488BFA488B0AE80A9CFCFF488D431448C1E0044803074C8B00488B5008'),
        (0x2D36573,'FFD0488B0DAC6F2E0A'),
        (0x2D36924,'FF907003000048895D40448965488B452C'),
        (0x2D36442,'8BD0488D4D30'),
        (0x2D365F6,'4C8BE04C63C085C0'),
        (0x2D36526,'4585F60F884E040000'),
        (0x2D368E2,'4585E40F889F000000')):
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(hex_bytes)))
        require(raw,bytes.fromhex(hex_bytes),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    for rva in (0x2D363D4,0x2D3641D,0x2D36468,0x2D365E9):
        require(pe.bytes_at_va(pe.image_base+rva,8),bytes.fromhex('B90B000000488BD6'),source,rva)
    switch=pe.bytes_at_va(pe.image_base+0x2D36994,56)
    require(switch,bytes.fromhex('C564D302CF64D302D664D302E264D302EC64D302D664D302F664D3029266D302A266D302B266D3021567D3022567D302B266D302E967D302'),source,0x2D36994)
    return {'edges':edges,'windows':windows,'switchData':{'rva':0x2D36994,'rawHex':switch.hex().upper()},
            'dispatcher':{'rva':0x3AF70,'slotBaseOffset':0x140,'slotStride':16,'inputSlotBits':16,
                          'boundary':'The reviewed entry computes class + (uint16(CX)+0x14)*16, loads pointer and companion. Its specialized branches and cold paths are not all closed; this is a slot-address connection, not a live override receipt.'},
            'level':'direct conditional native carrier construction and discarded read result',
            'boundary':'Both allocation branches perform one indirect call at class+0x370 with a 16-byte carrier, then call the joined manager carrier entry without testing returned EAX. Slot 35 is declared Stream.Read, not ReadExactly. The large branch obtains length separately for comparison, low-32-bit allocation request and low-32-bit carrier length; equality/stability is not checked. The small branch also narrows a fresh result before stack allocation. Later negative checks apply to the narrowed dword, not the original 64-bit result. No source position, complete-fill loop, short-read check, authenticated payload length or final parser EOF is established; allocation helpers and concrete overrides remain unresolved.'}


def vfs_stream_identity(pe,md,modules,image_owners,reg,*,source):
    """Normal allocation candidate plus independent token/parent/slot identities."""
    identity=named_top_level_type(md.buf,b'Common.Beyond.dll',b'Beyond.VFS',b'VFSFileReadStream',source=source)
    require((identity['typeDefinitionIndex'],identity['byvalTypeIndex']),(31896,147393),source)
    require(md.types[31896].parent_index,143204,source)
    require(143204<reg['typesCount'],True,source)
    parent_pointer=pe.u64_at_va(int(reg['types'],16)+143204*8)
    parent_raw=pe.bytes_at_va(parent_pointer,16)
    require(parent_raw,bytes.fromhex('07930000000000000000120000000000'),source,parent_pointer)
    cell=rip_qword_load_target(pe.bytes_at_va(pe.image_base+0x2D7A588,7),pe.image_base+0x2D7A588,source=source)
    raw=pe.bytes_at_va(cell,8)
    index=unresolved_usage_index(raw,reg['typesCount'],tag=1,source=source,offset=cell)
    require(index,identity['byvalTypeIndex'],source,cell)
    pointer=pe.u64_at_va(int(reg['types'],16)+index*8)
    type_raw=pe.bytes_at_va(pointer,16)
    require(type_raw,bytes.fromhex('987C0000000000000000120000000000'),source,pointer)
    methods=module_methods(pe,md,modules,image_owners,
        [(247416,'Beyond.VFS.VirtualFileSystem','GetAssetStream',0x2D7A4C0),
         (247418,'Beyond.VFS.VirtualFileSystem','GetAssetStream',0x3187CF0),
         (247484,'Beyond.VFS.VFSFileReadStream','.ctor',0x2D076C0),
         (247486,'Beyond.VFS.VFSFileReadStream','Read',0x2D06B70),
         (247495,'Beyond.VFS.VFSFileReadStream','get_Length',0x4A490D0),
         (247496,'Beyond.VFS.VFSFileReadStream','get_Position',0x3DBBDC0)],
        source=source,expected_image='Common.Beyond.dll')
    for index,slot in ((247486,35),(247495,11),(247496,12)):
        require(md.methods[index].slot,slot,source,index)
    return {'typeIdentity':identity,'parentTypePointerVa':parent_pointer,'parentTypeRawHex':parent_raw.hex().upper(),
            'allocationCellVa':cell,'allocationCellRawHex':raw.hex().upper(),
            'allocationTypePointerVa':pointer,'allocationTypeRawHex':type_raw.hex().upper(),'methods':methods,
            'level':'exact static type/parent/token/slot relation; conditional allocation connection',
            'boundary':'The allocation callsite loads a type usage for VFSFileReadStream and passes the returned object plus the same 32-byte descriptor and inner stream to its token-joined constructor. Metadata parent points to the separately joined Stream record. This identifies the normal construction path, not successful execution, resolved live type usage, replacement callbacks, selected source file or authenticated bytes.'}


def vfs_stream_consumer(pe,*,source):
    """Descriptor-to-state and nested stream relations on reviewed normal paths."""
    edges=[]
    for rva,target in ((0x2D7A580,0x2D7A640),(0x2D7A5A0,0x26060),(0x2D7A5DF,0x2D076C0),
                       (0x2D06BCA,0x3AF70),(0x3DBBE03,0x3AF70),(0x2D06C24,0x508E0),
                       (0x4C36099,0x3A8ADF0),(0x2D06CDE,0x2C97740)):
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+target,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'targetRva':target,'rawHex':raw.hex().upper()})
    windows=[]
    for rva,hex_bytes in (
        (0x2D0770C,'410F1006488D4F4848895F48410F104E100F1147280F114F38'),
        (0x4A49105,'8B433C4883C4205BC3'),
        (0x3DBBE08,'8B4B38482BC14883C4205BC3'),
        (0x2D06BC2,'B90C000000488BD3'),
        (0x3DBBDF5,'488B53484885D27433B90C000000'),
        (0x2D06C15,'B9230000004C8D4424300F29442430'),
        (0x2D06C29,'8BF83B46080F87DCF4F201'),
        (0x50906,'498B80700300004D8B80780300000F29442420FFD0'),
        (0x2D06CE3,'8BC7488B7C2468488B5C24704883C4505EC3')):
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(hex_bytes)))
        require(raw,bytes.fromhex(hex_bytes),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    return {'edges':edges,'windows':windows,'level':'direct conditional native descriptor/state/return connection',
            'descriptorBytes':32,'descriptorStateOffset':0x28,'innerStreamOffset':0x48,
            'length':{'stateOffset':0x3C,'descriptorOffset':0x14,
                      'boundary':'The normal getter zero-extends this dword into RAX. It is copied from the constructor descriptor, not queried from physical-file EOF.'},
            'position':{'baseStateOffset':0x38,'descriptorOffset':0x10,
                        'boundary':'The normal getter calls slot 12 on the inner stream and subtracts the zero-extended descriptor dword. No initial inner position or seek execution is established.'},
            'read':{'boundary':'Normal Read subtracts logical Position from the zero-extended length word and uses the low 32 bits of a positive difference, otherwise zero; its signed request comparison does not certify arbitrary 64-bit ranges. An oversized request goes through a carrier-slicing helper whose full ABI remains open. The specialized inner dispatcher ignores entry ECX, copies the 16-byte input and calls fixed class+0x370 (slot 35) once, returning its EAX. Read unsigned-checks that count does not exceed the resulting request, optionally passes exactly the returned prefix to another stateful helper, and returns that count without a full-fill loop. The concrete inner override and optional transform remain unresolved.'},
            'boundary':'All statements are conditional on the reviewed no-replacement paths. Callback overrides, inner stream construction/seek, allocation extents, descriptor-to-current-VFS identity/hash and source/EOF receipt remain unresolved. Logical position arithmetic is not physical-file ownership or proof of byte equality.'}


def file_stream_open(pe,md,modules,image_owners,reg,*,source):
    """Selected normal file-stream creation/seek paths; no path or EOF receipt."""
    identity=named_top_level_type(md.buf,b'mscorlib.dll',b'System.IO',b'FileStream',source=source)
    require((identity['typeDefinitionIndex'],identity['byvalTypeIndex']),(37648,119269),source)
    require(md.types[37648].parent_index,143204,source)
    allocations=[]
    for rva in (0x2D7AD7F,0x5BBB5C0):
        cell=rip_qword_load_target(pe.bytes_at_va(pe.image_base+rva,7),pe.image_base+rva,source=source)
        raw=pe.bytes_at_va(cell,8)
        index=unresolved_usage_index(raw,reg['typesCount'],tag=1,source=source,offset=cell)
        require(index,identity['byvalTypeIndex'],source,cell)
        pointer=pe.u64_at_va(int(reg['types'],16)+index*8)
        type_raw=pe.bytes_at_va(pointer,16)
        require(type_raw,bytes.fromhex('10930000000000000000120000000000'),source,pointer)
        allocations.append({'rva':rva,'cellVa':cell,'cellRawHex':raw.hex().upper(),
                             'typePointerVa':pointer,'typeRawHex':type_raw.hex().upper()})
    require(allocations[0]['cellVa'],allocations[1]['cellVa'],source)
    methods=module_methods(pe,md,modules,image_owners,
        [(247286,'Beyond.VFS.UnityFileLoaderHelper','ReadFileByStream',0x2D7A640),
         (247302,'Beyond.VFS.UnityPersistFileHelper','ReadPersistAssetFileByStream',0x5BBB52C),
         (247315,'Beyond.VFS.UnityStreamingFileHelper','ReadStreamAssetFileByStream',0x2D7ACD0)],
        source=source,expected_image='Common.Beyond.dll')
    methods+=module_methods(pe,md,modules,image_owners,
        [(287703,'System.IO.FileStream','.ctor',0x30A4310),
         (287706,'System.IO.FileStream','.ctor',0x2DF9D00),
         (287727,'System.IO.FileStream','Seek',0x2FC8A30)],source=source,expected_image='mscorlib.dll')
    require(md.methods[287727].slot,32,source,287727)
    edges=[]
    for rva,target in ((0x2D7A716,0x2D7ACD0),(0x2D7A975,0x5BBB52C),
                       (0x2D7ADD5,0x2DF9D00),(0x5BBB607,0x30A4310),(0x5BBB61E,0x51D80)):
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+target,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'targetRva':target,'rawHex':raw.hex().upper()})
    windows=[]
    for rva,hex_bytes in (
        (0x2D7A549,'8B6B10'),(0x2D7A68C,'4080FF010F84C60200004080FF027423'),
        (0x2D7ACEB,'4963F8'),(0x5BBB547,'4963F8'),
        (0x2D7ADDA,'85FF7425'),(0x5BBB60C,'85FF7E14'),
        (0x2D7ADE9,'498B8140030000488BD74D8B89480300004533C0488BCBFFD0'),
        (0x5BBB610,'4C8BC7B9200000004533C9488BD3'),
        (0x51DA9,'4C8D4B14448BC749C1E104488BD64D030E498BCE498B014D8B4908')):
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(hex_bytes)))
        require(raw,bytes.fromhex(hex_bytes),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    switch=pe.bytes_at_va(pe.image_base+0x2D7ACA8,28)
    require(switch,bytes.fromhex('D0A9D702DFA9D702EEA9D70251AAD70260AAD702EEA9D70219ABD702'),source,0x2D7ACA8)
    return {'typeIdentity':identity,'allocations':allocations,'methodIdentities':methods,'edges':edges,
            'windows':windows,'switchData':{'rva':0x2D7ACA8,'rawHex':switch.hex().upper()},
            'level':'exact static allocation/method identity; direct conditional initial seek',
            'boundary':'Normal mode 1 and mode 2 select distinct token-joined helpers and FileStream constructors. The descriptor dword+0x10 reaches their offset argument and is sign-extended from int32. Mode 1 seeks only for positive offsets; mode 2 seeks for any nonzero offset. Both use declared FileStream.Seek slot 32 with numeric origin 0 and discard its return; the general dispatcher uses the low 16-bit slot number and preserves the supplied offset/origin. Normal return gives the constructed stream, not proof of a successful physical path/hash match or actual initial position. Root selection, path construction, FileStream constructor/Seek internals, replacement callbacks and authenticated logical-file bytes remain unresolved. Switch data is not code.'}


def vfs_descriptor_path(pe,md,modules,image_owners,*,source):
    """Normal descriptor lookup and mode projection, not a serialized BLC join."""
    methods=module_methods(pe,md,modules,image_owners,
        [(247352,'Beyond.VFS.FVFBlockFileInfo','get_fileChunkMD5Name',0x2D751D0),
         (247359,'Beyond.VFS.FVFBlockFileInfo','get_loaderPosType',0x2D75510),
         (247371,'Beyond.VFS.FVFBlockFileInfo','GetRelativeChunkFilePath',0x2D7A040)],
        source=source,expected_image='Common.Beyond.dll')
    edges=[]
    for rva,target in ((0x2D7A52D,0x2D7A040),(0x2D7A53A,0x2D75510),
                       (0x2D7A13E,0x2D751D0),(0x2D752DE,0x3820560),
                       (0x4C48A6A,0x6DBEEC0)):
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+target,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'targetRva':target,'rawHex':raw.hex().upper()})
    windows=[]
    for rva,hex_bytes in (
        (0x2D7557F,'8B4318C1E80A'),(0x2D7A546,'0FB6F0'),(0x2D7A56C,'440FB6C6'),
        (0x2D7A0DE,'F64718020F871810ED01'),
        (0x2D7A134,'4533C0488D4D20488BD7'),
        (0x2D75260,'837F08000F8CD837ED01'),
        (0x2D75285,'448B7708488B88B8000000488B5908'),
        (0x2D752CA,'418BD6488BCB'),
        (0x2D752E8,'85C00F885237ED01'),
        (0x2D752F0,'488B4B184885C90F849E0000003B41180F838F000000'),
        (0x2D75306,'489848C1E0050F10440830'),(0x2D7531E,'0F1106'),
        (0x4C48A6F,'0F57C0E99AC812FE')):
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(hex_bytes)))
        require(raw,bytes.fromhex(hex_bytes),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    return {'methodIdentities':methods,'edges':edges,'windows':windows,
            'mode':{'descriptorOffset':0x18,'loadBytes':4,'rightShift':10,'callerMask':255,
                    'effectiveBitRangeInclusive':[10,17]},
            'lookup':{'descriptorKeyOffset':8,'containerArrayOffset':0x18,
                      'arrayCountOffset':0x18,'indexedStride':32,'indexedReadBias':0x30,'resultBytes':16},
            'level':'direct conditional native lookup and bit projection; exact static method identity',
            'boundary':'On the no-replacement path, the mode getter logically shifts descriptor dword+0x18 by 10; its caller passes only AL, hence bits 10..17. With descriptor byte+0x18 bit 1 clear, the relative-path routine calls the token-joined chunk-name getter with a separate 16-byte output buffer. A nonnegative descriptor dword+8 is passed to a lookup on static-carrier+8. A nonnegative result is checked against the count at array carrier+0x18, then 16 bytes are copied from array+0x30+result*32. A negative key or lookup result diverts to a helper call; if that call returns normally, the branch zeroes XMM0 and rejoins the same 16-byte output copy. It is not a proven throwing rejection or an authenticated missing-chunk receipt. The normal lookup does not read an inline descriptor-leading hash. Method names do not prove these bytes equal the authenticated BLC chunk MD5. Complete lookup implementation, container population/producer, negative-path helper effects, alternate bit-1 path, path encoding/root selection and replacement callbacks remain unresolved; no current logical-file or EOF receipt follows.'}


def vfs_descriptor_producer(pe,md,modules,image_owners,reg,table,*,source):
    """Paired storage and original MethodInfo class contexts, not live contents."""
    methods=module_methods(pe,md,modules,image_owners,
        [(247351,'Beyond.VFS.FVFBlockFileInfo','_SetFileChunkMD5Name',0x2D755E0)],
        source=source,expected_image='Common.Beyond.dll')
    methods+=module_methods(pe,md,modules,image_owners,
        [(286427,'System.Collections.Generic.Dictionary`2','TryGetValue',None),
         (286407,'System.Collections.Generic.Dictionary`2','set_Item',None)],
        source=source,expected_image='mscorlib.dll')
    value=named_top_level_type(md.buf,b'Beyond.Byte.dll',b'Beyond.Byte',b'UInt128',source=source)
    require(value['typeDefinitionIndex'],0xDF7E,source)
    int_raw='3B8D0000000000000000088000000000'
    value_raw='7EDF0000000000000000118000000000'
    instances=[]
    for index,expected in ((3297,[int_raw,value_raw]),(4291,[value_raw,int_raw])):
        instance=table.resolve(index)
        require([a.raw_type_record_hex for a in instance.arguments],expected,source)
        instances.append(instance.as_dict())
    usage=[]
    for rva,index,definition,ci in ((0x2D752A2,55461,286427,3297),
        (0x2D756A4,70920,286427,4291),(0x2D75759,70927,286407,4291),
        (0x2D757D4,55468,286407,3297)):
        cell=rip_qword_load_target(pe.bytes_at_va(pe.image_base+rva,7),pe.image_base+rva,source=source)
        raw=pe.bytes_at_va(cell,8)
        actual=unresolved_usage_index(raw,reg['methodSpecsCount'],tag=6,source=source,offset=cell)
        require(actual,index,source,cell)
        va=int(reg['methodSpecs'],16)+actual*12
        spec=pe.bytes_at_va(va,12)
        require(method_spec_record(spec,len(md.methods),reg['genericInstsCount'],source=source,offset=va),
                (definition,ci,-1),source,va)
        usage.append({'rva':rva,'cellVa':cell,'rawHex':raw.hex().upper(),
                      'methodSpecIndex':actual,'methodSpecRawHex':spec.hex().upper()})
    storage=[]
    for rva in (0x2D7527E,0x2D75689,0x2D757B9):
        cell=rip_qword_load_target(pe.bytes_at_va(pe.image_base+rva,7),pe.image_base+rva,source=source)
        require(cell,pe.image_base+0xD072F48,source,rva)
        storage.append({'rva':rva,'cellVa':cell})
    edges=[]
    for rva,target in ((0x2D756EB,0x2D79390),(0x2D757B4,0x3E1DF70),(0x2D75825,0x3820080)):
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+target,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'targetRva':target,'rawHex':raw.hex().upper()})
    windows=[]
    for rva,hex_bytes in ((0x2D756F0,'85C0783D'),
        (0x2D75701,'3B41180F83FC010000489848C1E0058B5C0838895E08'),
        (0x2D75763,'8B5A202B5A28'),(0x2D7578A,'41B1010F104500448BC3498BCE'),
        (0x2D75801,'0F10450041B101498BCE'),(0x2D7581E,'8BD34889442420'),
        (0x2D7582A,'E9E5FEFFFF'),(0x2D756AB,'488B4720488B88C0000000488B81B0000000'),
        (0x2D75769,'488B4720488B88C0000000488B81C0000000')):
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(hex_bytes)))
        require(raw,bytes.fromhex(hex_bytes),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    return {'methods':methods,'valueType':value,'instances':instances,'methodUsages':usage,
            'storageReferences':storage,'edges':edges,'windows':windows,
            'level':'exact static ordered instances and MethodSpec usages; direct conditional producer flow',
            'boundary':'The source usage cells name TryGetValue/set_Item, not FindEntry/TryInsert simply because the inlined call targets look like those helpers. Their MethodInfo+0x20 supplies the original Dictionary class before class RGCTX slots are loaded. Registered arguments are Int32/UInt128 and the exact reverse order. The setter probes static-carrier+0x10 using the incoming 16 bytes; a nonnegative result is bounds-checked and its indexed dword copied to descriptor+8. On a miss it computes dword+0x20 minus dword+0x28, supplies the same integer and 16-byte value in reverse orders to two helpers with numeric behavior 1, then stores that integer to descriptor+8. The second helper uses static-carrier+8, the same storage selected by the getter. Helper return values are not checked. Complete insertion/comparer/collision semantics, initialization, replacement paths, other mutations and actual reciprocal contents are unproved. UInt128 identity is not BLC MD5 provenance; serialized source/carrier/cursor and EOF remain unresolved.'}


def vfs_bytebuf_consumer(pe,md,modules,image_owners,reg,*,source):
    """Conditional serialized-input cursor path; native permissiveness is not validation."""
    methods=module_methods(pe,md,modules,image_owners,
        [(247366,'Beyond.VFS.FVFBlockFileInfo','ReadFromByteBuf',0x2D76D10)],
        source=source,expected_image='Common.Beyond.dll')
    methods+=module_methods(pe,md,modules,image_owners,
        [(449337,'Beyond.Byte.ByteHelper','ReadULong',0x2D78240)],source=source,expected_image='Beyond.Byte.dll')
    identity=named_top_level_type(md.buf,b'Beyond.Byte.dll',b'Beyond.Byte',b'ByteBufStream',source=source)
    require(identity['typeDefinitionIndex'],57215,source)
    method=md.methods[247366]
    require((method.parameter_start,method.parameter_count),(235374,2),source)
    require(235376<=len(md.parameters),True,source)
    require(md.parameters[235375].type_index,93608,source)
    require(93608<reg['typesCount'],True,source)
    pointer=pe.u64_at_va(int(reg['types'],16)+93608*8)
    type_raw=pe.bytes_at_va(pointer,16)
    require(type_raw,bytes.fromhex('7FDF0000000000000000112000000000'),source,pointer)
    edges=[]
    for rva,target in ((0x2D76F35,0x2D78240),(0x2D76FAD,0x2D78240),
        (0x2D76FC2,0x2D78240),(0x2D770CB,0x2D79390),
        (0x2D77847,0x3E1DF70),(0x2D778B2,0x3820080)):
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+target,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'targetRva':target,'rawHex':raw.hex().upper()})
    windows=[]
    for rva,hex_bytes in (
        (0x2D76EB9,'66C1E108660BCA6683C1020FBFC10103'),
        (0x2D76F2A,'4533C941B0018BD6488BCF'),(0x2D76F3A,'830308'),
        (0x2D76FB2,'8D5608488945F74533C941B001488BCF'),
        (0x2D76FC7,'488945FF0F2875F7830310'),
        (0x2D770B1,'488D55F7488BCF660F7F75F7'),
        (0x2D770F4,'8B7C0838897D0F'),
        (0x2D776FE,'0F1045070F104D170F11000F114810'),
        (0x2D78298,'8D47073B43180F8D02010000'),
        (0x2D783A6,'33C0EBC3'),(0x2D782B1,'4084F60F84877ED701')):
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(hex_bytes)))
        require(raw,bytes.fromhex(hex_bytes),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    return {'methods':methods,'sourceType':identity,'parameterTypePointerVa':pointer,
            'parameterTypeRawHex':type_raw.hex().upper(),'edges':edges,'windows':windows,
            'level':'exact static source-type identity; direct conditional cursor/value path',
            'boundary':'The selected source parameter joins ByteBufStream. On the reviewed no-replacement path R8 supplies a mutable carrier with cursor dword+0 and array object+8. Two initial bytes are assembled little-endian, incremented by 2 in 16 bits, then sign-extended before adding to the cursor. After an eight-byte helper call and cursor advance, two further helper calls at cursor and cursor+8 form the 16-byte container lookup input; the cursor advances 16. The same paired insertion targets are used on lookup miss, and the resulting integer enters the returned 32-byte descriptor. ReadULong with the supplied nonzero flag assembles eight bytes little-endian after per-byte index checks, but signed int32(offset+7) >= array count returns zero normally; callers still advance their cursor. Overflow and alternate flag/replacement paths are not generalized. This is not a fail-closed source-range validator or proof that returned zeros came from file bytes. Later skips, narrowed values, version/flag branches and cursor save/restore require their own closure. The array origin, authenticated BLC identity, complete carrier allocation, initial/final cursor and logical-file EOF remain unproved.'}


def vfs_block_cursor(pe,md,modules,image_owners,*,source):
    """Array -> shared cursor -> nested records; distinguish checksum and EOF."""
    methods=module_methods(pe,md,modules,image_owners,
        [(247331,'Beyond.VFS.VFBlockMainInfo','ReadFromByteBuf',0x33AF150),
         (247335,'Beyond.VFS.FVFBlockChunkInfo','ReadFromByteBuf',0x2D76170)],
        source=source,expected_image='Common.Beyond.dll')
    methods+=module_methods(pe,md,modules,image_owners,
        [(449333,'Beyond.Byte.ByteBufStream','CreateFromByte',0x449AEB0),
         (449317,'Beyond.Byte.ByteBufStream','ReadInt',0x2D76630)],source=source,expected_image='Beyond.Byte.dll')
    edges=[]
    for rva,target in ((0x33AF224,0x449AEB0),(0x33AF346,0x2D76170),
        (0x2D76351,0x2D76D10),(0x4D86E74,0x2D76630),
        (0x33AF1C4,0x2D767D0),(0x33AF1E8,0x2FE7660)):
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+target,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'targetRva':target,'rawHex':raw.hex().upper()})
    windows=[]
    for rva,hex_bytes in (
        (0x449AEE1,'C744243400000000897C24304889742438'),
        (0x449AEF7,'0F10442430488B742468488BC30F1103'),
        (0x33AF21A,'488D4DB0458BC6488BD6'),
        (0x33AF33C,'4C8D45A08BD6488D4DC0'),
        (0x2D7634C,'4C8BC68BD5'),
        (0x2D76356,'0F10000F1048100F11030F114B104883C3204883EF0175C2'),
        (0x2D76249,'4C63F0'),(0x2D76286,'498BDE48C1E305'),
        (0x2D76326,'4585F67E43'),
        (0x33AF1A6,'8B5E18412BDE83EB0485DB0F8EEE7C9D01'),
        (0x33AF1ED,'3BF80F858A7C9D01'),
        (0x33AF3B0,'8B40182B45A085C0410F4EC685C07E0A837F48030F84A47A9D01'),
        (0x4D86E79,'90E94B8562FE'),(0x33AF3CA,'488BC7')):
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(hex_bytes)))
        require(raw,bytes.fromhex(hex_bytes),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    return {'methods':methods,'edges':edges,'windows':windows,
            'level':'exact static identities; direct conditional shared-cursor and return paths',
            'boundary':'The normal main-info entry passes its input array and supplied start index to CreateFromByte, which constructs 16 bytes: cursor dword, zero dword, original array pointer. Main, chunk and file readers share that same mutable carrier. Chunk processing sign-extends a ReadInt result and requests count*32 bytes before its positive-count loop; each file result is copied as 32 bytes. Allocation-helper behavior and negative-count rejection are not proved by this loop. Before parsing, main compares two helper results using array length minus start minus four and the selected tail position; helper algorithms and authenticated array provenance remain open. After the chunk loop, the normal remaining calculation clamps nonpositive array-length-minus-cursor to zero. Positive remaining with stored version 3 causes one ReadInt call, whose result is discarded before returning the object; other versions can return with positive remaining. No final equality check follows this extra read. This is not an EOF validator, even if the earlier comparison succeeds. Replacement callbacks, helper internals, upstream decryption/file identity, full record grammar and final source receipt remain unresolved.'}


def vfs_block_transform(pe,md,modules,image_owners,*,source):
    """Reviewed normal-path array aliasing, not a complete cipher implementation."""
    methods=module_methods(pe,md,modules,image_owners,
        [(247532,'Beyond.VFS.VFSUtils','DecryptCreateBlockGroupInfo',0x318B640)],
        source=source,expected_image='Common.Beyond.dll')
    methods+=module_methods(pe,md,modules,image_owners,
        [(452763,'Beyond.XXEnc.XXE1','TransformBytes',0x507D3C4),
         (452780,'Beyond.XXEnc.XXE1','WorkBytes',0x2C97EF0)],
        source=source,expected_image='Common.Beyond.XXEnc.dll')
    edges=[]
    for rva,target in ((0x318B91E,0x507D3C4),(0x507D3DE,0x2C97EF0),
        (0x318B93D,0x33AF150),(0x2C97FE6,0x2C97A90)):
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+target,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'targetRva':target,'rawHex':raw.hex().upper()})
    windows=[]
    for rva,hex_bytes in (
        (0x318B66A,'488BF1'),
        (0x318B8FE,'488B82B8000000448B80E4000000448B4E18452BC848897C2420488BD6488BCB'),
        (0x318B92A,'488B88B80000004533C08B91E4000000488BCE'),
        (0x318B942,'488BF8488BC7'),
        (0x507D3C4,'4883EC4848C74424300000000044894C24284C8BCA4489442420'),
        (0x2C97EFD,'448B642478498BE9458BE84C8BFA488BF14585E40F8EBD000000'),
        (0x2C97F42,'448B742470438D0426413B41180F8FA082E401438D04043942180F8CFE81E401'),
        (0x2C97F62,'418BF8452BF0'),(0x2C97F70,'0FB65E3080E33F7468'),
        (0x2C97F79,'418D043E3B4518736B4C8B46284D85C07468440FB6CB453B48187358413B7F187352'),
        (0x2C97F9B,'418D043EFEC34863C84863C7FFC70FB654292043325401204288543820'),
        (0x2C97FB8,'8BC7412BC5885E30413BC47CAB')):
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(hex_bytes)))
        require(raw,bytes.fromhex(hex_bytes),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    storage=[]
    for rva in (0x318B8F7,0x318B923):
        raw=pe.bytes_at_va(pe.image_base+rva,7)
        cell=rip_qword_load_target(raw,pe.image_base+rva,source=source)
        require(cell,pe.image_base+0xD0B9A10,source,rva)
        storage.append({'rva':rva,'cellVa':cell,'rawHex':raw.hex().upper()})
    return {'methods':methods,'edges':edges,'windows':windows,'staticStorage':storage,
            'level':'exact static identities; direct conditional in-place byte transform',
            'boundary':'On the reviewed non-replacement path, the entry retains its original array in RSI. It passes that array, static-carrier+0xE4 as offset and signed 32-bit array-length-minus-offset as count to TransformBytes. The wrapper forwards identical input/output array pointers and identical input/output offsets to WorkBytes. A positive-count normal loop reads one input byte, XORs it with a byte from state+0x28 array, and writes the same output index; its state byte counter is masked with 63 and zero invokes a separate block helper. Nonpositive count returns without validation. Initial length sums use signed 32-bit arithmetic; per-byte array indices also have unsigned bounds checks. This is not a reusable fail-closed range parser. After the transform returns, the same original array reaches the already pinned main-info reader, with a fresh +0xE4 load from the same static storage cell. No equality check proves the two runtime offset loads stayed identical. Static values, key/span and constructor ABI, state initialization/block generation, exceptional and replacement behavior, cipher parity with the maintained decoder, physical-file identity and actual execution remain unresolved. This establishes neither a complete decryption algorithm nor EOF consumption.'}


def vfs_block_file_source(pe,md,modules,image_owners,*,source):
    """File-read return carrier and loop; actual paths and Read override stay open."""
    methods=module_methods(pe,md,modules,image_owners,
        [(247400,'Beyond.VFS.VirtualFileSystem','CreateBlockFromPersistAssetFile',0x318BC00),
         (247401,'Beyond.VFS.VirtualFileSystem','CreateFromStreamAssetFile',0x318BD20),
         (247301,'Beyond.VFS.UnityPersistFileHelper','ReadPersistAssetFileAllBytes',0x318BFA0),
         (247314,'Beyond.VFS.UnityStreamingFileHelper','ReadStreamAssetFileAllBytes',0x318C0C0)],
        source=source,expected_image='Common.Beyond.dll')
    methods+=module_methods(pe,md,modules,image_owners,
        [(287401,'System.IO.File','ReadAllBytes',0x318C220),
         (287719,'System.IO.FileStream','Read',0x2FCA460)],source=source,expected_image='mscorlib.dll')
    require(md.methods[287719].slot,34,source,287719)
    require(md.methods[287719].parameter_count,3,source,287719)
    edges=[]
    for rva,target in ((0x318BC48,0x318BE20),(0x318BD63,0x318BE20),
        (0x318BC60,0x318BFA0),(0x318BD8F,0x318C0C0),
        (0x318BC8A,0x318B640),(0x318BDA9,0x318B640),
        (0x318C060,0x2D71FA0),(0x318C17E,0x2D71FA0),
        (0x318C06A,0x318C220),(0x318C188,0x318C220),
        (0x318C2BE,0x2DF9D00),(0x318C2F3,0x3AF70)):
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+target,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'targetRva':target,'rawHex':raw.hex().upper()})
    windows=[]
    for rva,hex_bytes in (
        (0x318BC81,'4533C0488BD3488BC8'),(0x318BDA0,'4533C0488BD3488BC8'),
        (0x318C065,'33D2488BC8'),(0x318C06F,'488BF8'),(0x318C07D,'488BC7'),
        (0x318C183,'33D2488BC8'),(0x318C18D,'488BF8'),(0x318C19B,'488BC7'),
        (0x318C26A,'4533F6'),(0x318C2EE,'B90B000000'),
        (0x318C2F8,'488BF8483DFFFFFF7F0F8FB20000004885C00F8483000000'),
        (0x318C310,'8BD0'),(0x318C31E,'4C8BF885FF7E4D'),
        (0x318C341,'4C8B9060030000488B80680300004889442420448BCF458BC6498BD7488BCE41FFD2'),
        (0x318C363,'85C00F84AF0000004403F02BF8EBAF'),
        (0x318C372,'4C89BC24A0000000'),(0x318C3FB,'498BC7')):
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(hex_bytes)))
        require(raw,bytes.fromhex(hex_bytes),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    return {'methods':methods,'edges':edges,'windows':windows,'readSlot':34,
            'level':'exact static identities; direct conditional read-loop and return-array chain',
            'boundary':'Both reviewed block constructors pass the returned array of their respective file helper directly to DecryptCreateBlockGroupInfo, after nonnull/nonempty checks. On the normal successful helper paths, a path-carrier conversion result is passed to System.IO.File.ReadAllBytes, whose returned array is preserved across cleanup and returned unchanged. The actual root strings, relative path construction, path-carrier conversion, selection/fallback and authenticated on-disk file/hash remain unresolved. ReadAllBytes calls a FileStream constructor and dispatches Length via numeric slot 11. Its positive signed length branch rejects values above INT32_MAX, requests an array of the narrowed length, and loops while signed remaining is positive. Each call uses class+0x360 and companion+0x368 (slot 34, not the previously reviewed slot 35), passes array/accumulated offset/remaining, then adds EAX to offset and subtracts EAX from remaining. Zero EAX branches to error helpers rather than the normal loop return. There is no local negative/oversized returned-count rejection or final equality check; full-fill reasoning requires the Read override contract. The registered FileStream Read definition independently declares slot 34 and three parameters, but concrete live dispatch, constructor/override internals, zero-length alternate helper, allocation/error/cleanup behavior and actual file execution are not proved. A length-based read loop is not a source-hash receipt or a serialized-reader EOF check.'}


def native_file_read(pe,md,modules,image_owners,*,source):
    """Static import/argument/count connection; no live OS or handle receipt."""
    methods=module_methods(pe,md,modules,image_owners,
        [(287719,'System.IO.FileStream','Read',0x2FCA460),
         (287775,'System.IO.MonoIO','Read',0x3AFCB00)],source=source,expected_image='mscorlib.dll')
    edges=[]
    for rva in (0x2FCA582,0x2FCA69D):
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+0x3AFCB00,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'targetRva':0x3AFCB00,'rawHex':raw.hex().upper()})
    windows=[]
    for rva,hex_bytes in (
        (0x2FCA4BD,'85ED0F8826AACF0185DB0F88BAA9CF01418B46183BE80F8F55A9CF012BC33BE80F8FF2A8CF01'),
        (0x2FCA508,'412BFF3BDF7F028BFB'),
        (0x2FCA576,'448BC8498BCF4533C0498BD5'),
        (0x2FCA68C,'448BCB4889442420448BC5498BD6498BCF'),
        (0x2FCA6BC,'83F8FF0F848CA6CF014863C348014668E90DFFFFFF'),
        (0x2FCA5DE,'03DF8BC3'),
        (0x3AFCB1D,'418BD94963F04C8BF24533E4'),
        (0x3AFCB7A,'4C8B7810'),
        (0x3AFCB93,'488BBC24B00000004489278D041E413B46180F87AE000000'),
        (0x3AFCBAB,'488D56204903D644896424344C896424204C8D4C2434448BC3498BCF'),
        (0x3AFCBCD,'85C07508'),(0x3AFCBD7,'89078B5C2434'),
        (0x3AFCBF5,'B8FFFFFFFF833F000F45D8895C2438'),(0x3AFCC3C,'8BC3')):
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(hex_bytes)))
        require(raw,bytes.fromhex(hex_bytes),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    # This selected-build witness authenticates the header directory reference,
    # first descriptor and two exact name thunks. Other imports stay opaque.
    optional=pe.u32_at_file(0x3C)+24
    require(pe.u32_at_file(optional+120),0xCF8EBC0,source,optional+120)
    require(pe.u32_at_file(optional+124),220,source,optional+124)
    require(pe.bytes_at_va(pe.image_base+0xCF8EBC0,20),
            struct.pack('<IIIII',0xCF8ECE8,0,0,0xCF8FE50,0xA82F048),source,0xCF8EBC0)
    require(pe.bytes_at_va(pe.image_base+0xCF8FE50,13),b'KERNEL32.dll\0',source,0xCF8FE50)
    imports=[]
    for rva,index,name_rva,hint,name in (
        (0x3AFCBC7,78,0xCF8FC30,0x4A9,b'ReadFile'),
        (0x3AFCBD1,4,0xCF8F668,0x28D,b'GetLastError')):
        raw=pe.bytes_at_va(pe.image_base+rva,6)
        require(len(raw),6,source,rva)
        require(raw[:2],b'\xff\x15',source,rva)
        slot=rva+6+struct.unpack_from('<i',raw,2)[0]
        require(slot,0xA82F048+index*8,source,rva)
        lookup=0xCF8ECE8+index*8
        require(pe.bytes_at_va(pe.image_base+lookup,8),struct.pack('<Q',name_rva),source,lookup)
        require(pe.bytes_at_va(pe.image_base+name_rva,len(name)+3),struct.pack('<H',hint)+name+b'\0',source,name_rva)
        imports.append({'callRva':rva,'iatSlotRva':slot,'lookupSlotRva':lookup,
                        'nameRva':name_rva,'name':name.decode('ascii'),'dll':'KERNEL32.dll'})
    return {'methods':methods,'edges':edges,'windows':windows,'selectedImports':imports,
            'level':'exact static import/identity joins; direct conditional buffer and returned-count flow',
            'boundary':'The reviewed FileStream array overload checks negative offset/count and offset against array length minus count before its normal buffered path. Buffered and direct reads call the same MonoIO helper. That helper extracts a handle carrier at +0x10, compares the 32-bit offset-plus-count against array length, then passes handle, array+0x20+sign-extended offset, count, address of a zeroed out DWORD and a zero fifth argument to the static ReadFile import slot. A zero API return calls the static GetLastError slot and stores its result through the supplied error pointer. The helper returns the out DWORD when that error word is zero, otherwise -1; it does not derive the count from the API boolean return. The direct FileStream branch records that count, tests its error and -1 paths, updates state position and adds already-buffered bytes for its normal return. This distinguishes API boolean, out-byte count, error and accumulated read count. Only two name thunks and their descriptor are joined, not the entire import directory; live IAT contents, imported function behavior, handle provenance, full buffered-state invariants, alternate async/error/cleanup paths and runtime execution remain unresolved. No authenticated-file receipt, unconditional full-read guarantee or serialized EOF follows.'}


def vfs_path_carrier(pe,md,modules,image_owners,*,source):
    """Four-slot path carrier construction/consumption, not concrete root identity."""
    methods=module_methods(pe,md,modules,image_owners,
        [(247308,'Beyond.VFS.UnityPersistFileHelper','GetPersistAssetFilePath',0x2D7F920),
         (247322,'Beyond.VFS.UnityStreamingFileHelper','GetStreamAssetFilePath',0x2D7DBF0),
         (247278,'Beyond.VFS.UnityFileLoaderHelper','get_persistentDataPath',0x2D7FE70),
         (247272,'Beyond.VFS.UnityFileLoaderHelper','get_streamingAssetsPath',0x2F46C10)],
        source=source,expected_image='Common.Beyond.dll')
    methods+=module_methods(pe,md,modules,image_owners,
        [(452858,'Beyond.VFS.ThreadUnsafeStringUtils','AppendPathInfo',0x2D7E480)],
        source=source,expected_image='Unsafe.VFS.dll')
    edges=[]
    for rva,target in ((0x318BFFA,0x2D7F770),(0x318C12E,0x2D7AE60),
        (0x2D7F7CB,0x2D7F920),(0x2D7AEC6,0x2D7DBF0),
        (0x2D7FB68,0x2D7FE70),(0x2D7FD10,0x2D7FE70),
        (0x2D7DF60,0x2F46C10),(0x2D7E0CC,0x2F46C10),(0x2D7E210,0x2F46C10),
        (0x318C03E,0x2D7E480),(0x318C15D,0x2D7E480),
        (0x2D7E601,0x2DF2AA0),(0x2D7E636,0x2D72FA0)):
        raw=pe.bytes_at_va(pe.image_base+rva,5)
        require(relative_branch_target(raw,pe.image_base+rva,source=source),pe.image_base+target,source,rva)
        require(raw[0],0xE8,source,rva)
        edges.append({'rva':rva,'targetRva':target,'rawHex':raw.hex().upper()})
    windows=[]
    for rva,hex_bytes in (
        (0x2D7F7D3,'0F10000F1048100F11030F114B10'),
        (0x2D7AECE,'0F10000F1048100F11030F114B10'),
        (0x2D7FB6D,'4889442438'),(0x2D7FBCF,'4889742440'),(0x2D7FC2F,'4C897C2448'),
        (0x2D7FD15,'4889442438'),(0x2D7FD70,'4C897C2440'),
        (0x2D7FDE3,'498BC6410F1106410F114E10'),
        (0x2D7DF65,'488945C8'),(0x2D7DFBF,'4C8975D0'),(0x2D7E00F,'488975D8'),
        (0x2D7E215,'488945C8'),(0x2D7E26F,'488975D0'),
        (0x2D7E2D9,'410F1107410F114F10'),
        (0x2D7E58A,'488B7E08'),(0x2D7E5A4,'4C8B7610'),(0x2D7E5B7,'4C8B3E488B7618'),
        (0x2D7E5EE,'48897424204D8BCE4C8BC7498BD7488D4C2438'),
        (0x2D7E61E,'488D5020'),(0x2D7E62B,'4533C9448B442440488BCB')):
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(hex_bytes)))
        require(raw,bytes.fromhex(hex_bytes),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    return {'methods':methods,'edges':edges,'windows':windows,'carrierByteLength':32,
            'level':'exact static identities; direct conditional four-slot carrier flow',
            'boundary':'The file-helper checks call two distinct builders and copy both 16-byte halves of their results into the caller-supplied 32-byte carrier. On the non-replacement builder paths, slot +0 comes from branch-selected static storage and slot +8 from the respective path getter. Nonempty first input normally fills +0x10 with that input and +0x18 with the second candidate; the empty/null first-input branch instead fills +0x10 with the second candidate and leaves +0x18 zero. Streaming can transform the second candidate before these stores; its helper behavior and predicate semantics remain unresolved. AppendPathInfo receives that carrier, skips work when slot +0 is null/empty, substitutes a shared static value for null slots +8/+0x10/+0x18, and forwards +0,+8,+0x10,+0x18 in that order to another helper with a separate stack companion. Its resulting temporary array+0x20 and temporary DWORD length are passed to the append consumer. The copy width and argument order do not establish formatting syntax, separators, string contents, final output length, concrete root, overlay selection or file/hash identity. Static values, getter initialization, formatting/append ABI and helper internals, replacements and runtime execution remain unresolved.'}


def vfs_path_format_context(pe,md,modules,image_owners,reg,table,*,source):
    """Original generic arguments and append units, not complete format grammar."""
    methods=module_methods(pe,md,modules,image_owners,
        [(443949,'Cysharp.Text.Utf16ValueStringBuilder','AppendFormat',None),
         (443868,'Beyond.UnSafeString','Append',0x2D72FA0)],source=source,expected_image='ZString.dll')
    rva=0x2D7E5E2
    cell=rip_qword_load_target(pe.bytes_at_va(pe.image_base+rva,7),pe.image_base+rva,source=source)
    require(cell,pe.image_base+0xD06A7F8,source,rva)
    raw=pe.bytes_at_va(cell,8)
    index=unresolved_usage_index(raw,reg['methodSpecsCount'],tag=6,source=source,offset=cell)
    require(index,627375,source,cell)
    va=int(reg['methodSpecs'],16)+index*12
    spec=pe.bytes_at_va(va,12)
    require(method_spec_record(spec,len(md.methods),reg['genericInstsCount'],source=source,offset=va),
            (443949,-1,8335),source,va)
    instance=table.resolve(8335)
    require([a.raw_type_record_hex for a in instance.arguments],
            ['C78C00000000000000000E0000000000']*3,source)
    windows=[]
    for at,hex_bytes in (
        (0x2D7E5E9,'4889442428'),(0x2DF2AC1,'4C8B757F488BFA4C8BE1'),
        (0x2DF2B28,'4863C30FB74C47146683F97B'),
        (0x2DF2D9E,'488B457F488B556F488B4038488B4808'),
        (0x2DF2E0C,'488B457F488B5567488B4038488B08'),
        (0x2DF2E94,'488B457F488B5577488B4038488B4810'),
        (0x2DF2D43,'45017C2408'),
        (0x2D72FAD,'4C8BFA418BF0418BD0488BD9'),
        (0x2D73006,'488B43208B088D04364863E84863C14C8D3447'),
        (0x2D73029,'4C8BC5498BD7498BCEFFD0'),
        (0x2D73065,'488B43208B0003F0'),(0x2D73097,'488B43208930'),
        (0x2D730CE,'488B43208B003B43287D38'),
        (0x2D73103,'488B43208B00489833C966890C47')):
        chunk=pe.bytes_at_va(pe.image_base+at,len(bytes.fromhex(hex_bytes)))
        require(chunk,bytes.fromhex(hex_bytes),source,at)
        windows.append({'rva':at,'rawHex':chunk.hex().upper()})
    return {'methods':methods,'usageCellVa':cell,'usageRawHex':raw.hex().upper(),
            'methodSpecIndex':index,'methodSpecRawHex':spec.hex().upper(),
            'methodInstantiation':instance.as_dict(),'windows':windows,
            'level':'exact static original MethodSpec; direct conditional 16-bit-unit consumption',
            'boundary':'The AppendPathInfo call supplies an original AppendFormat MethodSpec with three ordered string-tag arguments, stored as its stack companion. Do not replace that context with arguments inferred from the shared code body. The reviewed body reads the companion at its sixth ABI position; numeric selector branches use the first/second/third value alongside companion+0x38 slots 0/8/16. Actual RGCTX inflation and nested formatter execution are not established. Input scanning reads 16-bit elements at string+0x14+index*2; literal copying advances the temporary cursor by element count. The downstream UnSafeString.Append receives pointer and count, calls a capacity helper, computes signed-extended 32-bit count*2 for an indirect copy target, and advances its stored cursor by the original count. A zero 16-bit terminator is written only if the updated signed cursor is below capacity. Hence the forwarded count is a two-byte-unit count on this path, not a byte length or an unconditional terminator guarantee. Capacity/copy resolver internals, replacement paths, format-item parsing, actual generic dispatch, output validity/length, concrete path and source identity remain unresolved.'}


def vfs_format_item(pe,*,source):
    """Local format-item return ABI; not whole-format or serialized EOF."""
    windows=[]
    for rva,expected in (
        (0x2DF2D39,'488D4DC7448BC3488BD7'),
        (0x2DF2D48,'E8131700000F10008B7018'),
        (0x2DF4468,'418BD8488BFA488BF1'),
        (0x2DF447F,'FFC348636A10'),
        (0x2DF44AF,'0FB75442148D42D06683F809'),
        (0x2DF4515,'4183FE10'),
        (0x2DF4594,'44895E04FFC3'),
        (0x2DF45AC,'448936'),
        (0x2DF45B4,'44897E1C'),
        (0x2DF45BD,'895E180F114608'),
        (0x2DF4639,'488D4F1444895C242C4A8D0C61896C242848894C24200F28442420'),
        (0x4C5DC40,'4183FE100F8C906819FE'),
        (0x4C5DD0E,'41F7DF4533DB')):
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(expected)))
        require(raw,bytes.fromhex(expected),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    return {'windows':windows,'resultByteLength':32,
            'resultRanges':[
                {'offset':0,'length':4,'role':'numeric selector'},
                {'offset':4,'length':4,'role':'zero'},
                {'offset':8,'length':16,'role':'zero or bounded colon-span pointer/count/padding'},
                {'offset':24,'length':4,'role':'index after closing brace'},
                {'offset':28,'length':4,'role':'zero or comma-derived signed numeric value'}],
            'level':'direct conditional native return ABI',
            'boundary':'The caller supplies RCX result storage, RDX format carrier and R8D opening-brace index; the helper returns the same storage in RAX. Main and separate cold fragments were reviewed together. Reads use carrier+0x14 and two-byte indices, with length at +0x10. The numeric selector is decimal accumulated and must be below 16 before proceeding. Normal return writes all 32 result bytes: selector, zero padding, a zero span or nonempty colon-span pointer with count and zero padding, index one past the closing brace, and a comma-derived numeric value (zero when absent). The nonempty span excludes colon and closing brace and checks start/count against carrier length. The caller copies both 16-byte halves and reads result+0x18; this is a local item cursor, not whole-format EOF. Comma parsing invokes an unreviewed character helper; error helper behavior, arbitrary-input validity, string-construction ABI, nested generic formatting and actual execution remain unresolved. No full grammar emulator or runtime output path is asserted.'}


def vfs_path_literals(pe,md,*,source,metadata_source):
    """Exact literal pool intervals plus selected native tag-5 consumers."""
    require(len(md.buf)>=24,True,metadata_source,0)
    row_start,row_size,pool_start,pool_size=struct.unpack_from('<iiii',md.buf,8)
    if not (row_start>=24 and row_size>=0 and row_size%8==0 and row_start<=len(md.buf)
            and row_size<=len(md.buf)-row_start):
        raise ContextError(metadata_source,8,'bounded eight-byte literal row table after header',
                           {'start':row_start,'size':row_size,'fileLength':len(md.buf)})
    if not (pool_start>=row_start+row_size and pool_size>=0 and pool_start<=len(md.buf)
            and pool_size<=len(md.buf)-pool_start):
        raise ContextError(metadata_source,16,'bounded literal pool after row table',
                           {'start':pool_start,'size':pool_size,'rowEnd':row_start+row_size,'fileLength':len(md.buf)})
    count=row_size//8
    require(count<=1_000_000,True,metadata_source,8)
    rows=[literal_record(md.buf[at:at+8],pool_size,source=metadata_source,offset=at)
          for at in range(row_start,row_start+row_size,8)]
    require(pe.bytes_at_va(pe.image_base+0x4139C,4),struct.pack('<I',0x41331),source,0x4139C)
    raw=pe.bytes_at_va(pe.image_base+0x41333,5)
    require(raw,b'\xe8'+struct.pack('<i',0x2D8DE0-0x41333-5),source,0x41333)
    windows=[]
    for rva,expected in ((0x41280,'8BC1C1E81D8BF1D1EE81E6FFFFFF0FFFC8'),
        (0x2D8E1D,'48635008486340104903D0'),
        (0x2D8E2F,'4903C04A634C0204428B14024803C8')):
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(expected)))
        require(raw,bytes.fromhex(expected),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    selected=[]
    for rva,index,expected in ((0x2D7FAB2,48841,b'{0}/{1}/{2}'),
        (0x2D7FB13,48957,b'{0}{1}{2}'),(0x2D7FC9C,48832,b'{0}/{1}'),
        (0x2D7DEEA,48841,b'{0}/{1}/{2}'),(0x2D7E068,48849,b'{0}/{1}{2}'),
        (0x2D7E188,48832,b'{0}/{1}')):
        cell=rip_qword_load_target(pe.bytes_at_va(pe.image_base+rva,7),pe.image_base+rva,source=source)
        usage=pe.bytes_at_va(cell,8)
        actual=unresolved_usage_index(usage,count,tag=5,source=source,offset=cell)
        require(actual,index,source,cell)
        start,length=rows[actual]
        value=md.buf[pool_start+start:pool_start+start+length]
        require(value,expected,metadata_source,pool_start+start)
        selected.append({'rva':rva,'cellVa':cell,'usageRawHex':usage.hex().upper(),
                         'literalIndex':actual,'metadataOffset':pool_start+start,
                         'byteLength':length,'rawHex':value.hex().upper(),'ascii':value.decode('ascii')})
    return {'selected':selected,'windows':windows,
            'literalSweep':{'success':count,'failed':0,'unsupported':0,'rowStart':row_start,
                            'rowByteLength':row_size,'poolStart':pool_start,'poolByteLength':pool_size,
                            'rowsStartLength':rows},
            'level':'exact static literal bytes; direct conditional tag-5 pool-address connection',
            'boundary':'The usage resolver extracts tag and index, and tag 5 selects the literal resolver. Its cache-miss path uses header offsets +8/+16, an eight-byte row stride, row+4 pool-relative offset and row+0 byte length to call the string constructor. All literal rows have bounded pool intervals; aliases and unreferenced pool bytes are allowed, not claimed as an exclusive file partition. Six reviewed path-builder loads join four exact ASCII byte sequences containing braces and slashes. The existing builder windows store these load results into slot zero. These are static format inputs, not demonstrated output paths: cache initialization, string-constructor encoding/ABI, format-item parsing, nested formatter execution, getter values, branch selection and runtime file identity remain unresolved.'}


def audit():
    gate = native_gate()
    corpus_path = ROOT / 'reports/animestudio/skilldata_current_latest.json'
    require(sha(corpus_path), CORPUS_SHA, corpus_path)
    corpus = json.loads(corpus_path.read_text(encoding='utf-8'))
    verify_current_report_inputs(corpus)
    mapper_path = ROOT / 'tools/endfield-il2cpp/map_body_targets_to_gameassembly.py'
    catalog_path = ROOT / 'tools/endfield-il2cpp/catalog_option_flow_metadata.py'
    sources = [Path(__file__), Path(__file__).with_name('il2cpp_context.py'),
               mapper_path, catalog_path, ROOT / 'scripts/common.py']
    source_hashes = {str(p): sha(p) for p in sources}
    mapper = load('context_audit_mapper', mapper_path)
    catalog = load('context_audit_catalog', catalog_path)
    pe = mapper.PeImage(gate.gameassembly)
    md = catalog.Metadata(gate.metadata)
    require(hashlib.sha256(pe.buf).hexdigest().upper(), GA_SHA, gate.gameassembly)
    require(hashlib.sha256(md.buf).hexdigest().upper(), MD_SHA, gate.metadata)
    candidates = mapper.find_code_registration_candidates(pe, {md.string(x.name_index) for x in md.images})
    require(candidates, [0x18A88E640], gate.gameassembly)
    image_owners = type_image_owners(md.buf, len(md.types), source=str(gate.metadata))
    require(pe.u32_at_va(candidates[0]+0x68), len(md.images), gate.gameassembly, candidates[0]+0x68)
    module_pointers = pe.bytes_at_va(pe.u64_at_va(candidates[0]+0x70), len(md.images)*8)
    module_rows = [(pe.c_string_at_va(pe.u64_at_va(pointer)), pointer)
                   for (pointer,) in struct.iter_unpack('<Q', module_pointers)]
    modules = match_image_modules([md.string(item.name_index) for item in md.images],
                                  module_rows, source=str(gate.gameassembly))
    image_rows = []
    module_rgctx_bytes = {}
    rgctx_inventory = []
    for item in md.images:
        name = md.string(item.name_index)
        if name not in modules:
            raise ContextError(str(gate.metadata), item.index, 'matching CodeGenModule name', name)
        image_rows.append({'imageIndex': item.index, 'name': name, 'typeStart': item.type_start,
                           'typeCount': item.type_count, 'moduleVa': modules[name]})
        entry_count=pe.u32_at_va(modules[name]+0x50)
        entry_base=pe.u64_at_va(modules[name]+0x58)
        require(entry_count<=1_000_000,True,gate.gameassembly,modules[name]+0x50)
        entry_bytes=pe.bytes_at_va(entry_base,entry_count*16) if entry_count else b''
        decoded_entries=rgctx_range_entries(entry_bytes,0,entry_count,source=str(gate.gameassembly),offset=entry_base)
        require(len(decoded_entries),entry_count,gate.gameassembly,entry_base)
        module_rgctx_bytes[name]=(entry_base,entry_bytes)
        rgctx_inventory.append({'imageIndex':item.index,'name':name,'entryBaseVa':entry_base,
                                'success':entry_count,'failed':0,'unsupported':0,
                                'sha256':hashlib.sha256(entry_bytes).hexdigest().upper()})
    registration = mapper.find_metadata_registration(pe, candidates[0])
    require(registration, 0x18A88E860, gate.gameassembly)
    for begin, end, expected in CONSUMER_WINDOWS:
        require(hashlib.sha256(pe.bytes_at_va(pe.image_base + begin, end-begin)).hexdigest().upper(),
                expected, gate.gameassembly, begin)
    for rva, prefix, expected in (
        (0x15E4C, '488D0D', candidates[0]),
        (0x15E68, '48890D', pe.image_base+0xDEB09B8),
        (0x12F74, '4C8B15', pe.image_base+0xDEB09B8),
        (0x2C7555, '4C8B1D', pe.image_base+0xDEB09B8),
        (0x37DEADB, '488D0D', pe.image_base+0xCFF4E48),
        (0x37DE8E9, '488B15', pe.image_base+0xCFF4E48),
    ):
        instruction = pe.bytes_at_va(pe.image_base+rva, 7)
        require(instruction[:3].hex().upper(), prefix, gate.gameassembly, rva)
        require(pe.image_base+rva+7+struct.unpack_from('<i', instruction, 3)[0], expected,
                gate.gameassembly, rva)
    reg = mapper.metadata_registration_summary(pe, registration)
    table = GenericInstantiationTable(pe.bytes_at_va, int(reg['genericInsts'], 16),
                                     reg['genericInstsCount'], source=str(gate.gameassembly))
    summary, rows, failures = sweep(table)
    # Explicit raw MethodSpec -> pointer-table join, not an observed invocation.
    spec_index = 516756
    if not 0 <= spec_index < reg['methodSpecsCount']:
        raise ContextError(str(gate.gameassembly), registration, 'bounded MethodSpec index', spec_index)
    spec_va = int(reg['methodSpecs'], 16) + spec_index * 12
    raw = pe.bytes_at_va(spec_va, 12)
    definition, class_inst, method_inst = struct.unpack('<iii', raw)
    require((definition, class_inst, method_inst), (428394, -1, 41928), gate.gameassembly, spec_va)
    selected = table.resolve(method_inst)
    require(len(selected.arguments), 1, gate.gameassembly, selected.record_va)
    type_raw = bytes.fromhex(selected.arguments[0].raw_type_record_hex)
    require(type_raw[10], 0x1E, gate.gameassembly, selected.arguments[0].type_pointer_va)
    owner = method_parameter_owner(md.buf, struct.unpack_from('<Q', type_raw)[0],
                                   [m.generic_container_index for m in md.methods], source=str(gate.metadata))
    require(owner['methodIndex'], 428464, gate.metadata, owner['containerOffset'])
    selected_method_spec={'index':spec_index,'va':spec_va,'rawHex':raw.hex().upper(),
                          'definition':definition,'methodInstantiation':selected.as_dict(),
                          'openMethodParameterOwner':owner}
    usage_va = pe.image_base+0xCFF4E48
    usage_raw = pe.bytes_at_va(usage_va, 8)
    call_index = method_spec_usage_index(usage_raw, reg['methodSpecsCount'],
                                         source=str(gate.gameassembly), offset=usage_va)
    require(call_index, 619889, gate.gameassembly, usage_va)
    # Tag 6 selects table index 5. The pinned branch forwards the original
    # encoding to 2D8D10, whose tag-6 path uses MethodSpec -> triple -> 8D20.
    require(pe.u32_at_va(pe.image_base+0x4138C+5*4), 0x412AC,
            gate.gameassembly, 0x4138C+5*4)
    if not 0 <= call_index < reg['methodSpecsCount']:
        raise ContextError(str(gate.gameassembly), registration, 'bounded call MethodSpec index', call_index)
    call_va = int(reg['methodSpecs'], 16) + call_index * 12
    call_raw = pe.bytes_at_va(call_va, 12)
    call_definition, call_class, call_method = struct.unpack('<iii', call_raw)
    require((call_definition, call_class, call_method), (owner['methodIndex'], -1, 14693),
            gate.gameassembly, call_va)
    call_inst = table.resolve(call_method)
    ordinal = owner['ordinal']
    if not 0 <= ordinal < len(call_inst.arguments):
        raise ContextError(str(gate.gameassembly), call_inst.record_va,
                           'ordinal within selected call instantiation', ordinal)
    argument = call_inst.arguments[ordinal]
    require(argument.raw_type_record_hex, 'B02D0000000000000000120000000000',
            gate.gameassembly, argument.type_pointer_va)
    module = modules['MemoryPack.dll']
    require(pe.u32_at_va(module+0x40), 120, gate.gameassembly, module+0x40)
    require(pe.u32_at_va(module+0x50), 691, gate.gameassembly, module+0x50)
    ranges_va = pe.u64_at_va(module+0x48)
    start, count = select_rgctx_range(pe.bytes_at_va(ranges_va,120*12),691,0x06000075,
                                      source=str(gate.gameassembly),offset=ranges_va)
    require((start,count),(40,3),gate.gameassembly,ranges_va)
    entry_va = pe.u64_at_va(module+0x58)+(start+1)*16
    entry_raw = pe.bytes_at_va(entry_va,16)
    require(struct.unpack_from('<I',entry_raw)[0],2,gate.gameassembly,entry_va)
    type_index = pe.u32_at_va(struct.unpack_from('<Q',entry_raw,8)[0])
    require(type_index,211958,gate.gameassembly,entry_va)
    require(type_index<reg['typesCount'],True,gate.gameassembly,entry_va)
    type_pointer = pe.u64_at_va(int(reg['types'],16)+type_index*8)
    formatter_type_raw = pe.bytes_at_va(type_pointer,16)
    carrier_raw = pe.bytes_at_va(struct.unpack_from('<Q',formatter_type_raw)[0],32)
    base_raw = pe.bytes_at_va(struct.unpack_from('<Q',carrier_raw)[0],16)
    formatter_carrier = generic_type_carrier(formatter_type_raw,carrier_raw,base_raw,
                                             type_pointer=type_pointer,type_count=len(md.types),source=str(gate.gameassembly))
    formatter_inst = table.resolve_pointer(formatter_carrier['classInstantiationPointerVa'])
    require(formatter_inst.index, selected.index, gate.gameassembly,formatter_inst.record_va)
    require(formatter_carrier['baseDefinitionIndex'],54005,gate.metadata)
    require(md.type_full_name(md.types[54005]),'MemoryPack.MemoryPackFormatter`1',gate.metadata)
    require(pe.u32_at_va(pe.image_base+0x9850+(0x15-0xF)*4),0x979D,gate.gameassembly,0x9850)
    # Static immediate-registration site: identity joins only, not live state.
    adapter_cells = []
    for rva, opcode, tag, expected_index in (
            (0x2B00F2B, '488B0D', 1, 205127),
            (0x2B00F4C, '488B15', 6, 559804),
            (0x2B00F60, '488B05', 2, 120613),
            (0xB2830, '488B15', 6, 559804)):
        instruction = pe.bytes_at_va(pe.image_base+rva, 7)
        require(instruction[:3], bytes.fromhex(opcode), gate.gameassembly, rva)
        cell = rip_qword_load_target(instruction,pe.image_base+rva,source=str(gate.gameassembly))
        cell_raw = pe.bytes_at_va(cell, 8)
        index = unresolved_usage_index(cell_raw, reg['methodSpecsCount'] if tag == 6 else reg['typesCount'],
                                       tag=tag, source=str(gate.gameassembly), offset=cell)
        require(index, expected_index, gate.gameassembly, cell)
        adapter_cells.append({'instructionRva':rva, 'instructionHex':instruction.hex().upper(),
                              'cellVa':cell, 'rawHex':cell_raw.hex().upper(), 'tag':tag, 'index':index})
    require(adapter_cells[1]['cellVa'], adapter_cells[3]['cellVa'], gate.gameassembly)
    adapter_pointer = pe.u64_at_va(int(reg['types'],16)+205127*8)
    adapter_raw = pe.bytes_at_va(adapter_pointer,16)
    adapter_carrier_raw = pe.bytes_at_va(struct.unpack_from('<Q',adapter_raw)[0],32)
    adapter_base_raw = pe.bytes_at_va(struct.unpack_from('<Q',adapter_carrier_raw)[0],16)
    adapter = generic_type_carrier(adapter_raw,adapter_carrier_raw,adapter_base_raw,
                                   type_pointer=adapter_pointer,type_count=len(md.types),source=str(gate.gameassembly))
    require(adapter['baseDefinitionIndex'],13633,gate.metadata)
    require(md.type_full_name(md.types[13633]),'Beyond.MemoryPack.GenericMemoryPackFormatter`2',gate.metadata)
    adapter_inst = table.resolve_pointer(adapter['classInstantiationPointerVa'])
    require(adapter_inst.index,38555,gate.gameassembly)
    require(len(adapter_inst.arguments),2,gate.gameassembly)
    adapter_module=modules['MemoryPack.Beyond.dll']
    require(image_owners[13633],1,gate.metadata)
    require(md.types[13633].token,0x0200000B,gate.metadata)
    require(pe.u32_at_va(adapter_module+0x40),5,gate.gameassembly,adapter_module+0x40)
    adapter_ranges=pe.u64_at_va(adapter_module+0x48)
    adapter_entry_base,adapter_entry_bytes=module_rgctx_bytes['MemoryPack.Beyond.dll']
    adapter_start,adapter_count=select_rgctx_range(pe.bytes_at_va(adapter_ranges,5*12),len(adapter_entry_bytes)//16,
                                                   md.types[13633].token,source=str(gate.gameassembly),offset=adapter_ranges)
    require((adapter_start,adapter_count),(4,13),gate.gameassembly,adapter_ranges)
    adapter_entries=rgctx_range_entries(adapter_entry_bytes,adapter_start,adapter_count,
                                        source=str(gate.gameassembly),offset=adapter_entry_base)
    type_slot=adapter_entries[10]
    require(pe.bytes_at_va(pe.image_base+0x2DA8E66,15),bytes.fromhex('488B4320488B98C0000000488B5B50'),
            gate.gameassembly,0x2DA8E66)
    require(type_slot['kindRaw'],1,gate.gameassembly,type_slot['entryVa'])
    slot_type_index=pe.u32_at_va(type_slot['dataPointerVa'])
    require(slot_type_index,10486,gate.gameassembly,type_slot['dataPointerVa'])
    require(slot_type_index<reg['typesCount'],True,gate.gameassembly,type_slot['dataPointerVa'])
    slot_type_pointer=pe.u64_at_va(int(reg['types'],16)+slot_type_index*8)
    slot_type_raw=pe.bytes_at_va(slot_type_pointer,16)
    require(slot_type_raw[10],0x13,gate.gameassembly,slot_type_pointer+10)
    slot_owner=type_parameter_owner(md.buf,struct.unpack_from('<Q',slot_type_raw)[0],
                                    [t.generic_container_index for t in md.types],source=str(gate.metadata))
    require((slot_owner['typeIndex'],slot_owner['ordinal']),(13633,1),gate.metadata,slot_owner['containerOffset'])
    require(pe.u32_at_va(pe.image_base+0x9850+(0x13-0x0F)*4),0x9669,gate.gameassembly,0x9850)
    slot_argument=adapter_inst.arguments[slot_owner['ordinal']]
    nested_slots=[]
    for relative,expected_definition in ((3,102198),(4,428394),(11,277939)):
        entry=adapter_entries[relative]
        require(entry['kindRaw'],3,gate.gameassembly,entry['entryVa'])
        index=pe.u32_at_va(entry['dataPointerVa'])
        require(index<reg['methodSpecsCount'],True,gate.gameassembly,entry['dataPointerVa'])
        spec_va=int(reg['methodSpecs'],16)+index*12
        spec_raw=pe.bytes_at_va(spec_va,12)
        definition,ci,mi=method_spec_record(spec_raw,len(md.methods),reg['genericInstsCount'],
                                           source=str(gate.gameassembly),offset=spec_va)
        require(definition,expected_definition,gate.metadata)
        contexts=[]
        for kind,inst_index in (('class',ci),('method',mi)):
            inst=table.resolve(inst_index)
            arguments=[]
            for arg in inst.arguments:
                raw=bytes.fromhex(arg.raw_type_record_hex)
                require(raw[10],0x13,gate.gameassembly,arg.type_pointer_va+10)
                owner=type_parameter_owner(md.buf,struct.unpack_from('<Q',raw)[0],
                                            [t.generic_container_index for t in md.types],source=str(gate.metadata))
                require(owner['typeIndex'],13633,gate.metadata,owner['containerOffset'])
                require(owner['ordinal']<len(adapter_inst.arguments),True,gate.metadata,owner['parameterOffset'])
                concrete=adapter_inst.arguments[owner['ordinal']]
                arguments.append({'rawHex':arg.raw_type_record_hex,'owner':owner,
                                  'conditionalArgumentRawHex':concrete.raw_type_record_hex})
            contexts.append({'kind':kind,'instantiationIndex':inst_index,'arguments':arguments})
        nested_slots.append({'relativeIndex':relative,'moduleEntryIndex':entry['moduleEntryIndex'],
                             'methodSpecIndex':index,'methodSpecRawHex':spec_raw.hex().upper(),
                             'definition':definition,'methodName':md.string(md.methods[definition].name_index),'contexts':contexts})
    require(pe.bytes_at_va(pe.image_base+0x8619,4),bytes.fromhex('48895F20'),gate.gameassembly,0x8619)
    require(pe.bytes_at_va(pe.image_base+0x873E,17),bytes.fromhex('4D8D442408498BD5488D4DD8E8D1470300'),
            gate.gameassembly,0x873E)
    require([a.raw_type_record_hex for a in adapter_inst.arguments],
            ['B02D0000000000000000120000000000','2D360000000000000000120000000000'],gate.gameassembly)
    require(md.type_full_name(md.types[13869]),'Beyond.MemoryPack.Beyond_Gameplay_Core_GameplayTagListForMemoryPack',gate.metadata)
    key_pointer = pe.u64_at_va(int(reg['types'],16)+120613*8)
    require(key_pointer,adapter_inst.arguments[0].type_pointer_va,gate.gameassembly)
    ctor_va = int(reg['methodSpecs'],16)+559804*12
    ctor_raw = pe.bytes_at_va(ctor_va,12)
    require(struct.unpack('<iii',ctor_raw),(102200,38555,-1),gate.gameassembly,ctor_va)
    require(md.methods[102200].declaring_type,13633,gate.metadata)
    require(md.string(md.methods[102200].name_index),'.ctor',gate.metadata)
    require(pe.bytes_at_va(pe.image_base+0x867C0,5),bytes.fromhex('E99BAAFBFF'),gate.gameassembly,0x867C0)
    require(pe.bytes_at_va(pe.image_base+0xB2837,5),bytes.fromhex('E9741DFD03'),gate.gameassembly,0xB2837)
    storage_references = []
    for rva in (0x3800409,0x2DA4806,0x2DA49F5,0x2DA4C42):
        instruction = pe.bytes_at_va(pe.image_base+rva,7)
        target = rip_qword_load_target(instruction,pe.image_base+rva,source=str(gate.gameassembly))
        require(target,pe.image_base+0xD0EF5F0,gate.gameassembly,rva)
        storage_references.append({'instructionRva':rva,'instructionHex':instruction.hex().upper(),'targetVa':target})
    storage_raw = pe.bytes_at_va(storage_references[0]['targetVa'],8)
    sharing_instruction = pe.bytes_at_va(pe.image_base+0x2C6DE0,7)
    sharing_global = class_sharing_branch(pe.bytes_at_va(pe.image_base+0x2C6CA9,10),pe.image_base+0x2C6CA9,
                                          sharing_instruction,pe.image_base+0x2C6DE0,
                                          pe.bytes_at_va(pe.image_base+0x2C6DE7,4),source=str(gate.gameassembly))
    require(sharing_global,pe.image_base+0xDE9F470,gate.gameassembly,0x2C6DE0)
    require([bytes.fromhex(a.raw_type_record_hex)[10] for a in adapter_inst.arguments],[0x12,0x12],gate.gameassembly)
    object_identity = named_top_level_type(md.buf,b'mscorlib.dll',b'System',b'Object',source=str(gate.metadata))
    require((object_identity['imageIndex'],object_identity['typeDefinitionIndex'],object_identity['byvalTypeIndex']),
            (6,36358,133396),gate.metadata,object_identity['typeDefinitionOffset'])
    require(object_identity['byvalTypeIndex']<reg['typesCount'],True,gate.metadata)
    object_pointer=pe.u64_at_va(int(reg['types'],16)+object_identity['byvalTypeIndex']*8)
    object_raw=pe.bytes_at_va(object_pointer,16)
    require(object_raw.hex().upper(),'068E00000000000000001C0000000000',gate.gameassembly,object_pointer)
    object_pair=table.resolve(1088)
    require([a.raw_type_record_hex for a in object_pair.arguments],[object_raw.hex().upper()]*2,gate.gameassembly)
    # The code window ends before this separately read switch-data entry.
    switch_entry=pe.image_base+0x2CC87C+(0x1C-0x0F)*4
    require(pe.u32_at_va(switch_entry),0x2CC840,gate.gameassembly,switch_entry)
    object_key=object_type_comparison_key(object_raw,source=str(gate.gameassembly),offset=object_pointer)
    require(summary['failed'],0,'complete generic-instantiation sweep before candidate enumeration')
    object_candidates=[]
    for row in rows:
        arguments=row['arguments']
        if len(arguments)!=2:
            continue
        raw_arguments=[bytes.fromhex(a['raw_type_record_hex']) for a in arguments]
        if any(raw[10]!=0x1C for raw in raw_arguments):
            continue
        keys=[object_type_comparison_key(raw,source=str(gate.gameassembly),offset=a['type_pointer_va'])
              for raw,a in zip(raw_arguments,arguments)]
        if keys==[object_key,object_key]:
            object_candidates.append(row['index'])
    require(md.methods[102199].declaring_type,13633,gate.metadata)
    require(md.string(md.methods[102199].name_index),'Deserialize',gate.metadata)
    specs_base=int(reg['methodSpecs'],16)
    specs_raw=pe.bytes_at_va(specs_base,reg['methodSpecsCount']*12)
    spec_records=[method_spec_record(specs_raw[index*12:(index+1)*12],len(md.methods),reg['genericInstsCount'],
                                     source=str(gate.gameassembly),offset=specs_base+index*12)
                  for index in range(reg['methodSpecsCount'])]
    validate_selected_method_spec(selected_method_spec,specs_raw,specs_base,len(md.methods),
                                   reg['genericInstsCount'],source=str(gate.gameassembly))
    shared_specs=[index for index,(definition,ci,mi) in enumerate(spec_records)
                  if definition==102199 and ci in object_candidates and mi==-1]
    code=mapper.code_registration_summary(pe,candidates[0])
    methods_base=int(reg['genericMethodTable'],16)
    methods_raw=pe.bytes_at_va(methods_base,reg['genericMethodTableCount']*16)
    shared_rows=[]
    for index,(spec_index,_,_,_) in enumerate(struct.iter_unpack('<iiii',methods_raw)):
        if spec_index not in shared_specs:
            continue
        triple_raw=methods_raw[index*16+4:index*16+16]
        method,invoker,adjustor=method_pointer_indices(triple_raw,code['genericMethodPointersCount'],
                                                       code['invokerPointersCount'],source=str(gate.gameassembly),
                                                       offset=methods_base+index*16+4)
        pointer=pe.u64_at_va(int(code['genericMethodPointers'],16)+method*8)
        invoker_pointer=pe.u64_at_va(int(code['invokerPointers'],16)+invoker*8)
        require(pointer!=0 and invoker_pointer!=0,True,gate.gameassembly,methods_base+index*16)
        shared_rows.append({'tableIndex':index,'methodSpecIndex':spec_index,
                            'indices':[method,invoker,adjustor],'indicesRawHex':triple_raw.hex().upper(),
                            'methodPointerVa':pointer,'invokerPointerVa':invoker_pointer})
    producer_names=[]
    for rva,prefix,expected in ((0x15F0D,'488D0D',b'mscorlib.dll'),
                               (0x15F3C,'4C8D05',b'Object'),(0x15F43,'488D15',b'System')):
        instruction=pe.bytes_at_va(pe.image_base+rva,7)
        require(instruction[:3],bytes.fromhex(prefix),gate.gameassembly,rva)
        pointer=pe.image_base+rva+7+struct.unpack_from('<i',instruction,3)[0]
        require(pe.bytes_at_va(pointer,len(expected)+1),expected+b'\0',gate.gameassembly,pointer)
        producer_names.append({'instructionRva':rva,'stringVa':pointer,'ascii':expected.decode('ascii')})
    require(pe.bytes_at_va(pe.image_base+0x15F4F,7),bytes.fromhex('4889051A95E80D'),gate.gameassembly,0x15F4F)
    # Independently connect the registration producer to the cache seeding loop.
    # These are reviewed instruction boundaries inside the pinned consumers.
    producer=pe.bytes_at_va(pe.image_base+0x15E5A,7)
    require(producer[:3],bytes.fromhex('488D05'),gate.gameassembly,0x15E5A)
    require(pe.image_base+0x15E61+struct.unpack_from('<i',producer,3)[0],registration,gate.gameassembly,0x15E5A)
    require(pe.bytes_at_va(pe.image_base+0x15E6F,7),bytes.fromhex('4889054AABE90D'),gate.gameassembly,0x15E6F)
    seed_global=rip_qword_load_target(pe.bytes_at_va(pe.image_base+0x12D70,7),pe.image_base+0x12D70,source=str(gate.gameassembly))
    require(seed_global,pe.image_base+0xDEB09C0,gate.gameassembly,0x12D70)
    cache_storage=[]
    for rva in (0x9D16,0x13248):
        target=rip_qword_load_target(pe.bytes_at_va(pe.image_base+rva,7),pe.image_base+rva,source=str(gate.gameassembly))
        require(target,pe.image_base+0xDEB0568,gate.gameassembly,rva)
        cache_storage.append({'instructionRva':rva,'storageGlobalVa':target})
    return_evidence=serializer_return_consumers(pe,source=str(gate.gameassembly))
    return_evidence['methodIdentities']=module_methods(pe,md,modules,image_owners,
        [(428657,'MemoryPack.MemoryPackSerializer','Deserialize',0x970BFBC),
         (428658,'MemoryPack.MemoryPackSerializer','Deserialize',0x970C4A8),
         (428655,'MemoryPack.MemoryPackSerializer','Deserialize',0x970BFF0),
         (428667,'MemoryPack.MemoryPackSerializer+<DeserializeAsync>d__11','MoveNext',0x9711078)],
        source=str(gate.gameassembly))
    construction_evidence=reader_construction(pe,md,modules,image_owners,source=str(gate.gameassembly))
    cursor_evidence=reader_cursor_consumers(pe,source=str(gate.gameassembly))
    wrapper_evidence=wrapper_consumer(pe,md,reg,table,source=str(gate.gameassembly))
    resource_evidence=skill_resource_context(pe,md,modules,image_owners,table,reg,code,
        spec_records,specs_raw,methods_raw,source=str(gate.gameassembly))
    carrier_evidence=resource_carrier_consumers(pe,source=str(gate.gameassembly))
    stream_identity=stream_source_identity(pe,md,modules,image_owners,reg,code,spec_records,methods_raw,source=str(gate.gameassembly))
    stream_consumer=stream_carrier_consumer(pe,source=str(gate.gameassembly))
    vfs_identity=vfs_stream_identity(pe,md,modules,image_owners,reg,source=str(gate.gameassembly))
    vfs_consumer=vfs_stream_consumer(pe,source=str(gate.gameassembly))
    file_open=file_stream_open(pe,md,modules,image_owners,reg,source=str(gate.gameassembly))
    descriptor_path=vfs_descriptor_path(pe,md,modules,image_owners,source=str(gate.gameassembly))
    descriptor_producer=vfs_descriptor_producer(pe,md,modules,image_owners,reg,table,source=str(gate.gameassembly))
    bytebuf_consumer=vfs_bytebuf_consumer(pe,md,modules,image_owners,reg,source=str(gate.gameassembly))
    block_cursor=vfs_block_cursor(pe,md,modules,image_owners,source=str(gate.gameassembly))
    block_transform=vfs_block_transform(pe,md,modules,image_owners,source=str(gate.gameassembly))
    block_file_source=vfs_block_file_source(pe,md,modules,image_owners,source=str(gate.gameassembly))
    file_read=native_file_read(pe,md,modules,image_owners,source=str(gate.gameassembly))
    path_carrier=vfs_path_carrier(pe,md,modules,image_owners,source=str(gate.gameassembly))
    path_format=vfs_path_format_context(pe,md,modules,image_owners,reg,table,source=str(gate.gameassembly))
    path_literals=vfs_path_literals(pe,md,source=str(gate.gameassembly),metadata_source=str(gate.metadata))
    format_item=vfs_format_item(pe,source=str(gate.gameassembly))
    native_gate()
    require(sha(corpus_path), CORPUS_SHA, corpus_path)
    verify_current_report_inputs(corpus)
    for path, expected in source_hashes.items():
        require(sha(path), expected, path)
    return {
        'schemaVersion': 1, 'status': 'failed' if failures else 'structural-only',
        'inputSetSha256': corpus['inputSetSha256'],
        'corpusReference': {'path': str(corpus_path), 'sha256': CORPUS_SHA,
                            'boundary': 'Authenticated corpus reference; this native audit does not restream VFS bytes.'},
        'nativeInputs': {'gameassembly': str(gate.gameassembly), 'gameassemblySha256': GA_SHA,
                         'metadata': str(gate.metadata), 'metadataSha256': MD_SHA},
        'sourceHashes': source_hashes, 'registration': reg,
        'methodSpecSweep':{'success':len(spec_records),'failed':0,'unsupported':0,
                           'sourceVa':specs_base,'byteLength':len(specs_raw),
                           'sha256':hashlib.sha256(specs_raw).hexdigest().upper(),
                           'boundary':'All referenced 12-byte MethodSpecs have bounded definition and class/method instantiation indices. This is not runtime inflation or whole-PE EOF.'},
        'selectedSerializerReturnConsumers':return_evidence,
        'selectedSkillResourceContext':resource_evidence,
        'selectedResourceCarrierConsumers':carrier_evidence,
        'selectedStreamSourceIdentity':stream_identity,
        'selectedStreamCarrierConsumer':stream_consumer,
        'selectedVfsStreamIdentity':vfs_identity,
        'selectedVfsStreamConsumer':vfs_consumer,
        'selectedFileStreamOpen':file_open,
        'selectedVfsDescriptorPath':descriptor_path,
        'selectedVfsDescriptorProducer':descriptor_producer,
        'selectedVfsByteBufConsumer':bytebuf_consumer,
        'selectedVfsBlockCursor':block_cursor,
        'selectedVfsBlockTransform':block_transform,
        'selectedVfsBlockFileSource':block_file_source,
        'selectedNativeFileRead':file_read,
        'selectedVfsPathCarrier':path_carrier,
        'selectedVfsPathFormatContext':path_format,
        'selectedVfsPathLiterals':path_literals,
        'selectedVfsFormatItem':format_item,
        'selectedReaderConstruction':construction_evidence,
        'selectedReaderCursorConsumers':cursor_evidence,
        'selectedWrapperConsumer':wrapper_evidence,
        'selectedNestedAdapterSlots':{'rows':nested_slots,'level':'exact static MethodSpec/VAR relation',
                                      'boundary':'Relative slots 3, 4 and 11 independently join DeserializeNotNull<T0,T1>, GetFormatter<T1> and CreateInstance<T1>. Every VAR reciprocally belongs to the adapter type; conditional concrete arguments come from the separately authenticated immediate registration. Method names do not establish serialization order, actual nested dispatch or source cursor.'},
        'selectedMethodCompanionConstruction': {'lookupRva':0x8D20,'constructorRva':0x84B0,
                                                 'classStoreRva':0x8619,'methodPointerResolverCallRva':0x874A,
                                                 'classFieldOffset':0x20,'pointerFieldOffsets':[0,8,16],
                                                 'level':'direct conditional native construction path',
                                                 'boundary':'On the reviewed cache-miss construction path, the original definition class and class-instantiation feed the generic-class carrier lookup/construction, then the class pointer is stored at MethodInfo+0x20. The pointer resolver receives the original definition and context pair separately, writes a stack result, and its code/adjustor/invoker pointers are copied to MethodInfo+0/+8/+0x10. Normalizing arguments for a shared code lookup therefore does not itself replace the already stored original class pointer. This is not a live MethodInfo receipt, proof of cache contents, actual target invocation, source extent or EOF.'},
        'rgctxDefinitionSweep': {'images':rgctx_inventory,
                                  'summary':{'success':sum(x['success'] for x in rgctx_inventory),'failed':0,'unsupported':0},
                                  'boundary':'Exact referenced 16-byte definitions for every matched module; numeric kinds, padding and payload pointers are preserved, not resolved runtime slots or a partition of the PE.'},
        'selectedAdapterClassSlot': {'typeDefinition':13633,'token':md.types[13633].token,
                                     'rangeStart':adapter_start,'rangeCount':adapter_count,'entries':adapter_entries,
                                     'selectedRelativeIndex':10,'selectedModuleEntryIndex':type_slot['moduleEntryIndex'],
                                     'consumerRva':0x2DA8E66,'runtimeSlotByteOffset':0x50,
                                     'typeIndex':slot_type_index,'typePointerVa':slot_type_pointer,
                                     'typeRawHex':slot_type_raw.hex().upper(),'parameterOwner':slot_owner,
                                     'conditionalContextArgument':{'pointerVa':slot_argument.type_pointer_va,'rawHex':slot_argument.raw_type_record_hex},
                                     'level':'exact static slot/VAR identity; direct conditional class-context connection',
                                     'boundary':'The class initializer reads class+0x118 token and image+0x38 module, uses 12-byte token ranges and 16-byte definitions, emits eight-byte slots at class+0xC0, and supplies generic-carrier+8 context to substitution. Relative slot 10 is module entry 14, kind 1, a reciprocal ordinal-1 VAR of the adapter type. The VAR branch uses the class instantiation, whose second argument at the immediate registration is the wrapper type. This does not certify initialized class contents, actual method companion, formatter cache selection, source length or EOF.'},
        'selectedSharedMethodCandidates': {'definition':102199,'methodSpecIndices':shared_specs,
                                           'rows':shared_rows,'level':'exact static table relation; conditional index consumer',
                                           'boundary':'All matching MethodSpecs and generic-method table rows are preserved. The separately pinned index reader checks method/invoker indices, loads their pointer slots, and with adjustor -1 reuses the method pointer. Non-sentinel adjustors remain unsupported by this bounded decoder. This does not certify the runtime triple-map population, query success, target invocation, actual reader ABI, source length or final cursor.'},
        'selectedObjectComparison': {'key':object_key,'matchingRegisteredInstantiations':object_candidates,
                                     'switchEntryVa':switch_entry,'switchTargetRva':0x2CC840,
                                     'level':'direct conditional native equality/hash projection',
                                     'boundary':'For object-tag records the reviewed comparator checks the tag and bit 29 of the word at +8, then returns equal; the reviewed hash branch depends on those same two values. Record addresses and other bytes do not participate in this branch. The complete registered-instance sweep enumerates every matching two-argument candidate without selecting one. Even a singleton does not prove cache execution, returned interned pointer, method lookup success, active formatter or file cursor.'},
        'selectedInstantiationCacheSeed': {'registrationGlobalVa':seed_global,
                                          'seedCallRva':0x12D8B,'insertRva':0x13170,
                                          'lookupRva':0x9C70,'storageReferences':cache_storage,
                                          'level':'direct conditional native producer/consumer connection',
                                          'boundary':'The initializer stores the selected MetadataRegistration and calls the seed routine. Its normal loop reads count+0x10 and pointer-table+0x18, passes each eight-byte slot to insertion, and insertion dereferences that slot to a record pointer. Insertion and lookup access the identical cache storage global and compare argument counts plus native type comparisons. This establishes a static registration-to-cache seed path, not successful initialization, cold-path completion, actual cache contents, interned pointer selection or active formatter dispatch.'},
        'selectedObjectIdentity': {'metadata':object_identity,'producerNames':producer_names,
                                   'registeredTypePointerVa':object_pointer,'rawTypeHex':object_raw.hex().upper(),
                                   'objectPairInstantiation':object_pair.as_dict(),
                                   'level':'exact static identity; direct conditional producer/class-copy connection',
                                   'boundary':'The initializer supplies mscorlib.dll/System/Object to the lookup chain and stores its return in the sharing global. Name-cache construction uses metadata namespace/name and lookup compares both strings, not only hashes. The matched TypeDef reaches the class cache; the miss constructor copies the registered byval type record to class+0x20. This links the normal producer to System.Object record bytes and the static object/object candidate pair. Runtime image/name/class-cache population, initialization execution and interned pointer identity remain unobserved; no active Deserialize or file-cursor selection follows.'},
        'selectedSharingBranch': {'argumentTags':[0x12,0x12], 'normalizerRva':0x2C6C10,
                                  'canonicalCarrierGlobalVa':sharing_global,'carrierTypeOffset':0x20,
                                  'level':'direct conditional native branch; producer identity recorded separately',
                                  'boundary':'On an original-context lookup miss, the reviewed method-pointer resolver transforms class and method argument vectors and retries the triple lookup. Each non-null class-tag argument directly becomes the same global carrier+0x20, preserving vector order/count before interning. The normal producer links to System.Object bytes, but initialization execution, interned vector identity, lookup-table population, cold paths and actual invocation are not established; this does not select the object/object Deserialize candidate. The normalizer code ends before its separately located eight-dword switch table.'},
        'selectedProviderStorage': {'references':storage_references,'cellRawHex':storage_raw.hex().upper(),
                                    'level':'direct conditional consumer connection',
                                    'boundary':'Registration and GetFormatter read the identical RIP cell, then class+0xB8 and static-carrier+0x18. Direct lookup traverses that storage and returns a matched node+0x18 through the local result slot. A miss can invoke lazy callbacks, retry lookup, or construct and register other values. Static storage identity does not establish live contents, comparer results, initialization/replacement history or selected adapter dispatch.'},
        'selectedImmediateAdapter': {'cells':adapter_cells, 'typeCarrier':adapter,
                                    'argumentTypeNames':['Beyond.Gameplay.Core.GameplayTagList','Beyond.MemoryPack.Beyond_Gameplay_Core_GameplayTagListForMemoryPack'],
                                    'classInstantiation':adapter_inst.as_dict(),
                                    'constructorMethodSpecVa':ctor_va,'constructorRawHex':ctor_raw.hex().upper(),
                                    'level':'exact static identity; direct conditional registration callsite',
                                    'boundary':'The type carrier and constructor share the ordered Core/ForMemoryPack instance, and the Core key uses the identical registered type pointer. The reviewed callsite passes the constructed-object stack slot and type-derived key to a registration function which forwards them to static-carrier+0x18 storage. This does not establish execution, allocation/constructor ABI completion, live cache selection, adapter Deserialize dispatch, source length or final cursor.'},
        'selectedFormatterTypeCarrier': {**formatter_carrier,'rgctxEntryVa':entry_va,
                                         'rgctxEntryRawHex':entry_raw.hex().upper(),
                                         'classInstantiationIndex':formatter_inst.index,
                                         'baseName':md.type_full_name(md.types[54005]),
                                         'boundary':'Exact static pointer/range/MVAR identity; the 32-byte carrier window is not a certified allocation extent and its last 16 bytes remain opaque. Native generic inflation iterates the class-inst arguments using the supplied context. This is the open formatter check type, not the active formatter object or proof that runtime inflation/caches executed.'},
        'selectedUsageCell': {'va': usage_va, 'rawHex': usage_raw.hex().upper(),
                              'methodSpecIndex': call_index, 'resolverSwitchEntryRva': 0x4138C+5*4,
                              'boundary': 'Direct static initialization mechanism: the guarded wrapper passes this cell address to the lazy resolver; tag 6 routes through MethodSpec/triple lookup and a non-null result is exchanged into the cell. The callsite reads the same cell. Initialization execution, cache history, active formatter and source cursor remain unobserved.'},
        'staticImageOwnership': {'typeCount': len(image_owners), 'images': image_rows,
                                 'selectedReadValueImage': image_owners[md.methods[428464].declaring_type],
                                 'registrationGlobalRva': 0xDEB09B8,
                                 'matchingRule': 'Native bytewise name matching continues after a match; duplicate names could overwrite a prior result. This gate requires unique module names before accepting a static join.',
                                 'boundary': 'Exact metadata type partition and unique module-name joins. Native normal-path directory stores and name comparisons are separately pinned; initialization execution, cold paths and live invocation remain unobserved.'},
        'consumerWindows': CONSUMER_WINDOWS, 'summary': summary,
        'selectedMethodSpec': selected_method_spec,
        'selectedCallMethodSpec': {'index': call_index, 'va': call_va, 'rawHex': call_raw.hex().upper(),
                                   'methodInstantiation': call_inst.as_dict()},
        'conditionalSubstitution': {
            'ordinal': ordinal, 'selectedRawArgument': argument.raw_type_record_hex,
            'level': 'exact static joins; conditional runtime application',
            'boundary': 'The open parameter belongs to the selected call definition and its ordinal indexes this registered argument. The native leaf applies that ordinal to its supplied live context. This report does not establish that the actual invocation supplies this context.'},
        'boundary': 'Pointer array -> 16-byte record -> argument pointer array -> raw 16-byte type records only. No live generic context, formatter, field order, source cursor or EOF claim.',
        'failures': failures, 'rows': rows,
    }


def main():
    try:
        report = audit()
    except (ContextError, OSError, ValueError) as error:
        print(json.dumps({'status': 'failed', 'diagnostic': getattr(error, 'diagnostics', getattr(error, 'diagnostic', str(error)))}), file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False))
    return int(report['status'] == 'failed')


if __name__ == '__main__':
    raise SystemExit(main())
