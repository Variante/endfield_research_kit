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
from scripts.game_data.memorypack.corpus_gate import verify_current_report_inputs as verify_family_report_inputs
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
UNITY_SHA = 'BEE7BE52370ADDDD67BA61E4937CA51B7F272656841D187E95E505496DA798D1'
CORPUS_SHA = '65A47A978D282ED6C65C7EDE545C7464AC7765FD25249C27DFABB2380A337B75'
CONSUMER_WINDOWS = (
    (0x3F7FD20,0x3F7FD7D,'B5AB987DB105917F14B247D7B4448C44A4408CC6DB8280D221EBB21FC67D413B'),
    (0x3F7FD80,0x3F7FF19,'632D05A4F810BF260BFED357E3E80375DD943FFD926FC514382054E0DF2AFCEF'),
    (0x3D9BAF0,0x3D9BB4D,'7C7BF6A31C88EA2D1D2925193F774396233F35465E56AFBAC2DFC756B3C2599D'),
    (0x3D9BB50,0x3D9BCC5,'83DB6041548B27BB2CCE4E6DB6AD2803F3CFDDE712B2E07D02CA6D2127BDC05A'),
    (0x2CA8860,0x2CA88B7,'CA6788FE028DC684758CD40833EFA107116A7BF664BFBF1746D792E52114639F'),
    (0x2CA8700,0x2CA87C6,'B8944001C41E1AF65B44F7DDE366FCE5E4E8B35E2A32682E628C2E0A36145BEF'),
    (0x2CA8A10,0x2CA8AFD,'A839E67CFE09CC6BF53DA3BE9E149AEF9B411E9AA20D23C981A94C18C13678BC'),
    (0x39C6A40,0x39C6A9D,'650BBFFE813D1F3A7663C6C9C42E160E5799B70541246A11AAADABF1D3F08DD6'),
    (0x39C6AA0,0x39C6FA7,'6444AF67AF86E7809AF5A50AE6DEE922B699DCB1CA686DC81F4C3584AB817B90'),
    (0x3773670,0x37736CD,'D1E00A92152340C6A1F095DC4FF14393C99973AED0304478AD12506492E37A0C'),
    (0x3774060,0x37742A8,'AC1FF978FEF71639E74980B43AE00D9746518A9DD94B41772F2867963A596ED8'),
    (0x2CA88C0,0x2CA8912,'636D6E913965572E9F43C20D0BBA78706400327D19134D1EF6C71FB5DE6B397E'),
    (0x2CA86B0,0x2CA8700,'2358C208F5DDD372AF9E5401907272C1FB2A6E4C49E211689FFC047A2872BB65'),
    (0x3915318,0x3915998,'39C3FD3F0D261441F1790310D4D15455F09C4B0FD422E7810BA01A4C80D93189'),
    (0x390D880,0x390D949,'886BE1DB0B85A14E60725049F3358D0108A316A77762E9825E15BDEF42CF4C52'),
    (0xF8040,0xF8054,'6FAAAFEA02FCA6BE80BF3AB5DFD579015CCC2E16E4184E44799B89A328054879'),
    (0x2DA4260,0x2DA4713,'BCF62513ABA710E9AB67DBFDA036EFE7CEC127E1CADFB21E16530E168D2EBE02'),
    (0x4AF13B8,0x4AF14EB,'61FE687029897D01C5F5D0283742BCAB565002A11914EA01B54FBD87F2192D04'),
    (0x2DA4770,0x2DA4D6B,'4D521FFBEB8FADA0965B6F8DCD9BAE153964F3D5BAF7E22A199509C24867BD0D'),
    (0x2DF760,0x2DF827,'BB25B7DF06BAB2DBC8B2D54FB1DF15E7B5CB1E9EDCB553B06A82DDE63998F27D'),
    (0x1F0A0,0x1F0F8,'C9F38013332566AD167609C71B8F69552B51A2C45D2CEA1FDD23F35A5E62C727'),
    (0x2DF840,0x2DF8D0,'2D2C7C970E0E0DD329559040D4D6D0EEABAC001A756EDE943F1F05674FC7029B'),
    (0x248D0,0x249AC,'444E365BB37D609DD9797249C52EFC2BB7C0C81A41446EC74418B8DF509CA026'),
    (0x23970,0x23A01,'80D05BC4EB99B2FA602AEFA2B958A59BCBE6DC305730DEAC6B9985D636997060'),
    (0x22010,0x220F8,'1E01E4A3A3DC36DBAF211D51E1D536B33242F17305D82026070B610A5D901C04'),
    (0xE170,0xE1C2,'FD809E08E51CF3E1B28921E2E2C0652D36DC5D6352941014E8DC9D3C9F883A1C'),
    (0x20760, 0x20A33, 'E117B0BE3EFF364A7242B6EEC5F4C709DEB7FAE4E79DB2E5C9BA32CC7E54E7E1'),
    (0xF8718, 0xF8760, '83D8E4E7B974778AF6C6F832C5EB205EB612D2A469BDB76681A5B50156290EA1'),
    (0x1F1B0, 0x1F463, '1E349215CBE3DEA915C8B755F51D6FC71E2497296E8CA1F59E2248444003B8D0'),
    (0x2E6B64, 0x2E6B71, '7B5C59F3F5F7F5FE5E724565F80D81719EE1C470D4056BEA56BEE902565C6C37'),
    (0x2F46C10, 0x2F46D6A, '1DC5C757B06C54E0DDDE9F58667379DA87DF70B02495782B65EE5C99311D37E3'),
    (0x393CC10, 0x393CC45, 'F1AF611FC7780ADA8187C51843D77884F63A24E5B7F94E91FC9966C13351711E'),
    (0x2CB7620, 0x2CB7644, 'C332CA386F5074737EB183541FF260B00C2E320643BF053F232BC20BB7A6893F'),
    (0x24AD0, 0x24B56, 'C04E3409F7569FAE94392CA5CE396169B3B2772EAD624C33E830002C78A16997'),
    (0x24B60, 0x2500D, '56A439DA1E4192F3408C7313DCE204E51B31BFE461F0BE1F8DEA1FF47EDB7B12'),
    (0x25870, 0x25A20, 'A3ACD6AD99169AEAD1FA8F74CDF0B9F04742051A1889D30AD7DCC6C156B876E6'),
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


def buff_tag76_read_order(pe,md,reg,table,modules,image_owners,*,source):
    """Current anonymous tag-76 profile; no live list formatter or field names."""
    wrapper='Beyond.MemoryPack.Beyond_Gameplay_Core_Conditions_CheckSkillId_DataForMemoryPack'
    element='Beyond.MemoryPack.Beyond_Blackboard_BlackboardStringForMemoryPack'
    methods=module_methods(pe,md,modules,image_owners,
        [(124595,wrapper,'Deserialize',0x3F7FD80),
         (124596,wrapper+'+Beyond_Gameplay_Core_Conditions_CheckSkillId_DataForMemoryPackFormatter','Deserialize',0x3F7FD20),
         (162686,element,'Deserialize',0x3D9BB50),
         (162687,element+'+Beyond_Blackboard_BlackboardStringForMemoryPackFormatter','Deserialize',0x3D9BAF0)],
        source=source,expected_image='MemoryPack.Beyond.dll')
    windows=[]
    for at,expected in (
        (0x3F7FD49,'4533C0488BD3488BCF488B5C24304883C4205FE91F000000'),
        (0x3F7FE00,'4080FE050F85635BFD00'),
        (0x3D9BB19,'4533C0488BD3488BCF488B5C24304883C4205FE91F000000'),
        (0x3D9BBD5,'4080FD030F85E0621701'),
        (0x2CA8729,'488B43504863388B733083EE040F885C8CE30148834350048343400483434404897330'),
        (0x2CA874C,'48634344488B4B18482BC8483BCF0F8C528CE30183FFFF743785FF7517'),
        (0x2CA8780,'4533C08BD7488BCB488B5C2430488B7424384883C4205FE974020000'),
        (0x2CA8A97,'4533C9448BC7488BD5488BCEE878F8FFFF488BE885FF7418'),
        (0x2CA8AAF,'8B73302BF70F88B0A4F70148017B50017B40017B44897330')):
        raw=bytes.fromhex(expected);require(pe.bytes_at_va(pe.image_base+at,len(raw)),raw,source,at)
        windows.append({'rva':at,'rawHex':expected})
    calls=[]
    for at,target in ((0x3F7FDB6,0x2CA8860),(0x3F7FE10,0x2CA88C0),
        (0x3F7FE39,0x2CA86B0),(0x3F7FE5A,0x2CA86B0),(0x3F7FE7B,0x2CA86B0),
        (0x3F7FEA3,0x381F8F0),(0x3D9BBE5,0x2CA8700),
        (0x3D9BC13,0x2CA88C0),(0x3D9BC37,0x2CA8700)):
        raw=pe.bytes_at_va(pe.image_base+at,5);require(raw[:1],b'\xe8',source,at)
        require(relative_branch_target(raw,pe.image_base+at,source=source),pe.image_base+target,source,at)
        calls.append({'rva':at,'targetRva':target})
    at=pe.image_base+0x3F7FE96
    cell=rip_qword_load_target(pe.bytes_at_va(at,7),at,source=source)
    require(cell,pe.image_base+0xD039688,source,at)
    usage=pe.bytes_at_va(cell,8)
    require(method_spec_usage_index(usage,reg['methodSpecsCount'],source=source,offset=cell),610878,source,cell)
    va=int(reg['methodSpecs'],16)+610878*12;raw=pe.bytes_at_va(va,12)
    require(method_spec_record(raw,len(md.methods),reg['genericInstsCount'],source=source,offset=va),(428462,-1,62664),source,va)
    instance=table.resolve(62664)
    require(len(instance.arguments),1,source)
    arg=instance.arguments[0];tr=bytes.fromhex(arg.raw_type_record_hex)
    require(tr,bytes.fromhex('A834258D010000000000150000000000'),source)
    cp=struct.unpack_from('<Q',tr)[0];cr=pe.bytes_at_va(cp,32)
    require(len(cr),32,source,cp)
    bp=struct.unpack_from('<Q',cr)[0]
    require(bp!=0,True,source,cp)
    carrier=generic_type_carrier(tr,cr,pe.bytes_at_va(bp,16),type_pointer=arg.type_pointer_va,type_count=len(md.types),source=source)
    require(carrier['baseDefinitionIndex'],37521,source,bp)
    require(md.type_full_name(md.types[37521]),'System.Collections.Generic.List`1',source)
    nested=table.resolve_pointer(carrier['classInstantiationPointerVa'])
    require(nested.index,17007,source)
    require([a.raw_type_record_hex for a in nested.arguments],['B1000000000000000000120000000000'],source)
    require(md.type_full_name(md.types[177]),'Beyond.Blackboard+BlackboardString',source)
    return {'methods':methods,'windows':windows,'orderedCalls':calls,
        'nestedUsageCellVa':cell,'nestedUsageRawHex':usage.hex().upper(),
        'nestedMethodSpecIndex':610878,'nestedMethodSpecRawHex':raw.hex().upper(),
        'methodInstantiation':instance.as_dict(),'listCarrier':carrier,'elementInstantiation':nested.as_dict(),
        'level':'direct conditional consumer order; exact static nested type identity',
        'boundary':'Tag 76 routes to the current wrapper in selectedBuffUnionRoutes. Its member-five path reads one nonzero-normalized byte and three DWORDs before ReadPackable with List<BlackboardString>. The independently joined element reader takes member three, length-prefixed bytes, one normalized byte, then length-prefixed bytes. The length helper reads a signed DWORD: -1 returns null, zero takes an empty path, and positive length is forwarded unchanged to the byte consumer, which advances source/counters by that length after its decoder call. Payload bytes remain anonymous: encoding/cache contents, complete decoder parity, negative values below -1, live list formatter, concrete source carrier and final cursor/EOF are not proven. The maintained finite list profile is structural-only; neither managed names nor output-slot widths establish serialized order or gameplay meaning.'}


def buff_action_read_order(pe,md,reg,table,modules,image_owners,*,source,contract_path):
    """Selected action profile under audit()'s explicit native hash gate."""
    path=Path(contract_path)
    contract=json.loads(path.read_bytes())
    require(contract['schemaVersion'],1,path)
    methods=module_methods(pe,md,modules,image_owners,contract['methods'],
        source=source,expected_image='MemoryPack.Beyond.dll')
    for group in contract.get('methodGroups',[]):
        methods.extend(module_methods(pe,md,modules,image_owners,group['methods'],
            source=source,expected_image=group['image']))
    for row in contract['codeWindows']+contract.get('dataWindows',[]):
        start,end=row['startRva'],row['endRva']
        require(0<=start<end,True,path,start)
        raw=pe.bytes_at_va(pe.image_base+start,end-start)
        require(len(raw),end-start,source,start)
        require(hashlib.sha256(raw).hexdigest().upper(),row['sha256'],source,start)
    for row in contract['nestedContexts']:
        at=pe.image_base+row['instructionRva']
        ins=pe.bytes_at_va(at,7)
        require(ins,bytes.fromhex(row['instructionHex']),source,at)
        cell=rip_qword_load_target(ins,at,source=source)
        require(cell,row['cellVa'],source,at)
        usage=pe.bytes_at_va(cell,8)
        require(usage,bytes.fromhex(row['usageRawHex']),source,cell)
        index=method_spec_usage_index(usage,reg['methodSpecsCount'],source=source,offset=cell)
        require(index,row['methodSpecIndex'],source,cell)
        va=int(reg['methodSpecs'],16)+index*12
        spec=method_spec_record(pe.bytes_at_va(va,12),len(md.methods),reg['genericInstsCount'],source=source,offset=va)
        require(spec,tuple(row['methodSpec']),source,va)
        instance=table.resolve(spec[2])
        require([a.raw_type_record_hex for a in instance.arguments],[row['argumentRawHex']],source,va)
        argument=bytes.fromhex(row['argumentRawHex'])
        if row.get('generic') is not None:
            require(argument[10],0x15,source,va)
            cp=struct.unpack_from('<Q',argument)[0]
            cr=pe.bytes_at_va(cp,32)
            require(cr,bytes.fromhex(row['generic']['carrierRawHex']),source,cp)
            bp=struct.unpack_from('<Q',cr)[0];br=pe.bytes_at_va(bp,16)
            require(br,bytes.fromhex(row['generic']['baseRawHex']),source,bp)
            carrier=generic_type_carrier(argument,cr,br,type_pointer=instance.arguments[0].type_pointer_va,
                type_count=len(md.types),source=source)
            require(carrier['baseDefinitionIndex'],row['typeDefinition'],source,bp)
            nested=table.resolve_pointer(carrier['classInstantiationPointerVa'])
            require(nested.index,row['generic']['elementInstantiationIndex'],source,cp)
            require([a.raw_type_record_hex for a in nested.arguments],row['generic']['elementArguments'],source,cp)
        else:
            kind=row.get('typeKind',0x12)
            require(kind in (0x11,0x12),True,path,va)
            require(argument[10],kind,source,va)
            require(struct.unpack_from('<Q',argument)[0],row['typeDefinition'],source,va)
        require(0<=row['typeDefinition']<len(md.types),True,source,va)
        require(md.type_full_name(md.types[row['typeDefinition']]),row['typeName'],source,va)
    return {'contractPath':str(path),'contractSha256':sha(path),'methods':methods,
        'codeWindows':contract['codeWindows'],'dataWindows':contract.get('dataWindows',[]),'nestedContexts':contract['nestedContexts'],
        'anonymousReadOrder':contract['anonymousReadOrder'],
        'level':'direct selected consumer order; exact static nested type joins; structural-only parser profile',
        'boundary':contract['boundary']}


def buff_sequence_read_order(pe,md,modules,image_owners,*,source):
    """Selected member-three sequence: count, indirect elements, two bytes."""
    name='Beyond.MemoryPack.Beyond_Gameplay_Core_SequenceActionDataForMemoryPack'
    methods=module_methods(pe,md,modules,image_owners,
        [(104346,name,'Deserialize',0x39C6AA0),
         (104347,name+'+Beyond_Gameplay_Core_SequenceActionDataForMemoryPackFormatter','Deserialize',0x39C6A40)],
        source=source,expected_image='MemoryPack.Beyond.dll')
    windows=[]
    for at,expected in (
        (0x39C6A69,'4533C0488BD3488BCF488B5C24304883C4205FE91F000000'),
        (0x39C6B06,'488B43500FB6308B7B3083EF017911BA01000000488BCBE81EB6100284C0750D48FF4350FF4340FF4344897B304080FEFF7516'),
        (0x39C6B82,'4080FE030F85DD030000'),
        (0x39C6BF8,'488B43508B28448B73304183EE047911BA04000000488BCBE82BB5100284C07511488343500483434004834344044489733048634344488B4B18482BC84863C5483BC80F8C78030000'),
        (0x39C6D4D,'488B4738488B4818E806D53DFF4C8BF085ED0F8EB6000000'),
        (0x39C6D98,'4D8B16488BD34863C6498BCE4883C0044D8B8A980100004C8D04C741FF9290010000FFC63BF57CB0EB59'),
        (0x39C6EA2,'488B43500FB6288B7B3083EF017911BA01000000488BCBE882B2100284C0750D48FF4350FF4340FF4344897B30'),
        (0x39C6EE5,'4084ED0F95C0884119'),
        (0x39C6F07,'488B43500FB6288B7B3083EF017911BA01000000488BCBE81DB2100284C0750D48FF4350FF4340FF4344897B30'),
        (0x39C6F47,'4084ED4C8B6C2428488B6C24680F95C04C8B742420884118')):
        raw=bytes.fromhex(expected);require(pe.bytes_at_va(pe.image_base+at,len(raw)),raw,source,at)
        windows.append({'rva':at,'rawHex':expected})
    return {'methods':methods,'windows':windows,'level':'direct conditional selected-consumer structure',
        'boundary':'Header FF clears the output; header 3 takes a signed DWORD count after the one-byte header. The fast count path compares total-minus-consumed with the count, not count times an element width. Count -1 skips elements; zero uses a separate empty-array helper. Positive counts call a provider-selected class+0x190 target with the same reader, an eight-byte array output slot and class+0x198 companion. Output-slot width is not serialized element width. Then two bytes are consumed and nonzero-normalized, writing object offsets 0x19 then 0x18. No semantic field names, live provider identity, negative-count allocation behavior, nested extent, authenticated source cursor or EOF are promoted. Maintained framing rejects counts below -1 conservatively.'}


def buff_ifelse_read_order(pe,md,reg,table,modules,image_owners,*,source):
    """Selected reader's member-eight fast path; no live dispatch or EOF claim."""
    name='Beyond.MemoryPack.Beyond_Gameplay_Core_IfElseAction_IfElseActionDataForMemoryPack'
    methods=module_methods(pe,md,modules,image_owners,
        [(120613,name,'Deserialize',0x3774060),
         (120614,name+'+Beyond_Gameplay_Core_IfElseAction_IfElseActionDataForMemoryPackFormatter','Deserialize',0x3773670)],
        source=source,expected_image='MemoryPack.Beyond.dll')
    windows=[]
    for at,expected in (
        (0x3773699,'4533C0488BD3488BCF488B5C24304883C4205FE9AF090000'),
        (0x3774093,'837B30010F8C089A6B01488B43500FB6288B733083EE010F880B9A6B0148FF4350FF4340FF43448973304080FDFF0F8482010000'),
        (0x37740FA,'4080FD080F85D1996B01'),
        (0x2CA88CF,'83793001488BD90F8CBCA5F701488B43500FB6308B7B3083EF010F88BCA5F70148FF4350FF4340FF4344897B30'),
        (0x2CA8901,'4084F6488B7424380F95C04883C4205FC3'),
        (0x2CA86BF,'83793004488BD90F8C9EA7F701488B43508B308B7B3083EF040F889FA7F70148834350048343400483434404897B30')):
        raw=bytes.fromhex(expected);require(pe.bytes_at_va(pe.image_base+at,len(raw)),raw,source,at)
        windows.append({'rva':at,'rawHex':expected})
    calls=[]
    for at,target,width in ((0x377410A,0x2CA88C0,1),(0x3774135,0x2CA86B0,4),
        (0x3774159,0x2CA86B0,4),(0x377417D,0x2CA86B0,4),(0x37741A1,0x2CA88C0,1),
        (0x37741CA,0x2DA5C90,None),(0x37741F3,0x2DA5C90,None),(0x377421C,0x2DA5C90,None)):
        raw=pe.bytes_at_va(pe.image_base+at,5);require(raw[:1],b'\xe8',source,at)
        require(relative_branch_target(raw,pe.image_base+at,source=source),pe.image_base+target,source,at)
        calls.append({'rva':at,'targetRva':target,'fastSerializedWidth':width})
    operands=[]
    for at in (0x37741BD,0x37741E6,0x377420F):
        cell=rip_qword_load_target(pe.bytes_at_va(pe.image_base+at,7),pe.image_base+at,source=source)
        require(cell,pe.image_base+0xCFF4E68,source,at)
        raw=pe.bytes_at_va(cell,8)
        require(method_spec_usage_index(raw,reg['methodSpecsCount'],source=source,offset=cell),619962,source,cell)
        operands.append({'rva':at,'cellVa':cell,'usageRawHex':raw.hex().upper()})
    va=int(reg['methodSpecs'],16)+619962*12;raw=pe.bytes_at_va(va,12)
    require(method_spec_record(raw,len(md.methods),reg['genericInstsCount'],source=source,offset=va),
            (428464,-1,16408),source,va)
    instance=table.resolve(16408)
    require([a.raw_type_record_hex for a in instance.arguments],['F2230000000000000000120000000000'],source)
    require(9202<len(md.types),True,source)
    require(md.type_full_name(md.types[9202]),'Beyond.Gameplay.Core.SequenceActionData',source)
    return {'methods':methods,'windows':windows,'orderedCalls':calls,'nestedOperands':operands,
        'nestedMethodSpecIndex':619962,'nestedMethodSpecRawHex':raw.hex().upper(),'nestedInstantiation':instance.as_dict(),
        'level':'direct selected-consumer order and fast widths; exact nested static type argument',
        'boundary':'The token/module-joined formatter forwards RDX reader and R8 output to the static reader. After a one-byte member header, its header-eight branch passes the same reader to byte/nonzero normalization, three raw DWORD reads, a second byte/nonzero normalization, then three nested helper calls. The fast scalar prefix is 14 bytes after the header; no signedness or gameplay names are assigned. All three nested callsites use one MethodSpec with SequenceActionData as its type argument, not a proven live formatter. Header FF, reused-object preprocessing, allocation/init, other header values and segment-replacement paths are outside this fast-path claim. No nested serialized widths, complete record extent, concrete source cursor or EOF are established.'}


def buff_ifelse_forwarding(pe,md,reg,table,*,source):
    """Exact thunk contexts and conditional reuse flow, not nested field grammar."""
    windows=[]
    for at,expected in (
        (0x30E2DC,'488B15D530DD0CE908165103'),
        (0xA1EA7C,'4C8B053D296C0CE974AC7C08'),
        (0x4E67AA1,'4C8B0518992708488BD3E8CC6FBBFB90E9345FAAFE'),
        (0x91E96FC,'48895C24084889742410574883EC204983783800498BD8488BFA488BF17508488BCBE86D58E6F64C8B4338488BD7488BCE4D8B00488B5C2430488B7424384883C4205FE93C6812F7'),
        (0x30FF80,'E90BFFA303'),
        (0x3D4FE90,'48895C24084889742410574883EC204983783800498BD8488BFA488BF17444488B0D3AF7390983B9E0000000007451488B4338488B08E8954305FF4885C07413B9050000004C8BCF4C8BC6488BD0E81DF42EFC488B5C2430488B7424384883C4205FC3488D0DF6F63909E861132FFC48837B380075A9488BCBE882F02FFCEB9FE8AB632DFCEBA8')):
        raw=bytes.fromhex(expected);require(pe.bytes_at_va(pe.image_base+at,len(raw)),raw,source,at)
        windows.append({'rva':at,'rawHex':expected})
    rows=[]
    for at,index,definition,target in ((0x30E2DC,614208,428462,0x381F8F0),
                                     (0xA1EA7C,618298,428461,0x91E96FC)):
        cell=rip_qword_load_target(pe.bytes_at_va(pe.image_base+at,7),pe.image_base+at,source=source)
        usage=pe.bytes_at_va(cell,8)
        require(method_spec_usage_index(usage,reg['methodSpecsCount'],source=source,offset=cell),index,source,cell)
        va=int(reg['methodSpecs'],16)+index*12;raw=pe.bytes_at_va(va,12)
        require(method_spec_record(raw,len(md.methods),reg['genericInstsCount'],source=source,offset=va),
                (definition,-1,24608),source,va)
        rows.append({'thunkRva':at,'tailTargetRva':target,'usageCellVa':cell,'usageRawHex':usage.hex().upper(),
                     'methodSpecIndex':index,'methodSpecRawHex':raw.hex().upper(),'methodDefinition':definition})
    instance=table.resolve(24608)
    require([a.raw_type_record_hex for a in instance.arguments],['233F0000000000000000120000000000'],source)
    return {'windows':windows,'contexts':rows,'methodInstantiation':instance.as_dict(),
        'level':'direct conditional register flow; exact static MethodSpec/type argument identity',
        'boundary':'Both C9 branch thunks replace the callsite companion before tail transfer. Their different MethodSpecs have the same single IfElse wrapper argument, independently identified in selectedBuffUnionRoutes. Creation preserves RCX reader and replaces RDX; its target body is not promoted here. Reuse preserves RCX reader and RDX output-slot address, replaces R8, ensures companion+0x38 and forwards its first slot through a tail thunk. The next body takes that companion first slot to the separately reviewed provider, then, only for a non-null result, passes selector 5, provider object, unchanged reader and output slot to 0x3F300. These bodies do not directly read serialized fields. Live provider/formatter and concrete nested consumer ABI remain unresolved; no record length, field order, authenticated source cursor or EOF follows.'}


def buff_union_routes(pe,md,reg,modules,image_owners,*,source):
    """Selected current tag routes, not a replacement serialization schema."""
    name='Beyond.MemoryPack.Beyond_Gameplay_Core_AbilityAction_AbilityActionDataForMemoryPack+Beyond_Gameplay_Core_AbilityAction_AbilityActionDataForMemoryPackFormatter'
    methods=module_methods(pe,md,modules,image_owners,[(107657,name,'Deserialize',0x390D950),
        (107659,name,'.cctor',0x417AC00)],source=source,expected_image='MemoryPack.Beyond.dll')
    windows=[]
    for at,expected in (
        (0x390D974,'488D5424384533C06689742438488BCFE8F7FEFFFF84C00F8422BD55010FB774243881FE9F0100000F87E0BC5501488D1557266FFC8B8CB2185391034803CAFFE1'),
        (0x390D8D2,'4080FEFA731C66418936B001'),
        (0x390D8F4,'754B837B30020F8C208A5501488B43500FB700664189068B7B3083EF020F881F8A550148834350028343400283434402897B30EBB3'),
        (0x390D941,'33C066418906EB95'),
        (0x4E66320,'4533C0BA02000000488BCBE82C2E8A0490E9CE75AAFE'),
        (0x4E696B3,'48893333D2E92543AAFE'),
        (0x417E68A,'488B0DE70FF20833D2E85872C2FE488BCF488BD8E87D4DE8FB4C8B0D9E87E70841B8C9000000488BD3488BCFE8B1EE18FC'),
        (0x417E4D1,'488B0D3018F20833D2E81174C2FE488BCF488BD8E8364FE8FB4C8B0D5789E70841B8C0000000488BD3488BCFE86AF018FC'),
        (0x390E160,'488B1529B57209488B0BE8B1566FFC488BCF4885C00F852F905501488B1576357D09E8690111FD488903488BD0E950F8FFFF'),
        (0x390DA8A,'488B15FF1B7909488B0BE8875D6FFC488BCF4885C00F85FC9F5501488B150C397D09E82B08A0FC488903488BD0E926FFFFFF'),
        (0x3910A00,'488B1509F37809488B0BE8112E6FFC488BCF4885C00F859B6F5501488B153E097D09E865DF10FD488903488BD0E9B0CFFFFF'),
        (0x39149EA,'488B150F5A7209488B0BE827EE6EFC488BCF4885C00F856B215501488B1554D17C09E8C39310FD488903488BD0E9C68FFFFF'),
        (0x390DCB0,'488B15B1936F09488B0BE8615B6FFC488BCF4885C00F8595A35501488B15E6307D09E8451011FD488903488BD0E900FDFFFF'),
        (0x390DC1A,'488B1527307309488B0BE8F75B6FFC488BCF4885C00F8571915501488B1514387D09E8130311FD488903488BD0E996FDFFFF'),
        (0x390DED6,'488B1563997009488B0BE83B596FFC488BCF4885C00F85F4A75501488B1588297D09E8CF1211FD488903488BD0E9DAFAFFFF'),
        (0x390DC4C,'488B15C5287909488B0BE8C55B6FFC488BCF4885C00F85539C5501488B15AA357D09E8050C11FD488903488BD0E964FDFFFF'),
        (0x390E354,'488B15E5C97209488B0BE8BD546FFC488BCF4885C00F85E38A5501488B1572317D09E881FC10FD488903488BD0E95CF6FFFF'),
        (0x390DA58,'488B1541B77809488B0BE8B95D6FFC488BCF4885C00F853B9A5501488B15A6357D09E86908A0FC488903488BD0E958FFFFFF'),
        (0x390E1C4,'488B159DC67209488B0BE84D566FFC488BCF4885C00F85888C5501488B1512337D09E8F9FD10FD488903488BD0E9ECF7FFFF'),
        (0x390E0FC,'488B158DC67209488B0BE815576FFC488BCF4885C00F85A48D5501488B158A337D09E839FF10FD488903488BD0E9B4F8FFFF'),
        (0x390DCE2,'488B15C7CD7209488B0BE82F5B6FFC488BCF4885C00F85F18D5501488B15943D7D09E8770011FD488903488BD0E9CEFCFFFF'),
        (0x390E994,'488B158DAB7209488B0BE87D4E6FFC488BCF4885C00F8525885501488B152A2D7D09E859F910FD488903488BD0E91CF0FFFF'),
        (0x390DA29,'488B15B0BF7809488B0BE8E85D6FFC488BCF4885C00F854C9E5501488B15F5377D09E8A408A0FC488903488BD0EB8A'),
        (0x390DDDC,'488B15B5BF7209488B0BE8355A6FFC488BCF4885C00F8531925501488B15DA377D09E89D0311FD488903488BD0E9D4FBFFFF'),
        (0x390E674,'488B1585277309488B0BE89D516FFC488BCF4885C00F855E8C5501488B15BA307D09E851FD10FD488903488BD0E93CF3FFFF'),
        (0x390E098,'488B1569C97209488B0BE879576FFC488BCF4885C00F85C98D5501488B150E347D09E86DFF10FD488903488BD0E918F9FFFF'),
        (0x390E0CA,'488B1597997809488B0BE847576FFC488BCF4885C00F8595825501488B15BC3C7D09E81FF710FD488903488BD0E9E6F8FFFF'),
        (0x390DB20,'488B1559227809488B0BE8F15C6FFC488BCF4885C00F851B9A5501488B155E357D09E87107A0FC488903488BD0E990FEFFFF'),
        (0x390D9B5,'488B1544AF7809488B0BE85C5E6FFC488BCF4885C00F858A9C5501488B1559377D09E83009A0FC488903488BD0488BCBE806CF72FC488B5C2430488B7424404883C4205FC3'),
        (0x390E44E,'488B1503B87209488B0BE8C3536FFC488BCF4885C00F85248B5501488B1598317D09E8E3FC10FD488903488BD0E962F5FFFF'),
        (0x390DDAA,'488B15179C7109488B0BE8675A6FFC488BCF4885C00F856EB25501488B151C277D09E8A31A11FD488903488BD0E906FCFFFF'),
        (0x390E9F8,'488B15C1AD7109488B0BE8194E6FFC488BCF4885C00F854AA45501488B15CE197D09E8D50C11FD488903488BD0E9B8EFFFFF'),
        (0x390EC1E,'488B1563AD7209488B0BE8F34B6FFC488BCF4885C00F856D845501488B15402A7D09E8DFF510FD488903488BD0E992EDFFFF'),
        (0x390E1F6,'488B15037E6F09488B0BE81B566FFC488BCF4885C00F850BA15501488B15882C7D09E8A30C11FD488903488BD0E9BAF7FFFF'),
        (0x390E4B2,'488B15CFA97809488B0BE85F536FFC488BCF4885C00F8535905501488B150C2C7D09E80B0111FD488903488BD0E9FEF4FFFF'),
        (0x390E804,'488B15D5766F09488B0BE80D506FFC488BCF4885C00F85E89A5501488B159A267D09E8650611FD488903488BD0E9ACF1FFFF'),
        (0x390DF9E,'488B15E32F7309488B0BE873586FFC488BCF4885C00F859D925501488B15E0367D09E8AF0311FD488903488BD0E912FAFFFF'),
        (0x390DF6C,'488B152D237909488B0BE8A5586FFC488BCF4885C00F855D995501488B156A337D09E8150911FD488903488BD0E944FAFFFF'),
        (0x390EB88,'488B1501227309488B0BE8894C6FFC488BCF4885C00F8535875501488B15B62B7D09E825F810FD488903488BD0E928EEFFFF'),
        (0x390E5DE,'488B15B38E7109488B0BE833526FFC488BCF4885C00F85A3AA5501488B15B01E7D09E8C31211FD488903488BD0E9D2F3FFFF'),
        (0x390E73C,'488B15DD277309488B0BE8D5506FFC488BCF4885C00F85EA8A5501488B15522F7D09E8F9FB10FD488903488BD0E974F2FFFF'),
        (0x390F4B6,'488B158BA47209488B0BE85B436FFC488BCF4885C00F85C07B5501488B15B0217D09E83BED10FD488903488BD0E9FAE4FFFF'),
        (0x390E8FE,'488B1543677009488B0BE8134F6FFC488BCF4885C00F8595A05501488B1500217D09E8B70A11FD488903488BD0E9B2F0FFFF'),
        (0x390E12E,'488B150B9F7109488B0BE8E3566FFC488BCF4885C00F8510AE5501488B15E8227D09E8A71611FD488903488BD0E982F8FFFF'),
        (0x390E4E4,'488B15F5B57209488B0BE82D536FFC488BCF4885C00F853E8B5501488B15C2307D09E8ADFC10FD488903488BD0E9CCF4FFFF'),
        (0x390F2C2,'488B1507AC7209488B0BE84F456FFC488BCF4885C00F8515795501488B1534287D09E857EB10FD488903488BD0E9EEE6FFFF')):
        raw=bytes.fromhex(expected);require(pe.bytes_at_va(pe.image_base+at,len(raw)),raw,source,at)
        windows.append({'rva':at,'rawHex':expected})
    table_va=pe.image_base+0x3915318;raw=pe.bytes_at_va(table_va,416*4)
    require(len(raw),416*4,source,table_va)
    targets=[r[0] for r in struct.iter_unpack('<I',raw)]
    rows=[]
    for tag,target,index,definition,suffix,init in (
        (0xC9,0x390DA8A,106672,16163,'IfElseAction_IfElseActionData',0x417E68A),
        (0xC0,0x3910A00,106641,16145,'GainCostAction_Data',0x417E4D1),
        (0x40,0x39149EA,106441,16615,'CheckDamageTag_Data',None),
        (0x76,0x390E160,106507,16683,'Conditions_CheckSkillId_Data',None),
        (0xEC,0x390DCB0,106853,16241,'ModifyDynamicBlackboard_Data',None),
        (0x50,0x390DC1A,106467,16717,'CompareFloat_Data',None),
        (0x11F,0x390DED6,106969,16341,'RaiseTrainLevelEvent_Data',None),
        (0xB4,0x390DC4C,106625,16117,'FinishBuffAdvanced_Data',None),
        (0x56,0x390E354,106476,16593,'Conditions_CheckBuffIdInContext_Data',None),
        (0x92,0x390DA58,106537,16047,'CreateBuffAction_Data',None),
        (0x57,0x390E1C4,106475,16595,'Conditions_CheckBuffIdInContextAdvanced_Data',None),
        (0x5B,0x390E0FC,106480,16611,'Conditions_CheckDamageDecorateMask_Data',None),
        (0x3C,0x390DCE2,106437,16601,'CheckBuffStackNumAdvanced_Data',None),
        (0x78,0x390E994,106509,16687,'Conditions_CheckSkillType_Data',None),
        (0xB2,0x390DA29,106623,16111,'FindTargetAction_FindTargetActionData',None),
        (0x68,0x390DDDC,106493,16647,'Conditions_CheckMainCharacterCondition_Data',None),
        (0x81,0x390E674,106518,16707,'Conditions_CheckTimedMarkerCondition_Data',None),
        (0x58,0x390E098,106478,16599,'Conditions_CheckBuffStackNum_Data',None),
        (0x02,0x390E0CA,106256,16115,'AbilityActions_FinishBuffAction_Data',None),
        (0x9A,0x390DB20,106550,16063,'DamageAction_DamageActionData',None),
        (0xA2,0x390D9B5,106579,16079,'EffectAction_EffectActionData',None),
        (0x65,0x390E44E,106490,16641,'Conditions_CheckHp_Data',None),
        (0x169,0x390DDAA,107143,16485,'SpawnAbilityEntity_Data',None),
        (0x157,0x390E9F8,107097,16453,'SetSkillCdAtOnce_Data',None),
        (0x6E,0x390EC1E,106499,16665,'Conditions_CheckPoiseValue_Data',None),
        (0xFE,0x390E1F6,106901,16277,'ObtainCostAction_Data',None),
        (0x96,0x390E4B2,106541,16055,'CreateTimedMarker_Data',None),
        (0xFD,0x390E804,106885,16275,'NotNextCheckAction_Data',None),
        (0x7C,0x390DF9E,106513,16697,'Conditions_CheckTagMatch_Data',None),
        (0xB6,0x390DF6C,106627,16123,'FinishOwnerAction_Data',None),
        (0x80,0x390EB88,106517,16705,'Conditions_CheckTargetsEqual_Data',None),
        (0x16E,0x390E5DE,107148,16493,'SpellInflictionOnChar_Data',None),
        (0x7B,0x390E73C,106512,16695,'Conditions_CheckSuperArmor_Data',None),
        (0x6D,0x390F4B6,106498,16663,'Conditions_CheckPhysicalInflictionType_Data',None),
        (0x136,0x390E8FE,107005,16387,'SaveBuffStackNumAdvanced_Data',None),
        (0x163,0x390E12E,107114,16475,'SimpleCalcBBAction_Data',None),
        (0x69,0x390E4E4,106494,16653,'Conditions_CheckObjectTypeMatch_Data',None),
        (0x44,0x390F2C2,106445,16633,'CheckGlobalCDTimerAction_Data',None)):
        require(targets[tag],target,source,table_va+tag*4)
        operands=[]
        for at,usage_tag in ((target,1),)+(((init,2),) if init is not None else ()):
            ins=pe.bytes_at_va(pe.image_base+at,7)
            cell=pe.image_base+at+7+struct.unpack_from('<i',ins,3)[0]
            usage=pe.bytes_at_va(cell,8)
            found=unresolved_usage_index(usage,reg['typesCount'],tag=usage_tag,source=source,offset=cell)
            require(found,index,source,cell)
            pointer=pe.u64_at_va(int(reg['types'],16)+index*8)
            record=pe.bytes_at_va(pointer,16);require(len(record),16,source,pointer)
            require(record[10],0x12,source,pointer+10)
            require(struct.unpack_from('<Q',record)[0],definition,source,pointer)
            require(definition<len(md.types),True,source,pointer)
            expected_name='Beyond.MemoryPack.Beyond_Gameplay_Core_'+suffix+'ForMemoryPack'
            require(md.type_full_name(md.types[definition]),expected_name,source,pointer)
            operands.append({'instructionRva':at,'cellVa':cell,'usageRawHex':usage.hex().upper(),
                'usageTag':usage_tag,'registeredTypeIndex':index,'typePointerVa':pointer,'typeRawHex':record.hex().upper()})
        if len(operands)==2:require(operands[0]['typePointerVa'],operands[1]['typePointerVa'],source)
        rows.append({'tag':tag,'switchTargetRva':target,'typeDefinition':definition,'wrapperName':expected_name,'operands':operands})
    return {'methods':methods,'windows':windows,'switchTableRva':0x3915318,'switchEntryCount':416,
        'switchTableSha256':hashlib.sha256(raw).hexdigest().upper(),'rows':rows,
        'level':'direct current native tag-to-wrapper routing; exact metadata identity',
        'boundary':'The token/module-joined reader calls the bounded tag helper then uses its ushort output in an unsigned <=0x19F switch. The helper fast path consumes one byte and directly returns tags below 0xFA. FA consumes two more bytes as a little-endian ushort with no lower-value restriction; its short-input path calls an external refill helper, not an in-body zero-result failure. FB..FF return false with zero tag output, skipping the AL=1 instruction; the dispatcher false path clears its output. The maintained finite parser retains FF null and leaves FB..FE unsupported. Segment replacement is not certified. Selected table entries reach exact type-usage operands. For C9 and C0, separate cctor callsites pass those literal tags alongside a helper result derived from the same registered type pointer (usage kind two versus branch kind one). Current C9 describes the IfElse wrapper; C0 describes GainCost, contradicting the legacy Buff reader C0 name. Tag 40 describes CheckDamageTag. This is not a blanket tag renumbering rule or proof of nested fields, actual object allocation, formatter execution, record extent or EOF. Do not alias C9 to the legacy C0 parser or promote existing labels for current bytes without the concrete nested consumer ABI.'}


def element_provider_state_flow(pe,*,source):
    """Selected state-dependent lookup path; enclosing bodies are gated by audit."""
    windows=[]
    for at,expected in (
        (0xF8040,'F68138010000017405488BC1EB05E9ED93F4FFC3'),
        (0x2DA427F,'488B5D38488B1B'),
        (0x2DA42B0,'B201488BCBE8462826FD4C8D6020'),
        (0x2DA439A,'488B4A10488B43704C8B34C8'),
        (0x2DA43E9,'498BCEE87F030000488BD8488B4538488B4008'),
        (0x2DA4412,'488BD0488B0BE833F425FD84C00F842AD0D401'),
        (0x2DA4592,'498B47704C8934F8'),
        (0x2DA482E,'488B80B8000000488B6818'),
        (0x2DA4970,'443B7B28754E488B75184C8B7310'),
        (0x2DA49A7,'33C948897C24204D8BCE4C8BC6488BD0E8745D29FD84C00F8516010000'),
        (0x2DA4ADA,'833D2BA70F0B00488B43184889442468'),
        (0x2DA4C7F,'4C8B0D52032A0A4C8BC3488BD7E80F44E000'),
        (0x2DA4C91,'488B442468'),
        (0x4AF1447,'4533F6E9652F2BFE')):
        raw=bytes.fromhex(expected)
        require(pe.bytes_at_va(pe.image_base+at,len(raw)),raw,source,at)
        windows.append({'rva':at,'rawHex':expected})
    return {'windows':windows,'level':'direct conditional state/return flow',
        'boundary':'The short class helper returns its input unchanged when bit zero at +0x138 is set; otherwise it tail-jumps to initialization, whose return cannot be replaced by the fast-path identity. The provider receives a companion, not a serialized reader. Companion method-context slot zero feeds a helper and its result+0x20 becomes a lookup key. A successful first-table lookup uses a 24-byte row index to load a qword carrier from a separate vector; a miss may construct and insert a carrier. A null context element can instead forward a null carrier to the next helper. That helper consults static-carrier+0x18 state, compares a hash and invokes a separate equality target before returning a matched node+0x18 value. Miss branches include conditional helper calls, allocations and publication through another helper; they are not equivalent to selecting the static registered candidate. The common return comes from the writable local slot. The caller checks the returned object against companion method-context slot one before returning it or entering an error path. These branches establish state dependence, not cache contents, helper success, concrete formatter identity, execution, serialized bytes or EOF. Hash/equality algorithms, all initialization and generation helper implementations, and live mutation ordering remain unresolved.'}


def adapter_conversion_context(pe,md,reg,table,entries,*,source):
    """Static interface carrier and slot identity; not a live conversion target."""
    require(len(entries),13,source)
    entry=entries[8]
    require((entry['relativeIndex'],entry['kindRaw']),(8,2),source,entry['entryVa'])
    index=pe.u32_at_va(entry['dataPointerVa'])
    require(index,45287,source,entry['dataPointerVa'])
    require(index<reg['typesCount'],True,source,entry['dataPointerVa'])
    pointer=pe.u64_at_va(int(reg['types'],16)+index*8)
    require(pointer!=0,True,source)
    raw=pe.bytes_at_va(pointer,16);require(len(raw),16,source,pointer)
    require(raw[10],0x15,source,pointer+10)
    cp=struct.unpack_from('<Q',raw)[0];require(cp!=0,True,source,pointer)
    cr=pe.bytes_at_va(cp,32);require(len(cr),32,source,cp)
    bp=struct.unpack_from('<Q',cr)[0];require(bp!=0,True,source,cp)
    carrier=generic_type_carrier(raw,cr,pe.bytes_at_va(bp,16),type_pointer=pointer,
        type_count=len(md.types),source=source)
    require(carrier['baseDefinitionIndex'],32173,source,bp)
    interface=md.types[32173]
    require(md.type_full_name(interface),'Beyond.MemoryPack.IMemoryPackDeSerializeWrapper`1',source)
    inst=table.resolve_pointer(carrier['classInstantiationPointerVa'])
    require(inst.index,12827,source,inst.record_va)
    require(len(inst.arguments),1,source,inst.record_va)
    arg=bytes.fromhex(inst.arguments[0].raw_type_record_hex)
    require(arg,bytes.fromhex('F2020000000000000000130000000000'),source,inst.record_va)
    owner=type_parameter_owner(md.buf,struct.unpack_from('<Q',arg)[0],
        [t.generic_container_index for t in md.types],source=source)
    require((owner['typeIndex'],owner['ordinal']),(13633,0),source,owner['containerOffset'])
    method_entry=entries[9]
    require((method_entry['relativeIndex'],method_entry['kindRaw']),(9,3),source,method_entry['entryVa'])
    spec=pe.u32_at_va(method_entry['dataPointerVa'])
    require(spec,173212,source,method_entry['dataPointerVa'])
    require(spec<reg['methodSpecsCount'],True,source,method_entry['dataPointerVa'])
    spec_va=int(reg['methodSpecs'],16)+spec*12
    spec_raw=pe.bytes_at_va(spec_va,12)
    definition,ci,mi=method_spec_record(spec_raw,len(md.methods),reg['genericInstsCount'],source=source,offset=spec_va)
    require((definition,ci,mi),(249850,inst.index,-1),source,spec_va)
    require((interface.method_start,interface.method_count),(definition,1),source)
    method=md.methods[definition]
    require((method.declaring_type,method.slot,method.parameter_count,method.token),
        (32173,0,0,0x06001747),source)
    require(md.string(method.name_index),'GetValue',source)
    return {'carrier':carrier,'interfaceEntry':entry,'methodEntry':method_entry,
        'instantiation':inst.as_dict(),'argumentOwner':owner,'methodSpecIndex':spec,
        'methodSpecRawHex':spec_raw.hex().upper(),'methodDefinition':definition,'methodSlot':method.slot,
        'level':'exact static carrier/VAR/MethodSpec and metadata slot identity',
        'boundary':'Adapter relative class slot eight describes IMemoryPackDeSerializeWrapper with the reciprocal adapter ordinal-zero VAR. Slot nine describes GetValue with the identical class-instantiation index; its independently decoded metadata slot is zero and it has no explicit parameters. This distinguishes the conversion interface argument T0 from the existing slot-four formatter query for T1; it does not by itself decode the method return type or implementation. The native helper requests interface slot zero, but does not read RGCTX slot nine directly. The static relationship does not prove inflated interface pointers, a live implementation, method body semantics, serialized order, source consumption or EOF. Do not substitute the shared-code Object candidate for the original companion context.'}


def list_element_value_flow(pe,*,source):
    """Ref-object dispatch followed by object conversion; not a DWORD byte read."""
    windows=[]
    for at,expected in (
        (0x3B1373A,'4C89442418'),(0x3B1374B,'498BF9488BF2488BD9'),
        (0x3B1376E,'488B4F20E8C9485EFC488B88C0000000488B4920E8D90A29FF'),
        (0x3B1378C,'B9050000004C8D4C24404C8BC3488BD0E85FBB52FC'),
        (0x3B137A1,'488B5C24404885DB7460'),
        (0x3B137AB,'488B4F20E88C485EFC488B88C0000000488B4940E87C485EFC'),
        (0x3B137C4,'33C94C8BC3488BD0E82F3058FC'),(0x3B137D6,'8906'),(0x3B1380B,'33C0EBC2'),
        (0x96814,'498B38498BF00FB7E9488BDA'),
        (0x96828,'440FB7873001000033C066413BC0731C'),
        (0x96838,'488B97B00000000FB7C84803C948391CCA741A'),
        (0x96865,'0FB7D0488B87B00000004803D28B44D00803C548984883C01448C1E0044803C7'),
        (0x96885,'4C8B00488BCE488B5008'),(0x968A3,'49FFE0')):
        raw=bytes.fromhex(expected)
        require(pe.bytes_at_va(pe.image_base+at,len(raw)),raw,source,at)
        windows.append({'rva':at,'rawHex':expected})
    bodies=[]
    for start,end,expected in (
        (0x3B13730,0x3B1380F,'8F484C44B26A8E791ED7FA7470F1ACEA2C46391E6869DE64D9B206FC6ECB05C7'),
        (0x96800,0x968A6,'C9595BDA4FE4DBC11FC0B54731878C8F1305752C0DE7BA35104FE8DC134F8743')):
        raw=pe.bytes_at_va(pe.image_base+start,end-start)
        require(len(raw),end-start,source,start)
        digest=hashlib.sha256(raw).hexdigest().upper();require(digest,expected,source,start)
        bodies.append({'rva':start,'byteLength':len(raw),'sha256':digest})
    return {'windows':windows,'bodies':bodies,'outputByteLength':4,
            'level':'direct conditional ref-object/output and interface-dispatch flow',
            'boundary':'The non-FF helper retains reader RCX, output RDX and companion R9, and saves incoming R8 in the stack qword later passed by address to formatter dispatch. Companion-derived class slots supply the provider query and conversion interface carrier. Dispatch receives the original reader plus that initialized writable object slot. A null resulting object yields EAX=0; otherwise the conversion helper receives slot number zero, a separately derived interface carrier and the resulting object. Its hit path compares exact pointers in 16-byte class interface records, adds the requested ushort slot to a record DWORD offset, sign-extends the 32-bit sum and addresses a target/companion pair at class+(sum+0x14)*16. Its miss path delegates pair resolution to another helper. The common path tail-jumps with RCX=object and RDX=the loaded companion; it does not pass the original reader to this conversion target. The outer helper writes returned EAX to its four-byte output. That width is therefore a converted result width, not proof of a serialized DWORD load or four-byte cursor advance. Pair bounds, interface/class initialization, provider and conversion identities, actual target selection, delegated byte consumption and EOF remain unresolved.'}


def list_element_shared_context(pe,table,reg,code,spec_records,methods_raw,*,source):
    """Selected code-context candidate; never overwrite a live companion context."""
    inst=table.resolve(5059)
    require([a.raw_type_record_hex for a in inst.arguments],
            ['A22D0000000000000000118000000000','068E00000000000000001C0000000000'],source,inst.record_va)
    require(len(spec_records),reg['methodSpecsCount'],source)
    selected={i for i,row in enumerate(spec_records) if row==(102199,5059,-1)}
    require(sorted(selected),[165248],source)
    rows=generic_method_candidates(methods_raw,reg['genericMethodTableCount'],len(spec_records),selected,
        code['genericMethodPointersCount'],code['invokerPointersCount'],source=source,
        offset=int(reg['genericMethodTable'],16))
    for row in rows:
        slot=int(code['genericMethodPointers'],16)+row['indices'][0]*8
        row['methodPointerSlotVa']=slot;row['methodPointerVa']=pe.u64_at_va(slot)
    require([(r['methodSpecIndex'],r['methodPointerVa']) for r in rows],[(165248,pe.image_base+0x40BB390)],source)
    return {'classInstantiation':inst.as_dict(),'methodDefinition':102199,'methodSpecIndices':sorted(selected),
            'codeCandidates':rows,'level':'exact selected static MethodSpec/code-context relation',
            'boundary':'The selected MethodSpec of the previously module/token-joined GenericMemoryPackFormatter Deserialize definition has ordered GameplayTag-record and Object-record arguments and no method instantiation. Its bounded generic-method table entry joins the dispatcher comparison target. This is a shared-code candidate context, not the actual object class or loaded companion context. The companion class supplies the specialized branch RGCTX slots independently; substituting the shared Object argument into that context is invalid without separate evidence. Actual provider selection, companion inflation, element payload and EOF remain unresolved.'}


def list_element_null_probe(pe,*,source):
    """Conditional FF peek and one-byte consumption, not a terminal grammar."""
    windows=[]
    for at,rawhex in (
        (0x3EDF9A0,'40534883EC20488BD9C644243000E87D8EDCFE84C00F8537F8CC004883C4205BC3'),
        (0x4BAF1F2,'488D542430488BCBE861960FFEB001E9B50733FF'),
        (0x2CA8830,'40534883EC2083793001488BD90F8CBD8BE301488B43508038FF0F94C04883C4205BC3'),
        (0x2CA8860,'48895C24084889742410574883EC2083793001488BF2488BD90F8C958BE301488B43500FB608880E8B7B3083EF010F88938BE30148FF4350FF4340FF4344897B30803EFF488B5C2430488B7424380F95C04883C4205FC3'),
        (0x4AE1400,'4533C0BA01000000E84F7DC20490E930741CFE'),
        (0x4AE1414,'4533C0BA01000000E83B7DC20490E958741CFEBA01000000488BCBE80C0DFF0084C00F8565741CFEE953741CFE')):
        raw=bytes.fromhex(rawhex)
        require(pe.bytes_at_va(pe.image_base+at,len(raw)),raw,source,at)
        windows.append({'rva':at,'byteLength':len(raw),'rawHex':rawhex,'sha256':hashlib.sha256(raw).hexdigest().upper()})
    return {'windows':windows,'markerByte':255,'fastConsumedBytesOnMatch':1,
            'level':'direct conditional marker-peek and consumed-counter flow',
            'boundary':'The selected helper calls a peek routine that ensures one readable byte if needed, compares cursor[0] with 0xFF and returns the comparison without directly advancing cursor or counters. A false result returns immediately. A true result calls a byte consumer with the same reader and a local byte output, then returns true regardless of that consumer AL result. The consumer copies one byte out; its fast path advances cursor, local and consumed counters by one and decrements remaining by one. It returns byte!=0xFF, so the wrapper does not simply forward that boolean. Cold paths use the already reviewed ensure/advance routines; ensure may replace the segment, so absence of fast pointer increment does not imply unchanged allocation. The dispatcher true branch clears its DWORD output. This conditional FF handling does not identify a serialized union, prove the non-FF element width, guarantee source validity, or establish source/terminal/EOF consumption. The shared target identity does not prove this branch executes.'}


def list_element_dispatch(pe,*,source):
    """Object-selected target/companion ABI, not a selected element reader."""
    bodies=[]
    for start,end,expected in (
        (0x98CD0,0x98DF1,'1BF6036D17FE88296002DAF06C93284CA14CA2C7117C2E89240F7FAF2D1D61FE'),
        (0x2FCA38,0x2FCA56,'F223AF3B187BBB846AD744B4553E69B70D6BBBB616C49CB208C55A3CB2E3D9B9')):
        raw=pe.bytes_at_va(pe.image_base+start,end-start)
        require(len(raw),end-start,source,start)
        digest=hashlib.sha256(raw).hexdigest().upper()
        require(digest,expected,source,start)
        bodies.append({'rva':start,'byteLength':len(raw),'sha256':digest})
    # Decode the actual RIP operand rather than infer a target from nearby names.
    at=0x98CF9;raw=pe.bytes_at_va(pe.image_base+at,7)
    require(raw[:3],bytes.fromhex('488D0D'),source,at)
    require(len(raw),7,source,at)
    target=at+7+struct.unpack_from('<i',raw,3)[0]
    require(target,0x40BB390,source,at)
    return {'bodies':bodies,'targetPairOffsets':[0x190,0x198],'specializedTargetRva':target,
            'fallbackCallRva':0x2FCA4E,'level':'direct conditional object-target/companion ABI',
            'boundary':'Entry RDX is retained as the formatter object, R8 as the reader and R9 as the output pointer; incoming RCX is overwritten by the object class before the initialization helper call. The class is then reloaded and its +0x190 target and +0x198 companion are loaded as a pair. If the target differs from the exact RIP-derived comparison address, the cold branch performs an ordinary indirect CALL with RCX=object, RDX=reader, R8=output and R9=the loaded companion, then rejoins cleanup. It is not a tail jump, nor a companion inferred from declaration order. The equal-target path instead reads the loaded companion class RGCTX slots and calls another helper with the retained reader. A nonzero AL clears the output DWORD; the other path eventually forwards the retained reader/output, a helper-derived value and class slot three to another reader helper. These distinct branches do not certify which target the live object selects. Class initialization, actual target/companion identity and inflation, all delegated read widths/cursor changes and final EOF remain unresolved. No constant element byte width or terminal-candidate elimination follows.'}


def list_formatter_candidate(pe,md,modules,image_owners,reg,code,table,spec_records,methods_raw,*,source):
    """Concrete registered candidate, separate from active provider dispatch."""
    identities=module_methods(pe,md,modules,image_owners,
        [(428795,'MemoryPack.Formatters.ListFormatter`1','Deserialize',None)],source=source)
    require(identities[0]['token'],0x060001C0,source)
    index=209879
    require(index<reg['typesCount'],True,source)
    pointer=pe.u64_at_va(int(reg['types'],16)+index*8)
    require(pointer!=0,True,source,int(reg['types'],16)+index*8)
    raw=pe.bytes_at_va(pointer,16);require(len(raw),16,source,pointer)
    require(raw[10],0x15,source,pointer)
    carrier_pointer=struct.unpack_from('<Q',raw)[0]
    require(carrier_pointer!=0,True,source,pointer)
    carrier_raw=pe.bytes_at_va(carrier_pointer,32);require(len(carrier_raw),32,source,carrier_pointer)
    base_pointer=struct.unpack_from('<Q',carrier_raw)[0]
    require(base_pointer!=0,True,source,carrier_pointer)
    base_raw=pe.bytes_at_va(base_pointer,16)
    carrier=generic_type_carrier(raw,carrier_raw,base_raw,type_pointer=pointer,type_count=len(md.types),source=source)
    require(carrier['baseDefinitionIndex'],54057,source,base_pointer)
    require(md.methods[428795].declaring_type,54057,source)
    inst=table.resolve_pointer(carrier['classInstantiationPointerVa'])
    require(inst.index,816,source,inst.record_va)
    require(len(inst.arguments),1,source,inst.record_va)
    require(inst.arguments[0].raw_type_record_hex,'A22D0000000000000000118000000000',source,inst.record_va)
    # spec_records is the already bounded complete MethodSpec inventory from audit().
    require(len(spec_records),reg['methodSpecsCount'],source)
    selected={i for i,row in enumerate(spec_records) if row==(428795,816,-1)}
    require(sorted(selected),[215461],source)
    candidates=generic_method_candidates(methods_raw,reg['genericMethodTableCount'],len(spec_records),selected,
        code['genericMethodPointersCount'],code['invokerPointersCount'],source=source,
        offset=int(reg['genericMethodTable'],16))
    for row in candidates:
        slot=int(code['genericMethodPointers'],16)+row['indices'][0]*8
        row['methodPointerSlotVa']=slot;row['methodPointerVa']=pe.u64_at_va(slot)
    require([(r['methodSpecIndex'],r['methodPointerVa']) for r in candidates],
            [(215461,pe.image_base+0x3BA40F0)],source)
    windows=[]
    for at,expected in ((0x3BA410E,'488B47508B30'),
        (0x3BA4120,'48834750048347400483474404895F30'),
        (0x3BA4130,'48634744488B4F18482BC84863C6483BC8'),
        (0x3BA4147,'83FEFF0F842F010000'),(0x3BA415F,'49833E00488B4520488B88C00000000F8518653201'),
        (0x3BA41C1,'85F60F881F653201'),(0x3BA4282,'49C70600000000'),
        (0x4ECA6AB,'FF431CC7431800000000E9799BCDFE'),
        (0x3BA4261,'85F67F4D'),(0x3BA42C3,'4C8D4C24584C8BC7498BD7E8FD494FFC'),
        (0x3BA4312,'41FFC4443BE60F8D47FFFFFFEB92')):
        chunk=bytes.fromhex(expected)
        require(pe.bytes_at_va(pe.image_base+at,len(chunk)),chunk,source,at)
        windows.append({'rva':at,'rawHex':expected})
    return {'methodIdentities':identities,'registeredTypeIndex':index,'typeCarrier':carrier,
            'classInstantiation':inst.as_dict(),'methodSpecIndices':sorted(selected),'codeCandidates':candidates,
            'windows':windows,'level':'exact static candidate identity; direct conditional header and loop flow',
            'boundary':'The registered ListFormatter type and Deserialize MethodSpec share the same one-argument instantiation as the previously joined List carrier. The complete selected MethodSpec/code-table join yields one static code candidate, not proof of provider selection. This body receives the reader in RDX, output-slot pointer in R8 and companion in R9. Its fast header path reads a signed DWORD, advances cursor and both counters by four, and compares total-minus-consumed with the sign-extended count without multiplying by an element width. Header -1 clears the output. With a null output, other negative counts reach a helper followed by INT3; with an existing output, the reviewed reuse branch instead increments object+0x1C, clears object+0x18 and reaches a loop guarded by count>0. Thus this body does not universally reject all counts below -1. Each positive iteration passes the same reader and a zeroed four-byte output slot to element dispatch, then forwards the output word to another helper and increments its loop index. A four-byte output slot does not prove four serialized bytes per element. Cold header paths call the separately reviewed ensure/advance helpers. Element formatter identity, helper effects, successful allocation/reuse, actual MethodInfo/provider selection, authenticated source span and final cursor/EOF remain unresolved. Keep both terminal grammars.'}


def nested_reader_context(pe, md, modules, image_owners, reg, table, *, source, metadata_source):
    """Slot-zero context chain: reciprocal parameters, never live substitution."""
    methods=module_methods(pe,md,modules,image_owners,
        [(428462,'MemoryPack.MemoryPackReader','ReadPackable',None),
         (428464,'MemoryPack.MemoryPackReader','ReadValue',None),
         (428394,'MemoryPack.MemoryPackFormatterProvider','GetFormatter',None)],source=source,
        expected_image='MemoryPack.dll')
    module=modules['MemoryPack.dll']
    require(pe.u32_at_va(module+0x40),120,source,module+0x40)
    require(pe.u32_at_va(module+0x50),691,source,module+0x50)
    range_va=pe.u64_at_va(module+0x48);entry_va=pe.u64_at_va(module+0x58)
    ranges=pe.bytes_at_va(range_va,120*12)
    require(len(ranges),120*12,source,range_va)
    containers=[m.generic_container_index for m in md.methods]
    rows=[]
    for definition,token,start,count,kind,index,next_definition,inst_index in (
        (428462,0x06000073,36,1,3,517554,428464,54984),
        (428464,0x06000075,40,3,3,516756,428394,41928),
        (428394,0x0600002F,13,2,1,2190,None,None)):
        require(md.methods[definition].token,token,metadata_source,definition)
        require(select_rgctx_range(ranges,691,token,source=source,offset=range_va),(start,count),source,range_va)
        at=entry_va+start*16;raw=pe.bytes_at_va(at,16)
        require(len(raw),16,source,at)
        require(struct.unpack_from('<I',raw)[0],kind,source,at)
        payload=struct.unpack_from('<Q',raw,8)[0]
        encoded=pe.bytes_at_va(payload,4)
        require(encoded,struct.pack('<I',index),source,payload)
        row={'methodDefinition':definition,'token':token,'relativeSlot':0,'moduleEntryIndex':start,
             'entryVa':at,'entryRawHex':raw.hex().upper(),'index':index,'kind':kind}
        if kind==3:
            require(index<reg['methodSpecsCount'],True,source,payload)
            spec_at=int(reg['methodSpecs'],16)+index*12
            spec=pe.bytes_at_va(spec_at,12)
            parsed=method_spec_record(spec,len(md.methods),reg['genericInstsCount'],source=source,offset=spec_at)
            require(parsed,(next_definition,-1,inst_index),source,spec_at)
            inst=table.resolve(inst_index)
            require(len(inst.arguments),1,source,inst.record_va)
            argument=inst.arguments[0];type_at=argument.type_pointer_va
            type_raw=bytes.fromhex(argument.raw_type_record_hex)
            row.update({'methodSpecVa':spec_at,'methodSpecRawHex':spec.hex().upper(),
                        'nextMethodDefinition':next_definition,'methodInstantiation':inst.as_dict()})
        else:
            require(index<reg['typesCount'],True,source,payload)
            slot=int(reg['types'],16)+index*8
            pointer=pe.bytes_at_va(slot,8)
            require(len(pointer),8,source,slot)
            type_at=struct.unpack('<Q',pointer)[0]
            require(type_at!=0,True,source,slot)
            type_raw=pe.bytes_at_va(type_at,16)
        require(len(type_raw),16,source,type_at)
        require(type_raw[10],0x1E,source,type_at)
        owner=method_parameter_owner(md.buf,struct.unpack_from('<Q',type_raw)[0],containers,source=metadata_source)
        require((owner['methodIndex'],owner['ordinal']),(definition,0),metadata_source,owner['containerOffset'])
        row.update({'typePointerVa':type_at,'typeRawHex':type_raw.hex().upper(),'parameterOwner':owner})
        rows.append(row)
    windows=[]
    for at,expected in ((0x381F904,'488BDA4C8BF9'),(0x381F915,'488B4338488B18'),
                        (0x381F944,'488B4338488B30'),(0x381F956,'488B5E38488B1B'),
                        (0x381FB0D,'B9050000004C8D4C24204D8BC7488BD3E8DEF781FC')):
        raw=bytes.fromhex(expected)
        require(pe.bytes_at_va(pe.image_base+at,len(raw)),raw,source,at)
        windows.append({'rva':at,'rawHex':expected})
    return {'methods':methods,'rows':rows,'windows':windows,
            'level':'exact static token/MethodSpec/MVAR joins; direct conditional nested context reads',
            'boundary':'The selected nested body retains its incoming reader and follows MethodInfo+0x38 slot zero three times before deriving a provider key. The corresponding independently image/token-joined ranges identify ReadPackable to ReadValue, ReadValue to GetFormatter, then the GetFormatter MVAR type. Each method edge has one open method argument whose reciprocal owner is the preceding method and whose ordinal is zero; the final type is a distinct ordinal-zero parameter owned by GetFormatter itself. These are three different parameter records, not interchangeable raw identities. Conditional on ordinary context inflation from the previously authenticated ReadPackable<List<...>> call, this chain carries that same concrete argument through the intermediate contexts. All three generic definition ordinary-pointer slots are null; static ranges do not select a shared body. The body passes the retained reader and separate output slot to dispatch, but actual initialized MethodInfos, substitution, provider key/cache contents, list formatter, source length and final cursor remain unobserved. No list framing, element meaning or terminal uniqueness follows.'}


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
            'boundary':'The AppendPathInfo call supplies an original AppendFormat MethodSpec with three ordered string-tag arguments, stored as its stack companion. Do not replace that context with arguments inferred from the shared code body. The reviewed body reads the companion at its sixth ABI position; numeric selector branches use the first/second/third value alongside companion+0x38 slots 0/8/16. Actual RGCTX inflation and nested formatter execution are not established. Input scanning reads 16-bit elements at string+0x14+index*2; literal copying advances the temporary cursor by element count. The downstream UnSafeString.Append receives pointer and count, calls a capacity helper, computes signed-extended 32-bit count*2 for an indirect copy target, and advances its stored cursor by the original count. A zero 16-bit terminator is written only if the updated signed cursor is below capacity. Hence the forwarded count is a two-byte-unit count on this path, not a byte length or an unconditional terminator guarantee. Capacity/copy resolver internals, replacement paths, complete format grammar, actual generic dispatch, output validity/length, concrete path and source identity remain unresolved.'}


def resolver_key_comparison(pe,*,source):
    """Bounded-prefix lexicographic comparison and caller length tie-breaks."""
    windows=[]
    for at,expected in (
        (0x2DF760,'482BD14983F808'),(0x2DF790,'8A013A0411750C'),
        (0x2DF79F,'4833C0C31BC083D8FFC3'),
        (0x2DF814,'488B0C0A480FC8480FC9483BC11BC083D8FFC3'),
        (0x1F21F,'4C8BC7483BF74C0F42C6E832052C00'),
        (0x1F29C,'483BFE7293'),
        (0x1F264,'4C8BC6483BDE4C0F42C3E8ED042C00'),
        (0x1F42E,'483BF30F8349FEFFFF'),
        (0x1F36F,'4C8BC7483BF74C0F42C6E8E2032C00'),
        (0x1F3D5,'483BFE72AA'),(0x1F43C,'483BF3738B')):
        raw=pe.bytes_at_va(pe.image_base+at,len(bytes.fromhex(expected)))
        require(raw,bytes.fromhex(expected),source,at)
        windows.append({'rva':at,'rawHex':raw.hex().upper()})
    return {'windows':windows,'level':'direct conditional byte-order comparison',
            'boundary':'The complete comparator consumes the supplied byte count using alignment bytes, bounded qword groups and remaining bytes. Equal prefixes return zero. Byte mismatches return -1/+1 using unsigned comparison flags; qword mismatches byte-swap both operands before the same unsigned ordering, preserving first-byte lexicographic order. The resolver supplies the smaller key/query byte length, then uses length comparisons to order equal prefixes, for both original and transformed queries. Hence a matching prefix alone is not key equality. No character decoding, case folding or locale comparison occurs in this reviewed helper. Its count is not an independent allocation bound; valid pointer extents and string construction/copy, tree invariants, actual keys and execution remain prerequisites. This does not establish a live lookup result, formatter selection or file identity.'}


def resolver_prefix_query(pe,*,source):
    """Conditional prefix extent, not live key equality or lookup success."""
    windows=[]
    for at,expected in (
        (0x1F2D6,'BA28000000488BCBE85D052C00'),
        (0x1F2EC,'482BC34883F8FF'),
        (0x1F2F9,'4C8BC84533C0488D542440488D4C2420E892FDFFFF'),
        (0x1F30E,'488BD0488D4C2420E855460000'),
        (0x1F0BD,'4C3941100F828F7A2C00488B4110492BC0493BC14C0F42C8'),
        (0x1F0D5,'488379180F7603488B094A8D14014D8BC1488BCBE8E2570000'),
        (0x2399C,'0F10070F11030F104F100F114B10'),
        (0x24973,'4C8BC348894718488BD648895F10498BCEE897A32B00')):
        raw=pe.bytes_at_va(pe.image_base+at,len(bytes.fromhex(expected)))
        require(raw,bytes.fromhex(expected),source,at)
        windows.append({'rva':at,'rawHex':raw.hex().upper()})
    return {'windows':windows,'queryStart':0,'delimiterByte':40,
            'level':'direct conditional prefix-range construction',
            'boundary':'After a successful delimiter search the resolver subtracts the query data pointer from the result, supplies that difference as requested length and supplies start zero to the subrange helper. The helper unsigned-checks start<=length, clamps requested length to length-start, selects inline or pointer bytes by capacity>15 and forwards source+start with the bounded count to a constructor. Its result is moved as two 16-byte halves into the second query carrier. For a valid successful search of the first left parenthesis this requests exactly the bytes before that delimiter, excluding parentheses and their suffix; it does not simply remove two final bytes. The reviewed search uses scalar and SIMD matching; no arbitrary no-match return guarantee is promoted from undefined BSF-zero destination contents. Allocation/copy/comparison helper semantics, malformed carriers, actual cache/tree contents and successful lookup remain unresolved. This conditional extent does not establish live equivalence between the requested and registered names.'}


def unity_loader_conversion(pe,*,source):
    """Selected conversion counts and end pointer; no successful API receipt."""
    bodies=[]
    for start,end,expected in (
        (0x22A130,0x22A235,'AEF375DB6CF045093078E4299BCCB8EF554CF3E39C8F1682350D542BCD7A539B'),
        (0x22A090,0x22A0D5,'3B05F568B8ED9FA3D4F39B42D3765B62FF2DAD7A61D1B0425E1E8D57C411FF7F'),
        (0xEDA2CA,0xEDA2DD,'CDFAA7C4BF101716557C796C22B29B593F21B1181CD5CA0670E9AE8AFCA6BB17'),
        (0xEDA2F2,0xEDA305,'F141693EAD546988017B299AD444ECE651B9904562BE0654D0CEF9C165CDC250'),
        (0x3CE6A0,0x3CE6B8,'90A3B5C1237913A161A55C77A96688A23E1FAD0DA89E369F0C9DC40BF754F202')):
        raw=pe.bytes_at_va(pe.image_base+start,end-start)
        require(len(raw),end-start,source,start)
        digest=hashlib.sha256(raw).hexdigest().upper()
        require(digest,expected,source,start)
        bodies.append({'rva':start,'byteLength':len(raw),'sha256':digest})
    caller=bytes.fromhex('E805BEF2FF488D9424A0000000488D4C2430E853BDF2FF')
    require(pe.bytes_at_va(pe.image_base+0x2FE326,len(caller)),caller,source,0x2FE326)
    return {'bodies':bodies,'callerRva':0x2FE326,'callerRawHex':caller.hex().upper(),
            'codePageArgument':65001,'flagsArgument':0,'elementByteLength':2,
            'level':'direct conditional count, terminator and end-pointer flow',
            'boundary':'The converter receives a pointer-to-input-pointer, a 64-bit input count and an output representation. With nonzero count its first selected MultiByteToWideChar import call receives ECX=65001, EDX=0, R8=input data, R9D=low DWORD input count, a null output and zero output count. A nonpositive EAX goes to an unreviewed reset helper. A positive EAX is sign-extended and used for capacity selection, stored length (or inline 12-length WORD encoding), and a zero WORD at data+2*length before a second import call. The second call uses the same input bytes/count and a helper-derived output data/count; its EAX survives the epilogue but the module caller does not inspect it before calling the end-pointer helper. That helper selects inline/pointer data and writes data+2*representationLength into its output slot. Its length leaf returns QWORD +0x10 unless tag BYTE +0x20=1, when it returns 12-zero-extended WORD +0x18; it preserves the R8 data register used by the end-pointer caller. Tag-two cold branches call a capacity helper before rejoining. Capacity allocation, reset and tag mutation remain unresolved, so neither output bounds nor conversion success is asserted. Representation length and the subsequent slash-loop end are not validated against the second API return. This is not Unicode parity, an OS binding receipt, a loaded-image hash or a SkillData final cursor.'}


def unity_loader_input(pe,*,source):
    """Exact selected caller's fixed inline request, not loaded image identity."""
    windows=[]
    # These are selected path windows, not whole-function coverage. The helper's
    # other branches cannot be selected by this caller's explicit tag=1/count=16.
    for start,end,expected in (
        (0x5579C0,0x557A20,'C8C0DCA5C01C98FA0E86CCCFB3563C582786D42C411A9BFDA6A16F1A8625DC7A'),
        (0xF48826,0xF48830,'603B5330B684DA48E711384D93EC77A08D666CD2F2F778E33918B2CCF13A3B26'),
        (0x74A60,0x74A99,'4AA8D511727CC6C391DE9337AE1A5E47AF18F4F3EF3F9D70D2C8649BAFBE47B9')):
        raw=pe.bytes_at_va(pe.image_base+start,end-start)
        require(len(raw),end-start,source,start)
        digest=hashlib.sha256(raw).hexdigest().upper()
        require(digest,expected,source,start)
        windows.append({'rva':start,'byteLength':len(raw),'sha256':digest})
    literal=b'GameAssembly.dll'
    require(pe.bytes_at_va(pe.image_base+0x187F180,16),literal,source,0x187F180)
    return {'windows':windows,'literalRva':0x187F180,'requestedModuleName':literal.decode('ascii'),
            'requestByteLength':16,'loaderCallRva':0x557A1B,'loaderRva':0x31E6C0,
            'level':'direct selected caller inline-byte construction and argument flow',
            'boundary':'The caller initializes a stack representation with tag BYTE +0x20=1, then calls a helper with count 16. On these explicit inputs the reviewed helper path compares count against 24 and returns the original representation address without mutating it or invoking other callees. The caller copies the exact 16-byte GameAssembly.dll literal to that address and writes a separate zero byte at +16. Its tag-one cold branch sets BYTE +0x18=8, rejoins the hot path and passes the same representation address in RCX to the reviewed module loader. The previously verified length helper therefore computes 24-8=16 on this carrier. Other capacity/helper branches and the caller after the loader call are outside this claim. This proves a static basename request, not actual invocation, conversion correctness, the selected module-cache entry, Windows search-path resolution, loaded absolute path or loaded image hash. It cannot certify a current GameAssembly binding or any SkillData source/cursor.'}


def unity_module_lookup(pe,*,source):
    """Selected loader/lookup control flow and import identities, not live bindings."""
    bodies=[]
    # Include split hot fragments and their explicit cold branch destinations.
    # Callees are not included in these extents or implicitly given semantics.
    for start,end,expected in (
        (0x2FE290,0x2FE40F,'F3362A1AE0D28E3F6EA2F4C0606C3FCE395EEE92AC7ED140172969691E5C3064'),
        (0xEFE324,0xEFE37B,'7BCEC022B9ACAB3E5D1EACBF5F25CFEC4E492BB9BD213BF1596A6F12D2637756'),
        (0x31E670,0x31E6B3,'20303ED34206BCD416A1CA61BCCE44C1022E929A69844EE7C5A5F9D730776624'),
        (0xF00A86,0xF00AFF,'76809E14C42148522DF78F2C0594B126180942EBA7F4F23C4EF0F41BB38BCB78'),
        (0x31E6C0,0x31E6DA,'CA1191138A5ECBDBA6B4E705D8C9FCB3C17F96B47989FCEAB060605A3EAA1DC1')):
        raw=pe.bytes_at_va(pe.image_base+start,end-start)
        require(len(raw),end-start,source,start)
        digest=hashlib.sha256(raw).hexdigest().upper()
        require(digest,expected,source,start)
        bodies.append({'rva':start,'byteLength':len(raw),'sha256':digest})
    optional=pe.u32_at_file(0x3C)+24
    require(pe.u32_at_file(optional+120),0x1C3624C,source,optional+120)
    require(pe.u32_at_file(optional+124),420,source,optional+124)
    require(pe.bytes_at_va(pe.image_base+0x1C3624C,20),
            struct.pack('<IIIII',0x1C36648,0,0,0x1C38088,0x185B258),source,0x1C3624C)
    require(pe.bytes_at_va(pe.image_base+0x1C38088,13),b'KERNEL32.dll\0',source,0x1C38088)
    imports=[]
    for at,index,name_rva,hint,name in (
        (0x2FE388,207,0x1C37618,0x3F7,b'LoadLibraryW'),
        (0x31E689,211,0x1C375CE,0x2DD,b'GetProcAddress'),
        (0x22A16A,216,0x1C3756A,0x423,b'MultiByteToWideChar'),
        (0x22A1F5,216,0x1C3756A,0x423,b'MultiByteToWideChar')):
        raw=pe.bytes_at_va(pe.image_base+at,6)
        require(len(raw),6,source,at)
        require(raw[:2],b'\xff\x15',source,at)
        slot=at+6+struct.unpack_from('<i',raw,2)[0]
        require(slot,0x185B258+index*8,source,at)
        lookup=0x1C36648+index*8
        require(pe.bytes_at_va(pe.image_base+lookup,8),struct.pack('<Q',name_rva),source,lookup)
        require(pe.bytes_at_va(pe.image_base+name_rva,len(name)+3),
                struct.pack('<H',hint)+name+b'\0',source,name_rva)
        imports.append({'callRva':at,'iatSlotRva':slot,'lookupSlotRva':lookup,
                        'nameRva':name_rva,'name':name.decode('ascii'),'dll':'KERNEL32.dll'})
    return {'bodies':bodies,'selectedImports':imports,'moduleHandleCacheRva':0x1CF4C20,
            'level':'exact selected import identities; direct conditional handle and lookup-result flow',
            'boundary':'The loader entry forwards its incoming RCX to a module helper, stores the returned RAX in the shared module-handle cache and exits on zero before the export-request body. The helper has a runtime-cache branch that returns a qword supplied by another helper. Its other branch extracts input representation data/length, invokes conversion helpers, iterates two-byte elements up to a helper-supplied end pointer replacing 0x2F with 0x5C, selects inline or pointer storage and passes it as RCX to the selected static LoadLibraryW import slot. The imported return is preserved, optionally stored through a cache helper, and returned after cleanup. The export lookup helper preserves incoming module/name arguments for the selected GetProcAddress import, returns its nonzero result, or returns zero for a null module. On a zero imported result its cold branch calls diagnostic/cleanup helpers and rejoins the return of the saved zero, conditional on those calls returning normally. Only the first import descriptor and three selected name thunks are joined, including both conversion calls to MultiByteToWideChar, not complete import-table coverage or live IAT contents. Cache lookup/insertion and string conversion helper semantics, end-pointer validity, actual input module path, loaded image identity, successful binding and execution remain unresolved. No authenticated SkillData source, final cursor or terminal uniqueness follows.'}


def unity_conversion_exports(pe,unity,*,source,unity_source):
    """Two selected export chains and conditional output-slot write ABI."""
    requests=[]
    for at,rawhex,name_at,name,export_name_at,name_slot,ordinal_slot,function_slot,index,target in (
        (0x3205CD,'488B0D4C469D01488D150D6D6601E890E0FFFF488905D14A9D01',0x19872E8,
         'il2cpp_string_new_len',0xCF8DAF9,0xCF8BC5C,0xCF8C0EE,0xCF8B5E4,243,0x24AD0),
        (0x31FA06,'488B0D13529D01488D1544636601E857ECFFFF48890538519D01',0x1985D58,
         'il2cpp_gc_wbarrier_set_field',0xCF8D0D4,0xCF8BAD8,0xCF8C02C,0xCF8B460,146,0xE170)):
        raw=bytes.fromhex(rawhex);literal=name.encode('ascii')+b'\0'
        require(unity.bytes_at_va(unity.image_base+at,len(raw)),raw,unity_source,at)
        require(unity.bytes_at_va(unity.image_base+name_at,len(literal)),literal,unity_source,name_at)
        for slot,expected in ((name_slot,struct.pack('<I',export_name_at)),
                              (ordinal_slot,struct.pack('<H',index)),(function_slot,struct.pack('<I',target))):
            require(pe.bytes_at_va(pe.image_base+slot,len(expected)),expected,source,slot)
        require(pe.bytes_at_va(pe.image_base+export_name_at,len(literal)),literal,source,export_name_at)
        requests.append({'name':name,'loaderRva':at,'rawHex':rawhex,'exportTargetRva':target,'ordinal':index+1})
    require(pe.bytes_at_va(pe.image_base+0xE177,6),bytes.fromhex('4C8BCA4C8902'),source,0xE177)
    return {'requests':requests,'level':'exact selected export identities; direct conditional output-slot store',
            'boundary':'Unity requests string_new_len into the first conversion cache and gc_wbarrier_set_field into the second. Selected GameAssembly export name/ordinal/function slots join the former to the previously reviewed byte-to-string constructor, and the latter to a leaf that writes R8 into [RDX] before optional atomic bitmap marking. The caller passes the first result in R8 and its separate output slot in RDX, then reads that slot. Conditional on these dynamic bindings and successful calls, the returned qword is the first constructor result, not a second newly constructed object. The barrier marking branch and constructor internal allocation helpers are not a live GC receipt. Loader module identity, actual cache bindings, lifecycle, input validity, query normalization and concrete directory remain unresolved. Only selected export chains are joined, not full export coverage.'}


def unity_path_return(pe,*,source):
    """Selected return-slot and string representation, not runtime path value."""
    windows=[]
    for rva,expected in (
        (0x32BA24,'488D4C2420E822000000488BD0488D4C2460E88502FAFF'),
        (0x32BA3B,'488D4C2420E8CB8ED4FF488B442460'),
        (0x32BA63,'4C8D0596245401488BCB488D542420E819000000'),
        (0x2CBCC6,'488BD94C8BCA488BCAE81C8FDAFF'),
        (0x2CBCD4,'80792001751F448BC0488D4C2430498BD1E816000000'),
        (0x2CBCEA,'488B08488BC348890B'),(0x2CBCF9,'4D8B09EBDC'),
        (0x74BF0,'807920017405488B4110C3480FBE5118B818000000482BC2C3'),
        (0x2CBD06,'488B05AB93A2014C8BCA488BD9418BD0498BC9FFD0'),
        (0x2CBD1B,'4C8BC0488D54243033C9FF152D8EA201488B442430488903')):
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(expected)))
        require(raw,bytes.fromhex(expected),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    literal=b'StreamingAssets\0'
    require(pe.bytes_at_va(pe.image_base+0x186DF00,len(literal)),literal,source,0x186DF00)
    return {'windows':windows,'literal':'StreamingAssets','representationTagOffset':32,
            'level':'direct conditional return-slot flow',
            'boundary':'The selected registered target builds a temporary representation, passes it to a converter with a separate output slot, cleans up the temporary and returns that output qword. A nested builder supplies the exact StreamingAssets literal to another helper, not proof of concatenation semantics or root value. The converter length helper returns QWORD +0x10 unless BYTE +0x20 equals one; on that branch it returns 24 minus sign-extended BYTE +0x18. The same tag chooses inline representation versus the pointer at +0. Only the low DWORD length reaches the next helper. That helper calls a dynamic function with data pointer and length, then forwards its result to a second dynamic function with a separate output slot and returns the slot qword. These calls are not yet verified managed-string constructors. Dynamic targets, allocation/cleanup and joining helpers, underlying path initialization, tag validity and actual execution remain unresolved; no authenticated file or runtime directory is asserted.'}


def unity_registration_pair(pe,*,source):
    """Shared native loop index proves static pairing, not active registration."""
    body=pe.bytes_at_va(pe.image_base+0x3BF7C0,0x53)
    require(hashlib.sha256(body).hexdigest().upper(),
            'DAA468EB7D4B399BCE0FCEB29186340606D92272D61C56D5D08D4FC158888AB7',source,0x3BF7C0)
    count=0xF7E;values_rva=0x19DD250;names_rva=0x19E4E40
    values_raw=pe.bytes_at_va(pe.image_base+values_rva,count*8)
    names_raw=pe.bytes_at_va(pe.image_base+names_rva,count*8)
    require(len(values_raw),count*8,source,values_rva)
    require(len(names_raw),count*8,source,names_rva)
    rows=[]
    for i,((value,),(name,)) in enumerate(zip(struct.iter_unpack('<Q',values_raw),struct.iter_unpack('<Q',names_raw))):
        # Addressability only: not complete name strings or function bodies.
        require(len(pe.bytes_at_va(value,1)),1,source,values_rva+i*8)
        require(len(pe.bytes_at_va(name,1)),1,source,names_rva+i*8)
        rows.append({'index':i,'nameVa':name,'valueVa':value})
    selected=rows[299]
    require(selected['nameVa'],pe.image_base+0x19F1D50,source,names_rva+299*8)
    require(selected['valueVa'],pe.image_base+0x32BA20,source,values_rva+299*8)
    literal=b'UnityEngine.Application::get_streamingAssetsPath\0'
    require(pe.bytes_at_va(selected['nameVa'],len(literal)),literal,source,0x19F1D50)
    return {'loopRva':0x3BF7C0,'loopSha256':hashlib.sha256(body).hexdigest().upper(),
            'namesRva':names_rva,'valuesRva':values_rva,'slotByteLength':8,
            'summary':{'success':count,'failed':0,'unsupported':0},'rows':rows,
            'selected':dict(selected,name=literal[:-1].decode('ascii')),
            'level':'direct static name/value argument pairing',
            'boundary':'The complete loop starts at index zero, derives image base with RIP-relative LEA, loads RDX and RCX from separate arrays using the same byte offset, calls the reviewed forwarder and advances by eight until 0xF7E entries. Both complete pointer vectors are bounded and every target is checked for one-byte addressability only; this is not complete string/body decoding. Entry 299 independently pairs the selected interface name with RVA 0x32BA20. The registered name lacks the parentheses in the resolver request, so matching still depends on the unclosed query helper path. Loop invocation, callback effects, dynamic export resolution, tree insertion, duplicate registrations and the selected target body/return ABI remain unresolved. No current directory or authenticated-file identity is inferred.'}


def unity_registration_forwarder(pe,*,source):
    """Selected dynamic export request and forwarding, not live binding."""
    raw=pe.bytes_at_va(pe.image_base+0x3BF270,0x6A)
    require(hashlib.sha256(raw).hexdigest().upper(),
            'B5EAB384DA5D794DB6D62A17D18789C09FB178E6BA346BB0EB3F12D1A739BCB3',source,0x3BF270)
    windows=[]
    for rva,value in ((0x31E8F9,'488B0D20639D01488D15F1536601E864FDFFFF488905AD669D01'),
                      (0x3BF2D3,'48FF25E65C9301')):
        chunk=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(value)))
        require(chunk,bytes.fromhex(value),source,rva)
        windows.append({'rva':rva,'rawHex':chunk.hex().upper()})
    name=b'il2cpp_add_internal_call\0'
    require(pe.bytes_at_va(pe.image_base+0x1983CF8,len(name)),name,source,0x1983CF8)
    return {'windows':windows,'forwarderRva':0x3BF270,'forwarderByteLength':len(raw),
            'forwarderSha256':hashlib.sha256(raw).hexdigest().upper(),
            'requestedExport':name[:-1].decode('ascii'),'functionCacheRva':0x1CF4FC0,
            'level':'exact static request; direct conditional two-argument forwarding',
            'boundary':'A selected loader window supplies a module-handle carrier and the NUL-terminated export name to a dynamic lookup helper, then stores its result in the function cache. The full reviewed forwarding function preserves the two entry arguments, passes them to each selected callback in a separately stored pointer array when its count is positive, then tail-jumps through that same function cache with the original arguments. The zero-callback branch reaches the same tail jump. This connects requested export name to a conditional cache consumer, not the actual module handle, resolved function identity, successful initialization or runtime execution. Callback identities/state, lookup helper cold paths, registration callers and concrete interface-name/function-value pairs remain unresolved. The nearby interface-name pointer array is only a lead and is not joined by position or matching counts.'}


def vfs_root_resolver(pe,*,source):
    """Static requested interface and conditional cache flow, not actual root."""
    windows=[]
    for rva,expected in (
        (0x2F46CD9,'E8325F9F00'),(0x2F46CE5,'488BD8'),
        (0x2F46CFD,'488B89B800000048895908'),
        (0x2F46CA7,'488B80B8000000488B4008'),
        (0x393CC14,'488B052D12570A4885C07407'),
        (0x393CC20,'4883C42848FFE0'),
        (0x393CC27,'488D0D1A7BEF06E87D256EFC'),
        (0x393CC3C,'4889050512570AEBDB'),
        (0x1F1DC,'4C8B2D7515E90D498B5D084D8BFD'),
        (0x1F293,'498B4740E957010000'),
        (0x1F2D6,'BA28000000488BCBE85D052C00'),
        (0x1F32A,'4C8B2D2714E90D498B5D084D8BFD'),
        (0x1F3CC,'4D3BFD751133DBEB11'),
        (0x1F3E2,'498B5F40'),(0x1F3F0,'488BC3'),
        (0x2E6B64,'48C7C0FFFFFFFFE97F87D3FF'),
        (0x2076F,'4889542410'),(0x2077D,'488BEC'),
        (0x207E6,'4C8B256BFFE80D'),
        (0x208BB,'488D1D96FEE80D'),
        (0x208CA,'B948000000E848301700'),
        (0x208DD,'0F1045D80F1140200F104DE80F114830'),
        (0x20924,'E837FCFFFF4C8BE8488B453849894540'),
        (0xF872C,'4889052580DB0D4889052680DB0D'),
        (0xF873F,'488900488940084889401066C7401801014889050180DB0D'),
        (0xCF8B1F0,'00000000FFFFFFFF0000000044C2F80C010000009E0100009E01000018B2F80C90B8F80C08BFF80C'),
        (0xCF8B914,'EFC4F80C'),(0xCF8BF4A,'2100'),
        (0xCF8B29C,'30050200'),(0x20530,'E92B020000')):
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(expected)))
        require(raw,bytes.fromhex(expected),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    name=b'UnityEngine.Application::get_streamingAssetsPath()\0'
    require(pe.bytes_at_va(pe.image_base+0xA834748,len(name)),name,source,0xA834748)
    export_name=b'il2cpp_add_internal_call\0'
    require(pe.bytes_at_va(pe.image_base+0xCF8C4EF,len(export_name)),export_name,source,0xCF8C4EF)
    return {'windows':windows,'requestedInterface':name[:-1].decode('ascii'),
            'nameRva':0xA834748,'functionCacheRva':0xDEADE48,
            'lookupCarrierGlobalRva':0xDEB0758,'candidateValueOffset':64,
            'registrationWriterRva':0x20760,'sentinelInitializerRva':0xF8718,
            'selectedWriterExport':{'name':export_name[:-1].decode('ascii'),
                                    'ordinal':34,'stubRva':0x20530},
            'level':'exact static resolver name; direct conditional cache flow',
            'boundary':'The normal non-replacement streaming-path getter initialization branch calls the wrapper, preserves RAX in RBX and stores it in static carrier+8; the normal return reads that slot. The wrapper loads a cached function pointer and tail-jumps to it when nonnull. On cache miss it passes the exact NUL-terminated interface name to the resolver, checks the result, stores that result in the same function-pointer cell and tail-jumps. The requested name is not a verified resolved function identity, ABI or actual directory. The resolver loads a runtime tree carrier from a static global, follows child pointers using comparison helper results and returns candidate node+0x40 after its first lookup. If that lookup chooses the sentinel, it constructs a second query through helpers (including a search passed byte 0x28) and traverses the same carrier again; a final sentinel yields zero, otherwise node+0x40 supplies the result. The independently reviewed writer scans the first argument to a NUL byte, prepares a 32-byte key carrier and searches the same global tree. Its insertion path requests 0x48 bytes, copies the key carrier into node+0x20 and calls an insertion helper; both existing-candidate and returned-node paths store the original second argument into node+0x40. A separate initializer zeroes two global slots, requests 0x48 bytes, writes self pointers at node+0/+8/+0x10 and marker WORD 0x0101 at +0x18, then stores that pointer in the lookup global. Neither function being present proves initialization, insertion success or actual selected name/value pairs. The selected PE export header, name-pointer slot, ordinal-index slot and function slot independently join il2cpp_add_internal_call (ordinal 34) to a five-byte tail-jump stub into this writer, preserving incoming arguments. Only this selected export chain is certified, not complete export-table coverage; the stub is not assigned to the preceding pdata entry. Export callers and their actual name/value arguments, insertion/allocator internals, string construction/comparison/search/subrange helper semantics and live contents, replacement/cold failure paths, class initialization, comparison predicate semantics, live cache contents and the final path/file/hash connection remain unresolved.'}


def vfs_string_carrier(pe,*,source):
    """Conditional literal conversion and character-reader carrier connection."""
    windows=[]
    for rva,expected in (
        (0x2CB7624,'4C6341108BC2493BC07D0D4863C20FB7444114'),
        (0x24AD6,'448BC2488BD1488D4C2420E87A000000'),
        (0x24AE7,'488D4C242048837C243807480F474C24208B542430E86F0D0000'),
        (0x24BB2,'0FB60A80F980730C440FB6C141B901000000'),
        (0x24CC1,'0FB61E0FB60E80F9800F833C01000048FFC6'),
        (0x24CED,'488D480148894F10488BCF48837F18077603488B0F66891C416644896C4102'),
        (0x259DC,'897B10664489647B14'),
        (0x259FB,'4C8BC7488D4B144D03C0498BD6E813932B00')):
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(expected)))
        require(raw,bytes.fromhex(expected),source,rva)
        windows.append({'rva':rva,'rawHex':raw.hex().upper()})
    return {'windows':windows,'lengthOffset':16,'elementDataOffset':20,'elementByteLength':2,
            'level':'direct conditional native carrier flow; ASCII widening branch',
            'boundary':'The format-item comma helper zero-extends the input DWORD index before comparing it with sign-extended carrier length at +0x10; for nonnegative length this rejects negative indices as well as indices at or above length. The accepted path returns the zero-extended WORD at carrier+0x14+index*2. Literal construction forwards its input pointer and zero-extended DWORD byte count into a temporary 32-byte conversion carrier. On the reviewed ASCII branch each byte below 0x80 becomes one 16-bit element, the temporary element count advances by one, and a following zero WORD is written. The wrapper chooses inline versus pointer storage by capacity>7 and forwards the low DWORD element count. The next helper writes result+0x10 length and a zero WORD at result+0x14+count*2 on its nonempty allocation path, then calls the copy helper with destination result+0x14, original element pointer and count*2. These offsets independently agree with the format-item reader. Allocation/capacity/copy helpers, empty singleton contents, non-ASCII cold/error branches, cache initialization and actual execution remain unresolved; this is not complete Unicode conversion parity or proof of a runtime output path.'}


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
            'boundary':'The caller supplies RCX result storage, RDX format carrier and R8D opening-brace index; the helper returns the same storage in RAX. Main and separate cold fragments were reviewed together. Reads use carrier+0x14 and two-byte indices, with length at +0x10. The numeric selector is decimal accumulated and must be below 16 before proceeding. Normal return writes all 32 result bytes: selector, zero padding, a zero span or nonempty colon-span pointer with count and zero padding, index one past the closing brace, and a comma-derived numeric value (zero when absent). The nonempty span excludes colon and closing brace and checks start/count against carrier length. The caller copies both 16-byte halves and reads result+0x18; this is a local item cursor, not whole-format EOF. The character helper is separately joined in selectedVfsStringCarrier; error helper behavior, arbitrary-input validity, string-construction ABI, nested generic formatting and actual execution remain unresolved. No full grammar emulator or runtime output path is asserted.'}


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
    buff_path=ROOT/'reports/animestudio/buffdata_current_latest.json'
    buff_sha=sha(buff_path);buff_corpus=json.loads(buff_path.read_text(encoding='utf-8'))
    verify_family_report_inputs(buff_corpus,expected_format='animestudio-buffdata-current-vfs-corpus',label='BuffData')
    require(buff_corpus['inputSetSha256'],corpus['inputSetSha256'],buff_path)
    require(buff_corpus['status'],'complete',buff_path)
    mapper_path = ROOT / 'tools/endfield-il2cpp/map_body_targets_to_gameassembly.py'
    catalog_path = ROOT / 'tools/endfield-il2cpp/catalog_option_flow_metadata.py'
    sources = [Path(__file__), Path(__file__).with_name('il2cpp_context.py'),
               mapper_path, catalog_path, ROOT / 'scripts/common.py',
               Path(__file__).with_name('buff_ec_native.json'),
               Path(__file__).with_name('buff_50_native.json'),
               Path(__file__).with_name('buff_11f_native.json'),
               Path(__file__).with_name('buff_b4_native.json'),
               Path(__file__).with_name('buff_56_native.json'),
               Path(__file__).with_name('buff_92_native.json'),
               Path(__file__).with_name('buff_57_native.json'),
               Path(__file__).with_name('buff_5b_native.json'),
               Path(__file__).with_name('buff_3c_native.json'),
               Path(__file__).with_name('buff_78_native.json'),
               Path(__file__).with_name('buff_b2_native.json'),
               Path(__file__).with_name('buff_68_native.json'),
               Path(__file__).with_name('buff_81_native.json'),
               Path(__file__).with_name('buff_58_native.json'),
               Path(__file__).with_name('buff_02_native.json'),
               Path(__file__).with_name('buff_9a_native.json'),
               Path(__file__).with_name('buff_a2_native.json'),
               Path(__file__).with_name('buff_65_native.json'),
               Path(__file__).with_name('buff_169_native.json'),
               Path(__file__).with_name('buff_157_native.json'),
               Path(__file__).with_name('buff_6e_native.json'),
               Path(__file__).with_name('buff_fe_native.json'),
               Path(__file__).with_name('buff_96_native.json'),
               Path(__file__).with_name('buff_fd_native.json'),
               Path(__file__).with_name('buff_7c_native.json'),
               Path(__file__).with_name('buff_b6_native.json'),
               Path(__file__).with_name('buff_80_native.json'),
               Path(__file__).with_name('buff_16e_native.json'),
               Path(__file__).with_name('buff_7b_native.json'),
               Path(__file__).with_name('buff_6d_native.json'),
               Path(__file__).with_name('buff_136_native.json'),
               Path(__file__).with_name('buff_163_native.json'),
               Path(__file__).with_name('buff_69_native.json'),
               Path(__file__).with_name('buff_44_native.json')]
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
    adapter_conversion=adapter_conversion_context(pe,md,reg,table,adapter_entries,source=str(gate.gameassembly))
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
    nested_context=nested_reader_context(pe,md,modules,image_owners,reg,table,
                                         source=str(gate.gameassembly),metadata_source=str(gate.metadata))
    list_candidate=list_formatter_candidate(pe,md,modules,image_owners,reg,code,table,spec_records,methods_raw,
                                            source=str(gate.gameassembly))
    list_dispatch=list_element_dispatch(pe,source=str(gate.gameassembly))
    list_shared=list_element_shared_context(pe,table,reg,code,spec_records,methods_raw,source=str(gate.gameassembly))
    list_null_probe=list_element_null_probe(pe,source=str(gate.gameassembly))
    list_value_flow=list_element_value_flow(pe,source=str(gate.gameassembly))
    element_provider=element_provider_state_flow(pe,source=str(gate.gameassembly))
    buff_routes=buff_union_routes(pe,md,reg,modules,image_owners,source=str(gate.gameassembly))
    buff_forwarding=buff_ifelse_forwarding(pe,md,reg,table,source=str(gate.gameassembly))
    buff_order=buff_ifelse_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly))
    buff_sequence=buff_sequence_read_order(pe,md,modules,image_owners,source=str(gate.gameassembly))
    buff_tag76=buff_tag76_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly))
    buff_ec=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_ec_native.json'))
    buff_50=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_50_native.json'))
    buff_11f=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_11f_native.json'))
    buff_b4=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_b4_native.json'))
    buff_56=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_56_native.json'))
    buff_92=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_92_native.json'))
    buff_57=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_57_native.json'))
    buff_9a=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_9a_native.json'))
    buff_a2=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_a2_native.json'))
    buff_65=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_65_native.json'))
    buff_169=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_169_native.json'))
    buff_157=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_157_native.json'))
    buff_6e=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_6e_native.json'))
    buff_fe=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_fe_native.json'))
    buff_96=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_96_native.json'))
    buff_fd=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_fd_native.json'))
    buff_7c=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_7c_native.json'))
    buff_b6=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_b6_native.json'))
    buff_80=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_80_native.json'))
    buff_16e=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_16e_native.json'))
    buff_44=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_44_native.json'))
    buff_69=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_69_native.json'))
    buff_163=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_163_native.json'))
    buff_136=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_136_native.json'))
    buff_6d=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_6d_native.json'))
    buff_7b=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_7b_native.json'))
    buff_02=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_02_native.json'))
    buff_58=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_58_native.json'))
    buff_81=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_81_native.json'))
    buff_68=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_68_native.json'))
    buff_b2=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_b2_native.json'))
    buff_78=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_78_native.json'))
    buff_3c=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_3c_native.json'))
    buff_5b=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_5b_native.json'))
    list_candidate['bodyWindows']=[]
    for start,end,digest in (
        (0x3BA40F0,0x3BA4364,'6D15262413608863F8223A3A1F9465529CD29B6129E3B390D7DAC8179E77DEAA'),
        (0x4ECA65C,0x4ECA705,'5B65758E858AF46037B7133644A3A9264E3FD4AA1D87B479B80A240EB0A31A90')):
        require(hashlib.sha256(pe.bytes_at_va(pe.image_base+start,end-start)).hexdigest().upper(),digest,gate.gameassembly,start)
        list_candidate['bodyWindows'].append({'rva':start,'byteLength':end-start,'sha256':digest})
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
    string_carrier=vfs_string_carrier(pe,source=str(gate.gameassembly))
    root_resolver=vfs_root_resolver(pe,source=str(gate.gameassembly))
    prefix_query=resolver_prefix_query(pe,source=str(gate.gameassembly))
    key_comparison=resolver_key_comparison(pe,source=str(gate.gameassembly))
    unity_path=gate.gameassembly.with_name('UnityPlayer.dll')
    unity_pe=mapper.PeImage(unity_path)
    require(hashlib.sha256(unity_pe.buf).hexdigest().upper(),UNITY_SHA,unity_path)
    unity_forwarder=unity_registration_forwarder(unity_pe,source=str(unity_path))
    unity_pair=unity_registration_pair(unity_pe,source=str(unity_path))
    unity_path_evidence=unity_path_return(unity_pe,source=str(unity_path))
    unity_exports=unity_conversion_exports(pe,unity_pe,source=str(gate.gameassembly),unity_source=str(unity_path))
    unity_lookup=unity_module_lookup(unity_pe,source=str(unity_path))
    unity_input=unity_loader_input(unity_pe,source=str(unity_path))
    unity_conversion=unity_loader_conversion(unity_pe,source=str(unity_path))
    for start,end,expected in (
        (0x32BA20,0x32BA4F,'91C1865559D71D25761B6C551458A116EFF8627187BF5D956EE06A913D94859B'),
        (0x32BA50,0x32BA8A,'D1A40F21F2A58620BC46D667AF2C16770354F1A5B4E2D9578ACB07AD10BAC48F'),
        (0x2CBCC0,0x2CBCFE,'A4BF4C13EC67E4C0D35956DB7EE2B19AF80604A19E48664821050D8F2AB7D015'),
        (0x2CBD00,0x2CBD3C,'EB78D7B88E5827D4DC6B440287BCE1AAC6C22D9550AA80B32E0163E96D2B02A0'),
        (0x74BF0,0x74C09,'FAFE139CBBA402A8EA97D77D582388541E95BED7B63400896A7A053BB1D70C47')):
        require(hashlib.sha256(unity_pe.bytes_at_va(unity_pe.image_base+start,end-start)).hexdigest().upper(),expected,unity_path,start)
    require(sha(unity_path),UNITY_SHA,unity_path)
    native_gate()
    require(sha(corpus_path), CORPUS_SHA, corpus_path)
    verify_current_report_inputs(corpus)
    require(sha(buff_path),buff_sha,buff_path)
    verify_family_report_inputs(buff_corpus,expected_format='animestudio-buffdata-current-vfs-corpus',label='BuffData')
    for path, expected in source_hashes.items():
        require(sha(path), expected, path)
    return {
        'schemaVersion': 1, 'status': 'failed' if failures else 'structural-only',
        'inputSetSha256': corpus['inputSetSha256'],
        'buffCorpusReference':{'path':str(buff_path),'sha256':buff_sha,'summary':buff_corpus['summary'],
                               'inputSetSha256':buff_corpus['inputSetSha256']},
        'corpusReference': {'path': str(corpus_path), 'sha256': CORPUS_SHA,
                            'boundary': 'Authenticated corpus reference; this native audit does not restream VFS bytes.'},
        'nativeInputs': {'gameassembly': str(gate.gameassembly), 'gameassemblySha256': GA_SHA,
                         'metadata': str(gate.metadata), 'metadataSha256': MD_SHA,
                         'unityplayer':str(unity_path),'unityplayerSha256':UNITY_SHA},
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
        'selectedVfsStringCarrier':string_carrier,
        'selectedVfsRootResolver':root_resolver,
        'selectedResolverPrefixQuery':prefix_query,
        'selectedResolverKeyComparison':key_comparison,
        'selectedUnityRegistrationForwarder':unity_forwarder,
        'selectedUnityRegistrationPair':unity_pair,
        'selectedUnityPathReturn':unity_path_evidence,
        'selectedUnityConversionExports':unity_exports,
        'selectedUnityModuleLookup':unity_lookup,
        'selectedUnityLoaderInput':unity_input,
        'selectedUnityLoaderConversion':unity_conversion,
        'selectedReaderConstruction':construction_evidence,
        'selectedReaderCursorConsumers':cursor_evidence,
        'selectedWrapperConsumer':wrapper_evidence,
        'selectedNestedReaderContext':nested_context,
        'selectedListFormatterCandidate':list_candidate,
        'selectedListElementDispatch':list_dispatch,
        'selectedListElementSharedContext':list_shared,
        'selectedListElementNullProbe':list_null_probe,
        'selectedListElementValueFlow':list_value_flow,
        'selectedAdapterConversionContext':adapter_conversion,
        'selectedElementProviderStateFlow':element_provider,
        'selectedBuffUnionRoutes':buff_routes,
        'selectedBuffIfElseForwarding':buff_forwarding,
        'selectedBuffIfElseReadOrder':buff_order,
        'selectedBuffSequenceReadOrder':buff_sequence,
        'selectedBuffTag76ReadOrder':buff_tag76,
        'selectedBuffEcReadOrder':buff_ec,
        'selectedBuff50ReadOrder':buff_50,
        'selectedBuff11fReadOrder':buff_11f,
        'selectedBuffB4ReadOrder':buff_b4,
        'selectedBuff56ReadOrder':buff_56,
        'selectedBuff92ReadOrder':buff_92,
        'selectedBuff57ReadOrder':buff_57,
        'selectedBuff5bReadOrder':buff_5b,
        'selectedBuff3cReadOrder':buff_3c,
        'selectedBuff78ReadOrder':buff_78,
        'selectedBuffB2ReadOrder':buff_b2,
        'selectedBuff68ReadOrder':buff_68,
        'selectedBuff81ReadOrder':buff_81,
        'selectedBuff58ReadOrder':buff_58,
        'selectedBuff02ReadOrder':buff_02,
        'selectedBuff9AReadOrder':buff_9a,
        'selectedBuffA2ReadOrder':buff_a2,
        'selectedBuff65ReadOrder':buff_65,
        'selectedBuff169ReadOrder':buff_169,
        'selectedBuff157ReadOrder':buff_157,
        'selectedBuff6EReadOrder':buff_6e,
        'selectedBuffFEReadOrder':buff_fe,
        'selectedBuff96ReadOrder':buff_96,
        'selectedBuffFDReadOrder':buff_fd,
        'selectedBuff7CReadOrder':buff_7c,
        'selectedBuffB6ReadOrder':buff_b6,
        'selectedBuff80ReadOrder':buff_80,
        'selectedBuff16EReadOrder':buff_16e,
        'selectedBuff7BReadOrder':buff_7b,
        'selectedBuff6DReadOrder':buff_6d,
        'selectedBuff136ReadOrder':buff_136,
        'selectedBuff163ReadOrder':buff_163,
        'selectedBuff69ReadOrder':buff_69,
        'selectedBuff44ReadOrder':buff_44,
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
