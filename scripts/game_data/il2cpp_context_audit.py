"""Exact-build, read-only generic-instantiation audit; JSON is emitted to stdout.

No runtime MethodInfo or serialized source cursor is inferred. Native tables
are referenced PE extents, not a claim to consume the entire PE to EOF.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import struct
import sys
from pathlib import Path

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp_context import ContextError, GenericInstantiationTable, method_parameter_owner, type_image_owners, match_image_modules, method_spec_usage_index, generic_type_carrier, select_rgctx_range, unresolved_usage_index, rip_qword_load_target
from scripts.game_data.memorypack.skill_corpus import verify_current_report_inputs
from scripts.game_data.memorypack.corpus_gate import verify_current_report_inputs as verify_family_report_inputs
from scripts.game_data.memorypack.skill_terminal import TerminalError as SkillTerminalError
from scripts.game_data.memorypack.skill_terminal import frame_skill_terminal_at
from scripts.game_data.memorypack.buff import read_skill_gameplay_tag_list_field
from scripts.game_data.memorypack.buff import read_skill_toggle_buff_data
from scripts.game_data.memorypack.buff import read_skill_ui_range_hint_data
from scripts.game_data.il2cpp_context import class_sharing_branch
from scripts.game_data.il2cpp_context import named_top_level_type
from scripts.game_data.il2cpp_context import object_type_comparison_key
from scripts.game_data.il2cpp_context import method_pointer_indices, generic_method_candidates
from scripts.game_data.il2cpp_context import type_parameter_owner, rgctx_range_entries
from scripts.game_data.il2cpp_context import method_spec_record, usage_method_spec, relative_branch_target, method_token_pointer
from scripts.game_data.il2cpp_context import literal_record

from scripts.repo_paths import REPO_ROOT

ROOT = REPO_ROOT
GA_SHA = 'C24495E51B406F03B03890C4788EE618AE022C991405BE5D5B8B787CB775AE89'
MD_SHA = '0076743397ACADF03D3B0064343A963C7C88863B8160526D397E4B3EFB96F02E'
UNITY_SHA = 'BEE7BE52370ADDDD67BA61E4937CA51B7F272656841D187E95E505496DA798D1'
CORPUS_SHA = '172EF3021E4A2956F08380A84A238A872C8F6293B555A427E832105E61609800'
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
    (0x32CCF70,0x32CD277,'CB497F6362D9DA9396D6533F6CC037536FC9499D67848F1E8BBBAC8AA2F03688'),
    (0x32CE4B0,0x32CE75C,'1FB17BEDE173176E0BC082E7C315267B6FC6F3CE76796DB90A627E9B0E9D7767'),
    (0x32CE860,0x32CE8C0,'1F6F3F32B14A6DCBB87743E94C1DB14106B3AB3EE17D6C6EBB14F7DB0347A3EB'),
    (0x32CE8C0,0x32CE920,'D0D022A7D27D843AD4BFFE86FEC8A5FA07037249273A8ECB5AEC0167FEF98F33'),
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
    verified_source_read_calls = verify_contract_source_read_calls(
        pe, contract, source=source)
    return {'contractPath':str(path),'contractSha256':sha(path),'methods':methods,
        'codeWindows':contract['codeWindows'],'dataWindows':contract.get('dataWindows',[]),'nestedContexts':contract['nestedContexts'],
        'anonymousReadOrder':contract['anonymousReadOrder'],
        'verifiedSourceReadCallSites':verified_source_read_calls,
        'level':'direct selected consumer order; exact static nested type joins; structural-only parser profile',
        'boundary':contract['boundary']}


def verify_contract_source_read_calls(pe, contract, *, source):
    """Verify contract-pinned direct source-reader calls against the selected PE."""
    rows = contract.get('sourceReadCallSites', [])
    if not isinstance(rows, list):
        raise ContextError(source, 0, 'sourceReadCallSites array', rows)
    if not rows:
        return []
    read_orders = contract.get('anonymousReadOrder')
    if not isinstance(read_orders, dict) or len(read_orders) != 1:
        raise ContextError(source, 0, 'one root member read-order for source callsites',
                           read_orders)
    root_key, root_order = next(iter(read_orders.items()))
    if not isinstance(root_order, list) or not re.search(r'member\d+$', root_key):
        raise ContextError(source, 0, 'root member-count key and read-order array',
                           [root_key, root_order])
    verified = []
    seen = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ContextError(source, index, f'source read callsite {index} object', row)
        member_index = row.get('memberIndex')
        read_type = row.get('readType')
        instruction_rva = row.get('callInstructionRva')
        target_rva = row.get('targetRva')
        if (type(member_index) is not int or not 0 <= member_index < len(root_order) or
                type(instruction_rva) is not int or type(target_rva) is not int or
                not isinstance(read_type, str)):
            raise ContextError(source, index,
                               f'source read callsite {index} bounded member/RVA fields', row)
        require(root_order[member_index], read_type, source, instruction_rva)
        if instruction_rva in seen:
            raise ContextError(source, instruction_rva,
                               'unique source read call instruction RVA', instruction_rva)
        seen.add(instruction_rva)
        raw = pe.bytes_at_va(pe.image_base + instruction_rva, 5)
        require(raw[:1], b'\xE8', source, instruction_rva)
        target = relative_branch_target(raw, pe.image_base + instruction_rva, source=source)
        require(target, pe.image_base + target_rva, source, instruction_rva)
        verified.append({
            'rootReadOrderKey': root_key,
            'memberIndex': member_index,
            'readType': read_type,
            'callInstructionRva': instruction_rva,
            'instructionByteLength': len(raw),
            'rawHex': raw.hex().upper(),
            'targetRva': target - pe.image_base,
            'classification': 'exact-build direct E8 source-reader call',
        })
    return verified


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
    root_methods=[row for row in methods if row.get('methodIndex')==104346]
    require(len(root_methods),1,source,0x39C6AA0)
    require(root_methods[0].get('pointerVa')-pe.image_base,0x39C6AA0,source,0x39C6AA0)
    root_windows=[(start,end,digest) for start,end,digest in CONSUMER_WINDOWS
                  if start==0x39C6AA0]
    require(root_windows,[(0x39C6AA0,0x39C6FA7,
                           '6444AF67AF86E7809AF5A50AE6DEE922B699DCB1CA686DC81F4C3584AB817B90')],
            source,0x39C6AA0)
    root_start,root_end,root_sha=root_windows[0]
    return {'methods':methods,'windows':windows,
        'rootCodeWindow':{'startRva':root_start,'endRva':root_end,'sha256':root_sha},
        'level':'direct conditional selected-consumer structure',
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
    root_windows=[(start,end,digest) for start,end,digest in CONSUMER_WINDOWS
                  if start==0x3774060]
    require(root_windows,[(0x3774060,0x37742A8,
                           'AC1FF978FEF71639E74980B43AE00D9746518A9DD94B41772F2867963A596ED8')],
            source,0x3774060)
    root_start,root_end,root_sha=root_windows[0]
    return {'methods':methods,'windows':windows,'orderedCalls':calls,'nestedOperands':operands,
        'nestedMethodSpecIndex':619962,'nestedMethodSpecRawHex':raw.hex().upper(),
        'nestedTypeDefinition':9202,
        'nestedTypeName':'Beyond.Gameplay.Core.SequenceActionData',
        'nestedInstantiation':instance.as_dict(),
        'rootCodeWindow':{'startRva':root_start,'endRva':root_end,
                          'sha256':root_sha},
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
        (0x3910618,'488B1589297009'),
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
        (0x3910D20,'488B15A1CA7809488B0BE8F12A6FFC488BCF4885C00F8537835501488B153EC9'),
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
        (0x390F2C2,'488B1507AC7209488B0BE84F456FFC488BCF4885C00F8515795501488B1534287D09E857EB10FD488903488BD0E9EEE6FFFF'),
        (0x390EE44,'488B159D676F09488B0BE8CD496FFC488BCF4885C00F857E965501488B155A217D09E8F90111FD488903488BD0E96CEBFFFF'),
        (0x390E228,'488B1529A97809488B0BE8E9556FFC488BCF4885C00F8528935501488B15462E7D09E8010411FD488903488BD0E988F7FFFF'),
        (0x390E642,'488B15BF147909488B0BE8CF516FFC488BCF4885C00F85F0935501488B15AC2C7D09E89B0311FD488903488BD0E96EF3FFFF'),
        (0x390D9FA,'488B1587756F09488B0BE8175E6FFC488BCF4885C00F85F6AB5501488B15BC2D7D09E8DF08A0FC488903488BD0EBB9'),
        (0x390F25E,'488B152BA67709488B0BE8B3456FFC488BCF4885C00F85D7715501488B15A82B7D09E83FE610FD488903488BD0E952E7FFFF'),
        (0x390F2F4,'488B15551B7309488B0BE81D456FFC488BCF4885C00F851D7F5501488B15AA237D09E829F010FD488903488BD0E9BCE6FFFF'),
        (0x390E6D8,'488B1501237309488B0BE839516FFC488BCF4885C00F858D8C5501488B15DE307D09E8A1FD10FD488903488BD0E9D8F2FFFF'),
        (0x390F038,'488B1591AB7209488B0BE8D9476FFC488BCF4885C00F85217C5501488B15A62B7D09E841EE10FD488903488BD0E978E9FFFF'),
        (0x390F772,'488B1597AF7209488B0BE89F406FFC488BCF4885C00F8519775501488B151C1D7D09E8B7E810FD488903488BD0E93EE2FFFF'),
        (0x390EA5C,'488B151D107909488B0BE8B54D6FFC488BCF4885C00F85C18F5501488B15A2287D09E869FF10FD488903488BD0E954EFFFFF'),
        (0x390E70A,'488B156F577009488B0BE807516FFC488BCF4885C00F857CA45501488B15F4237D09E81F0E11FD488903488BD0E9A6F2FFFF'),
        (0x390DB52,'488B159FF27809488B0BE8BF5C6FFC488BCF4885C00F85B9A25501488B15FC307D09E8831011FD488903488BD0E95EFEFFFF'),
        (0x390E25A,'488B158F1E7909488B0BE8B7556FFC488BCF4885C00F8502975501488B154C307D09E86F0611FD488903488BD0E956F7FFFF'),
        (0x390F57E,'488B15CBA57209488B0BE893426FFC488BCF4885C00F85B97A5501488B1520207D09E81FEC10FD488903488BD0E932E4FFFF'),
        (0x390DB84,'488B15552E7809488B0BE88D5C6FFC488BCF4885C00F85158C5501488B157A3D7D09E889FF10FD488903488BD0E92CFEFFFF'),
        (0x390F9CA,'488B15DF837109488B0BE8473E6FFC488BCF4885C00F8578965501488B15DC0A7D09E8B3FE10FD488903488BD0E9E6DFFFFF'),
        (0x390ED7C,'488B15051F7309488B0BE8954A6FFC488BCF4885C00F85E9845501488B15DA297D09E80DF610FD488903488BD0E934ECFFFF'),
        (0x390E516,'488B15CB896F09488B0BE8FB526FFC488BCF4885C00F85D79A5501488B1598277D09E8AF0711FD488903488BD0E99AF4FFFF'),
        (0x390DEA4,'488B15F5C37209488B0BE86D596FFC488BCF4885C00F857A905501488B1582367D09E82D0211FD488903488BD0E90CFBFFFF'),
        (0x390F70E,'488B1593AA7809488B0BE803416FFC488BCF4885C00F8532745501488B1550247D09E887E610FD488903488BD0E9A2E2FFFF'),
        (0x390F86C,'488B1505367009488B0BE8A53F6FFC488BCF4885C00F854C945501488B1512137D09E87DFD10FD488903488BD0E944E1FFFF'),
        (0x390F5B0,'488B1579A27209488B0BE861426FFC488BCF4885C00F85727B5501488B1556207D09E8D1EC10FD488903488BD0E900E4FFFF'),
        (0x390E480,'488B15D1BF7209488B0BE891536FFC488BCF4885C00F854A8A5501488B15D6307D09E809FC10FD488903488BD0E930F5FFFF'),
        (0x390DE40,'488B1529C27209488B0BE8D1596FFC488BCF4885C00F853F8D5501488B15DE3C7D09E89DFF10FD488903488BD0E970FBFFFF'),
        (0x390E3EA,'488B153F217809488B0BE827546FFC488BCF4885C00F85EE835501488B15DC357D09E877F710FD488903488BD0E9C6F5FFFF'),
        (0x390F358,'488B15399B7809488B0BE8B9446FFC488BCF4885C00F857A815501488B15861D7D09E841F210FD488903488BD0E958E6FFFF'),
        (0x390FF10,'488B1551997209488B0BE801396FFC488BCF4885C00F8527725501488B15E6167D09E889E310FD488903488BD0E9A0DAFFFF'),
        (0x390EB24,'488B150DF37809488B0BE8ED4C6FFC488BCF4885C00F8548A55501488B1562197D09E8890D11FD488903488BD0E98CEEFFFF'),
        (0x390E322,'488B15E7A37109488B0BE8EF546FFC488BCF4885C00F85DDAB5501488B1524217D09E86B1411FD488903488BD0E98EF6FFFF'),
        (0x391035C,'488B153D077309488B0BE8B5346FFC488BCF4885C00F851E705501488B154A147D09E835E110FD488903488BD0E954D6FFFF'),
        (0x390EA2A,'488B15BF8E7109488B0BE8E74D6FFC488BCF4885C00F8596A65501488B15241B7D09E8D70E11FD488903488BD0E986EFFFFF'),
        (0x390FD1C,'488B155D5B7009488B0BE8F53A6FFC488BCF4885C00F85F58B5501488B15120C7D09E851F610FD488903488BD0E994DCFFFF'),
        (0x390E76E,'488B15BBF47809488B0BE8A3506FFC488BCF4885C00F85E5945501488B1548247D09E8CB0311FD488903488BD0E942F2FFFF'),
        (0x390EE76,'488B159BB37209488B0BE89B496FFC488BCF4885C00F8593805501488B15C0267D09E843F210FD488903488BD0E93AEBFFFF'),
        (0x390F54C,'488B1575637009488B0BE8C5426FFC488BCF4885C00F8511925501488B15A2137D09E801FD10FD488903488BD0E964E4FFFF'),
        (0x390DD46,'488B1543477809488B0BE8CB5A6FFC488BCF4885C00F857D895501488B15383B7D09E807FD10FD488903488BD0E96AFCFFFF'),
        (0x390EFA2,'488B1577AE7709488B0BE86F486FFC488BCF4885C00F853F745501488B15A42E7D09E89BE810FD488903488BD0E90EEAFFFF'),
        (0x390E610,'488B1549607009488B0BE801526FFC488BCF4885C00F8537A55501488B151E247D09E8DD0E11FD488903488BD0E9A0F3FFFF'),
        (0x390F1C8,'488B1529157909488B0BE849466FFC488BCF4885C00F85AC715501488B15A62B7D09E839E610FD488903488BD0E9E8E7FFFF'),
        (0x390FA2E,'488B151B0F7309488B0BE8E33D6FFC488BCF4885C00F8572735501488B15F0197D09E817E510FD488903488BD0E982DFFFFF'),
        (0x390EF70,'488B15A1B57209488B0BE8A1486FFC488BCF4885C00F856F7F5501488B15FE257D09E8F5F010FD488903488BD0E940EAFFFF'),
        (0x39105E6,'488B1523437009488B0BE82B326FFC488BCF4885C00F8572845501488B15C0037D09E853EE10FD488903488BD0E9CAD3FFFF'),
        (0x390F614,'488B1525157309488B0BE8FD416FFC488BCF4885C00F85FD7C5501488B15E2207D09E805EE10FD488903488BD0E99CE3FFFF'),
        (0x3910D84,'488B1565627109488B0BE88D2A6FFC488BCF4885C00F857B835501488B15A2F77C09E8B9EB10FD488903488BD0E92CCCFFFF'),
        (0x390F740,'488B1561AD7209488B0BE8D1406FFC488BCF4885C00F852A745501488B15EE237D09E885E610FD488903488BD0E970E2FFFF'),
        (0x390E002,'488B15B7A07809488B0BE80F586FFC488BCF4885C00F852C975501488B159C317D09E85F0711FD488903488BD0E9AEF9FFFF'),
        (0x390FEDE,'488B15E39F7209488B0BE833396FFC488BCF4885C00F8555705501488B1538167D09E80BE210FD488903488BD0E9D2DAFFFF'),
        (0x391000A,'488B158F4A7009488B0BE807386FFC488BCF4885C00F85638A5501488B15840A7D09E853F410FD488903488BD0E9A6D9FFFF'),
        (0x390EF0C,'488B1575A97809488B0BE805496FFC488BCF4885C00F855D855501488B1512217D09E82DF610FD488903488BD0E9A4EAFFFF'),
        (0x390FA60,'488B1559067909488B0BE8B13D6FFC488BCF4885C00F85D27E5501488B151E187D09E8A5EE10FD488903488BD0E950DFFFFF'),
        (0x390E386,'488B15DBB57709488B0BE88B546FFC488BCF4885C00F85C4805501488B15683A7D09E83BF510FD488903488BD0E92AF6FFFF'),
        (0x39107DA,'488B15EFFE7709488B0BE837306FFC488BCF4885C00F8552605501488B15AC117D09E8E7D310FD488903488BD0E9D6D1FFFF'),
        (0x390DAEE,'488B152B736F09488B0BE8235D6FFC488BCF4885C00F85AEAA5501488B15082D7D09E8AF07A0FC488903488BD0E9C2FEFFFF'),
        (0x39100A0,'488B1579267009488B0BE871376FFC488BCF4885C00F856C8C5501488B15A60A7D09E89DF510FD488903488BD0E910D9FFFF'),
        (0x39150C0,'488B1511F26F09488B0BE851E76EFC488BCF4885C00F85483A5501488B159EB97C09E8E5A310FD488903488BD0E9F088FFFF'),
        (0x390EEDA,'488B15B7537009488B0BE837496FFC488BCF4885C00F85439C5501488B157C1B7D09E8D70511FD488903488BD0E9D6EAFFFF'),
        (0x390ECB4,'488B1535A37809488B0BE85D4B6FFC488BCF4885C00F855D885501488B15F2237D09E82DF910FD488903488BD0E9FCECFFFF'),
        (0x390E89A,'488B15F78A7109488B0BE8774F6FFC488BCF4885C00F858FA85501488B156C1C7D09E8D31011FD488903488BD0E916F1FFFF'),
        (0x391038E,'488B15B3907809488B0BE883346FFC488BCF4885C00F851A715501488B15680C7D09E8DBE110FD488903488BD0E922D6FFFF'),
        (0x3915250,'488B1509207109488B0BE8C1E56EFC488BCF4885C00F85C43E5501488B15C6B27C09E805A710FD488903488BD0E96087FFFF'),
        (0x390F0CE,'488B15536E6F09488B0BE843476FFC488BCF4885C00F8509925501488B15B81D7D09E8BFFD10FD488903488BD0E9E2E8FFFF'),
        (0x390FF42,'488B15970B7309488B0BE8CF386FFC488BCF4885C00F85BA735501488B15CC177D09E8B3E410FD488903488BD0E96EDAFFFF'),
        (0x391508E,'488B1543F76F09488B0BE883E76EFC488BCF4885C00F85B5395501488B1528B97C09E893A310FD488903488BD0E92289FFFF'),
        (0x390F326,'488B15E3157309488B0BE8EB446FFC488BCF4885C00F8515805501488B15B0247D09E823F110FD488903488BD0E98AE6FFFF'),
        (0x39102C6,'488B155B9C7209488B0BE84B356FFC488BCF4885C00F85826C5501488B1548127D09E82FDE10FD488903488BD0E9EAD6FFFF'),
        (0x39102F8,'488B1501967209488B0BE819356FFC488BCF4885C00F85546D5501488B1596127D09E8BDDE10FD488903488BD0E9B8D6FFFF'),
        (0x3914B48,'488B15B94B7209488B0BE8C9EC6EFC488BCF4885C00F855C265501488B1586CB7C09E88D9710FD488903488BD0E9688EFFFF'),
        (0x390FB5A,'488B15875D7109488B0BE8B73C6FFC488BCF4885C00F85A5975501488B158C0B7D09E8C3FF10FD488903488BD0E956DEFFFF'),
        (0x3910712,'488B15BF507109488B0BE8FF306FFC488BCF4885C00F85D88B5501488B15E4FF7C09E8F3F310FD488903488BD0E99ED2FFFF'),
        (0x391505C,'488B15ED027009488B0BE8B5E76EFC488BCF4885C00F85D2395501488B156AB97C09E8ADA310FD488903488BD0E95489FFFF'),
        (0x390F89E,'488B152B597109488B0BE8733F6FFC488BCF4885C00F85B99A5501488B15200E7D09E8BB0211FD488903488BD0E912E1FFFF'),
        (0x3910B90,'488B1589427009488B0BE8812C6FFC488BCF4885C00F85EE7D5501488B1556FE7C09E849E810FD488903488BD0E920CEFFFF'),
        (0x390ED18,'488B1591817009488B0BE8F94A6FFC488BCF4885C00F85F1995501488B150E1B7D09E8D50411FD488903488BD0E998ECFFFF'),
        (0x3914A80,'488B15D1587209488B0BE891ED6EFC488BCF4885C00F8535245501488B15F6C97C09E8CD9510FD488903488BD0E9308FFFFF'),
        (0x390E2BE,'488B15637C7109488B0BE853556FFC488BCF4885C00F85AAAF5501488B1570237D09E8F31711FD488903488BD0E9F2F6FFFF'),
        (0x390DC7E,'488B15E3277809488B0BE8935B6FFC488BCF4885C00F85308C5501488B15C03D7D09E8AFFF10FD488903488BD0E932FDFFFF'),
        (0x3915124,'488B155D417109488B0BE8EDE66EFC488BCF4885C00F85873D5501488B154AB37C09E82DA610FD488903488BD0E98C88FFFF'),
        (0x3910D52,'488B1517677109488B0BE8BF2A6FFC488BCF4885C00F8544835501488B151CF87C09E87FEB10FD488903488BD0E95ECCFFFF'),
        (0x390E2F0,'488B15D9FA7809488B0BE821556FFC488BCF4885C00F85DC805501488B155E3B7D09E841F510FD488903488BD0E9C0F6FFFF'),
        (0x391083E,'488B1593987809488B0BE8D32F6FFC488BCF4885C00F853D625501488B1560127D09E8DFD410FD488903488BD0E972D1FFFF'),
        (0x390FE7A,'488B155F9E7809488B0BE897396FFC488BCF4885C00F85BD6E5501488B152C1D7D09E853E010FD488903488BD0E936DBFFFF'),
        (0x391006E,'488B15D3327009488B0BE8A3376FFC488BCF4885C00F85898C5501488B15E00A7D09E8C3F510FD488903488BD0E942D9FFFF'),
        (0x390F1FA,'488B153F947809488B0BE817466FFC488BCF4885C00F850A855501488B15C41F7D09E837F510FD488903488BD0E9B6E7FFFF'),
        (0x390EBEC,'488B153D2C7809488B0BE8254C6FFC488BCF4885C00F8523AA5501488B152A177D09E81D1111FD488903488BD0E9C4EDFFFF'),
        (0x390E3B8,'488B15712A7809488B0BE859546FFC488BCF4885C00F8553805501488B15663A7D09E8C1F410FD488903488BD0E9F8F5FFFF'),
        (0x390E57A,'488B158F927009488B0BE897526FFC488BCF4885C00F8565A15501488B15DC227D09E8370C11FD488903488BD0E936F4FFFF'),
        (0x39103F2,'488B150F847809488B0BE81F346FFC488BCF4885C00F85E0715501488B154C0D7D09E88BE210FD488903488BD0E9BED5FFFF'),
        (0x390EB56,'488B153B387809488B0BE8BB4C6FFC488BCF4885C00F85587B5501488B15302D7D09E8EBEE10FD488903488BD0E95AEEFFFF'),
        (0x391032A,'488B1577067309488B0BE8E7346FFC488BCF4885C00F8526705501488B15A4147D09E82BE110FD488903488BD0E986D6FFFF'),
        (0x390EFD4,'488B15B51E7309488B0BE83D486FFC488BCF4885C00F85E17D5501488B1532247D09E895EF10FD488903488BD0E9DCE9FFFF'),
        (0x3910938,'488B15E18D7809488B0BE8D92E6FFC488BCF4885C00F85D96A5501488B150E077D09E8C5DB10FD488903488BD0E978D0FFFF'),
        (0x3910B2C,'488B15CD697009488B0BE8E52C6FFC488BCF4885C00F851C7C5501488B15D2FD7C09E809E710FD488903488BD0E984CEFFFF'),
        (0x3910AFA,'488B151F687009488B0BE8172D6FFC488BCF4885C00F85397C5501488B1514FE7C09E823E710FD488903488BD0E9B6CEFFFF'),
        (0x3910C26,'488B15B3257009488B0BE8EB2B6FFC488BCF4885C00F85BC805501488B1540FF7C09E8E7E910FD488903488BD0E98ACDFFFF'),
        (0x3914B16,'488B15D34C7209488B0BE8FBEC6EFC488BCF4885C00F85B4255501488B1518CB7C09E82F9710FD488903488BD0E99A8EFFFF'),
        (0x3914AE4,'488B15A54C7209488B0BE82DED6EFC488BCF4885C00F85D1255501488B1552CB7C09E8559710FD488903488BD0E9CC8EFFFF'),
        (0x390DF08,'488B1519AD7109488B0BE809596FFC488BCF4885C00F8564AF5501488B1596247D09E8011811FD488903488BD0E9A8FAFFFF'),
        (0x390E5AC,'488B15DD447809488B0BE865526FFC488BCF4885C00F853D805501488B1532337D09E811F410FD488903488BD0E904F4FFFF'),
        (0x390ECE6,'488B15E37D7109488B0BE82B4B6FFC488BCF4885C00F859BA45501488B1500197D09E8B70C11FD488903488BD0E9CAECFFFF'),
        (0x390E9C6,'488B15C3137909488B0BE84B4E6FFC488BCF4885C00F85EA8F5501488B1560297D09E8C3FF10FD488903488BD0E9EAEFFFFF'),
        (0x390EAC0,'488B1589706F09488B0BE8514D6FFC488BCF4885C00F8580985501488B158E237D09E8210411FD488903488BD0E9F0EEFFFF'),
        (0x390E034,'488B157D1B7909488B0BE8DD576FFC488BCF4885C00F85289A5501488B1592337D09E8E50911FD488903488BD0E97CF9FFFF'),
        (0x390ED4A,'488B15BFE87809488B0BE8C74A6FFC488BCF4885C00F8586A85501488B157CE97809E8EFE210FD488903488BD0E966ECFFFF'),
        (0x390EEA8,'488B1579767009488B0BE869496FFC488BCF4885C00F85DF985501488B15261A7D09E8D50311FD488903488BD0E908EBFFFF'),
        (0x390F3BC,'488B15358C7109488B0BE855446FFC488BCF4885C00F85979B5501488B1532117D09E8550411FD488903488BD0E9F4E5FFFF'),
        (0x390F22C,'488B15DDFD7809488B0BE8E5456FFC488BCF4885C00F8590895501488B1552217D09E84DF810FD488903488BD0E984E7FFFF'),
        (0x390F006,'488B151B7C7009488B0BE80B486FFC488BCF4885C00F85EE975501488B1598187D09E8BF0211FD488903488BD0E9AAE9FFFF'),
        (0x390F290,'488B15390F7809488B0BE881456FFC488BCF4885C00F85B1755501488B15EE267D09E83DE910FD488903488BD0E920E7FFFF'),
        (0x390F678,'488B15C97D7009488B0BE899416FFC488BCF4885C00F85FA905501488B1566127D09E8EDFB10FD488903488BD0E938E3FFFF'),
        (0x390F420,'488B1551E37809488B0BE8F1436FFC488BCF4885C00F8538835501488B15A6E17809E84DDB10FD488903488BD0E990E5FFFF'),
        (0x390DE0E,'488B15838A6F09488B0BE8035A6FFC488BCF4885C00F8593A35501488B15F02F7D09E8CB0F11FD488903488BD0E9A2FBFFFF'),
        (0x390E868,'488B15F1797109488B0BE8A94F6FFC488BCF4885C00F856DA95501488B153E1D7D09E8951111FD488903488BD0E948F1FFFF'),
        (0x390F3EE,'488B15D3627109488B0BE823446FFC488BCF4885C00F85E79E5501488B1518127D09E8FF0611FD488903488BD0E9C2E5FFFF'),
        (0x390F38A,'488B1567107909488B0BE887446FFC488BCF4885C00F857E855501488B150C1F7D09E857F510FD488903488BD0E926E6FFFF'),
        (0x390F998,'488B15216E6F09488B0BE8793E6FFC488BCF4885C00F85DF875501488B1586147D09E811F410FD488903488BD0E918E0FFFF'),
        (0x390F83A,'488B15DF617009488B0BE8D73F6FFC488BCF4885C00F85EC905501488B15E4107D09E84BFB10FD488903488BD0E976E1FFFF'),
        (0x390F4E8,'488B1589427009488B0BE829436FFC488BCF4885C00F8563975501488B15BE157D09E8C50011FD488903488BD0E9C8E4FFFF'),
        (0x390F6AA,'488B1537E17809488B0BE867416FFC488BCF4885C00F8516985501488B1574DF7809E847D910FD488903488BD0E906E3FFFF'),
        (0x390DF3A,'488B1587BE7809488B0BE8D7586FFC488BCF4885C00F85A68A5501488B15943B7D09E89BFD10FD488903488BD0E976FAFFFF'),
        (0x390F808,'488B1529707009488B0BE809406FFC488BCF4885C00F85D78F5501488B15A6107D09E8A5FA10FD488903488BD0E9A8E1FFFF'),
        (0x390DABC,'488B15E5617009488B0BE8555D6FFC488BCF4885C00F85B5B05501488B1552307D09E8ED07A0FC488903488BD0E9F4FEFFFF'),
        (0x390E192,'488B1537AF7109488B0BE87F566FFC488BCF4885C00F8504AD5501488B15F4217D09E89B1511FD488903488BD0E91EF8FFFF'),
        (0x390F06A,'488B157FAE7709488B0BE8A7476FFC488BCF4885C00F858C735501488B15CC2D7D09E8EBE710FD488903488BD0E946E9FFFF'),
        (0x390FD4E,'488B159B557109488B0BE8C33A6FFC488BCF4885C00F851E965501488B1560097D09E823FE10FD488903488BD0E962DCFFFF'),
        (0x390FD80,'488B1599D87809488B0BE8913A6FFC488BCF4885C00F8565985501488B1526D97809E8D1D210FD488903488BD0E930DCFFFF'),
        (0x390DBB6,'488B153BBF7809488B0BE85B5C6FFC488BCF4885C00F85D9975501488B15E83B7D09E8E70811FD488903488BD0E9FAFDFFFF'),
        (0x391003C,'488B159D387009488B0BE8D5376FFC488BCF4885C00F85248C5501488B157A0A7D09E859F510FD488903488BD0E974D9FFFF'),
        (0x39100D2,'488B15D7D67809488B0BE83F376FFC488BCF4885C00F85D98E5501488B159CD57809E82BCF10FD488903488BD0E9DED8FFFF'),
        (0x390F100,'488B15B9877109488B0BE811476FFC488BCF4885C00F85D59F5501488B153E147D09E8190811FD488903488BD0E9B0E8FFFF'),
        (0x390FE16,'488B159B077809488B0BE8FB396FFC488BCF4885C00F85D7695501488B15A01B7D09E863DD10FD488903488BD0E99ADBFFFF'),
        (0x390FFA6,'488B154B5C6F09488B0BE86B386FFC488BCF4885C00F85AF835501488B15980E7D09E853EF10FD488903488BD0E90ADAFFFF'),
        (0x3910136,'488B15E3537109488B0BE8DB366FFC488BCF4885C00F85A3925501488B1550057D09E877FA10FD488903488BD0E97AD8FFFF'),
        (0x390FAF6,'488B157BF57809488B0BE81B3D6FFC488BCF4885C00F85B1805501488B1598187D09E86BEF10FD488903488BD0E9BADEFFFF'),
        (0x390FDE4,'488B15D52E7809488B0BE82D3A6FFC488BCF4885C00F851A685501488B15E21A7D09E8FDDB10FD488903488BD0E9CCDBFFFF'),
        (0x390F09C,'488B15DD8B7809488B0BE875476FFC488BCF4885C00F8514875501488B15CA207D09E819F710FD488903488BD0E914E9FFFF'),
        (0x390DE72,'488B151FCF7209488B0BE89F596FFC488BCF4885C00F85C3B65501488B15E4247D09E8371E11FD488903488BD0E93EFBFFFF'),
        (0x3910744,'488B1515AB7209488B0BE8CD306FFC488BCF4885C00F85DC8D5501488B1522FC7C09E84DF510FD488903488BD0E96CD2FFFF'),
        (0x390FBF0,'488B1511957809488B0BE8213C6FFC488BCF4885C00F858E785501488B1526147D09E855E910FD488903488BD0E9C0DDFFFF'),
        (0x390F9FC,'488B15D5677109488B0BE8153E6FFC488BCF4885C00F8581985501488B15220C7D09E8CD0011FD488903488BD0E9B4DFFFFF'),
        (0x390FCB8,'488B1519D17809488B0BE8593B6FFC488BCF4885C00F8568815501488B158E0F7D09E829EF10FD488903488BD0E9F8DCFFFF'),
        (0x39101FE,'488B15931A7809488B0BE813366FFC488BCF4885C00F8504655501488B1548177D09E8A3D810FD488903488BD0E9B2D7FFFF'),
        (0x3910488,'488B15F1FD7809488B0BE889336FFC488BCF4885C00F8556745501488B15460E7D09E805E410FD488903488BD0E928D5FFFF'),
        (0x39104EC,'488B155D666F09488B0BE825336FFC488BCF4885C00F85DB7B5501488B156A087D09E869E810FD488903488BD0E9C4D4FFFF'),
        (0x3910294,'488B15CDA97209488B0BE87D356FFC488BCF4885C00F858E6B5501488B1552127D09E81DDD10FD488903488BD0E91CD7FFFF'),
        (0x390EDE0,'488B1589B47809488B0BE8314A6FFC488BCF4885C00F85EB7B5501488B15FE2C7D09E8DDEE10FD488903488BD0E9D0EBFFFF'),
        (0x3910230,'488B15711C7809488B0BE8E1356FFC488BCF4885C00F85E7645501488B15E6167D09E8B9D810FD488903488BD0E980D7FFFF'),
        (0x3910424,'488B15C57B7809488B0BE8ED336FFC488BCF4885C00F85F5725501488B158A0D7D09E825E310FD488903488BD0E98CD5FFFF'),
        (0x390E6A6,'488B151B307809488B0BE86B516FFC488BCF4885C00F85DE805501488B1560327D09E85BF410FD488903488BD0E90AF3FFFF'),
        (0x390EA8E,'488B159B907109488B0BE8834D6FFC488BCF4885C00F859FA55501488B15281A7D09E8D70D11FD488903488BD0E922EFFFFF'),
        (0x390F966,'488B15C3A07209488B0BE8AB3E6FFC488BCF4885C00F853A775501488B15E81C7D09E8AFE810FD488903488BD0E94AE0FFFF'),
        (0x3910CEE,'488B15337D7109488B0BE8232B6FFC488BCF4885C00F8526825501488B1540F77C09E8C3EA10FD488903488BD0E9C2CCFFFF'),
        (0x390E066,'488B151B6D6F09488B0BE8AB576FFC488BCF4885C00F85F7A55501488B1528287D09E8F71011FD488903488BD0E94AF9FFFF'),
        (0x390E836,'488B15C3AD7809488B0BE8DB4F6FFC488BCF4885C00F85B18B5501488B15402F7D09E8A3FC10FD488903488BD0E97AF1FFFF'),
        (0x390E930,'488B15A9AF7809488B0BE8E14E6FFC488BCF4885C00F8531845501488B15262B7D09E8CDF510FD488903488BD0E980F0FFFF'),
        (0x390DD14,'488B15651E7809488B0BE8FD5A6FFC488BCF4885C00F85A28C5501488B15D23D7D09E89DFF10FD488903488BD0E99CFCFFFF')):
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
        (0x44,0x390F2C2,106445,16633,'CheckGlobalCDTimerAction_Data',None),
        (0x10F,0x390EE44,106926,16309,'PauseBuffTime_Data',None),
        (0x9B,0x390E228,106559,16065,'DebugPrintAction_Data',None),
        (0xC5,0x390E642,106660,16155,'HealAction_Data',None),
        (0x119,0x390D9FA,106941,16329,'PlaySoundAction_PlaySoundActionData',None),
        (0x0A,0x390F25E,106284,15903,'AddGlobalCDTimer_Data',None),
        (0x7A,0x390F2F4,106511,16691,'Conditions_CheckSpellInflictionType_Data',None),
        (0x88,0x390E6D8,106525,16725,'Conditions_Probablity_Data',None),
        (0x48,0x390F038,106449,16657,'CheckOriginSkillType_Data',None),
        (0x5A,0x390F772,106479,16609,'Conditions_CheckCustomAbilityEvent_Data',None),
        (0xC4,0x390EA5C,106651,16153,'GetTargetBuffBBAdvanced_Data',None),
        (0x145,0x390E70A,107077,16417,'SendBattleSignalToLevel_Data',None),
        (0xDE,0x390DB52,106784,16221,'LaunchProjectile_Data',None),
        (0xBD,0x390E25A,106633,16139,'ForEachAction_Data',None),
        (0x6A,0x390F57E,106495,16655,'Conditions_CheckObtainAtbType_Data',None),
        (0x24,0x390DB84,106353,15971,'CameraImpulseAction_CameraImpulseActionData',None),
        (0x16B,0x390F9CA,107145,16489,'SpawnInteractiveGoldCoin_Data',None),
        (0x7E,0x390ED7C,106515,16701,'Conditions_CheckTargetContains_Data',None),
        (0x35,0x390DD14,106376,16005,'CharHurtAnimAction_Data',None),
        (0xEA,0x390E516,106809,16237,'MergeTargetAction_Data',None),
        (0x61,0x390DEA4,106486,16629,'Conditions_CheckEntityNum_Data',None),
        (0x3F,0x390F70E,106440,16015,'CheckConsumeBuffLayer_Data',None),
        (0x14D,0x390F86C,107087,16433,'SetBuffDurationAction_Data',None),
        (0x73,0x390F5B0,106504,16675,'Conditions_CheckSkillCastId_Data',None),
        (0x5D,0x390E480,106483,16619,'Conditions_CheckDamageType_Data',None),
        (0x42,0x390DE40,106443,16623,'CheckDistanceCondition_Data',None),
        (0x27,0x390E3EA,106362,15977,'CastSkill_Data',None),
        (0x95,0x390F358,106540,16053,'CreateGlobalBuffAction_Data',None),
        (0x74,0x390FF10,106505,16677,'Conditions_CheckSkillDamageType_Data',None),
        (0x16D,0x390EB24,107149,16491,'SpellInfliction_Data',None),
        (0x160,0x390E322,107109,16469,'ShowHideActorAction_ShowHideActorData',None),
        (0x89,0x391035C,106526,16727,'Conditions_SaveHealValue_Data',None),
        (0x171,0x390EA2A,107157,16499,'StoreAttributeValue_Data',None),
        (0x132,0x390FD1C,107002,16379,'SaveAtbObtainValue_Data',None),
        (0xD4,0x390E76E,106768,16193,'InterruptAction_Data',None),
        (0x60,0x390EE76,106485,16627,'Conditions_CheckEnemyRank_Data',None),
        (0x126,0x390F54C,106982,16377,'RecoverFromPoiseBreak_Data',None),
        (0x1C,0x390DD46,106329,15939,'BlowOffCharacterAction_Data',None),
        (0x06,0x390EFA2,106277,15897,'AchieveSpecialGameEventAction_Data',None),
        (0x142,0x390E610,107018,16411,'SaveValueFromAIBlackboard_Data',None),
        (0x03,0x390F1C8,106257,16121,'AbilityActions_FinishGlobalBuffAction_Data',None),
        (0x51,0x390FA2E,106468,16719,'CompareString_Data',None),
        (0x5E,0x390EF70,106482,16621,'Conditions_CheckDamageTypeMask_Data',None),
        (0x13B,0x39105E6,107011,16397,'SaveDamageContext_Data',None),
        (0x84,0x390F614,106521,16713,'Conditions_CheckWeaponTypeCondition_Data',None),
        (0x85,0x3910906,106522,16715,'Conditions_CompareDeckAttr_Data',None),
        (0x174,0x3910D84,107160,16505,'StoreEntityProperty_Data',None),
        (0x41,0x390F740,106442,16617,'CheckDamageTransferredSource_Data',None),
        (0xA9,0x390E002,106594,16095,'EnemyHurtAnimAction_Data',None),
        (0x62,0x390FEDE,106487,16635,'Conditions_CheckHasDamageSkillCastId_Data',None),
        (0x13C,0x391000A,107012,16399,'SaveDamageSkillCastId_Data',None),
        (0x90,0x390EF0C,106534,16043,'CountShieldUIAction_Data',None),
        (0xBB,0x390FA60,106636,16135,'ForceTargetInFightAction_Data',None),
        (0x0B,0x390E386,106285,15905,'AddTagAction_Data',None),
        (0x0C,0x390FDB2,106286,15907,'AddTagToEntities_Data',None),
        (0x26,0x3910776,106361,15975,'CastPlungingAttack_Data',None),
        (0x10C,0x39105B4,106924,16303,'PatrolTeleport_Data',None),
        (0x2B,0x39107DA,106366,15985,'ChangeSeasonTowerEnergyAction_Data',None),
        (0x115,0x390DAEE,106937,16321,'PlayAnimationAction_PlayAnimationActionData',None),
        (0x151,0x39100A0,107091,16441,'SetHpFloor_Data',None),
        (0x13F,0x39150C0,107015,16405,'SaveShieldValueToBB_Data',None),
        (0x140,0x390EEDA,107016,16407,'SaveTargetDistanceAction_Data',None),
        (0x98,0x390ECB4,106543,16059,'CurveEvaluateFloat_Data',None),
        (0x176,0x390E89A,107166,16509,'SwitchAction_Data',None),
        (0x93,0x391038E,106538,16049,'CreateBuffAttachingSkill_Data',None),
        (0x175,0x3915250,107161,16507,'StoreSkillDamageType_Data',None),
        (0xFC,0x390F0CE,106886,16273,'NotifyCharPassiveUIAction_Data',None),
        (0x83,0x390FF42,106520,16711,'Conditions_CheckUsp_Data',None),
        (0x13A,0x391508E,107010,16395,'SaveCollectedBuffBbValue_Data',None),
        (0x86,0x390F326,106523,16721,'Conditions_ModifyCollectedBuffBbValue_Data',None),
        (0x63,0x39102C6,106488,16637,'Conditions_CheckHealTag_Data',None),
        (0x6B,0x39102F8,106496,16659,'Conditions_CheckOverHeal_Data',None),
        (0x77,0x3914B48,106508,16685,'Conditions_CheckSkillInterruptReason_Data',None),
        (0x188,0x390FB5A,107209,16545,'TriggerCustomAbilityEvent_Data',None),
        (0x187,0x3910712,107207,16543,'TriggerComboSkillAction_Data',None),
        (0x139,0x391505C,107009,16393,'SaveCharTypeId_Data',None),
        (0x18A,0x390F89E,107211,16549,'TriggerLiinoUIEvent_Data',None),
        (0x135,0x3910B90,107007,16385,'SaveBuffStackNum_Data',None),
        (0x122,0x390ED18,106976,16347,'ReadSkillSettingData_Data',None),
        (0x5C,0x3914A80,106481,16613,'Conditions_CheckDamageIgnoreImmuneLevel_Data',None),
        (0x183,0x390E2BE,107194,16535,'TimeDilationAction_Data',None),
        (0x2F,0x390DC7E,106371,15993,'ChannelingAction_Data',None),
        (0x15C,0x3915124,107102,16463,'ShakeCountShieldUIAction_Data',None),
        (0x16F,0x3910D52,107150,16495,'SpendAtbAction_Data',None),
        (0x05,0x390E2F0,106259,16195,'AbilityActions_InterruptCurSkillAction_Data',None),
        (0x3A,0x391083E,106435,16013,'CheckBuffEnhanceChangedLayer_Data',None),
        (0x4C,0x390FE7A,106455,16023,'ClearProjectileAction_Data',None),
        (0x150,0x391006E,107090,16439,'SetGeneralAbilityCd_Data',None),
        (0xA7,0x390F1FA,106586,16091,'EnablePartsAction_Data',None),
        (0x19E,0x390EBEC,107707,15957,'AddCameraControlStateAction_AddCameraControlStateActionData',None),
        (0x08,0x390E3B8,106281,15959,'AddDynamicCcsAction_AddDynamicCcsActionData',None),
        (0x120,0x390E57A,106970,16343,'RandomAction_Data',None),
        (0x9F,0x39103F2,106567,16073,'DispelAction_Data',None),
        (0x1B,0x390EB56,106327,15937,'BlowOffAction_Data',None),
        (0x87,0x391032A,106524,16723,'Conditions_OrConditionAction_Data',None),
        (0x52,0x390EFD4,106469,16693,'Condition_CheckSquadInFight_Data',None),
        (0x8E,0x3910938,106532,16039,'CostAtbRefreshLongestSkillCd_Data',None),
        (0x125,0x3910B2C,106981,16353,'RecoverDashEnergy_Data',None),
        (0x124,0x3910AFA,106980,16351,'RecordBattleDetails_Data',None),
        (0x14F,0x3910C26,107089,16437,'SetFirstDashParam_Data',None),
        (0x71,0x3914B16,106502,16671,'Conditions_CheckProjectileInPerfectDodgeCd_Data',None),
        (0x70,0x3914AE4,106501,16669,'Conditions_CheckProjectileIgnoreImmuneLevel_Data',None),
        (0x159,0x390DF08,107099,16457,'SetSuperArmorAction_Data',None),
        (0x16,0x390E5AC,106311,15927,'AuraAction_Data',None),
        (0x178,0x390ECE6,107170,16513,'SwitchModeAction_Data',None),
        (0xC1,0x390E9C6,106648,16147,'GetAITransDataAction_Data',None),
        (0x101,0x390EAC0,106904,16283,'OnSpellAbnormalStartFinish_Data',None),
        (0xC7,0x390E034,106665,16159,'HitStopAction_Data',None),
        (0x19B,0x390ED4A,107236,16215,'VulnerableAction_Data',None),
        (0x128,0x390EEA8,106984,16357,'RecoverPoiseAction_Data',None),
        (0x164,0x390F3BC,107119,16477,'SkillAffixAction_Data',None),
        (0xCF,0x390F22C,106675,16175,'IgniteBuffTextAction_Data',None),
        (0x12B,0x390F006,106988,16363,'RefreshBuffAttrModifierValue_Data',None),
        (0x2C,0x390F290,106367,15987,'ChangeSkillAction_Data',None),
        (0x127,0x390F678,106983,16355,'RecoverLockOnEndIfNoLockAction_Data',None),
        (0xAB,0x390F420,106601,16217,'EnhancedAction_Data',None),
        (0xF6,0x390DE0E,106865,16261,'MoveToAction_Data',None),
        (0x17C,0x390E868,107184,16521,'TeleportAction_Data',None),
        (0x186,0x390F3EE,107206,16541,'TriggerCharSpellInflictionEvent_Data',None),
        (0xB9,0x390F38A,106634,16129,'ForceHideHeadBarAction_Data',None),
        (0xF4,0x390F998,106863,16257,'MoveGaitAction_Data',None),
        (0x133,0x390F83A,107003,16381,'SaveBuffLifeTime_Data',None),
        (0x14A,0x390F4E8,107085,16427,'SetAnimatorParamAction_Data',None),
        (0x15D,0x390F6AA,107103,16213,'ShelterAction_Data',None),
        (0x37,0x390DF3A,106426,16009,'CharWeaponVisibleAction_CharWeaponVisibleActionData',None),
        (0x12A,0x390F808,106987,16361,'RefrainObtainUsp_Data',None),
        (0x144,0x390DABC,107076,16415,'SelfRotateAction_Data',None),
        (0x15B,0x390E192,107101,16461,'SetWeaknessAction_Data',None),
        (7,0x390F06A,106280,15899,'AddAIMarkerAction_Data',None),
        (395,0x390FD4E,107216,16551,'TriggerSpellBurstEventAction_Data',None),
        (412,0x390FD80,107242,16207,'WeakAction_Data',None),
        (138,0x390DBB6,106527,16031,'ContinuousFindTargetAction_Data',None),
        (331,0x391003C,107084,16429,'SetAnimTimeScaleAction_Data',None),
        (358,0x39100D2,107124,16209,'SlowAction_Data',None),
        (370,0x390F100,107158,16501,'StoreBuffCount_Data',None),
        (40,0x390FE16,106363,15979,'ChangeGeneralAbilityButton_Data',None),
        (258,0x390FFA6,106905,16285,'OnSpellInflictionStart_Data',None),
        (398,0x3910136,107220,16557,'TyphoeaArcheryChipDataAction_Data',None),
        (206,0x390FAF6,106674,16173,'IgniteAction_Data',None),
        (23,0x390FDE4,106319,15929,'BindBountyEnemyAction_Data',None),
        (173,0x390F09C,106609,16101,'EventListenerAction_Data',None),
        (408,0x390DE72,107233,16577,'VoiceTriggerAction_VoiceTriggerActionData',None),
        (407,0x3910744,107232,16575,'VoiceInterruptAction_VoiceInterruptActionData',None),
        (145,0x390FBF0,106535,16045,'CreateAdditionalBattleShape_Data',None),
        (388,0x390F9FC,107197,16537,'TogglableAction_Data',None),
        (223,0x390FCB8,106786,16223,'LaunchUpwardAction_Data',None),
        (31,0x39101FE,106332,15945,'BombTouchLayerAction_Data',None),
        (183,0x3910488,106629,16125,'FlowTextAction_Data',None),
        (240,0x39104EC,106858,16249,'ModifyResilienceDecreaseFactor_Data',None),
        (85,0x3910294,106474,16591,'Conditions_CheckBuffFromSource_Data',None),
        (54,0x390EDE0,106425,16007,'CharWeaponAnimationAction_CharWeaponAnimationActionData',None),
        (32,0x3910230,106337,15949,'BreakoutAction_Data',None),
        (168,0x3910424,106589,16093,'EnableSpecialAim_Data',None),
        (35,0x390E6A6,106338,15955,'BroadcastAlertToCharactersAction_BroadcastAlertToCharactersActionData',None),
        (362,0x390EA8E,107144,16487,'SpawnEnemyAction_Data',None),
        (111,0x390F966,106500,16667,'Conditions_CheckProfession_Data',None),
        (353,0x3910CEE,107110,16471,'ShowSquadTipsAction_Data',None),
        (284,0x390E066,106956,16335,'PullAction_Data',None),
        (140,0x390E836,106530,16035,'ConvertToTargetContext_Data',None),
        (78,0x390E930,106459,16027,'ComboCacheAction_Data',None),
        (148,0x391096A,106539,16051,'CreateDynamicBattleShape_Data',None),
        (188,0x39109CE,106637,16137,'ForceTriggerWeakness_Data',None),
        (344,0x3910C8A,107098,16455,'SetStrafeModeAction_Data',None),
        (346,0x3910CBC,107100,16459,'SetWaterDroneItemModePersistLiquidIdAction_Data',None),
        (364,0x3910D20,107147,16211,'SpeedupAction_Data',None),
        (377,0x3910104,107177,16515,'TagQueryListenerAction_Data',None),
        (402,0x3910DB6,107225,16565,'TyphoeaIsInShootingRangeAction_Data',None),
        (334,0x3910618,107088,16435,'SetDamageTagImmuneRule_Data',None),
        (224,0x390E7D2,106794,15961,'LockCameraAimAction_LockCameraAimActionData',None),
        (13,0x3910168,106291,15909,'AirborneAction_AirborneActionData',None),
        (0xD5,0x4E67C83,106689,16187,'IntResourceHpCheckAction_Data',None),
        (0xD6,0x4E67CC6,106690,16189,'IntResourceOnHpZeroAction_Data',None)):
        require(targets[tag],target,source,table_va+tag*4)
        operands=[]
        for at,usage_tag in ((target,1),)+(((init,2),) if init is not None else ()):
            ins=pe.bytes_at_va(pe.image_base+at,7)
            require(len(ins),7,source,pe.image_base+at)
            cell=pe.image_base+at+7+struct.unpack_from('<i',ins,3)[0]
            usage=pe.bytes_at_va(cell,8)
            found=unresolved_usage_index(usage,reg['typesCount'],tag=usage_tag,source=source,offset=cell)
            require(found,index,source,cell)
            pointer=pe.u64_at_va(int(reg['types'],16)+index*8)
            record=pe.bytes_at_va(pointer,16);require(len(record),16,source,pointer)
            require(record[10],0x12,source,pointer+10)
            require(struct.unpack_from('<Q',record)[0],definition,source,pointer)
            require(definition<len(md.types),True,source,pointer)
            namespace='View' if tag==0x19E else 'Core'
            expected_name='Beyond.MemoryPack.Beyond_Gameplay_'+namespace+'_'+suffix+'ForMemoryPack'
            require(md.type_full_name(md.types[definition]),expected_name,source,pointer)
            operands.append({'instructionRva':at,'cellVa':cell,'usageRawHex':usage.hex().upper(),
                'usageTag':usage_tag,'registeredTypeIndex':index,'typePointerVa':pointer,'typeRawHex':record.hex().upper()})
        if len(operands)==2:require(operands[0]['typePointerVa'],operands[1]['typePointerVa'],source)
        rows.append({'tag':tag,'switchTargetRva':target,'typeDefinition':definition,'wrapperName':expected_name,'operands':operands})
    return {'methods':methods,'windows':windows,'switchTableRva':0x3915318,'switchEntryCount':416,
        'switchTableSha256':hashlib.sha256(raw).hexdigest().upper(),'rows':rows,
        'level':'direct current native tag-to-wrapper routing; exact metadata identity',
        'boundary':'The token/module-joined reader calls the bounded tag helper then uses its ushort output in an unsigned <=0x19F switch. The helper fast path consumes one byte and directly returns tags below 0xFA. FA consumes two more bytes as a little-endian ushort with no lower-value restriction; its short-input path calls an external refill helper, not an in-body zero-result failure. FB..FF return false with zero tag output, skipping the AL=1 instruction; the dispatcher false path clears its output. The maintained finite parser retains FF null and leaves FB..FE unsupported. Segment replacement is not certified. Selected table entries reach exact type-usage operands, including current union364 to SpeedupAction. For C9 and C0, separate cctor callsites pass those literal tags alongside a helper result derived from the same registered type pointer (usage kind two versus branch kind one). Current C9 describes the IfElse wrapper; C0 describes GainCost, contradicting the legacy Buff reader C0 name. Tag 40 describes CheckDamageTag. This is not a blanket tag renumbering rule or proof of nested fields, actual object allocation, formatter execution, record extent or EOF. Do not alias C9 to the legacy C0 parser or promote existing labels for current bytes without the concrete nested consumer ABI.'}


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
        (0x3BA4141,'0F8CB4653201'),
        (0x3BA4147,'83FEFF0F842F010000'),(0x3BA415F,'49833E00488B4520488B88C00000000F8518653201'),
        (0x3BA41C1,'85F60F881F653201'),(0x3BA4282,'49C70600000000'),
        (0x4ECA6FB,'33D28BCEE8900A8404CCCC'),
        (0x4ECA6AB,'FF431CC7431800000000E9799BCDFE'),
        (0x3BA4261,'85F67F4D'),(0x3BA42C3,'4C8D4C24584C8BC7498BD7E8FD494FFC'),
        (0x3BA4312,'41FFC4443BE60F8D47FFFFFFEB92')):
        chunk=bytes.fromhex(expected)
        require(pe.bytes_at_va(pe.image_base+at,len(chunk)),chunk,source,at)
        windows.append({'rva':at,'rawHex':expected})
    range_failure_branch_rva=0x3BA4141
    range_failure_branch_raw=pe.bytes_at_va(pe.image_base+range_failure_branch_rva,6)
    require(range_failure_branch_raw,bytes.fromhex('0F8CB4653201'),source,
            range_failure_branch_rva)
    range_failure_target_rva=(range_failure_branch_rva+6+
                              struct.unpack_from('<i',range_failure_branch_raw,2)[0])
    require(range_failure_target_rva,0x4ECA6FB,source,range_failure_branch_rva)
    return {'methodIdentities':identities,'registeredTypeIndex':index,'typeCarrier':carrier,
            'classInstantiation':inst.as_dict(),'methodSpecIndices':sorted(selected),'codeCandidates':candidates,
            'windows':windows,'level':'exact static candidate identity; direct conditional header and loop flow',
            'fastHeaderGuard':{
                'countWidthBytes':4,
                'signedCount':True,
                'remainingBytesComparedToCount':True,
                'comparisonRva':0x3BA4130,
                'comparisonRawHex':'48634744488B4F18482BC84863C6483BC8',
                'rangeFailureCondition':'remaining < signed count',
                'rangeFailureBranchRva':range_failure_branch_rva,
                'rangeFailureBranchRawHex':range_failure_branch_raw.hex().upper(),
                'rangeFailureTargetRva':range_failure_target_rva,
                'rangeFailureBodyRawHex':'33D28BCEE8900A8404CCCC',
                'boundary':'The four-byte signed count is compared with remaining bytes after the header. A signed remaining<count branch reaches a helper call followed by INT3 if the helper returns; it does not enter the normal positive-element loop.',
            },
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


def wrapper_consumer(pe, md, modules, image_owners, reg, table, *, source):
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
    wrapper_methods=module_methods(pe,md,modules,image_owners,
        [(104357,'Beyond.MemoryPack.Beyond_Gameplay_Core_GameplayTagListForMemoryPack','Deserialize',0x37DF680),
         (104358,'Beyond.MemoryPack.Beyond_Gameplay_Core_GameplayTagListForMemoryPack+Beyond_Gameplay_Core_GameplayTagListForMemoryPackFormatter','Deserialize',0x37DF620)],
        source=source,expected_image='MemoryPack.Beyond.dll')
    code_windows=[]
    for rva,expected,role in (
        (0x37DF6A8,'837B3001','compare remaining bytes to one-byte wrapper header'),
        (0x37DF6B2,'488B43500FB630','read one wrapper header byte from reader cursor'),
        (0x37DF6C5,'48FF4350FF4340FF4344897B30','advance cursor and consumed counters by one byte'),
        (0x37DF6D2,'4080FEFF745649833E000F846CBB65014080FE010F8595BB6501',
         'accept null header 0xFF or non-null member-count header 1'),
    ):
        raw=pe.bytes_at_va(pe.image_base+rva,len(bytes.fromhex(expected)))
        require(raw,bytes.fromhex(expected),source,rva)
        code_windows.append({'rva':rva,'rawHex':raw.hex().upper(),'role':role})
    return {'methodSpec':spec,'methodInstantiation':inst.as_dict(),
            'listCarrier':carrier,'elementInstantiation':element_inst.as_dict(),
            'methodIdentities':wrapper_methods,'headerCodeWindows':code_windows,
            'wrapperFraming':{
                'headerByteWidth':1,'acceptedNonNullHeaderByte':1,'nullHeaderByte':0xFF,
                'remainingOffset':0x30,'cursorOffset':0x50,
                'consumedCounterOffsets':[0x40,0x44],
                'nestedCallRva':0x37DF6F9,
                'boundary':'The reviewed reader consumes exactly one header byte before the nested List<GameplayTag> read. Header 0xFF takes the null path; non-null header 1 reaches the nested read; other values leave the supported path. This is static wrapper code, not proof that the runtime provider selects it for the current file.',
            },
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


def skilldata_corpus_branch_evidence(corpus, *, source):
    """Cross-check the already-authenticated current SkillData census branches.

    This consumes report rows, not VFS bytes.  It keeps parser cursor and peek
    positions separate and never turns a conditional empty-list endpoint into
    an exact formatter cursor.
    """
    input_set = corpus.get('inputSetSha256')
    if not isinstance(input_set, str) or len(input_set) != 64:
        raise ContextError(source, 0, 'current 64-hex SkillData inputSetSha256', input_set)
    files = corpus.get('files')
    if not isinstance(files, list) or not files:
        raise ContextError(source, 0, 'nonempty current SkillData file rows', type(files).__name__)
    branch_counts = {'bothListsEmpty': 0, 'firstEmptySecondNonempty': 0, 'firstNonempty': 0}
    samples = {}
    def check_row(actual, expected, path, field):
        if actual != expected:
            raise ContextError(source, 0, f'{path}.{field} == {expected!r}', actual)

    for row in files:
        path = row.get('virtualPath')
        if not isinstance(path, str) or not path.startswith('Data/Json/SkillData/'):
            raise ContextError(source, 0, 'logical SkillData virtualPath', path)
        context = row.get('boundaryContext')
        prefix = row.get('commonPrefixFraming')
        if not isinstance(context, dict) or not isinstance(prefix, dict):
            raise ContextError(source, 0, 'bounded prefix and boundary context', path)
        check_row(context.get('inputSetSha256'), input_set, path, 'boundaryContext.inputSetSha256')
        check_row(context.get('logicalFileIdentity'), path, path, 'boundaryContext.logicalFileIdentity')
        check_row(context.get('logicalSha256'), row.get('logicalSha256'), path, 'boundaryContext.logicalSha256')
        check_row(context.get('parserCursor'), row.get('parserCursor'), path, 'boundaryContext.parserCursor')
        check_row(context.get('hardLimit'), row.get('hardLimit'), path, 'boundaryContext.hardLimit')
        lists = prefix.get('recordLists')
        if not isinstance(lists, list) or not lists:
            raise ContextError(source, 0, 'one or two current ActionGroupData list counts', path)
        first = lists[0].get('count')
        second = lists[1].get('count') if len(lists) > 1 else None
        if type(first) is not int or first < 0 or (second is not None and (type(second) is not int or second < 0)):
            raise ContextError(source, 0, 'nonnegative bounded list counts', {'path': path, 'counts': [first, second]})
        if first:
            branch = 'firstNonempty'
            expected_cursor = 6
            expected_stop = 0
        elif second:
            branch = 'firstEmptySecondNonempty'
            expected_cursor = 10
            expected_stop = 1
        else:
            branch = 'bothListsEmpty'
            expected_cursor = 10
            expected_stop = None
        check_row(row.get('parserCursor'), expected_cursor, path, 'parserCursor')
        check_row(prefix.get('cursorOffset'), f'0x{expected_cursor:x}', path, 'commonPrefixFraming.cursorOffset')
        ranges = prefix.get('byteRanges')
        if not isinstance(ranges, list):
            raise ContextError(source, 0, f'{path}.commonPrefixFraming.byteRanges list', ranges)
        range_cursor = 0
        for range_index, span in enumerate(ranges):
            start, end = span.get('start'), span.get('end')
            if (type(start) is not int or type(end) is not int or start != range_cursor
                    or end <= start or end > expected_cursor):
                raise ContextError(source, range_cursor,
                                   f'{path}.byteRanges[{range_index}] contiguous inside [0,{expected_cursor})',
                                   span)
            range_cursor = end
        if range_cursor != expected_cursor:
            raise ContextError(source, range_cursor,
                               f'{path}.byteRanges tile [0,{expected_cursor})', range_cursor)
        if expected_stop is not None:
            check_row(prefix.get('stopListIndex'), expected_stop, path, 'commonPrefixFraming.stopListIndex')
        else:
            check_row(prefix.get('stopListIndex'), None, path, 'commonPrefixFraming.stopListIndex')
        check_row(row.get('boundaryClass'), 'ambiguous', path, 'boundaryClass')
        candidates = row.get('framing', {}).get('candidateCount')
        check_row(type(candidates) is int and candidates >= 2, True, path, 'framing.candidateCount >= 2')
        branch_counts[branch] += 1
        sample = {
            'inputSetSha256': input_set,
            'logicalFileIdentity': path,
            'logicalSha256': row.get('logicalSha256'),
            'recordListCounts': [first] + ([] if second is None else [second]),
            'parserCursor': expected_cursor,
            'hardLimit': row.get('hardLimit'),
            'consumedByteRanges': prefix.get('byteRanges', []),
            'firstUnconsumedByteOffset': expected_cursor if branch != 'bothListsEmpty' else None,
            'peekOnlyMemberCount': (
                lists[0].get('firstRecordMemberCount') if branch == 'firstNonempty'
                else lists[1].get('firstRecordMemberCount') if branch == 'firstEmptySecondNonempty'
                else None
            ),
            'terminalCandidateStarts': [candidate.get('startOffset')
                                        for candidate in row.get('framing', {}).get('candidates', [])],
        }
        previous = samples.get(branch)
        sample_rank = (sum(sample['recordListCounts']), path)
        previous_rank = (sum(previous['recordListCounts']), previous['logicalFileIdentity']) if previous else None
        if previous_rank is None or sample_rank < previous_rank:
            samples[branch] = sample
    declared = corpus.get('summary', {}).get('filesSelected')
    if declared != len(files):
        raise ContextError(source, 0, 'summary.filesSelected equals report file row count',
                           {'declared': declared, 'actual': len(files)})
    return {
        'inputSetSha256': input_set,
        'filesSelected': len(files),
        'branchCounts': branch_counts,
        'representativeCurrentVfsSamples': samples,
        'emptyActionGroupCandidateRange': {
            'start': 1, 'end': 10, 'endExclusive': True,
            'candidateFiles': branch_counts['bothListsEmpty'],
            'conditionalOn': 'both List<T> reads taking the audited ListFormatter<T> candidate four-byte zero-count path',
            'exactClosedRecords': 0,
        },
        'wholeFileBoundary': {
            'ambiguousFiles': sum(1 for row in files if row.get('boundaryClass') == 'ambiguous'),
            'exactClosedRecords': corpus.get('summary', {}).get('byteBoundaryEvidence', {}).get('exactClosedRecords'),
            'boundary': 'The current report preserves all EOF candidates; these prefix branches do not choose the shifted terminal member.'
        },
        'boundary': 'Rows are cross-checked by inputSetSha256, logical identity/hash, parser cursor and hard limit. firstUnconsumedByteOffset is not consumed; peekOnlyMemberCount, where present, is a non-advancing peek. The current VFS report is authenticated but not re-streamed here.',
    }


def skilldata_actiongroup_branch_sample_witness(
        corpus, logical_path, raw, *, source, verified_action_tags=None,
        verified_action_prefix_tags=None):
    """Replay one current passiveEventActions list, stopping at unverified unions."""
    input_set = corpus.get('inputSetSha256')
    if (not isinstance(input_set, str) or len(input_set) != 64 or
            any(ch not in '0123456789abcdefABCDEF' for ch in input_set)):
        raise ContextError(source, 0, 'current 64-hex SkillData inputSetSha256', input_set)
    rows = [row for row in corpus.get('files', [])
            if isinstance(row, dict) and row.get('virtualPath') == logical_path]
    if len(rows) != 1:
        raise ContextError(source, 0,
                           f'exactly one current VFS SkillData row for {logical_path!r}',
                           len(rows))
    row = rows[0]
    if (not isinstance(logical_path, str) or
            not logical_path.startswith('Data/Json/SkillData/')):
        raise ContextError(source, 0, 'logical SkillData virtualPath', logical_path)
    if not isinstance(raw, bytes):
        raise ContextError(source, 0, 'current raw SkillData sample bytes', type(raw).__name__)

    hard_limit = row.get('hardLimit')
    if type(hard_limit) is not int or hard_limit != len(raw):
        raise ContextError(source, 0, 'sample hardLimit equals raw file length',
                           [hard_limit, len(raw)])
    logical_sha = hashlib.sha256(raw).hexdigest().upper()
    require(row.get('logicalSha256'), logical_sha, source, 0)
    require(row.get('inputSetSha256'), input_set, source, 0)
    boundary_context = row.get('boundaryContext')
    if not isinstance(boundary_context, dict):
        raise ContextError(source, 0, 'current sample boundaryContext', boundary_context)
    require(boundary_context.get('inputSetSha256'), input_set, source, 0)
    require(boundary_context.get('logicalFileIdentity'), logical_path, source, 0)
    require(boundary_context.get('logicalSha256'), logical_sha, source, 0)
    require(boundary_context.get('hardLimit'), hard_limit, source, 0)
    require(row.get('boundaryClass'), 'ambiguous', source, 0)
    candidate_count = row.get('framing', {}).get('candidateCount')
    require(type(candidate_count) is int and candidate_count >= 2, True, source, 0)
    prefix = row.get('commonPrefixFraming')
    record_lists = prefix.get('recordLists') if isinstance(prefix, dict) else None
    if not isinstance(record_lists, list) or not record_lists:
        raise ContextError(source, 0, 'one current ActionGroupData list count', record_lists)
    expected_list_count = record_lists[0].get('count')
    if type(expected_list_count) is not int or expected_list_count <= 0:
        raise ContextError(source, 2, 'positive current passiveEventActions list count',
                           expected_list_count)
    if len(raw) < 2:
        raise ContextError(source, 0, 'complete SkillData and ActionGroupData headers', len(raw))
    require(raw[0], 48, source, 0)
    require(raw[1], 2, source, 1)
    if len(raw) >= 6:
        actual_list_count = struct.unpack_from('<i', raw, 2)[0]
        require(actual_list_count, expected_list_count, source, 2)

    if verified_action_tags is None:
        verified_action_tags = {0xD5, 0xD6}
    if (not isinstance(verified_action_tags, (set, frozenset)) or
            any(type(tag) is not int or not 0 <= tag <= 0xFFFF
                for tag in verified_action_tags)):
        raise ContextError(source, 0, 'verified action tags as a set of 16-bit integers',
                           verified_action_tags)
    if verified_action_prefix_tags is None:
        verified_action_prefix_tags = set()
    if (not isinstance(verified_action_prefix_tags, (set, frozenset)) or
            any(type(tag) is not int or not 0 <= tag <= 0xFFFF
                for tag in verified_action_prefix_tags)):
        raise ContextError(source, 0,
                           'verified action-prefix tags as a set of 16-bit integers',
                           verified_action_prefix_tags)

    from scripts.game_data.memorypack.buff_actions import Reader, Unsupported

    class StopBeforeUnverifiedUnionReader(Reader):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.action_prefix_stop = None

        def _action(self, depth, tag, width):
            if tag == 0xFF or tag in verified_action_tags:
                return super()._action(depth, tag, width)
            if tag == 0xC9 and tag in verified_action_prefix_tags:
                start = self.pos
                available = self.limit - self.pos
                if (width != 1 or available < 2 or self.data[self.pos] != 0xC9 or
                        self.data[self.pos + 1] != 8):
                    raise Unsupported(self.source, start,
                                      'non-null 0xC9 member-eight normal path',
                                      tag,
                                      'opaque-union')
                self.take(width, 'union-tag')
                self.header(8)
                self.take(1, 'anonymous-byte')
                for _ in range(3):
                    self.take(4, 'anonymous-scalar32')
                self.take(1, 'anonymous-byte')
                self.action_prefix_stop = {
                    'tag': tag,
                    'start': start,
                    'end': self.pos,
                    'memberHeader': 8,
                    'sourceReadWidthsAfterHeader': [1, 4, 4, 4, 1],
                    'consumedUnionRecord': False,
                    'nextSourceReadType': 'Beyond.Gameplay.Core.SequenceActionData',
                    'nextSourceReadOffset': self.pos,
                    'nextSourceReadConsumed': False,
                    'nextSourceReadFirstByte': (
                        self.data[self.pos] if self.pos < self.limit else None),
                    'remainingBytesOpaque': True,
                }
                raise Unsupported(self.source, self.pos,
                                  'first nested SequenceActionData call remains unread',
                                  tag, 'verified-prefix-stop')
            # _action is entered before the tag bytes are consumed, so this
            # keeps every unverified union at its first byte (including FA/u16).
            raise Unsupported(self.source, self.pos,
                              'non-null AbilityActionData payload remains opaque',
                              tag, 'opaque-union')

    reader = StopBeforeUnverifiedUnionReader(raw, source, limit=hard_limit)
    reader.pos = 2
    parser_error = None
    try:
        reader.ability_action_map_collection_profile(0)
        parse_status = 'passive-list-consumed-to-conditional-static-end'
        boundary_class = 'structural-prefix'
    except Exception as exc:
        diagnostic = getattr(exc, 'diagnostic', None)
        if not isinstance(diagnostic, dict):
            raise
        parser_error = diagnostic
        if diagnostic.get('category') == 'opaque-union':
            parse_status = 'stopped-before-first-nonnull-action-union'
            boundary_class = 'opaque'
        elif diagnostic.get('category') == 'verified-prefix-stop':
            parse_status = 'stopped-after-verified-action-prefix'
            boundary_class = 'structural-prefix'
        elif diagnostic.get('category') == 'truncated':
            parse_status = 'truncated-structural-prefix'
            boundary_class = 'structural-prefix'
        elif diagnostic.get('category') in ('member-count', 'count-bounds', 'malformed'):
            parse_status = 'invalid-structural-prefix'
            boundary_class = 'malformed'
        else:
            parse_status = 'unsupported-structural-prefix'
            boundary_class = 'unsupported'

    consumed_ranges = [
        {'start': 0, 'end': 1, 'kind': 'SkillData.memberCount', 'value': raw[0]},
        {'start': 1, 'end': 2, 'kind': 'ActionGroupData.memberCount', 'value': raw[1]},
        *reader.ranges,
    ]
    range_cursor = 0
    for index, span in enumerate(consumed_ranges):
        start, end = span.get('start'), span.get('end')
        if (type(start) is not int or type(end) is not int or start != range_cursor or
                end <= start or end > reader.pos):
            raise ContextError(source, range_cursor,
                               f'byteRanges[{index}] contiguous inside [0,{reader.pos})', span)
        range_cursor = end
    require(range_cursor, reader.pos, source, range_cursor)

    count_fields = []
    for span in consumed_ranges:
        if span.get('kind') == 'count-i32':
            count_fields.append({
                'offset': span['start'],
                'end': span['end'],
                'signedI32': struct.unpack_from('<i', raw, span['start'])[0],
            })
    unconsumed_union = None
    if parser_error and parser_error.get('category') == 'opaque-union':
        offset = reader.pos
        unconsumed_union = {
            'offset': offset,
            'firstByte': raw[offset],
            'tag': parser_error.get('actual'),
            'consumed': False,
        }
    action_union_prefix_stop = getattr(reader, 'action_prefix_stop', None)
    if parser_error and parser_error.get('category') == 'verified-prefix-stop':
        if not isinstance(action_union_prefix_stop, dict):
            raise ContextError(source, reader.pos,
                               'verified-prefix diagnostic has a bounded action-prefix stop record',
                               action_union_prefix_stop)
        require(action_union_prefix_stop.get('end'), reader.pos, source, reader.pos)
    union_header_observations = []
    for record in reader.records:
        if record.get('kind') != 'union' or record.get('tag') == 0xFF:
            continue
        start = record.get('start')
        if type(start) is not int or not start < record.get('end', start):
            raise ContextError(source, reader.pos, 'completed action union has a byte range', record)
        tag_width = 3 if raw[start] == 0xFA else 1
        header_offset = start + tag_width
        if header_offset >= record['end'] or raw[header_offset] == 0xFF:
            continue
        union_header_observations.append({
            'tag': record['tag'],
            'start': start,
            'end': record['end'],
            'tagWidth': tag_width,
            'tagPrefixByte': raw[start],
            'tagEncodingHex': raw[start:header_offset].hex().upper(),
            'memberHeaderOffset': header_offset,
            'memberHeaderValue': raw[header_offset],
        })
    next_member_count_peek = None
    if (parse_status == 'passive-list-consumed-to-conditional-static-end' and
            reader.pos + 4 <= hard_limit):
        next_member_count_peek = {
            'fieldName': 'timelineActions.count',
            'offset': reader.pos,
            'signedI32': struct.unpack_from('<i', raw, reader.pos)[0],
            'consumed': False,
        }
    return {
        'inputSetSha256': input_set,
        'logicalFileIdentity': logical_path,
        'logicalSha256': logical_sha,
        'hardLimit': hard_limit,
        'parserCursor': reader.pos,
        'passiveEventActionsListCount': expected_list_count,
        'status': parse_status,
        'boundaryClass': boundary_class,
        'consumedByteRanges': consumed_ranges,
        'countI32Fields': count_fields,
        'completedNestedRecords': reader.records,
        'completedActionUnionHeaderObservations': union_header_observations,
        'nextMemberCountPeekOnly': next_member_count_peek,
        'opaqueByteRanges': ([] if reader.pos == hard_limit else [
            {'start': reader.pos, 'end': hard_limit, 'kind': 'unconsumed-actiongroup-and-skilldata-bytes'}
        ]),
        'firstUnconsumedActionUnionByte': unconsumed_union,
        'actionUnionPrefixStop': action_union_prefix_stop,
        'parserError': parser_error,
        'wholeSkillDataClassification': 'ambiguous',
        'wholeSkillDataExactClosedRecords': 0,
        'boundary': ('Only the first ActionGroupData passiveEventActions list is replayed. A union advances '
                     'only when its current-build tag route and hash-pinned native action reader are supplied '
                     'to the separate alignment gate; every other non-null tag stops at its first byte. '
                     'timelineActions, the rest of ActionGroupData, and the whole SkillData endpoint are '
                     'not consumed.'),
    }


def skilldata_timeline_branch_sample_witness(corpus, logical_path, raw, *, source):
    """Replay only the first TimelineActionData structural prefix in a current VFS row."""
    input_set = corpus.get('inputSetSha256')
    if (not isinstance(input_set, str) or len(input_set) != 64 or
            any(ch not in '0123456789abcdefABCDEF' for ch in input_set)):
        raise ContextError(source, 0, 'current 64-hex SkillData inputSetSha256', input_set)
    rows = [row for row in corpus.get('files', [])
            if isinstance(row, dict) and row.get('virtualPath') == logical_path]
    if len(rows) != 1:
        raise ContextError(source, 0,
                           f'exactly one current VFS SkillData row for {logical_path!r}',
                           len(rows))
    row = rows[0]
    if (not isinstance(logical_path, str) or
            not logical_path.startswith('Data/Json/SkillData/')):
        raise ContextError(source, 0, 'logical SkillData virtualPath', logical_path)
    if not isinstance(raw, bytes):
        raise ContextError(source, 0, 'current raw SkillData sample bytes',
                           type(raw).__name__)
    hard_limit = row.get('hardLimit')
    if type(hard_limit) is not int or hard_limit != len(raw):
        raise ContextError(source, 0, 'sample hardLimit equals raw file length',
                           [hard_limit, len(raw)])
    logical_sha = hashlib.sha256(raw).hexdigest().upper()
    require(row.get('logicalSha256'), logical_sha, source, 0)
    require(row.get('inputSetSha256'), input_set, source, 0)
    boundary_context = row.get('boundaryContext')
    if not isinstance(boundary_context, dict):
        raise ContextError(source, 0, 'current sample boundaryContext', boundary_context)
    for key, expected in (
            ('inputSetSha256', input_set),
            ('logicalFileIdentity', logical_path),
            ('logicalSha256', logical_sha),
            ('hardLimit', hard_limit)):
        require(boundary_context.get(key), expected, source, 0)
    require(row.get('boundaryClass'), 'ambiguous', source, 0)
    require(row.get('parserCursor'), 10, source, 0)
    require(row.get('hardLimit'), hard_limit, source, 0)
    framing = row.get('framing')
    if not isinstance(framing, dict):
        raise ContextError(source, 0, 'current ambiguous SkillData framing', framing)
    candidate_count = framing.get('candidateCount')
    require(type(candidate_count) is int and candidate_count >= 2, True, source, 0)
    prefix = row.get('commonPrefixFraming')
    if not isinstance(prefix, dict):
        raise ContextError(source, 0, 'current common SkillData prefix', prefix)
    require(prefix.get('parserCursor'), 10, source, 0)
    record_lists = prefix.get('recordLists')
    if not isinstance(record_lists, list) or len(record_lists) != 2:
        raise ContextError(source, 0, 'two current ActionGroupData list-count reads',
                           record_lists)
    count_offsets = []
    for index, item in enumerate(record_lists):
        raw_offset = item.get('countOffset')
        try:
            count_offsets.append(int(raw_offset, 0) if isinstance(raw_offset, str)
                                 else raw_offset)
        except ValueError as exc:
            raise ContextError(source, 2 + index * 4,
                               'bounded list-count source offset', raw_offset) from exc
    require(count_offsets, [2, 6], source, 2)
    first_count, timeline_count = (item.get('count') for item in record_lists)
    require(first_count, 0, source, 2)
    if type(timeline_count) is not int or timeline_count <= 0:
        raise ContextError(source, 6, 'positive current timelineActions list count',
                           timeline_count)
    if hard_limit < 10:
        raise ContextError(source, 0, 'current common prefix fits within hardLimit',
                           hard_limit)
    require(raw[0], 48, source, 0)
    require(raw[1], 2, source, 1)
    require(struct.unpack_from('<i', raw, 2)[0], first_count, source, 2)
    require(struct.unpack_from('<i', raw, 6)[0], timeline_count, source, 6)

    prefix_ranges = prefix.get('byteRanges')
    if not isinstance(prefix_ranges, list):
        raise ContextError(source, 0, 'current common-prefix byte-range manifest',
                           prefix_ranges)
    prefix_cursor = 0
    for index, span in enumerate(prefix_ranges):
        start, end = span.get('start'), span.get('end')
        if (type(start) is not int or type(end) is not int or
                start != prefix_cursor or end <= start or end > 10):
            raise ContextError(source, prefix_cursor,
                               f'common prefix byteRanges[{index}] contiguous in [0,10)', span)
        prefix_cursor = end
    require(prefix_cursor, 10, source, prefix_cursor)

    cursor = 10
    candidate_ranges = []
    failure = None

    def take(width, kind):
        nonlocal cursor, failure
        if type(width) is not int or width < 0:
            failure = {'category': 'malformed', 'offset': cursor,
                       'expected': 'non-negative byte width', 'actual': width}
            return None
        if width > hard_limit - cursor:
            failure = {'category': 'truncated', 'offset': cursor,
                       'expected': {'bytes': width},
                       'actual': {'remaining': hard_limit - cursor}}
            return None
        start = cursor
        cursor += width
        if width:
            candidate_ranges.append({'start': start, 'end': cursor, 'kind': kind})
        return raw[start:cursor]

    def header(expected, kind):
        nonlocal failure
        if cursor >= hard_limit:
            failure = {'category': 'truncated', 'offset': cursor,
                       'expected': {'bytes': 1}, 'actual': {'remaining': 0}}
            return False
        if raw[cursor] != expected:
            failure = {'category': 'member-count', 'offset': cursor,
                       'expected': expected, 'actual': raw[cursor]}
            return False
        return take(1, kind) is not None

    if not header(4, 'TimelineActionData.member-header'):
        pass
    elif take(4, 'TimelineActionData.endFrame.i32') is None:
        pass
    elif not header(3, 'SequenceActionData.member-header'):
        pass
    else:
        count_raw = take(4, 'SequenceActionData.actionData.count-i32')
        if count_raw is not None:
            action_count = struct.unpack('<i', count_raw)[0]
            if action_count < -1:
                failure = {'category': 'count-bounds', 'offset': cursor - 4,
                           'expected': {'minimum': -1}, 'actual': action_count}
            else:
                maximum = max(0, hard_limit - cursor - 2)
                if action_count > maximum:
                    failure = {'category': 'count-bounds', 'offset': cursor - 4,
                               'expected': {'minimum': -1, 'maximum': maximum},
                               'actual': action_count}

    tag_peek = None
    if failure is None and len(candidate_ranges) == 4 and action_count > 0:
        if cursor >= hard_limit:
            failure = {'category': 'truncated-action-tag', 'offset': cursor,
                       'expected': {'minimumBytes': 1},
                       'actual': {'remaining': 0}}
        else:
            first_byte = raw[cursor]
            tag_width = 3 if first_byte == 0xFA else 1
            if tag_width > hard_limit - cursor:
                failure = {'category': 'truncated-action-tag', 'offset': cursor,
                           'expected': {'bytes': tag_width},
                           'actual': {'remaining': hard_limit - cursor}}
                tag_peek = {'offset': cursor, 'firstByte': first_byte,
                            'tag': None, 'tagWidth': tag_width,
                            'encodingHex': raw[cursor:hard_limit].hex().upper(),
                            'consumed': False}
            else:
                tag = (struct.unpack_from('<H', raw, cursor + 1)[0]
                       if tag_width == 3 else first_byte)
                tag_peek = {'offset': cursor, 'firstByte': first_byte,
                            'tag': tag, 'tagWidth': tag_width,
                            'encodingHex': raw[cursor:cursor + tag_width].hex().upper(),
                            'consumed': False}

    candidate_status = 'candidate-first-timeline-sequence-prefix'
    if failure is not None:
        if failure['category'] in ('member-count', 'count-bounds', 'malformed'):
            candidate_status = 'malformed-timeline-structural-prefix'
        elif failure['category'] == 'truncated-action-tag':
            candidate_status = 'truncated-first-action-tag'
        else:
            candidate_status = 'truncated-timeline-structural-prefix'
    elif action_count <= 0:
        candidate_status = 'empty-first-sequence-action-list'

    return {
        'inputSetSha256': input_set.upper(),
        'logicalFileIdentity': logical_path,
        'logicalSha256': logical_sha,
        'hardLimit': hard_limit,
        'authoritativeParserCursor': 10,
        'candidateStart': 10,
        'candidateCursor': cursor,
        'timelineActionsListCount': timeline_count,
        'firstSequenceActionDataCount': action_count if failure is None or cursor >= 20 else None,
        'status': candidate_status,
        'failure': failure,
        'currentParserByteRanges': prefix_ranges,
        'candidateByteRanges': candidate_ranges,
        'firstActionUnionTagPeekOnly': tag_peek,
        'opaqueByteRanges': ([] if cursor == hard_limit else [
            {'start': cursor, 'end': hard_limit,
             'kind': 'unconsumed-timeline-actiongroup-and-skilldata-bytes'}]),
        'exactClosedTimelineActionRecords': 0,
        'exactClosedActionGroupDataRecords': 0,
        'wholeSkillDataClassification': 'ambiguous',
        'wholeSkillDataExactClosedRecords': 0,
        'boundary': ('The current corpus parser remains at byte 10. This separate structural candidate follows only the '
                     'first TimelineActionData header/endFrame and its SequenceActionData header/action count, then peeks '
                     'at most the first action tag. It does not close a timeline action, ActionGroupData or SkillData.'),
    }


def _skilldata_action_fixed_member_width(read_type):
    """Return widths for scalar members that the selected native reader reads inline."""
    if not isinstance(read_type, str):
        return None
    normalized = read_type.strip().lower().replace('_', '-')
    if normalized in ('byte', 'boolean', 'bool'):
        return 1
    if normalized in ('scalar32', 'float32', 'raw-float32', 'raw-float32-bits'):
        return 4
    if normalized == 'scalar64':
        return 8
    match = re.fullmatch(r'raw(\d+)', normalized)
    if match is not None:
        width = int(match.group(1))
        return width if width in (1, 2, 4, 8, 12, 16) else None
    return None


def _skilldata_verified_byte_payload_reader(action_reader, shared_helper, *, source):
    """Join the two PlayAnimation payload callsites to the audited signed-length helper."""
    call_sites = action_reader.get('verifiedSourceReadCallSites')
    if not isinstance(call_sites, list):
        raise ContextError(source, 0x115,
                           'verified PlayAnimation byte-payload source callsites', call_sites)
    selected = [row for row in call_sites if isinstance(row, dict) and
                row.get('readType') == 'byte-payload']
    expected_sites = {
        (4, 0x3777126, 0x2CA8700),
        (14, 0x377730E, 0x2CA8700),
    }
    actual_sites = {(row.get('memberIndex'), row.get('callInstructionRva'),
                     row.get('targetRva')) for row in selected}
    require(actual_sites, expected_sites, source, 0x115)
    require(len(selected), 2, source, 0x115)

    if not isinstance(shared_helper, dict):
        raise ContextError(source, 0x2CA8700,
                           'independent current signed-length byte-payload helper audit',
                           shared_helper)
    expected_windows = {
        0x2CA8729: '488B43504863388B733083EE040F885C8CE30148834350048343400483434404897330',
        0x2CA874C: '48634344488B4B18482BC8483BCF0F8C528CE30183FFFF743785FF7517',
        0x2CA8780: '4533C08BD7488BCB488B5C2430488B7424384883C4205FE974020000',
        0x2CA8A97: '4533C9448BC7488BD5488BCEE878F8FFFF488BE885FF7418',
        0x2CA8AAF: '8B73302BF70F88B0A4F70148017B50017B40017B44897330',
    }
    windows = shared_helper.get('windows')
    if not isinstance(windows, list):
        raise ContextError(source, 0x2CA8700,
                           'independent byte-payload helper/consumer instruction windows', windows)
    actual_windows = {row.get('rva'): row.get('rawHex', '').upper()
                      for row in windows if isinstance(row, dict)}
    for rva, raw_hex in expected_windows.items():
        require(actual_windows.get(rva), raw_hex, source, rva)
    helper_calls = shared_helper.get('orderedCalls')
    if not isinstance(helper_calls, list):
        raise ContextError(source, 0x2CA8700,
                           'independent byte-payload helper consumer callsites', helper_calls)
    expected_helper_calls = {(0x3D9BBE5, 0x2CA8700),
                             (0x3D9BC37, 0x2CA8700)}
    actual_helper_calls = {(row.get('rva'), row.get('targetRva'))
                           for row in helper_calls if isinstance(row, dict) and
                           row.get('targetRva') == 0x2CA8700}
    require(actual_helper_calls, expected_helper_calls, source, 0x2CA8700)
    boundary = shared_helper.get('boundary')
    if (not isinstance(boundary, str) or 'signed DWORD' not in boundary or
            '-1 returns null' not in boundary or 'positive length' not in boundary):
        raise ContextError(source, 0x2CA8700,
                           'bounded signed-length/null/positive payload consumer evidence', boundary)
    return {
        'actionTag': 0x115,
        'actionMemberCallSites': [dict(row) for row in selected],
        'sharedHelperTargetRva': 0x2CA8700,
        'independentConsumerCallSites': [
            {'callInstructionRva': rva, 'targetRva': target}
            for rva, target in sorted(actual_helper_calls)],
        'verifiedHelperWindows': [
            {'rva': rva, 'rawHex': actual_windows[rva]}
            for rva in sorted(expected_windows)],
        'lengthSemantics': 'signed-i32; -1 null; 0 empty; positive length-bounded opaque payload',
        'payloadSemantics': 'opaque; no decoding or gameplay field name is assigned',
        'providerSelection': 'unobserved',
    }


def _skilldata_read_byte_payload_candidate(raw, start, hard_limit, *, kind, source):
    """Read only a signed length and its in-bounds opaque payload bytes."""
    if start < 0 or hard_limit < start or hard_limit > len(raw):
        raise ContextError(source, start, 'byte-payload start and hard limit inside current raw bytes',
                           {'start': start, 'hardLimit': hard_limit, 'rawLength': len(raw)})
    if hard_limit - start < 4:
        return {
            'cursor': start, 'ranges': [], 'opaquePayloadByteRanges': [],
            'length': None, 'complete': False, 'status': 'truncated-byte-payload-length',
            'failure': {'category': 'truncated', 'offset': start,
                        'kind': f'{kind}.length-i32', 'expectedBytes': 4,
                        'remainingBytes': hard_limit - start},
        }
    length = struct.unpack_from('<i', raw, start)[0]
    ranges = [{'start': start, 'end': start + 4,
               'kind': f'{kind}.length-i32', 'value': length}]
    after_length = start + 4
    if length < -1:
        return {
            'cursor': after_length, 'ranges': ranges, 'opaquePayloadByteRanges': [],
            'length': length, 'complete': False, 'status': 'unsupported-byte-payload-length',
            'failure': {'category': 'unsupported', 'offset': start,
                        'kind': f'{kind}.length-i32', 'actual': length,
                        'supportedValues': '-1, 0, or a positive in-limit length'},
        }
    payload_length = max(length, 0)
    available = hard_limit - after_length
    if payload_length > available:
        return {
            'cursor': after_length, 'ranges': ranges, 'opaquePayloadByteRanges': [],
            'length': length, 'complete': False, 'status': 'truncated-byte-payload',
            'failure': {'category': 'truncated', 'offset': after_length,
                        'kind': f'{kind}.opaque-bytes', 'expectedBytes': payload_length,
                        'remainingBytes': available},
        }
    opaque_ranges = []
    if payload_length:
        payload_range = {'start': after_length, 'end': after_length + payload_length,
                         'kind': f'{kind}.opaque-bytes'}
        ranges.append(payload_range)
        opaque_ranges.append(dict(payload_range))
    return {
        'cursor': after_length + payload_length, 'ranges': ranges,
        'opaquePayloadByteRanges': opaque_ranges, 'length': length,
        'complete': True, 'status': 'bounded-byte-payload', 'failure': None,
    }


def _skilldata_read_sequence_data_candidate(raw, start, hard_limit, *, source):
    """Read SequenceActionData's null/empty path; stop before any list element."""
    ranges = []
    position = start
    if hard_limit - position < 1:
        return {'cursor': position, 'ranges': ranges, 'complete': False,
                'status': 'truncated-sequence-action-header', 'failure': {
                    'category': 'truncated', 'offset': position,
                    'kind': 'SequenceActionData.member-header', 'expectedBytes': 1,
                    'remainingBytes': 0}}
    header = raw[position]
    ranges.append({'start': position, 'end': position + 1,
                   'kind': 'SequenceActionData.member-header', 'value': header})
    position += 1
    if header == 0xFF:
        return {'cursor': position, 'ranges': ranges, 'complete': True,
                'status': 'candidate-null-sequence', 'header': header,
                'count': None, 'failure': None}
    if header != 3:
        return {'cursor': position, 'ranges': ranges, 'complete': False,
                'status': 'malformed-sequence-action-header', 'header': header,
                'failure': {'category': 'member-count', 'offset': start,
                            'expected': [3, 0xFF], 'actual': header}}
    if hard_limit - position < 4:
        return {'cursor': position, 'ranges': ranges, 'complete': False,
                'status': 'truncated-sequence-action-count', 'header': header,
                'failure': {'category': 'truncated', 'offset': position,
                            'kind': 'SequenceActionData.list-count-i32',
                            'expectedBytes': 4, 'remainingBytes': hard_limit - position}}
    count = struct.unpack_from('<i', raw, position)[0]
    ranges.append({'start': position, 'end': position + 4,
                   'kind': 'SequenceActionData.list-count-i32', 'value': count})
    position += 4
    if count < -1:
        return {'cursor': position, 'ranges': ranges, 'complete': False,
                'status': 'unsupported-sequence-action-count', 'header': header,
                'count': count, 'failure': {'category': 'unsupported',
                    'offset': position - 4, 'kind': 'SequenceActionData.list-count-i32',
                    'actual': count, 'supportedLowerBound': -1}}
    if count > 0:
        first_action_tag = None
        if position < hard_limit:
            first_action_tag = {
                'offset': position,
                'firstByte': raw[position],
                'consumed': False,
            }
        return {'cursor': position, 'ranges': ranges, 'complete': False,
                'status': 'stopped-before-sequence-action-elements', 'header': header,
                'count': count, 'firstActionUnionTagPeekOnly': first_action_tag,
                'failure': (None if first_action_tag is not None else {
                    'category': 'truncated', 'offset': position,
                    'kind': 'SequenceActionData.firstActionUnionTag',
                    'expectedBytes': 1, 'remainingBytes': 0})}
    for index in range(2):
        if position >= hard_limit:
            return {'cursor': position, 'ranges': ranges, 'complete': False,
                    'status': 'truncated-sequence-action-tail', 'header': header,
                    'count': count, 'failure': {'category': 'truncated',
                        'offset': position, 'kind': f'SequenceActionData.trailing-byte[{index}]',
                        'expectedBytes': 1, 'remainingBytes': 0}}
        ranges.append({'start': position, 'end': position + 1,
                       'kind': f'SequenceActionData.trailing-byte[{index}]',
                       'value': raw[position]})
        position += 1
    return {'cursor': position, 'ranges': ranges, 'complete': True,
            'status': 'candidate-empty-sequence', 'header': header,
            'count': count, 'failure': None}


def _skilldata_sequence_tail_windows(sequence_reader, *, source):
    expected = {
        0x39C6EA2: '488B43500FB6288B7B3083EF017911BA01000000488BCBE882B2100284C0750D48FF4350FF4340FF4344897B30',
        0x39C6F07: '488B43500FB6288B7B3083EF017911BA01000000488BCBE81DB2100284C0750D48FF4350FF4340FF4344897B30',
    }
    windows = sequence_reader.get('windows')
    if not isinstance(windows, list):
        raise ContextError(source, 0x39C6EA2,
                           'SequenceActionData empty-list trailing byte read windows', windows)
    actual = {row.get('rva'): str(row.get('rawHex', '')).upper()
              for row in windows if isinstance(row, dict)}
    for rva, raw_hex in expected.items():
        require(actual.get(rva), raw_hex, source, rva)
    return [{'rva': rva, 'rawHex': actual[rva]} for rva in sorted(expected)]


def _skilldata_continue_play_animation_candidate(raw, start, hard_limit, *,
                                                  action_start,
                                                  root_read_order,
                                                  sequence_reader,
                                                  payload_helper_evidence,
                                                  source):
    """Replay the 0x115 selected reader field sequence without closing parents."""
    if len(root_read_order) != 16 or root_read_order[:4] != [
            'byte', 'scalar32', 'scalar32', 'scalar32']:
        raise ContextError(source, start,
                           'PlayAnimation member16 reader order after the shared fixed prefix',
                           root_read_order)
    if (payload_helper_evidence.get('sharedHelperTargetRva') != 0x2CA8700 or
            payload_helper_evidence.get('providerSelection') != 'unobserved'):
        raise ContextError(source, start,
                           'current helper identity with runtime provider kept unobserved',
                           payload_helper_evidence)
    sequence_tail_windows = _skilldata_sequence_tail_windows(
        sequence_reader, source=source)
    ranges = []
    opaque_payload_ranges = []
    position = start
    nested_sequence = None
    failure = None
    status = None
    for member_index, member_type in enumerate(root_read_order[4:], start=4):
        member_kind = f'PlayAnimationAction.member{member_index}'
        if member_type == 'byte-payload':
            payload = _skilldata_read_byte_payload_candidate(
                raw, position, hard_limit, kind=f'{member_kind}.byte-payload',
                source=source)
            ranges.extend(payload['ranges'])
            opaque_payload_ranges.extend(payload['opaquePayloadByteRanges'])
            position = payload['cursor']
            if not payload['complete']:
                status = f'{payload["status"]}-member{member_index}'
                failure = payload['failure']
                break
            continue
        if member_type == 'sequence':
            nested_sequence = _skilldata_read_sequence_data_candidate(
                raw, position, hard_limit, source=source)
            nested_sequence['ranges'] = [
                {**row, 'kind': f'{member_kind}.sequence.{row["kind"]}'}
                for row in nested_sequence['ranges']
            ]
            ranges.extend(nested_sequence['ranges'])
            position = nested_sequence['cursor']
            if not nested_sequence['complete']:
                status = nested_sequence['status']
                failure = nested_sequence['failure']
                break
            continue
        width = _skilldata_action_fixed_member_width(member_type)
        if width is None:
            status = 'stopped-before-unsupported-play-animation-member'
            failure = {'category': 'unsupported', 'offset': position,
                       'memberIndex': member_index, 'readType': member_type}
            break
        if hard_limit - position < width:
            status = 'truncated-play-animation-fixed-member'
            failure = {'category': 'truncated', 'offset': position,
                       'memberIndex': member_index, 'kind': member_type,
                       'expectedBytes': width, 'remainingBytes': hard_limit - position}
            break
        ranges.append({'start': position, 'end': position + width,
                       'kind': f'{member_kind}.{member_type}'})
        position += width
    else:
        status = 'candidate-play-animation-reader-field-sequence-exhausted'
    complete = status == 'candidate-play-animation-reader-field-sequence-exhausted'
    return {
        'cursor': position,
        'ranges': ranges,
        'opaquePayloadByteRanges': opaque_payload_ranges,
        'complete': complete,
        'status': status,
        'failure': failure,
        'recordEndCandidate': ({
            'start': action_start,
            'end': position,
            'memberCount': 16,
            'sourceReadOrderKey': 'member16',
            'classification': 'candidate selected-reader field-sequence end; live provider/cache unobserved',
        } if complete else None),
        'nestedSequence': nested_sequence,
        'independentlyVerifiedSequenceTailWindows': sequence_tail_windows,
        'bytePayloadEvidence': payload_helper_evidence,
    }


def _skilldata_force_sync_reader_evidence(timeline_reader, *,
                                          payload_helper_evidence,
                                          bool_helper_evidence,
                                          gameassembly_image_base,
                                          source):
    """Verify the exact current ForceSync reader order before replaying bytes."""
    timeline_members = timeline_reader.get('serializedMembers')
    if not isinstance(timeline_members, list) or len(timeline_members) != 4:
        raise ContextError(source, 0, 'four current TimelineActionData members',
                           timeline_members)
    force_sync_member = timeline_members[3]
    force_sync_method_spec = force_sync_member.get('readerMethodSpec', {})
    require((force_sync_member.get('serializedOrderIndex'),
             force_sync_member.get('fieldName'),
             force_sync_method_spec.get('index'),
             force_sync_method_spec.get('genericType', {}).get('typeDefinitionIndex'),
             force_sync_method_spec.get('genericType', {}).get('typeName')),
            (3, 'forceSyncAnimData', 620038, 9198,
             'Beyond.Gameplay.Core.TimelineAction+ForceSyncAnimData'),
            source, 0x32CD16F)

    force_reader = timeline_reader.get('forceSyncAnimDataReader')
    if not isinstance(force_reader, dict):
        raise ContextError(source, 0x32CE4B0,
                           'current ForceSyncAnimData selected-reader evidence',
                           force_reader)
    require((force_reader.get('typeDefinitionIndex'), force_reader.get('typeName')),
            (9198, 'Beyond.Gameplay.Core.TimelineAction+ForceSyncAnimData'),
            source, 0x32CE4B0)

    methods = timeline_reader.get('methods')
    if not isinstance(methods, list):
        raise ContextError(source, 0x32CE4B0,
                           'TimelineActionData/ForceSync reader module-token rows', methods)
    root_type = ('Beyond.MemoryPack.Beyond_Gameplay_Core_TimelineAction_'
                 'ForceSyncAnimDataForMemoryPack')
    root_methods = [row for row in methods if isinstance(row, dict) and
                    row.get('methodIndex') == 107909]
    if len(root_methods) != 1:
        raise ContextError(source, 0x32CE4B0,
                           'one current ForceSyncAnimData root Deserialize method',
                           len(root_methods))
    root_method = root_methods[0]
    require((root_method.get('declaringType'), root_method.get('name'),
             root_method.get('image'), root_method.get('pointerVa')),
            (root_type, 'Deserialize', 'MemoryPack.Beyond.dll',
             gameassembly_image_base + 0x32CE4B0), source, 0x32CE4B0)

    windows = timeline_reader.get('codeWindows')
    if not isinstance(windows, list):
        raise ContextError(source, 0x32CE4B0,
                           'hash-pinned ForceSyncAnimData reader/formatter windows', windows)
    expected_root_window = (
        0x32CE4B0, 0x32CE75C,
        '1FB17BEDE173176E0BC082E7C315267B6FC6F3CE76796DB90A627E9B0E9D7767')
    matches = [row for row in windows if isinstance(row, dict) and
               (row.get('startRva'), row.get('endRva'), row.get('sha256')) ==
               expected_root_window]
    if len(matches) != 1:
        raise ContextError(source, 0x32CE4B0,
                           'one exact ForceSyncAnimData root code window', matches)

    expected_header_and_stores = {
        (0x32CE57E, '4080FE04'),
        (0x32CE5A9, '884610'),
        (0x32CE5D9, '49894018'),
    }
    reader_windows = force_reader.get('verifiedInstructionWindows')
    if not isinstance(reader_windows, list):
        raise ContextError(source, 0x32CE57E,
                           'ForceSync member-count and member-store instruction evidence',
                           reader_windows)
    actual_header_and_stores = {
        (row.get('rva'), str(row.get('rawHex', '')).upper())
        for row in reader_windows if isinstance(row, dict)
    }
    require(actual_header_and_stores, expected_header_and_stores, source, 0x32CE57E)

    members = force_reader.get('serializedMembers')
    if not isinstance(members, list) or len(members) != 4:
        raise ContextError(source, 0x32CE4B0,
                           'four current ForceSyncAnimData serialized members', members)
    expected_members = [
        (0, 'forceSync', 0x10, 'bool'),
        (1, 'montageName', 0x18, 'System.String'),
        (2, 'playbackSpeed', 0x24, 'System.Single'),
        (3, 'targetFrame', 0x20, 'System.Int32'),
    ]
    require([(row.get('serializedOrderIndex'), row.get('fieldName'),
              row.get('objectField', {}).get('fieldOffset'),
              row.get('objectField', {}).get('fieldType', {}).get('wireType'))
             for row in members], expected_members, source, 0x32CE4B0)
    for row in members:
        require(row.get('objectField', {}).get('typeDefinitionIndex'), 9198,
                source, row.get('serializedOrderIndex'))

    force_sync_reader = members[0].get('reader', {})
    montage_reader = members[1].get('reader', {})
    require((force_sync_reader.get('callInstructionRva'),
             force_sync_reader.get('callInstructionHex'),
             force_sync_reader.get('targetRva'), force_sync_reader.get('role')),
            (0x32CE58E, 'E82DA39DFF', 0x2CA88C0, 'read forceSync boolean'),
            source, 0x32CE58E)
    require((montage_reader.get('callInstructionRva'),
             montage_reader.get('callInstructionHex'),
             montage_reader.get('targetRva'), montage_reader.get('role')),
            (0x32CE5B2, 'E849A19DFF', 0x2CA8700, 'read montageName string'),
            source, 0x32CE5B2)

    scalar_expectations = {
        'playbackSpeed': (
            'inline-float32', 4,
            {(0x32CE635, 'F30F1030'), (0x32CE652, '4883435004'),
             (0x32CE67B, 'F30F117024')}),
        'targetFrame': (
            'inline-int32', 4,
            {(0x32CE69A, '8B28'), (0x32CE6B5, '4883435004'),
             (0x32CE6D8, '896820')}),
    }
    for field_name, (kind, byte_width, expected_instructions) in scalar_expectations.items():
        reader = next(row for row in members if row.get('fieldName') == field_name).get('reader', {})
        require((reader.get('kind'), reader.get('byteWidth')),
                (kind, byte_width), source, 0x32CE4B0)
        instructions = reader.get('verifiedInstructions')
        if not isinstance(instructions, list):
            raise ContextError(source, 0x32CE4B0,
                               f'{field_name} inline source-cursor instructions', instructions)
        actual_instructions = {
            (row.get('rva'), str(row.get('rawHex', '')).upper())
            for row in instructions if isinstance(row, dict)
        }
        require(actual_instructions, expected_instructions, source, 0x32CE4B0)

    shared_bool_reads = bool_helper_evidence.get('verifiedSharedHelperReads')
    if not isinstance(shared_bool_reads, list):
        raise ContextError(source, 0x2CA88C0,
                           'independent one-byte shared boolean-helper reader evidence',
                           shared_bool_reads)
    expected_shared_bool_reads = {
        (0x377410A, 0x2CA88C0, 1),
        (0x37741A1, 0x2CA88C0, 1),
    }
    actual_shared_bool_reads = {
        (row.get('callInstructionRva'), row.get('targetRva'),
         row.get('fastSerializedWidth'))
        for row in shared_bool_reads if isinstance(row, dict) and
        row.get('targetRva') == 0x2CA88C0
    }
    require(actual_shared_bool_reads, expected_shared_bool_reads,
            source, 0x2CA88C0)
    require((payload_helper_evidence.get('sharedHelperTargetRva'),
             payload_helper_evidence.get('providerSelection')),
            (0x2CA8700, 'unobserved'), source, 0x2CA8700)

    return {
        'timelineForceSyncMethodSpecIndex': 620038,
        'forceSyncTypeDefinitionIndex': 9198,
        'forceSyncRootMethodIndex': 107909,
        'forceSyncRootRva': 0x32CE4B0,
        'forceSyncRootCodeWindow': dict(matches[0]),
        'memberCountHeader': 4,
        'serializedMembers': [
            {'serializedOrderIndex': index, 'fieldName': field_name,
             'byteWidth': (1 if index == 0 else None if index == 1 else 4),
             'readerTargetRva': (0x2CA88C0 if index == 0 else
                                 0x2CA8700 if index == 1 else None)}
            for index, field_name, _, _ in expected_members],
        'sharedOneByteHelperEvidence': {
            'sourceRootRva': 0x3774060,
            'verifiedCallSites': [dict(row) for row in shared_bool_reads
                                  if row.get('targetRva') == 0x2CA88C0],
        },
        'sharedSignedLengthPayloadHelperTargetRva': 0x2CA8700,
        'runtimeProviderSelection': 'unobserved',
    }


def _skilldata_read_force_sync_candidate(raw, start, hard_limit, *,
                                         timeline_reader,
                                         payload_helper_evidence,
                                         bool_helper_evidence,
                                         gameassembly_image_base,
                                         source):
    """Consume the selected ForceSync reader's bounded field sequence only."""
    evidence = _skilldata_force_sync_reader_evidence(
        timeline_reader, payload_helper_evidence=payload_helper_evidence,
        bool_helper_evidence=bool_helper_evidence,
        gameassembly_image_base=gameassembly_image_base, source=source)
    if start < 0 or hard_limit < start or hard_limit > len(raw):
        raise ContextError(source, start,
                           'ForceSync candidate start and hard limit inside current raw bytes',
                           {'start': start, 'hardLimit': hard_limit,
                            'rawLength': len(raw)})
    ranges = []
    opaque_payload_ranges = []
    if hard_limit - start < 1:
        return {'cursor': start, 'ranges': ranges,
                'opaquePayloadByteRanges': opaque_payload_ranges,
                'complete': False, 'status': 'truncated-force-sync-member-header',
                'failure': {'category': 'truncated', 'offset': start,
                            'kind': 'ForceSyncAnimData.member-header',
                            'expectedBytes': 1, 'remainingBytes': 0},
                'recordEndCandidate': None, 'readerEvidence': evidence}
    header = raw[start]
    position = start + 1
    ranges.append({'start': start, 'end': position,
                   'kind': 'ForceSyncAnimData.member-header', 'value': header})
    if header != 4:
        return {'cursor': position, 'ranges': ranges,
                'opaquePayloadByteRanges': opaque_payload_ranges,
                'complete': False, 'status': 'malformed-force-sync-member-count',
                'failure': {'category': 'member-count', 'offset': start,
                            'expected': 4, 'actual': header},
                'recordEndCandidate': None, 'readerEvidence': evidence}
    if hard_limit - position < 1:
        return {'cursor': position, 'ranges': ranges,
                'opaquePayloadByteRanges': opaque_payload_ranges,
                'complete': False, 'status': 'truncated-force-sync-forceSync',
                'failure': {'category': 'truncated', 'offset': position,
                            'kind': 'ForceSyncAnimData.member0.forceSync.byte',
                            'expectedBytes': 1, 'remainingBytes': 0},
                'recordEndCandidate': None, 'readerEvidence': evidence}
    ranges.append({'start': position, 'end': position + 1,
                   'kind': 'ForceSyncAnimData.member0.forceSync.byte',
                   'value': raw[position],
                   'rawHex': raw[position:position + 1].hex().upper()})
    position += 1

    montage = _skilldata_read_byte_payload_candidate(
        raw, position, hard_limit,
        kind='ForceSyncAnimData.member1.montageName', source=source)
    ranges.extend(montage['ranges'])
    opaque_payload_ranges.extend(montage['opaquePayloadByteRanges'])
    position = montage['cursor']
    if not montage['complete']:
        return {'cursor': position, 'ranges': ranges,
                'opaquePayloadByteRanges': opaque_payload_ranges,
                'complete': False,
                'status': f'{montage["status"]}-montageName',
                'failure': montage['failure'], 'recordEndCandidate': None,
                'readerEvidence': evidence, 'montageNameLength': montage['length']}

    for member_index, field_name, kind in (
            (2, 'playbackSpeed', 'float32'),
            (3, 'targetFrame', 'int32')):
        if hard_limit - position < 4:
            return {'cursor': position, 'ranges': ranges,
                    'opaquePayloadByteRanges': opaque_payload_ranges,
                    'complete': False,
                    'status': f'truncated-force-sync-{field_name}',
                    'failure': {'category': 'truncated', 'offset': position,
                                'kind': f'ForceSyncAnimData.member{member_index}.{field_name}.{kind}',
                                'expectedBytes': 4,
                                'remainingBytes': hard_limit - position},
                    'recordEndCandidate': None, 'readerEvidence': evidence,
                    'montageNameLength': montage['length']}
        ranges.append({'start': position, 'end': position + 4,
                       'kind': f'ForceSyncAnimData.member{member_index}.{field_name}.{kind}',
                       'rawHex': raw[position:position + 4].hex().upper()})
        position += 4
    return {
        'cursor': position, 'ranges': ranges,
        'opaquePayloadByteRanges': opaque_payload_ranges,
        'complete': True,
        'status': 'candidate-force-sync-reader-field-sequence-exhausted',
        'failure': None,
        'recordEndCandidate': {
            'start': start, 'end': position, 'memberCount': 4,
            'sourceReadOrderKey': 'member4',
            'classification': 'candidate selected-reader field-sequence end; live provider/cache unobserved',
        },
        'readerEvidence': evidence,
        'montageNameLength': montage['length'],
    }


def _skilldata_read_following_timeline_action_data_prefix_candidate(
        raw, start, hard_limit, *, timeline_reader, sequence_reader,
        payload_helper_evidence, bool_helper_evidence,
        gameassembly_image_base, source):
    """Replay the next timeline element through its first nested action tag."""
    timeline_windows = timeline_reader.get('codeWindows')
    if not isinstance(timeline_windows, list) or not any(
            (row.get('startRva'), row.get('endRva'), row.get('sha256')) ==
            (0x32CCF70, 0x32CD277,
             'CB497F6362D9DA9396D6533F6CC037536FC9499D67848F1E8BBBAC8AA2F03688')
            for row in timeline_windows if isinstance(row, dict)):
        raise ContextError(source, 0x32CCF70,
                           'hash-pinned current TimelineActionData root reader', timeline_windows)
    timeline_members = timeline_reader.get('serializedMembers')
    if not isinstance(timeline_members, list) or len(timeline_members) != 4:
        raise ContextError(source, start, 'four current TimelineActionData member readers',
                           timeline_members)
    end_frame = timeline_members[0].get('reader', {})
    require((end_frame.get('callInstructionRva'), end_frame.get('callInstructionHex'),
             end_frame.get('targetRva'), end_frame.get('role')),
            (0x32CD05E, 'E84DB69DFF', 0x2CA86B0, 'read endFrame int32'),
            source, 0x32CD05E)
    header_windows = timeline_reader.get('verifiedInstructionWindows')
    if not isinstance(header_windows, list):
        raise ContextError(source, 0x32CD04E,
                           'TimelineActionData member-count header instruction evidence',
                           header_windows)
    require(any((row.get('rva'), str(row.get('rawHex', '')).upper()) ==
                (0x32CD04E, '4080FE04')
                for row in header_windows if isinstance(row, dict)), True,
            source, 0x32CD04E)

    shared_reads = bool_helper_evidence.get('verifiedSharedHelperReads')
    if not isinstance(shared_reads, list):
        raise ContextError(source, 0x2CA86B0,
                           'independent four-byte reader-helper evidence', shared_reads)
    expected_end_frame_witness = (0x3774135, 0x2CA86B0, 4)
    actual_shared_reads = {
        (row.get('callInstructionRva'), row.get('targetRva'),
         row.get('fastSerializedWidth'))
        for row in shared_reads if isinstance(row, dict)
    }
    require(expected_end_frame_witness in actual_shared_reads, True,
            source, 0x2CA86B0)
    _skilldata_sequence_tail_windows(sequence_reader, source=source)

    if start < 0 or hard_limit < start or hard_limit > len(raw):
        raise ContextError(source, start,
                           'following TimelineActionData start and hard limit inside raw bytes',
                           {'start': start, 'hardLimit': hard_limit,
                            'rawLength': len(raw)})
    ranges = []
    position = start
    if hard_limit - position < 1:
        return {'start': start, 'cursor': position, 'ranges': ranges,
                'status': 'truncated-following-timeline-action-member-header',
                'failure': {'category': 'truncated', 'offset': position,
                            'kind': 'TimelineActionData.member-header',
                            'expectedBytes': 1, 'remainingBytes': 0},
                'firstActionUnionTagPeekOnly': None,
                'candidateRecordEnd': None}
    header = raw[position]
    ranges.append({'start': position, 'end': position + 1,
                   'kind': 'TimelineActionData.member-header', 'value': header})
    position += 1
    if header != 4:
        return {'start': start, 'cursor': position, 'ranges': ranges,
                'status': 'malformed-following-timeline-action-member-count',
                'failure': {'category': 'member-count', 'offset': start,
                            'expected': 4, 'actual': header},
                'firstActionUnionTagPeekOnly': None,
                'candidateRecordEnd': None}
    if hard_limit - position < 4:
        return {'start': start, 'cursor': position, 'ranges': ranges,
                'status': 'truncated-following-timeline-action-end-frame',
                'failure': {'category': 'truncated', 'offset': position,
                            'kind': 'TimelineActionData.member0.endFrame.i32',
                            'expectedBytes': 4, 'remainingBytes': hard_limit - position},
                'firstActionUnionTagPeekOnly': None,
                'candidateRecordEnd': None}
    ranges.append({'start': position, 'end': position + 4,
                   'kind': 'TimelineActionData.member0.endFrame.i32',
                   'rawHex': raw[position:position + 4].hex().upper()})
    position += 4

    sequence_start = position
    sequence = _skilldata_read_sequence_data_candidate(
        raw, position, hard_limit, source=source)
    sequence['ranges'] = [
        {**row, 'kind': f'TimelineActionData.member1.{row["kind"]}'}
        for row in sequence['ranges']]
    ranges.extend(sequence['ranges'])
    position = sequence['cursor']
    tag_peek = sequence.get('firstActionUnionTagPeekOnly')
    if isinstance(tag_peek, dict):
        first_byte = tag_peek['firstByte']
        tag_width = 3 if first_byte == 0xFA else 1
        remaining = hard_limit - tag_peek['offset']
        if tag_width > remaining:
            tag_peek = {
                **tag_peek, 'tag': None, 'tagWidth': tag_width,
                'encodingHex': raw[tag_peek['offset']:hard_limit].hex().upper(),
            }
            return {
                'start': start, 'cursor': position, 'ranges': ranges,
                'status': 'truncated-following-timeline-action-tag',
                'failure': {'category': 'truncated-action-tag',
                            'offset': tag_peek['offset'],
                            'expected': {'bytes': tag_width},
                            'actual': {'remaining': remaining}},
                'timelineSequenceCount': sequence.get('count'),
                'timelineSequenceStart': sequence_start,
                'firstActionUnionTagPeekOnly': tag_peek,
                'candidateRecordEnd': None,
            }
        tag_peek = {
            **tag_peek,
            'tag': (struct.unpack_from('<H', raw, tag_peek['offset'] + 1)[0]
                    if tag_width == 3 else first_byte),
            'tagWidth': tag_width,
            'encodingHex': raw[tag_peek['offset']:tag_peek['offset'] + tag_width].hex().upper(),
        }

    if not sequence['complete']:
        status = ('stopped-before-following-timeline-sequence-action'
                  if sequence.get('status') == 'stopped-before-sequence-action-elements'
                  else sequence.get('status', 'ambiguous-following-timeline-sequence'))
        return {
            'start': start, 'cursor': position, 'ranges': ranges,
            'status': status, 'failure': sequence.get('failure'),
            'timelineSequenceCount': sequence.get('count'),
            'timelineSequenceStart': sequence_start,
            'timelineSequenceStatus': sequence.get('status'),
            'firstActionUnionTagPeekOnly': tag_peek,
            'candidateRecordEnd': None,
            'nextSourceReadType': 'TimelineActionData.member1.SequenceActionData action element',
            'nextSourceReadOffset': position,
            'nextSourceReadConsumed': False,
        }

    start_frame = timeline_members[2].get('reader', {})
    expected_start_frame = {
        (53268774, '448B30'), (53268802, '4883435004'),
        (53268807, '83434004'), (53268811, '83434404'),
    }
    actual_start_frame = {
        (row.get('rva'), str(row.get('rawHex', '')).upper())
        for row in start_frame.get('verifiedInstructions', [])
        if isinstance(row, dict)
    }
    require(actual_start_frame, expected_start_frame, source, position)
    if hard_limit - position < 4:
        return {'start': start, 'cursor': position, 'ranges': ranges,
                'status': 'truncated-following-timeline-action-start-frame',
                'failure': {'category': 'truncated', 'offset': position,
                            'kind': 'TimelineActionData.member2.startFrame.i32',
                            'expectedBytes': 4, 'remainingBytes': hard_limit - position},
                'timelineSequenceCount': sequence.get('count'),
                'timelineSequenceStart': sequence_start,
                'firstActionUnionTagPeekOnly': None,
                'candidateRecordEnd': None}
    ranges.append({'start': position, 'end': position + 4,
                   'kind': 'TimelineActionData.member2.startFrame.i32',
                   'rawHex': raw[position:position + 4].hex().upper()})
    position += 4
    force_sync = _skilldata_read_force_sync_candidate(
        raw, position, hard_limit, timeline_reader=timeline_reader,
        payload_helper_evidence=payload_helper_evidence,
        bool_helper_evidence=bool_helper_evidence,
        gameassembly_image_base=gameassembly_image_base, source=source)
    ranges.extend(force_sync['ranges'])
    position = force_sync['cursor']
    candidate_end = None
    if force_sync['complete']:
        candidate_end = {
            'start': start, 'end': position, 'memberCount': 4,
            'sourceReadOrderKey': 'member4',
            'classification': 'candidate selected TimelineActionData field-sequence end; live provider/cache unobserved',
        }
    return {
        'start': start, 'cursor': position, 'ranges': ranges,
        'status': (('candidate-following-timeline-action-field-sequence-exhausted'
                    if force_sync['complete'] else force_sync['status'])),
        'failure': force_sync.get('failure'),
        'timelineSequenceCount': sequence.get('count'),
        'timelineSequenceStart': sequence_start,
        'timelineSequenceStatus': sequence.get('status'),
        'firstActionUnionTagPeekOnly': tag_peek,
        'forceSyncAnimDataRecordEndCandidate': force_sync.get('recordEndCandidate'),
        'candidateRecordEnd': candidate_end,
        'forceSyncAnimDataReaderEvidence': force_sync['readerEvidence'],
        'opaquePayloadByteRanges': force_sync['opaquePayloadByteRanges'],
        'nextSourceReadType': ('next TimelineActionData list element'
                               if force_sync['complete'] else
                               force_sync.get('failure', {}).get('kind')),
        'nextSourceReadOffset': position,
        'nextSourceReadConsumed': False if force_sync['complete'] else None,
    }


def _skilldata_continue_following_play_animation_candidate(
        raw, following_timeline, hard_limit, *, timeline_actions_list_count,
        timeline_reader, sequence_reader, action_group_members, buff_routes,
        action_readers, payload_helper_evidence, bool_helper_evidence,
        gameassembly_image_base, source):
    """Continue a second TimelineActionData only for its exact 0x115 child path."""
    peek = following_timeline.get('firstActionUnionTagPeekOnly')
    if not isinstance(peek, dict) or peek.get('tag') != 0x115 or peek.get('tagWidth') != 3:
        raise ContextError(source, following_timeline.get('cursor', 0),
                           'non-consuming extended 0x115 child tag peek', peek)
    if following_timeline.get('timelineSequenceCount') != 1:
        raise ContextError(source, peek.get('offset', 0),
                           'one child in the second TimelineActionData SequenceActionData',
                           following_timeline.get('timelineSequenceCount'))
    reader = action_readers.get(0x115)
    if not isinstance(reader, dict):
        raise ContextError(source, peek['offset'],
                           'current 0x115 PlayAnimation selected reader', reader)
    union_evidence = skilldata_action_union_static_reader_evidence(
        0x115, reader, buff_routes,
        gameassembly_image_base=gameassembly_image_base, source=source)
    root_member_count = union_evidence.get('rootMemberCount')
    root_read_order = union_evidence.get('rootAnonymousReadOrder')
    require((root_member_count, union_evidence.get('rootReadOrderKey'),
             root_read_order[:4] if isinstance(root_read_order, list) else None),
            (16, 'member16', ['byte', 'scalar32', 'scalar32', 'scalar32']),
            source, peek['offset'])
    start = peek['offset']
    encoded_tag = bytes.fromhex(str(peek.get('encodingHex', '')))
    require((raw[start:start + 3], encoded_tag),
            (b'\xFA\x15\x01', b'\xFA\x15\x01'), source, start)
    header_offset = start + 3
    if header_offset >= hard_limit or raw[header_offset] != root_member_count:
        return {
            'cursor': start, 'ranges': [], 'opaquePayloadByteRanges': [],
            'status': 'stopped-before-following-play-animation-member-header',
            'failure': {'category': ('truncated' if header_offset >= hard_limit
                                     else 'member-count'),
                        'offset': header_offset, 'expected': root_member_count,
                        'actual': raw[header_offset] if header_offset < hard_limit else None},
            'candidatePlayAnimationRecordEnd': None,
            'candidateTimelineActionDataRecordEnd': None,
            'candidateActionGroupDataRecordEnd': None,
            'candidateTimelineContinuation': None,
            'readerEvidence': union_evidence,
        }
    position = header_offset + 1
    ranges = [
        {'start': start, 'end': header_offset,
         'kind': 'AbilityActionData.union-tag'},
        {'start': header_offset, 'end': position,
         'kind': 'PlayAnimationAction.memberCount'},
    ]
    fixed_members = []
    for member_index, member_type in enumerate(root_read_order[:4]):
        width = _skilldata_action_fixed_member_width(member_type)
        if width is None:
            raise ContextError(source, position,
                               'four current fixed 0x115 prefix member widths', member_type)
        if hard_limit - position < width:
            return {
                'cursor': position, 'ranges': ranges,
                'opaquePayloadByteRanges': [],
                'status': 'truncated-following-play-animation-fixed-prefix',
                'failure': {'category': 'truncated', 'offset': position,
                            'memberIndex': member_index, 'kind': member_type,
                            'expectedBytes': width,
                            'remainingBytes': hard_limit - position},
                'candidatePlayAnimationRecordEnd': None,
                'candidateTimelineActionDataRecordEnd': None,
                'candidateActionGroupDataRecordEnd': None,
                'candidateTimelineContinuation': None,
                'readerEvidence': union_evidence,
            }
        ranges.append({'start': position, 'end': position + width,
                       'kind': f'PlayAnimationAction.member{member_index}.{member_type}'})
        fixed_members.append(member_type)
        position += width

    require((payload_helper_evidence.get('actionTag'),
             payload_helper_evidence.get('sharedHelperTargetRva'),
             payload_helper_evidence.get('providerSelection')),
            (0x115, 0x2CA8700, 'unobserved'), source, start)
    payload_helper = payload_helper_evidence
    play_animation = _skilldata_continue_play_animation_candidate(
        raw, position, hard_limit, action_start=start,
        root_read_order=root_read_order, sequence_reader=sequence_reader,
        payload_helper_evidence=payload_helper, source=source)
    ranges.extend(play_animation['ranges'])
    position = play_animation['cursor']
    if not play_animation['complete']:
        return {
            'cursor': position, 'ranges': ranges,
            'opaquePayloadByteRanges': play_animation['opaquePayloadByteRanges'],
            'status': play_animation['status'], 'failure': play_animation['failure'],
            'candidatePlayAnimationRecordEnd': play_animation['recordEndCandidate'],
            'candidateTimelineActionDataRecordEnd': None,
            'candidateActionGroupDataRecordEnd': None,
            'candidateTimelineContinuation': None,
            'candidatePlayAnimationNestedSequence': play_animation.get('nestedSequence'),
            'readerEvidence': union_evidence,
            'bytePayloadHelperEvidence': payload_helper,
        }

    parent = _skilldata_continue_timeline_parent_candidate(
        raw, position, hard_limit, sequence_action_count=1,
        timeline_actions_list_count=timeline_actions_list_count,
        timeline_action_start=following_timeline['start'],
        timeline_reader=timeline_reader,
        sequence_tail_windows=play_animation['independentlyVerifiedSequenceTailWindows'],
        action_group_members=action_group_members,
        payload_helper_evidence=payload_helper,
        bool_helper_evidence=bool_helper_evidence,
        gameassembly_image_base=gameassembly_image_base,
        source=source)
    ranges.extend(parent['ranges'])
    position = parent['cursor']
    opaque_payload_ranges = [*play_animation['opaquePayloadByteRanges'],
                             *parent.get('opaquePayloadByteRanges', [])]
    return {
        'cursor': position, 'ranges': ranges,
        'opaquePayloadByteRanges': opaque_payload_ranges,
        'status': parent['status'], 'failure': parent.get('failure'),
        'candidatePlayAnimationRecordEnd': play_animation['recordEndCandidate'],
        'candidateTimelineActionDataRecordEnd': parent.get(
            'candidateTimelineActionDataRecordEnd'),
        'candidateActionGroupDataRecordEnd': parent.get(
            'candidateActionGroupDataRecordEnd'),
        'candidateTimelineContinuation': parent,
        'candidatePlayAnimationNestedSequence': play_animation.get('nestedSequence'),
        'readerEvidence': union_evidence,
        'bytePayloadHelperEvidence': payload_helper,
    }


def _skilldata_continue_timeline_parent_candidate(raw, start, hard_limit, *,
                                                   sequence_action_count,
                                                   timeline_actions_list_count,
                                                   timeline_action_start,
                                                   timeline_reader,
                                                   sequence_tail_windows,
                                                   action_group_members,
                                                   payload_helper_evidence,
                                                   bool_helper_evidence,
                                                   gameassembly_image_base,
                                                   source):
    """Continue one completed 0x115 child through its proven enclosing prefixes."""
    ranges = []
    position = start
    if sequence_action_count != 1:
        return {
            'cursor': position, 'ranges': ranges,
            'status': 'stopped-before-additional-sequence-action',
            'failure': None,
            'sequenceActionCount': sequence_action_count,
            'nextSourceReadType': 'next SequenceActionData action or trailing bytes',
            'nextSourceReadOffset': position,
        }
    for index in range(2):
        if position >= hard_limit:
            return {
                'cursor': position, 'ranges': ranges,
                'status': 'truncated-timeline-sequence-action-data-tail',
                'failure': {'category': 'truncated', 'offset': position,
                            'kind': f'TimelineActionData.member1.SequenceActionData.trailing-byte[{index}]',
                            'expectedBytes': 1, 'remainingBytes': 0},
                'sequenceActionCount': sequence_action_count,
                'nextSourceReadType': f'TimelineActionData.member1.SequenceActionData.trailing-byte[{index}]',
                'nextSourceReadOffset': position,
            }
        ranges.append({'start': position, 'end': position + 1,
                       'kind': f'TimelineActionData.member1.SequenceActionData.trailing-byte[{index}]',
                       'value': raw[position]})
        position += 1

    timeline_members = timeline_reader.get('serializedMembers')
    if not isinstance(timeline_members, list) or len(timeline_members) != 4:
        raise ContextError(source, position, 'four current TimelineActionData members',
                           timeline_members)
    start_frame = timeline_members[2].get('reader', {})
    expected_start_frame_instructions = {
        (53268774, '448B30'),
        (53268802, '4883435004'),
        (53268807, '83434004'),
        (53268811, '83434404'),
    }
    instructions = start_frame.get('verifiedInstructions')
    if not isinstance(instructions, list):
        raise ContextError(source, position,
                           'verified TimelineActionData startFrame source cursor instructions',
                           instructions)
    actual = {(row.get('rva'), row.get('rawHex')) for row in instructions
              if isinstance(row, dict)}
    require(actual, expected_start_frame_instructions, source, position)
    require((timeline_members[2].get('fieldName'), start_frame.get('kind'),
             start_frame.get('byteWidth')),
            ('_startFrame', 'inline-int32', 4), source, position)
    if hard_limit - position < 4:
        return {
            'cursor': position, 'ranges': ranges,
            'status': 'truncated-timeline-action-start-frame',
            'failure': {'category': 'truncated', 'offset': position,
                        'kind': 'TimelineActionData.member2.startFrame.i32',
                        'expectedBytes': 4, 'remainingBytes': hard_limit - position},
            'sequenceActionCount': sequence_action_count,
            'nextSourceReadType': 'TimelineActionData.member2.startFrame.i32',
            'nextSourceReadOffset': position,
        }
    ranges.append({'start': position, 'end': position + 4,
                   'kind': 'TimelineActionData.member2.startFrame.i32',
                   'rawHex': raw[position:position + 4].hex().upper()})
    position += 4
    force_sync_start = position
    force_sync = _skilldata_read_force_sync_candidate(
        raw, force_sync_start, hard_limit, timeline_reader=timeline_reader,
        payload_helper_evidence=payload_helper_evidence,
        bool_helper_evidence=bool_helper_evidence,
        gameassembly_image_base=gameassembly_image_base, source=source)
    ranges.extend(force_sync['ranges'])
    position = force_sync['cursor']
    common = {
        'sequenceActionCount': sequence_action_count,
        'timelineActionsListCount': timeline_actions_list_count,
        'sequenceTailEvidence': sequence_tail_windows,
        'timelineStartFrameEvidence': [
            {'rva': rva, 'rawHex': raw_hex}
            for rva, raw_hex in sorted(expected_start_frame_instructions)],
        'forceSyncAnimDataStart': force_sync_start,
        'forceSyncAnimDataContinuation': {
            'status': force_sync['status'],
            'cursor': force_sync['cursor'],
            'failure': force_sync['failure'],
            'montageNameLength': force_sync.get('montageNameLength'),
            'recordEndCandidate': force_sync.get('recordEndCandidate'),
            'readerEvidence': force_sync['readerEvidence'],
        },
        'forceSyncAnimDataRecordEndCandidate': force_sync.get('recordEndCandidate'),
        'opaquePayloadByteRanges': force_sync['opaquePayloadByteRanges'],
    }
    if not force_sync['complete']:
        return {
            'cursor': position, 'ranges': ranges,
            'status': force_sync['status'], 'failure': force_sync['failure'],
            'nextSourceReadType': (force_sync['failure'].get('kind')
                                   if isinstance(force_sync.get('failure'), dict)
                                   else 'ForceSyncAnimData remaining member reads'),
            'nextSourceReadOffset': position,
            'nextSourceReadConsumed': False,
            'classification': 'candidate TimelineActionData prefix; ForceSync reader incomplete',
            **common,
        }

    if type(timeline_action_start) is not int or not 0 <= timeline_action_start < force_sync_start:
        raise ContextError(source, force_sync_start,
                           'TimelineActionData start preceding its ForceSync child',
                           timeline_action_start)
    timeline_record_end = {
        'start': timeline_action_start, 'end': position,
        'memberCount': 4, 'sourceReadOrderKey': 'member4',
        'classification': 'candidate selected TimelineActionData field-sequence end; live provider/cache unobserved',
    }
    common['candidateTimelineActionDataRecordEnd'] = timeline_record_end

    if type(timeline_actions_list_count) is not int or timeline_actions_list_count < 1:
        return {
            'cursor': position, 'ranges': ranges,
            'status': 'unsupported-timeline-actions-list-count',
            'failure': {'category': 'unsupported',
                        'offset': timeline_action_start,
                        'actual': timeline_actions_list_count,
                        'supportedLowerBound': 1},
            'nextSourceReadType': None,
            'nextSourceReadOffset': position,
            'nextSourceReadConsumed': None,
            'classification': 'candidate TimelineActionData end; ActionGroupData list extent unsupported',
            **common,
        }

    if timeline_actions_list_count == 1:
        if not isinstance(action_group_members, list) or len(action_group_members) != 2:
            raise ContextError(source, 1, 'two current ActionGroupData serialized members',
                               action_group_members)
        require([row.get('serializedOrderIndex') for row in action_group_members],
                [0, 1], source, 1)
        require([row.get('fieldName') for row in action_group_members],
                ['passiveEventActions', 'timelineActions'], source, 1)
        action_group_end = {
            'start': 1, 'end': position, 'memberCount': 2,
            'sourceReadOrderKey': 'member2',
            'classification': 'candidate ActionGroupData field-sequence end; SkillData remains open',
        }
        return {
            'cursor': position, 'ranges': ranges,
            'status': 'candidate-actiongroup-reader-field-sequence-exhausted',
            'failure': None,
            'candidateActionGroupDataRecordEnd': action_group_end,
            'nextSourceReadType': 'next SkillData member after ActionGroupData',
            'nextSourceReadOffset': position,
            'nextSourceReadConsumed': False,
            'classification': 'candidate ActionGroupData field-sequence end; whole SkillData remains open',
            **common,
        }

    return {
        'cursor': position, 'ranges': ranges,
        'status': 'stopped-before-additional-timeline-action-data',
        'failure': None,
        'nextSourceReadType': 'next TimelineActionData list element',
        'nextSourceReadOffset': position,
        'nextSourceReadConsumed': False,
        'classification': 'candidate first TimelineActionData end; remaining list and parents remain open',
        **common,
    }


def skilldata_timeline_branch_static_alignment(
        witness, raw, skilldata_reader_order, sequence_reader, buff_routes,
        buff_action_readers, c9_prefix_evidence, *,
        gameassembly_image_base=0x180000000,
        byte_payload_helper_evidence=None, source):
    """Add typed native alignment and only bounded first-child prefixes to a candidate cursor."""
    if not isinstance(witness, dict) or not isinstance(raw, bytes):
        raise ContextError(source, 0, 'current timeline candidate witness and raw bytes',
                           [type(witness).__name__, type(raw).__name__])
    if not all(isinstance(value, dict) for value in
               (skilldata_reader_order, sequence_reader, buff_routes)):
        raise ContextError(source, 0, 'SkillData, Sequence and action-route native evidence objects',
                           [type(skilldata_reader_order).__name__, type(sequence_reader).__name__,
                            type(buff_routes).__name__])
    if not isinstance(buff_action_readers, dict) or any(
            type(tag) is not int or not isinstance(reader, dict)
            for tag, reader in buff_action_readers.items()):
        raise ContextError(source, 0, 'current tag-to-native action reader map',
                           type(buff_action_readers).__name__)
    input_set = witness.get('inputSetSha256')
    require(skilldata_reader_order.get('inputSetSha256'), input_set, source, 0)
    require(witness.get('hardLimit'), len(raw), source, 0)
    require(witness.get('logicalSha256'), hashlib.sha256(raw).hexdigest().upper(), source, 0)
    require(witness.get('authoritativeParserCursor'), 10, source, 0)
    require(witness.get('candidateStart'), 10, source, 0)
    if not isinstance(witness.get('candidateByteRanges'), list):
        raise ContextError(source, witness.get('candidateCursor', 10),
                           'candidate byte-range manifest', witness.get('candidateByteRanges'))

    require(skilldata_reader_order.get('firstSkillDataField', {}).get('fieldName'),
            'actionGroupData', source, 0)
    action_group_members = skilldata_reader_order.get('actionGroupDataMembers')
    if not isinstance(action_group_members, list) or len(action_group_members) != 2:
        raise ContextError(source, 1, 'two native ActionGroupData member reads',
                           action_group_members)
    require([row.get('fieldName') for row in action_group_members],
            ['passiveEventActions', 'timelineActions'], source, 1)
    require([row.get('serializedOrderIndex') for row in action_group_members],
            [0, 1], source, 1)
    require([row.get('readerMethodSpec', {}).get('index')
             for row in action_group_members], [610662, 610915], source, 1)
    first_list_type = action_group_members[0].get('readerMethodSpec', {}).get('genericType', {})
    timeline_list_type = action_group_members[1].get('readerMethodSpec', {}).get('genericType', {})
    require((first_list_type.get('typeName'), first_list_type.get('elementTypeName')),
            ('System.Collections.Generic.List`1',
             'Beyond.Gameplay.Core.AbilityActionMap'), source, 2)
    require((timeline_list_type.get('typeName'), timeline_list_type.get('elementTypeName'),
             timeline_list_type.get('elementTypeDefinitionIndex')),
            ('System.Collections.Generic.List`1',
             'Beyond.Gameplay.Core.TimelineAction+TimelineActionData', 9199), source, 6)
    action_group_windows = skilldata_reader_order.get('codeWindows')
    if not isinstance(action_group_windows, list) or not any(
            (row.get('rva'), row.get('byteLength'), row.get('sha256')) ==
            (58581179, 2314,
             'FEA359985EBF5DF75CC58D871469481F0F692B1768D84724FF5941D47CAD8132')
            for row in action_group_windows):
        raise ContextError(source, 1, 'hash-pinned SkillData/ActionGroupData root reader window',
                           action_group_windows)
    instructions = skilldata_reader_order.get('verifiedInstructionWindows')
    if not isinstance(instructions, list):
        raise ContextError(source, 1, 'current SkillData and ActionGroupData header/store instructions',
                           instructions)
    expected_instructions = {
        (58581199, '4080FD30'),
        (65273925, '4080FD02'),
        (65273975, '48894118'),
        (65274020, '48894110'),
    }
    actual_instructions = {(row.get('rva'), row.get('rawHex')) for row in instructions}
    require(expected_instructions <= actual_instructions, True, source, 1)

    timeline = skilldata_reader_order.get('timelineActionDataReader')
    if not isinstance(timeline, dict):
        raise ContextError(source, 10, 'current TimelineActionData native reader evidence', timeline)
    require((timeline.get('elementTypeDefinitionIndex'), timeline.get('elementTypeName')),
            (9199, 'Beyond.Gameplay.Core.TimelineAction+TimelineActionData'), source, 10)
    require(timeline.get('listReaderMethodSpec', {}).get('index'), 610915, source, 10)
    timeline_methods = timeline.get('methods')
    if not isinstance(timeline_methods, list):
        raise ContextError(source, 10, 'TimelineActionData and ForceSync reader module/token rows',
                           timeline_methods)
    require(sorted(row.get('methodIndex') for row in timeline_methods),
            [104653, 104654, 107909, 107910], source, 10)
    timeline_windows = timeline.get('codeWindows')
    if not isinstance(timeline_windows, list):
        raise ContextError(source, 10, 'TimelineActionData hash-pinned reader windows',
                           timeline_windows)
    require(any((row.get('startRva'), row.get('endRva'), row.get('sha256')) ==
                (0x32CCF70, 0x32CD277,
                 'CB497F6362D9DA9396D6533F6CC037536FC9499D67848F1E8BBBAC8AA2F03688')
                for row in timeline_windows), True, source, 10)
    timeline_members = timeline.get('serializedMembers')
    if not isinstance(timeline_members, list) or len(timeline_members) != 4:
        raise ContextError(source, 10, 'four selected TimelineActionData member reads',
                           timeline_members)
    require([row.get('fieldName') for row in timeline_members],
            ['_endFrame', '_sequenceActionData', '_startFrame', 'forceSyncAnimData'],
            source, 10)
    end_frame_reader = timeline_members[0].get('reader', {})
    require((end_frame_reader.get('targetRva'), end_frame_reader.get('role')),
            (0x2CA86B0, 'read endFrame int32'), source, 11)
    sequence_method = timeline_members[1].get('readerMethodSpec', {})
    require((sequence_method.get('index'),
             sequence_method.get('genericType', {}).get('typeDefinitionIndex')),
            (619962, 9202), source, 15)
    require((timeline_members[2].get('reader', {}).get('kind'),
             timeline_members[2].get('reader', {}).get('byteWidth')),
            ('inline-int32', 4), source, 0)
    sequence_reference = timeline.get('sequenceActionDataReaderReference', {})
    sequence_window = sequence_reader.get('rootCodeWindow', {})
    require((sequence_reference.get('methodIndex'), sequence_reference.get('rootRva'),
             sequence_reference.get('rootCodeWindowSha256')),
            (104346, 0x39C6AA0,
             '6444AF67AF86E7809AF5A50AE6DEE922B699DCB1CA686DC81F4C3584AB817B90'),
            source, 15)
    require((sequence_window.get('startRva'), sequence_window.get('endRva'),
             sequence_window.get('sha256')),
            (0x39C6AA0, 0x39C6FA7,
             '6444AF67AF86E7809AF5A50AE6DEE922B699DCB1CA686DC81F4C3584AB817B90'),
            source, 15)
    sequence_methods = sequence_reader.get('methods')
    if not isinstance(sequence_methods, list):
        raise ContextError(source, 15, 'selected SequenceActionData reader module/token rows',
                           sequence_methods)
    sequence_root_methods = [row for row in sequence_methods
                             if row.get('methodIndex') == 104346 and
                             row.get('declaringType') ==
                             'Beyond.MemoryPack.Beyond_Gameplay_Core_SequenceActionDataForMemoryPack' and
                             row.get('name') == 'Deserialize' and
                             row.get('image') == 'MemoryPack.Beyond.dll']
    if len(sequence_root_methods) != 1:
        raise ContextError(source, 15, 'one exact SequenceActionData root Deserialize method',
                           len(sequence_root_methods))
    require(sequence_root_methods[0].get('pointerVa'),
            gameassembly_image_base + 0x39C6AA0, source, 15)
    sequence_windows = sequence_reader.get('windows')
    if not isinstance(sequence_windows, list):
        raise ContextError(source, 15, 'selected SequenceActionData header/count instruction',
                           sequence_windows)
    sequence_header = [row for row in sequence_windows
                       if row.get('rva') == 0x39C6B82]
    if len(sequence_header) != 1:
        raise ContextError(source, 15, 'one selected SequenceActionData member-three header check',
                           len(sequence_header))
    require(sequence_header[0].get('rawHex'), '4080FE030F85DD030000', source, 0x39C6B82)

    typed_prefix_ownership = [
        {'start': 0, 'end': 1, 'kind': 'SkillData.memberCount', 'value': 48},
        {'start': 1, 'end': 2, 'kind': 'ActionGroupData.memberCount', 'value': 2},
        {'start': 2, 'end': 6, 'kind': 'ActionGroupData.passiveEventActions.count-i32',
         'value': 0},
        {'start': 6, 'end': 10, 'kind': 'ActionGroupData.timelineActions.count-i32',
         'value': witness.get('timelineActionsListCount')},
    ]
    candidate_ranges = [dict(row) for row in witness['candidateByteRanges']]
    candidate_cursor = witness.get('candidateCursor')
    status = witness.get('status')
    failure = witness.get('failure')
    union_peek = witness.get('firstActionUnionTagPeekOnly')
    union_evidence = None
    prefix_stop = None
    candidate_play_animation_record_end = None
    candidate_timeline_continuation = None
    candidate_timeline_action_data_record_end = None
    candidate_action_group_data_record_end = None
    candidate_following_timeline_action_prefix = None
    candidate_following_timeline_action_data_record_end = None
    candidate_following_play_animation_record_end = None
    candidate_following_timeline_continuation = None
    candidate_play_animation_nested_sequence = None
    candidate_opaque_payload_ranges = []
    candidate_byte_payload_helper_evidence = None
    route_rows = buff_routes.get('rows')
    if not isinstance(route_rows, list):
        raise ContextError(source, 20, 'current AbilityActionData route rows', route_rows)

    if (failure is None and isinstance(union_peek, dict) and
            type(union_peek.get('tag')) is int):
        tag = union_peek['tag']
        tag_routes = [row for row in route_rows if row.get('tag') == tag]
        if tag == 0xFF and union_peek.get('tagWidth') == 1:
            start = union_peek['offset']
            if start < len(raw):
                candidate_ranges.append({'start': start, 'end': start + 1,
                                         'kind': 'candidate-null-action-union'})
                candidate_cursor = start + 1
                status = 'stopped-after-null-action-union'
                prefix_stop = {
                    'tag': tag, 'start': start, 'end': candidate_cursor,
                    'classification': 'candidate-null-union-only',
                    'parentCompleted': False,
                }
        elif tag != 0xC9 and (tag == 0x115 or tag in buff_action_readers):
            reader = buff_action_readers.get(tag)
            if reader is None:
                status = 'stopped-before-action-without-current-reader'
            else:
                union_evidence = skilldata_action_union_static_reader_evidence(
                    tag, reader, buff_routes,
                    gameassembly_image_base=gameassembly_image_base, source=source)
                require(len(tag_routes), 1, source, union_peek['offset'])
                root_member_count = union_evidence.get('rootMemberCount')
                root_read_order_key = union_evidence.get('rootReadOrderKey')
                root_read_order = union_evidence.get('rootAnonymousReadOrder')
                if not isinstance(root_read_order, list):
                    raise ContextError(source, union_peek['offset'],
                                       'current selected action member read order',
                                       root_read_order)
                common_prefix = ['byte', 'scalar32', 'scalar32', 'scalar32']
                if tag == 0x115:
                    require((root_member_count, root_read_order_key,
                             root_read_order[:4]),
                            (16, 'member16', common_prefix),
                            source, union_peek['offset'])
                    require(root_read_order[4], 'byte-payload',
                            source, union_peek['offset'])
                    nested_contexts = reader.get('nestedContexts')
                    if not isinstance(nested_contexts, list):
                        raise ContextError(source, union_peek['offset'],
                                           'PlayAnimation SequenceActionData static type context',
                                           nested_contexts)
                    nested_sequence_contexts = [row for row in nested_contexts
                                                if row.get('methodSpecIndex') == 619962 and
                                                row.get('typeDefinition') == 9202 and
                                                row.get('typeName') ==
                                                'Beyond.Gameplay.Core.SequenceActionData']
                    require(len(nested_sequence_contexts), 1, source,
                            union_peek['offset'])
                if root_read_order[:4] != common_prefix:
                    status = 'stopped-before-action-without-bounded-prefix-contract'
                else:
                    start = union_peek['offset']
                    width = union_peek.get('tagWidth')
                    expected_width = 3 if union_peek.get('firstByte') == 0xFA else 1
                    try:
                        encoded_tag = bytes.fromhex(union_peek.get('encodingHex', ''))
                    except ValueError as error:
                        raise ContextError(source, start,
                                           'hex-encoded current action union tag',
                                           union_peek) from error
                    if (type(width) is not int or width != expected_width or
                            len(encoded_tag) != width or raw[start:start + width] != encoded_tag):
                        raise ContextError(source, start,
                                           'complete current AbilityActionData union tag encoding',
                                           union_peek)
                    header_offset = start + width
                    header_good = (header_offset < len(raw) and
                                   raw[header_offset] == root_member_count)
                    if not header_good:
                        status = ('stopped-before-play-animation-member-header'
                                  if tag == 0x115 else
                                  'stopped-before-action-member-header')
                        failure = {
                            'category': ('truncated' if header_offset >= len(raw)
                                         else 'member-count'),
                            'offset': header_offset,
                            'expected': root_member_count,
                            'actual': raw[header_offset] if header_offset < len(raw) else None,
                        }
                    else:
                        position = header_offset + 1
                        prefix_rows = [
                            {'start': start, 'end': header_offset,
                             'kind': 'AbilityActionData.union-tag'},
                            {'start': header_offset, 'end': position,
                             'kind': ('PlayAnimationAction.memberCount' if tag == 0x115
                                      else 'AbilityActionData.root-memberCount')},
                        ]
                        next_field = None
                        next_member_type = None
                        consumed_member_types = []
                        for member_index, member_type in enumerate(root_read_order):
                            member_width = _skilldata_action_fixed_member_width(member_type)
                            if member_width is None:
                                next_member_type = member_type
                                break
                            if member_width > len(raw) - position:
                                next_field = {
                                    'offset': position,
                                    'memberIndex': member_index,
                                    'kind': member_type,
                                    'expectedBytes': member_width,
                                    'remainingBytes': len(raw) - position,
                                }
                                break
                            member_label = ('PlayAnimationAction' if tag == 0x115
                                            else 'AbilityActionData')
                            prefix_rows.append({
                                'start': position,
                                'end': position + member_width,
                                'kind': f'{member_label}.member{member_index}.{member_type}',
                            })
                            position += member_width
                            consumed_member_types.append(member_type)
                        candidate_ranges.extend(prefix_rows)
                        candidate_cursor = position
                        if next_field is not None:
                            status = ('truncated-play-animation-fixed-prefix'
                                      if tag == 0x115 else
                                      'truncated-action-fixed-prefix')
                            failure = {'category': 'truncated', **next_field}
                        elif (tag == 0x115 and next_member_type == 'byte-payload'):
                            payload_helper = _skilldata_verified_byte_payload_reader(
                                reader, byte_payload_helper_evidence, source=source)
                            candidate_byte_payload_helper_evidence = payload_helper
                            action_continuation = _skilldata_continue_play_animation_candidate(
                                raw, position, witness['hardLimit'],
                                root_read_order=root_read_order,
                                sequence_reader=sequence_reader,
                                payload_helper_evidence=payload_helper,
                                action_start=start, source=source)
                            candidate_ranges.extend(action_continuation['ranges'])
                            candidate_opaque_payload_ranges.extend(
                                action_continuation['opaquePayloadByteRanges'])
                            candidate_cursor = action_continuation['cursor']
                            status = action_continuation['status']
                            failure = action_continuation['failure']
                            candidate_play_animation_record_end = action_continuation[
                                'recordEndCandidate']
                            candidate_play_animation_nested_sequence = action_continuation.get(
                                'nestedSequence')
                            if candidate_play_animation_record_end is not None:
                                parent_continuation = _skilldata_continue_timeline_parent_candidate(
                                    raw, candidate_cursor, witness['hardLimit'],
                                    sequence_action_count=witness.get(
                                        'firstSequenceActionDataCount'),
                                    timeline_actions_list_count=witness.get(
                                        'timelineActionsListCount'),
                                    timeline_action_start=witness.get('candidateStart'),
                                    timeline_reader=timeline,
                                    sequence_tail_windows=action_continuation[
                                        'independentlyVerifiedSequenceTailWindows'],
                                    action_group_members=action_group_members,
                                    payload_helper_evidence=payload_helper,
                                    bool_helper_evidence=c9_prefix_evidence,
                                    gameassembly_image_base=gameassembly_image_base,
                                    source=source)
                                candidate_timeline_continuation = parent_continuation
                                candidate_ranges.extend(parent_continuation['ranges'])
                                candidate_opaque_payload_ranges.extend(
                                    parent_continuation.get('opaquePayloadByteRanges', []))
                                candidate_timeline_action_data_record_end = (
                                    parent_continuation.get(
                                        'candidateTimelineActionDataRecordEnd'))
                                candidate_action_group_data_record_end = (
                                    parent_continuation.get(
                                        'candidateActionGroupDataRecordEnd'))
                                candidate_cursor = parent_continuation['cursor']
                                status = parent_continuation['status']
                                failure = parent_continuation['failure']
                                prefix_stop = {
                                    'tag': tag, 'start': start,
                                    'recordEndCandidate': candidate_play_animation_record_end,
                                    'end': candidate_cursor,
                                    'nextSourceReadType': parent_continuation.get(
                                        'nextSourceReadType'),
                                    'nextSourceReadOffset': parent_continuation.get(
                                        'nextSourceReadOffset'),
                                    'nextSourceReadConsumed': False,
                                    'classification': parent_continuation.get(
                                        'classification',
                                        'candidate-static-reader-record end; parent incomplete'),
                                }
                                if (parent_continuation.get('status') ==
                                        'stopped-before-additional-timeline-action-data'):
                                    following_timeline = (
                                        _skilldata_read_following_timeline_action_data_prefix_candidate(
                                            raw, candidate_cursor, witness['hardLimit'],
                                            timeline_reader=timeline,
                                            sequence_reader=sequence_reader,
                                            payload_helper_evidence=payload_helper,
                                            bool_helper_evidence=c9_prefix_evidence,
                                            gameassembly_image_base=gameassembly_image_base,
                                            source=source))
                                    candidate_following_timeline_action_prefix = following_timeline
                                    candidate_ranges.extend(following_timeline['ranges'])
                                    candidate_opaque_payload_ranges.extend(
                                        following_timeline.get('opaquePayloadByteRanges', []))
                                    candidate_cursor = following_timeline['cursor']
                                    status = following_timeline['status']
                                    failure = following_timeline.get('failure')
                                    prefix_stop = {
                                        'tag': tag, 'start': following_timeline['start'],
                                        'end': candidate_cursor,
                                        'nextSourceReadType': following_timeline.get(
                                            'nextSourceReadType'),
                                        'nextSourceReadOffset': following_timeline.get(
                                            'nextSourceReadOffset', candidate_cursor),
                                        'nextSourceReadConsumed': following_timeline.get(
                                            'nextSourceReadConsumed', False),
                                        'firstActionUnionTagPeekOnly': following_timeline.get(
                                            'firstActionUnionTagPeekOnly'),
                                        'classification': (
                                            'candidate following TimelineActionData prefix; '
                                            'nested action and later parents remain open'),
                                    }
                                    following_tag = following_timeline.get(
                                        'firstActionUnionTagPeekOnly')
                                    if (following_timeline.get('status') ==
                                            'stopped-before-following-timeline-sequence-action' and
                                            isinstance(following_tag, dict) and
                                            following_tag.get('tag') == 0x115 and
                                            following_timeline.get('timelineSequenceCount') == 1):
                                        remaining_timeline_actions = (
                                            witness.get('timelineActionsListCount') - 1)
                                        following_action = (
                                            _skilldata_continue_following_play_animation_candidate(
                                                raw, following_timeline, witness['hardLimit'],
                                                timeline_actions_list_count=remaining_timeline_actions,
                                                timeline_reader=timeline,
                                                sequence_reader=sequence_reader,
                                                action_group_members=action_group_members,
                                                buff_routes=buff_routes,
                                                action_readers=buff_action_readers,
                                                payload_helper_evidence=payload_helper,
                                                bool_helper_evidence=c9_prefix_evidence,
                                                gameassembly_image_base=gameassembly_image_base,
                                                source=source))
                                        following_timeline['playAnimationContinuation'] = {
                                            key: value for key, value in following_action.items()
                                            if key != 'ranges'}
                                        following_timeline['ranges'].extend(
                                            following_action['ranges'])
                                        following_timeline['opaquePayloadByteRanges'] = (
                                            following_action['opaquePayloadByteRanges'])
                                        following_timeline['cursor'] = following_action['cursor']
                                        following_timeline['status'] = following_action['status']
                                        following_timeline['failure'] = following_action['failure']
                                        following_timeline['candidateRecordEnd'] = (
                                            following_action.get(
                                                'candidateTimelineActionDataRecordEnd'))
                                        following_timeline['candidatePlayAnimationRecordEnd'] = (
                                            following_action.get(
                                                'candidatePlayAnimationRecordEnd'))
                                        following_timeline['candidateTimelineContinuation'] = (
                                            following_action.get(
                                                'candidateTimelineContinuation'))
                                        candidate_ranges.extend(following_action['ranges'])
                                        candidate_opaque_payload_ranges.extend(
                                            following_action['opaquePayloadByteRanges'])
                                        candidate_cursor = following_action['cursor']
                                        status = following_action['status']
                                        failure = following_action['failure']
                                        candidate_following_timeline_action_data_record_end = (
                                            following_action.get(
                                                'candidateTimelineActionDataRecordEnd'))
                                        candidate_following_play_animation_record_end = (
                                            following_action.get(
                                                'candidatePlayAnimationRecordEnd'))
                                        candidate_following_timeline_continuation = (
                                            following_action.get(
                                                'candidateTimelineContinuation'))
                                        if following_action.get(
                                                'candidateActionGroupDataRecordEnd') is not None:
                                            candidate_action_group_data_record_end = (
                                                following_action.get(
                                                    'candidateActionGroupDataRecordEnd'))
                                        next_continuation = following_action.get(
                                            'candidateTimelineContinuation')
                                        prefix_stop = {
                                            'tag': tag, 'start': following_timeline['start'],
                                            'end': candidate_cursor,
                                            'nextSourceReadType': (
                                                next_continuation.get('nextSourceReadType')
                                                if isinstance(next_continuation, dict) else
                                                following_action.get('nextSourceReadType')),
                                            'nextSourceReadOffset': (
                                                next_continuation.get('nextSourceReadOffset')
                                                if isinstance(next_continuation, dict) else
                                                candidate_cursor),
                                            'nextSourceReadConsumed': False,
                                            'classification': following_action.get(
                                                'classification',
                                                'candidate following TimelineActionData reader end; later parents remain open'),
                                        }
                            else:
                                nested = action_continuation.get('nestedSequence')
                                next_type = ('SequenceActionData list element'
                                if isinstance(nested, dict) and
                                             nested.get('status') ==
                                             'stopped-before-sequence-action-elements'
                                             else 'PlayAnimationAction remaining member reads')
                                prefix_stop = {
                                    'tag': tag, 'start': start,
                                    'end': candidate_cursor,
                                    'nextSourceReadType': next_type,
                                    'nextSourceReadOffset': candidate_cursor,
                                    'nextSourceReadConsumed': False,
                                    'classification': 'candidate-static-reader prefix; parent incomplete',
                                }
                        elif next_member_type is not None:
                            status = ('stopped-before-play-animation-byte-payload'
                                      if tag == 0x115 else
                                      'stopped-before-action-variable-member')
                            if tag == 0x115:
                                prefix_stop = {
                                    'tag': tag, 'start': start, 'end': position,
                                    'memberHeader': root_member_count,
                                    'sourceReadOrderPrefix': consumed_member_types,
                                    'nextSourceReadType': next_member_type,
                                    'nextSourceReadOffset': position,
                                    'nextSourceReadConsumed': False,
                                    'consumedUnionRecord': False,
                                    'classification': 'candidate-static-reader-prefix; provider unobserved',
                                }
                            else:
                                prefix_stop = {
                                    'tag': tag, 'start': start, 'end': position,
                                    'memberHeader': root_member_count,
                                    'rootReadOrderKey': root_read_order_key,
                                    'sourceReadOrderPrefix': consumed_member_types,
                                    'nextSourceReadType': next_member_type,
                                    'nextSourceReadOffset': position,
                                    'nextSourceReadConsumed': False,
                                    'consumedUnionRecord': False,
                                    'classification': 'candidate-static-reader-prefix; provider unobserved',
                                }
                        else:
                            status = 'candidate-action-reader-member-sequence-exhausted'
                            prefix_stop = {
                                'tag': tag, 'start': start, 'end': position,
                                'memberHeader': root_member_count,
                                'rootReadOrderKey': root_read_order_key,
                                'sourceReadOrderPrefix': consumed_member_types,
                                'nextSourceReadType': None,
                                'nextSourceReadOffset': position,
                                'nextSourceReadConsumed': None,
                                'consumedUnionRecord': False,
                                'classification': 'candidate-static-reader-member-sequence; provider unobserved',
                            }
        elif tag == 0xC9:
            require(len(tag_routes), 1, source, union_peek['offset'])
            if not isinstance(c9_prefix_evidence, dict):
                raise ContextError(source, union_peek['offset'],
                                   'current exact-build C9 member-eight prefix reader evidence',
                                   c9_prefix_evidence)
            c9_route = tag_routes[0]
            require((c9_prefix_evidence.get('tag'),
                     c9_prefix_evidence.get('switchTargetRva'),
                     c9_prefix_evidence.get('typeDefinition'),
                     c9_prefix_evidence.get('wrapperName')),
                    (0xC9, c9_route.get('switchTargetRva'), c9_route.get('typeDefinition'),
                     c9_route.get('wrapperName')), source, union_peek['offset'])
            require(c9_prefix_evidence.get('providerSelection'), 'unobserved', source,
                    union_peek['offset'])
            start = union_peek['offset']
            if union_peek.get('tagWidth') != 1 or raw[start] != 0xC9:
                raise ContextError(source, start, 'one-byte C9 union tag', union_peek)
            header_offset = start + 1
            header_good = header_offset < len(raw) and raw[header_offset] == 8
            if not header_good:
                status = 'stopped-before-if-else-member-header'
                failure = {'category': ('truncated' if header_offset >= len(raw)
                                        else 'member-count'),
                           'offset': header_offset, 'expected': 8,
                           'actual': raw[header_offset] if header_offset < len(raw) else None}
            else:
                position = start
                prefix_fields = [
                    (1, 'AbilityActionData.union-tag'),
                    (1, 'IfElseAction.memberCount'),
                    (1, 'IfElseAction.member0.byte'),
                    (4, 'IfElseAction.member1.scalar32'),
                    (4, 'IfElseAction.member2.scalar32'),
                    (4, 'IfElseAction.member3.scalar32'),
                    (1, 'IfElseAction.member4.byte'),
                ]
                prefix_rows = []
                next_field = None
                for field_width, kind in prefix_fields:
                    if field_width > len(raw) - position:
                        next_field = {'offset': position, 'kind': kind,
                                      'expectedBytes': field_width,
                                      'remainingBytes': len(raw) - position}
                        break
                    prefix_rows.append({'start': position,
                                        'end': position + field_width,
                                        'kind': kind})
                    position += field_width
                candidate_ranges.extend(prefix_rows)
                candidate_cursor = position
                if next_field is not None:
                    status = 'truncated-if-else-fixed-prefix'
                    failure = {'category': 'truncated', **next_field}
                else:
                    status = 'stopped-before-if-else-sequence-call'
                    prefix_stop = {
                        'tag': tag, 'start': start, 'end': position,
                        'memberHeader': 8,
                        'sourceReadWidthsAfterHeader': [1, 4, 4, 4, 1],
                        'nextSourceReadType': 'Beyond.Gameplay.Core.SequenceActionData',
                        'nextSourceReadOffset': position,
                        'nextSourceReadConsumed': False,
                        'consumedUnionRecord': False,
                        'classification': 'candidate-static-reader-prefix; provider unobserved',
                    }
        else:
            reader = buff_action_readers.get(tag)
            if len(tag_routes) == 1 and reader is not None:
                union_evidence = skilldata_action_union_static_reader_evidence(
                    tag, reader, buff_routes,
                    gameassembly_image_base=gameassembly_image_base, source=source)
                status = 'stopped-before-action-without-bounded-prefix-contract'
            elif tag_routes:
                status = 'stopped-before-action-without-current-reader'
            else:
                status = 'stopped-at-unknown-action-tag'

    candidate_ranges.sort(key=lambda row: (row['start'], row['end']))
    range_cursor = 10
    for index, span in enumerate(candidate_ranges):
        if (type(span.get('start')) is not int or type(span.get('end')) is not int or
                span['start'] != range_cursor or span['end'] <= span['start'] or
                span['end'] > witness['hardLimit']):
            raise ContextError(source, range_cursor,
                               f'timeline candidate byteRanges[{index}] contiguous from byte 10',
                               span)
        range_cursor = span['end']
    require(range_cursor, candidate_cursor, source, candidate_cursor)
    if status == 'stopped-at-unknown-action-tag':
        require(witness['firstActionUnionTagPeekOnly'].get('consumed'), False,
                source, candidate_cursor)
        require(candidate_cursor, witness['firstActionUnionTagPeekOnly']['offset'],
                source, candidate_cursor)

    return {
        'status': 'conditional-static-reader-alignment',
        'inputSetSha256': input_set,
        'logicalFileIdentity': witness.get('logicalFileIdentity'),
        'logicalSha256': witness.get('logicalSha256'),
        'hardLimit': witness.get('hardLimit'),
        'authoritativeParserCursor': witness.get('authoritativeParserCursor'),
        'candidateCursor': candidate_cursor,
        'timelineActionsListCount': witness.get('timelineActionsListCount'),
        'firstSequenceActionDataCount': witness.get('firstSequenceActionDataCount'),
        'typedPrefixOwnershipCandidate': typed_prefix_ownership,
        'candidateByteRanges': candidate_ranges,
        'firstActionUnionTagPeekOnly': witness.get('firstActionUnionTagPeekOnly'),
        'candidateActionReaderEvidence': union_evidence,
        'candidateActionPrefixStop': prefix_stop,
        'candidatePlayAnimationRecordEnd': candidate_play_animation_record_end,
        'candidatePlayAnimationNestedSequence': candidate_play_animation_nested_sequence,
        'candidateTimelineContinuation': candidate_timeline_continuation,
        'candidateTimelineActionDataRecordEnd': candidate_timeline_action_data_record_end,
        'candidateActionGroupDataRecordEnd': candidate_action_group_data_record_end,
        'candidateFollowingTimelineActionDataPrefix': candidate_following_timeline_action_prefix,
        'candidateFollowingTimelineActionDataRecordEnd': (
            candidate_following_timeline_action_data_record_end),
        'candidateFollowingPlayAnimationRecordEnd': (
            candidate_following_play_animation_record_end),
        'candidateFollowingTimelineContinuation': candidate_following_timeline_continuation,
        'opaquePayloadByteRanges': candidate_opaque_payload_ranges,
        'bytePayloadHelperEvidence': candidate_byte_payload_helper_evidence,
        'candidateStatus': status,
        'failure': failure,
        'opaqueByteRanges': ([] if candidate_cursor == witness['hardLimit'] else [{
            'start': candidate_cursor, 'end': witness['hardLimit'],
            'kind': 'unconsumed-timeline-actiongroup-and-skilldata-bytes'}]),
        'exactClosedTimelineActionRecords': 0,
        'exactClosedActionGroupDataRecords': 0,
        'wholeSkillDataClassification': 'ambiguous',
        'wholeSkillDataExactClosedRecords': 0,
        'runtimeProviderCacheSelection': 'unobserved',
        'boundary': ('This reader-path alignment is a separate candidate and never changes parserCursor 10. The 0x115 '
                     'candidate may follow exact-build signed-length byte-payload helpers, its static SequenceActionData '
                     'null/empty path, and the enclosing sequence tail/startFrame when each current byte fits. Opaque '
                     'payload content is not decoded; runtime formatter/provider selection remains unobserved. Unknown '
                     'tags remain at their first byte. No TimelineActionData, ActionGroupData or SkillData parent is '
                     'counted closed.'),
    }


def skilldata_action_readers_from_locals(local_values, *, source):
    """Collect only current native action readers backed by matching contracts."""
    readers = {}
    for variable_name, reader in local_values.items():
        variable_match = re.fullmatch(r'buff_([0-9a-f]+)', variable_name)
        if variable_match is None or not isinstance(reader, dict):
            continue
        contract_value = reader.get('contractPath')
        if not isinstance(contract_value, str) or not contract_value:
            continue
        contract_path = Path(contract_value).resolve()
        contract_match = re.fullmatch(r'buff_([0-9a-f]+)_native\.json',
                                      contract_path.name, flags=re.IGNORECASE)
        if contract_match is None:
            continue
        tag = int(variable_match.group(1), 16)
        require(int(contract_match.group(1), 16), tag, source, tag)
        expected_path = Path(__file__).with_name(
            f'buff_{tag:02x}_native.json').resolve()
        require(contract_path, expected_path, source, tag)
        if not contract_path.is_file():
            raise ContextError(source, tag, 'current selected action reader contract file',
                               str(contract_path))
        contract_sha = hashlib.sha256(contract_path.read_bytes()).hexdigest().upper()
        require(reader.get('contractSha256'), contract_sha, source, tag)
        if tag in readers:
            raise ContextError(source, tag, 'one selected native action reader per tag',
                               [variable_name, readers[tag]['variableName']])
        reader = dict(reader)
        reader['variableName'] = variable_name
        readers[tag] = reader
    return readers


def skilldata_action_union_static_reader_evidence(tag, reader, buff_routes, *,
                                                   gameassembly_image_base,
                                                   source):
    """Join one sample tag to its registered wrapper and exact current reader body."""
    if not isinstance(reader, dict):
        raise ContextError(source, tag, 'hash-pinned native reader for consumed action tag',
                           type(reader).__name__)
    route_rows = buff_routes.get('rows') if isinstance(buff_routes, dict) else None
    if not isinstance(route_rows, list):
        raise ContextError(source, tag, 'current AbilityActionData union route rows', route_rows)
    matching_routes = [row for row in route_rows if row.get('tag') == tag]
    if len(matching_routes) != 1:
        raise ContextError(source, tag, f'exactly one current route for tag {tag:#x}',
                           len(matching_routes))
    route = matching_routes[0]
    operands = route.get('operands')
    if not isinstance(operands, list) or not operands:
        raise ContextError(source, tag, 'registered tag-to-wrapper type-usage operand', operands)
    operand_rows = []
    for index, operand in enumerate(operands):
        if not isinstance(operand, dict):
            raise ContextError(source, tag, f'route operand {index} object', operand)
        if (type(operand.get('usageTag')) is not int or
                type(operand.get('registeredTypeIndex')) is not int):
            raise ContextError(source, tag, f'route operand {index} exact usage/type indices', operand)
        operand_rows.append({
            'usageTag': operand['usageTag'],
            'registeredTypeIndex': operand['registeredTypeIndex'],
        })

    expected_contract = Path(__file__).with_name(
        f'buff_{tag:02x}_native.json').resolve()
    contract_path = Path(reader.get('contractPath', '')).resolve()
    require(contract_path, expected_contract, source, tag)
    if not expected_contract.is_file():
        raise ContextError(source, tag, 'current selected action reader contract file',
                           str(expected_contract))
    contract_sha = hashlib.sha256(expected_contract.read_bytes()).hexdigest().upper()
    require(reader.get('contractSha256'), contract_sha, source, tag)

    methods = reader.get('methods')
    if not isinstance(methods, list):
        raise ContextError(source, tag, 'native action Deserialize module/token rows', methods)
    selected_methods = [row for row in methods
                        if row.get('declaringType') == route.get('wrapperName') and
                        row.get('name') == 'Deserialize']
    if len(selected_methods) != 1:
        raise ContextError(source, tag, 'one module/token-joined registered wrapper reader',
                           len(selected_methods))
    method = selected_methods[0]
    require(method.get('image'), 'MemoryPack.Beyond.dll', source, tag)
    pointer_va = method.get('pointerVa')
    if type(pointer_va) is not int:
        raise ContextError(source, tag, 'current root reader native pointer VA', pointer_va)
    root_rva = pointer_va - gameassembly_image_base
    code_windows = reader.get('codeWindows')
    if not isinstance(code_windows, list):
        raise ContextError(source, tag, 'hash-pinned selected action reader code windows',
                           code_windows)
    root_windows = [row for row in code_windows
                    if isinstance(row, dict) and row.get('startRva') == root_rva]
    if len(root_windows) != 1:
        raise ContextError(source, tag,
                           'one exact reader code window beginning at the registered method pointer',
                           {'rootRva': root_rva, 'matches': len(root_windows)})
    root_window = root_windows[0]
    if (type(root_window.get('endRva')) is not int or
            root_window['endRva'] <= root_window['startRva'] or
            not isinstance(root_window.get('sha256'), str) or
            not re.fullmatch(r'[0-9A-Fa-f]{64}', root_window['sha256'])):
        raise ContextError(source, tag, 'bounded 64-hex root reader code-window fingerprint',
                           root_window)

    read_order = reader.get('anonymousReadOrder')
    if not isinstance(read_order, dict) or not read_order:
        raise ContextError(source, tag, 'anonymous native member read order', read_order)
    root_order_key = next(iter(read_order))
    header_match = (re.search(r'member(\d+)$', root_order_key, flags=re.IGNORECASE)
                    if isinstance(root_order_key, str) else None)
    if header_match is None:
        raise ContextError(source, tag, 'root read-order key ending in its member count',
                           root_order_key)
    root_member_count = int(header_match.group(1))
    root_member_order = read_order[root_order_key]
    if not isinstance(root_member_order, list):
        raise ContextError(source, tag, 'root anonymous member read-order list',
                           root_member_order)
    return {
        'tag': tag,
        'switchTargetRva': route.get('switchTargetRva'),
        'typeDefinition': route.get('typeDefinition'),
        'wrapperName': route.get('wrapperName'),
        'operands': operand_rows,
        'methodIndex': method.get('methodIndex'),
        'contractFile': expected_contract.name,
        'contractSha256': contract_sha,
        'rootCodeWindow': {
            'startRva': root_window['startRva'],
            'endRva': root_window['endRva'],
            'sha256': root_window['sha256'],
        },
        'rootReadOrderKey': root_order_key,
        'rootMemberCount': root_member_count,
        'rootAnonymousReadOrder': root_member_order,
    }


def skilldata_action_union_c9_prefix_reader_evidence(reader, buff_routes, *,
                                                       gameassembly_image_base,
                                                       source):
    """Pin only the C9 member-eight scalar prefix before its generic children."""
    if not isinstance(reader, dict):
        raise ContextError(source, 0xC9,
                           'current exact-build IfElse selected-reader evidence',
                           type(reader).__name__)
    route_rows = buff_routes.get('rows') if isinstance(buff_routes, dict) else None
    if not isinstance(route_rows, list):
        raise ContextError(source, 0xC9, 'current AbilityActionData union route rows',
                           route_rows)
    matching_routes = [row for row in route_rows if row.get('tag') == 0xC9]
    if len(matching_routes) != 1:
        raise ContextError(source, 0xC9, 'one exact current C9 union route',
                           len(matching_routes))
    route = matching_routes[0]
    wrapper = ('Beyond.MemoryPack.Beyond_Gameplay_Core_IfElseAction_'
               'IfElseActionDataForMemoryPack')
    require(route.get('switchTargetRva'), 0x390DA8A, source, 0xC9)
    require(route.get('typeDefinition'), 16163, source, 0xC9)
    require(route.get('wrapperName'), wrapper, source, 0xC9)
    operands = route.get('operands')
    if not isinstance(operands, list):
        raise ContextError(source, 0xC9, 'C9 registered type-usage operands', operands)
    selected_operands = [row for row in operands
                         if row.get('usageTag') == 1 and
                         row.get('registeredTypeIndex') == 106672]
    require(len(selected_operands), 1, source, 0xC9)

    methods = reader.get('methods')
    if not isinstance(methods, list):
        raise ContextError(source, 0xC9, 'IfElse selected reader method rows', methods)
    selected_methods = [row for row in methods
                        if row.get('methodIndex') == 120613 and
                        row.get('declaringType') == wrapper and
                        row.get('name') == 'Deserialize']
    if len(selected_methods) != 1:
        raise ContextError(source, 0xC9,
                           'one token/module-joined IfElse root Deserialize method',
                           len(selected_methods))
    method = selected_methods[0]
    require(method.get('image'), 'MemoryPack.Beyond.dll', source, 0xC9)
    pointer_va = method.get('pointerVa')
    if type(pointer_va) is not int:
        raise ContextError(source, 0xC9, 'exact IfElse root reader pointer VA', pointer_va)
    root_rva = pointer_va - gameassembly_image_base
    require(root_rva, 0x3774060, source, 0xC9)
    root_window = reader.get('rootCodeWindow')
    if not isinstance(root_window, dict):
        raise ContextError(source, 0xC9, 'hash-pinned complete IfElse reader code window',
                           root_window)
    require((root_window.get('startRva'), root_window.get('endRva'),
             root_window.get('sha256')),
            (0x3774060, 0x37742A8,
             'AC1FF978FEF71639E74980B43AE00D9746518A9DD94B41772F2867963A596ED8'),
            source, 0xC9)

    expected_windows = {
        0x3774093:
            '837B30010F8C089A6B01488B43500FB6288B733083EE010F880B9A6B0148FF4350FF4340FF43448973304080FDFF0F8482010000',
        0x37740FA: '4080FD080F85D1996B01',
    }
    windows = reader.get('windows')
    if not isinstance(windows, list):
        raise ContextError(source, 0xC9, 'selected IfElse reader instruction windows', windows)
    window_evidence = []
    for rva, expected_hex in expected_windows.items():
        matches = [row for row in windows if row.get('rva') == rva]
        if len(matches) != 1:
            raise ContextError(source, rva, 'one exact selected IfElse normal-path window',
                               len(matches))
        actual_hex = matches[0].get('rawHex')
        require(actual_hex, expected_hex, source, rva)
        raw_window = bytes.fromhex(actual_hex)
        window_evidence.append({
            'startRva': rva,
            'endRva': rva + len(raw_window),
            'byteLength': len(raw_window),
            'sha256': hashlib.sha256(raw_window).hexdigest().upper(),
            'rawHex': actual_hex,
        })

    expected_calls = [
        (0x377410A, 0x2CA88C0, 1),
        (0x3774135, 0x2CA86B0, 4),
        (0x3774159, 0x2CA86B0, 4),
        (0x377417D, 0x2CA86B0, 4),
        (0x37741A1, 0x2CA88C0, 1),
        (0x37741CA, 0x2DA5C90, None),
        (0x37741F3, 0x2DA5C90, None),
        (0x377421C, 0x2DA5C90, None),
    ]
    calls = reader.get('orderedCalls')
    if not isinstance(calls, list):
        raise ContextError(source, 0xC9, 'selected IfElse ordered source-call rows', calls)
    actual_calls = [(row.get('rva'), row.get('targetRva'),
                     row.get('fastSerializedWidth')) for row in calls]
    require(actual_calls, expected_calls, source, 0x377410A)

    expected_nested_operand_rvas = [0x37741BD, 0x37741E6, 0x377420F]
    nested_operands = reader.get('nestedOperands')
    if not isinstance(nested_operands, list):
        raise ContextError(source, 0xC9, 'three exact nested generic type-usage rows',
                           nested_operands)
    require([row.get('rva') for row in nested_operands],
            expected_nested_operand_rvas, source, 0xC9)
    require(len({row.get('cellVa') for row in nested_operands}), 1, source, 0xC9)
    require(len({row.get('usageRawHex') for row in nested_operands}), 1, source, 0xC9)
    require(reader.get('nestedMethodSpecIndex'), 619962, source, 0xC9)
    require(reader.get('nestedTypeDefinition'), 9202, source, 0xC9)
    require(reader.get('nestedTypeName'),
            'Beyond.Gameplay.Core.SequenceActionData', source, 0xC9)
    instantiation = reader.get('nestedInstantiation')
    if not isinstance(instantiation, dict):
        raise ContextError(source, 0xC9,
                           'exact nested SequenceActionData type instantiation',
                           instantiation)
    arguments = instantiation.get('arguments')
    if not isinstance(arguments, (list, tuple)) or len(arguments) != 1:
        raise ContextError(source, 0xC9, 'one selected SequenceActionData type argument',
                           arguments)
    require(arguments[0].get('raw_type_record_hex'),
            'F2230000000000000000120000000000', source, 0xC9)

    return {
        'tag': 0xC9,
        'switchTargetRva': route['switchTargetRva'],
        'typeDefinition': route['typeDefinition'],
        'wrapperName': wrapper,
        'registeredTypeIndex': 106672,
        'methodIndex': method['methodIndex'],
        'rootMethodRva': root_rva,
        'rootCodeWindow': root_window,
        'memberHeader': 8,
        'prefixSourceReadWidthsAfterHeader': [1, 4, 4, 4, 1],
        'prefixByteLengthIncludingTagAndMemberHeader': 16,
        'codeWindows': window_evidence,
        'nestedSequenceMethodSpecIndex': reader['nestedMethodSpecIndex'],
        'nestedSequenceTypeDefinition': reader['nestedTypeDefinition'],
        'nestedSequenceTypeName': reader['nestedTypeName'],
        'verifiedSharedHelperReads': [
            {'callInstructionRva': rva, 'targetRva': target,
             'fastSerializedWidth': width}
            for rva, target, width in expected_calls[:5]],
        'nestedSequenceCallSites': [
            {'rva': rva, 'targetRva': target}
            for rva, target, width in expected_calls[5:]],
        'providerSelection': 'unobserved',
        'boundary': ('The current C9 route selects the exact IfElse root reader. Its selected member-eight '
                     'normal path reads a one-byte member header, widths 1/4/4/4/1, then makes three '
                     'generic calls whose MethodSpec type argument is SequenceActionData. This evidence '
                     'ends before the first generic child call; it does not establish which runtime '
                     'formatter/provider supplies that child reader or close the C9 union.'),
    }


def skilldata_actiongroup_c9_nested_sequence_candidate_replay(
        witness, raw, c9_prefix_reader, sequence_reader, buff_action_readers,
        buff_routes, *, source, gameassembly_image_base=0x180000000,
        candidate_limit=None):
    """Keep a bounded C9->Sequence replay explicitly separate from the parser cursor."""
    if not isinstance(witness, dict) or not isinstance(raw, bytes):
        raise ContextError(source, 0, 'current SkillData prefix witness and raw bytes',
                           [type(witness).__name__, type(raw).__name__])
    if not all(isinstance(value, dict) for value in
               (c9_prefix_reader, sequence_reader, buff_routes)):
        raise ContextError(source, 0,
                           'C9, SequenceActionData and action-route static evidence objects',
                           [type(c9_prefix_reader).__name__, type(sequence_reader).__name__,
                            type(buff_routes).__name__])
    if not isinstance(buff_action_readers, dict) or any(
            type(tag) is not int or not isinstance(reader, dict)
            for tag, reader in buff_action_readers.items()):
        raise ContextError(source, 0, 'current tag-to-native action reader map',
                           type(buff_action_readers).__name__)

    input_set = witness.get('inputSetSha256')
    if not isinstance(input_set, str) or not re.fullmatch(r'[0-9A-Fa-f]{64}', input_set):
        raise ContextError(source, 0, 'current SkillData inputSetSha256', input_set)
    logical_path = witness.get('logicalFileIdentity')
    if not isinstance(logical_path, str) or not logical_path.startswith('Data/Json/SkillData/'):
        raise ContextError(source, 0, 'logical SkillData file identity', logical_path)
    logical_sha = hashlib.sha256(raw).hexdigest().upper()
    require(witness.get('logicalSha256'), logical_sha, source, 0)
    hard_limit = witness.get('hardLimit')
    require(hard_limit, len(raw), source, 0)
    require(witness.get('status'), 'stopped-after-verified-action-prefix', source, 0)
    prefix = witness.get('actionUnionPrefixStop')
    if not isinstance(prefix, dict):
        raise ContextError(source, witness.get('parserCursor', 0),
                           'C9 structural-prefix witness', prefix)
    prefix_start = prefix.get('start')
    prefix_end = prefix.get('end')
    if (type(prefix_start) is not int or type(prefix_end) is not int or
            prefix_start < 0 or prefix_end <= prefix_start or prefix_end > hard_limit):
        raise ContextError(source, 0, 'C9 prefix range within current hardLimit',
                           [prefix_start, prefix_end, hard_limit])
    require(prefix.get('tag'), 0xC9, source, prefix_start if type(prefix_start) is int else 0)
    require(prefix.get('memberHeader'), 8, source,
            prefix_start + 1 if type(prefix_start) is int else 0)
    require(prefix.get('sourceReadWidthsAfterHeader'), [1, 4, 4, 4, 1], source,
            prefix_start if type(prefix_start) is int else 0)
    require(prefix_end - prefix_start, 16, source,
            prefix_start if type(prefix_start) is int else 0)
    require(witness.get('parserCursor'), prefix_end, source,
            prefix_end if type(prefix_end) is int else 0)
    require(prefix.get('consumedUnionRecord'), False, source,
            prefix_start if type(prefix_start) is int else 0)
    require(prefix.get('nextSourceReadType'),
            'Beyond.Gameplay.Core.SequenceActionData', source, prefix_end)
    require(prefix.get('nextSourceReadOffset'), prefix_end, source, prefix_end)
    require(prefix.get('nextSourceReadConsumed'), False, source, prefix_end)
    require(prefix.get('remainingBytesOpaque'), True, source, prefix_end)
    require(c9_prefix_reader.get('tag'), 0xC9, source, prefix_start)
    require(c9_prefix_reader.get('memberHeader'), 8, source, prefix_start + 1)
    require(c9_prefix_reader.get('prefixSourceReadWidthsAfterHeader'),
            [1, 4, 4, 4, 1], source, prefix_start)
    require(c9_prefix_reader.get('prefixByteLengthIncludingTagAndMemberHeader'),
            16, source, prefix_start)
    require(c9_prefix_reader.get('nestedSequenceMethodSpecIndex'), 619962, source, prefix_start)
    require(c9_prefix_reader.get('nestedSequenceTypeDefinition'), 9202, source, prefix_start)
    require(c9_prefix_reader.get('nestedSequenceTypeName'),
            'Beyond.Gameplay.Core.SequenceActionData', source, prefix_start)
    require(c9_prefix_reader.get('providerSelection'), 'unobserved', source, prefix_start)
    c9_root = c9_prefix_reader.get('rootCodeWindow')
    require((c9_root.get('startRva'), c9_root.get('endRva'), c9_root.get('sha256'))
            if isinstance(c9_root, dict) else None,
            (0x3774060, 0x37742A8,
             'AC1FF978FEF71639E74980B43AE00D9746518A9DD94B41772F2867963A596ED8'),
            source, prefix_start)
    expected_call_sites = [
        {'rva': 0x37741CA, 'targetRva': 0x2DA5C90},
        {'rva': 0x37741F3, 'targetRva': 0x2DA5C90},
        {'rva': 0x377421C, 'targetRva': 0x2DA5C90},
    ]
    require(c9_prefix_reader.get('nestedSequenceCallSites'), expected_call_sites,
            source, prefix_start)

    sequence_methods = sequence_reader.get('methods')
    if not isinstance(sequence_methods, list):
        raise ContextError(source, prefix_end, 'SequenceActionData native method rows',
                           sequence_methods)
    selected_sequence_methods = [row for row in sequence_methods
                                 if isinstance(row, dict) and
                                 row.get('methodIndex') == 104346 and
                                 row.get('declaringType') ==
                                 'Beyond.MemoryPack.Beyond_Gameplay_Core_SequenceActionDataForMemoryPack' and
                                 row.get('name') == 'Deserialize' and
                                 row.get('image') == 'MemoryPack.Beyond.dll']
    if len(selected_sequence_methods) != 1:
        raise ContextError(source, prefix_end,
                           'one module/token-joined SequenceActionData root reader',
                           len(selected_sequence_methods))
    sequence_method = selected_sequence_methods[0]
    if type(sequence_method.get('pointerVa')) is not int:
        raise ContextError(source, prefix_end,
                           'SequenceActionData root reader pointer VA', sequence_method)
    sequence_root_rva = sequence_method['pointerVa'] - gameassembly_image_base
    require(sequence_root_rva, 0x39C6AA0, source, prefix_end)
    sequence_root = sequence_reader.get('rootCodeWindow')
    require((sequence_root.get('startRva'), sequence_root.get('endRva'),
             sequence_root.get('sha256')) if isinstance(sequence_root, dict) else None,
            (0x39C6AA0, 0x39C6FA7,
             '6444AF67AF86E7809AF5A50AE6DEE922B699DCB1CA686DC81F4C3584AB817B90'),
            source, prefix_end)

    if candidate_limit is None:
        candidate_limit = hard_limit
    if (type(candidate_limit) is not int or
            not prefix_end <= candidate_limit <= hard_limit):
        raise ContextError(source, prefix_end,
                           'candidateLimit within [C9 prefix end, current hardLimit]',
                           candidate_limit)

    from scripts.game_data.memorypack.buff_actions import FrameError, Reader, Unsupported

    class GuardedSequenceReader(Reader):
        def action(self, depth):
            start = self.pos
            lead = self.peek()
            width = 3 if lead == 0xFA else 1
            if width > self.limit - self.pos:
                raise FrameError(self.source, self.pos, {'bytes': width},
                                 {'remaining': self.limit - self.pos}, 'truncated')
            tag = struct.unpack_from('<H', self.data, self.pos + 1)[0] if width == 3 else lead
            if tag != 0xFF and tag not in buff_action_readers:
                raise Unsupported(self.source, start,
                                  'current selected native action-reader contract for nested tag',
                                  tag, 'union-tag')
            if tag != 0xFF:
                native_reader = buff_action_readers[tag]
                native_evidence = skilldata_action_union_static_reader_evidence(
                    tag, native_reader, buff_routes,
                    gameassembly_image_base=gameassembly_image_base,
                    source=self.source)
                action_reader_evidence_by_tag.setdefault(tag, native_evidence)
                header_offset = start + width
                if (header_offset < self.limit and
                        self.data[header_offset] != 0xFF and
                        self.data[header_offset] != native_evidence['rootMemberCount']):
                    raise Unsupported(
                        self.source, start,
                        {'nativeReaderMemberCount': native_evidence['rootMemberCount'],
                         'firstUnconsumedByte': start},
                        {'tag': tag, 'memberHeaderOffset': header_offset,
                         'memberHeaderValue': self.data[header_offset]},
                        'native-header')
            return super().action(depth)

    reader = GuardedSequenceReader(raw, source, limit=candidate_limit)
    reader.pos = prefix_end
    candidate_sequence_ranges = []
    candidate_calls = []
    candidate_action_ranges = []
    action_reader_evidence_by_tag = {}
    failure = None
    for call_index, call_site in enumerate(expected_call_sites):
        start = reader.pos
        first_range_index = len(reader.ranges)
        first_record_index = len(reader.records)
        call_error = None
        try:
            reader.sequence(depth=0)
        except FrameError as exc:
            diagnostic = getattr(exc, 'diagnostic', None)
            if not isinstance(diagnostic, dict):
                raise
            call_error = diagnostic
            failure = diagnostic

        end = reader.pos
        new_ranges = [dict(row) for row in reader.ranges[first_range_index:]]
        range_cursor = start
        for range_index, byte_range in enumerate(new_ranges):
            if (type(byte_range.get('start')) is not int or
                    type(byte_range.get('end')) is not int or
                    byte_range['start'] != range_cursor or
                    byte_range['end'] <= range_cursor or byte_range['end'] > end):
                raise ContextError(source, range_cursor,
                                   f'candidate call {call_index} byteRanges[{range_index}] contiguous',
                                   byte_range)
            range_cursor = byte_range['end']
        require(range_cursor, end, source, end)

        new_records = reader.records[first_record_index:]
        for record in new_records:
            if record.get('kind') != 'union':
                continue
            tag = record.get('tag')
            union_start, union_end = record.get('start'), record.get('end')
            if (type(tag) is not int or type(union_start) is not int or
                    type(union_end) is not int or
                    not start <= union_start < union_end <= end):
                raise ContextError(source, start,
                                   'candidate child union range contained within attempted SequenceActionData call',
                                   record)
            lead = raw[union_start]
            tag_width = 3 if lead == 0xFA else 1
            if tag_width == 3:
                actual_tag = struct.unpack_from('<H', raw, union_start + 1)[0]
            else:
                actual_tag = lead
            require(actual_tag, tag, source, union_start)
            if tag == 0xFF:
                candidate_action_ranges.append({
                    'tag': tag, 'start': union_start, 'end': union_end,
                    'sequenceCallIndex': call_index,
                    'memberHeaderValue': None,
                    'nativeActionReaderEvidence': None,
                    'classification': 'candidate-only-null-action-range',
                })
                continue
            native_reader = buff_action_readers.get(tag)
            if not isinstance(native_reader, dict):
                raise ContextError(source, union_start,
                                   'native action-reader contract for completed candidate child tag', tag)
            native_evidence = skilldata_action_union_static_reader_evidence(
                tag, native_reader, buff_routes,
                gameassembly_image_base=gameassembly_image_base, source=source)
            header_offset = union_start + tag_width
            if header_offset >= union_end:
                raise ContextError(source, header_offset,
                                   'candidate non-null child contains its member header',
                                   [union_start, union_end, tag_width])
            member_header = raw[header_offset]
            if member_header != 0xFF:
                require(member_header, native_evidence['rootMemberCount'], source,
                        header_offset)
            action_reader_evidence_by_tag.setdefault(tag, native_evidence)
            candidate_action_ranges.append({
                'tag': tag, 'start': union_start, 'end': union_end,
                'sequenceCallIndex': call_index,
                'memberHeaderValue': member_header,
                'nativeActionReaderEvidence': native_evidence,
                'classification': 'candidate-only-static-reader-child-range',
            })

        matching_outer_sequences = [row for row in new_records
                                    if row.get('kind') == 'sequence' and
                                    row.get('start') == start and row.get('end') == end]
        complete = call_error is None
        if complete:
            require(len(matching_outer_sequences), 1, source, start)
            candidate_range = {
                'start': start,
                'end': end,
                'kind': 'candidate-SequenceActionData-call-range',
                'callSiteRva': call_site['rva'],
                'byteRanges': new_ranges,
                'completedChildActionTags': [
                    row['tag'] for row in candidate_action_ranges
                    if row['sequenceCallIndex'] == call_index],
                'classification': 'candidate-only; runtime provider/cache selection unobserved',
            }
            candidate_sequence_ranges.append(candidate_range)
            call_status = 'candidate-sequence-range-replayed'
        else:
            require(matching_outer_sequences, [], source, start)
            call_status = call_error.get('category', 'unsupported')
            call_row = {
                'callIndex': call_index,
                'callSiteRva': call_site['rva'],
                'start': start,
                'candidateCursor': end,
                'completed': False,
                'status': call_status,
                'diagnostic': call_error,
                'consumedByteRanges': new_ranges,
            }
            if call_status in ('union-tag', 'native-header') and end < candidate_limit:
                lead = raw[end]
                width = 3 if lead == 0xFA else 1
                peeked_tag = (struct.unpack_from('<H', raw, end + 1)[0]
                              if width == 3 and candidate_limit - end >= 3 else
                              lead if width == 1 else None)
                call_row['firstUnconsumedActionUnionByte'] = {
                    'offset': end,
                    'firstByte': lead,
                    'decodedTag': peeked_tag,
                    'consumed': False,
                }
                if call_status == 'native-header':
                    call_row['nativeReaderHeaderConflict'] = call_error.get('actual')
            candidate_calls.append(call_row)
            break
        candidate_calls.append({
            'callIndex': call_index,
            'callSiteRva': call_site['rva'],
            'start': start,
            'end': end,
            'completed': True,
            'status': call_status,
            'candidateRange': candidate_range,
        })

    candidate_cursor = reader.pos
    overall_ranges = [dict(row) for row in reader.ranges]
    range_cursor = prefix_end
    for range_index, byte_range in enumerate(overall_ranges):
        if (type(byte_range.get('start')) is not int or
                type(byte_range.get('end')) is not int or
                byte_range['start'] != range_cursor or
                byte_range['end'] <= range_cursor or
                byte_range['end'] > candidate_cursor):
            raise ContextError(source, range_cursor,
                               f'candidateByteRanges[{range_index}] contiguous from C9 prefix cursor',
                               byte_range)
        range_cursor = byte_range['end']
    require(range_cursor, candidate_cursor, source, candidate_cursor)
    if failure is None:
        status = 'three-sequence-call-candidates-replayed'
    elif failure.get('category') == 'union-tag':
        status = 'stopped-before-first-unverified-nested-action'
    elif failure.get('category') == 'native-header':
        status = 'ambiguous-native-reader-header'
    elif failure.get('category') == 'truncated':
        status = 'truncated-candidate-sequence'
    elif failure.get('category') in ('count-bounds', 'member-count', 'malformed'):
        status = 'malformed-candidate-sequence'
    else:
        status = 'unsupported-candidate-sequence'
    return {
        'candidateOnly': True,
        'status': status,
        'inputSetSha256': input_set,
        'logicalFileIdentity': logical_path,
        'logicalSha256': logical_sha,
        'hardLimit': hard_limit,
        'candidateLimit': candidate_limit,
        'candidateStart': prefix_end,
        'candidateCursor': candidate_cursor,
        'candidateByteRanges': overall_ranges,
        'sequenceCallCandidates': candidate_calls,
        'candidateSequenceRanges': candidate_sequence_ranges,
        'candidateActionUnionRanges': candidate_action_ranges,
        'currentActionReaderEvidence': [
            action_reader_evidence_by_tag[tag]
            for tag in sorted(action_reader_evidence_by_tag)],
        'selectedNativeSequenceReader': {
            'methodIndex': sequence_method['methodIndex'],
            'image': sequence_method['image'],
            'rootCodeWindow': sequence_root,
        },
        'runtimeProviderCacheSelection': 'unobserved',
        'authoritativeParserCursor': witness['parserCursor'],
        'authoritativeParserCursorUnchanged': True,
        'exactClosedSequenceRecords': 0,
        'exactClosedC9UnionRecords': 0,
        'exactClosedActionGroupDataRecords': 0,
        'exactClosedWholeSkillDataRecords': 0,
        'failure': failure,
        'remainingSourceBytesOpaque': [
            *([] if candidate_cursor >= candidate_limit else [{
                'start': candidate_cursor,
                'end': candidate_limit,
                'kind': 'candidate-replay-remainder-opaque',
            }]),
            *([] if candidate_limit >= hard_limit else [{
                'start': candidate_limit,
                'end': hard_limit,
                'kind': 'beyond-candidateLimit-opaque',
            }]),
        ],
        'boundary': ('The three SequenceActionData calls are replayed only as a separate candidate using the '
                     'current native Sequence root and child-action reader contracts. Runtime provider/cache '
                     'selection for the C9 generic calls is unobserved. Candidate ranges never advance the '
                     'authoritative parser cursor and never close the C9 union, AbilityActionMap, parent list, '
                     'ActionGroupData, or whole SkillData record.'),
    }


def skilldata_actiongroup_branch_static_alignment(witness, skilldata_reader,
                                                   ability_map_reader,
                                                   shared_list_reader,
                                                   sequence_reader,
                                                   buff_d5_reader,
                                                   buff_d6_reader,
                                                   buff_routes, *, source,
                                                   buff_action_readers=None,
                                                   buff_action_prefixes=None,
                                                   gameassembly_image_base=0x180000000):
    """Align current ActionGroupData samples with separately audited native readers."""
    if not all(isinstance(value, dict) for value in
               (witness, skilldata_reader, ability_map_reader,
                shared_list_reader, sequence_reader, buff_d5_reader,
                buff_d6_reader, buff_routes)):
        raise ContextError(source, 0,
                           'sample plus SkillData, AbilityActionMap, List<T>, Sequence and D5/D6 static evidence',
                           [type(value).__name__ for value in
                            (witness, skilldata_reader, ability_map_reader,
                             shared_list_reader, sequence_reader, buff_d5_reader,
                             buff_d6_reader, buff_routes)])
    if buff_action_readers is None:
        buff_action_readers = {}
    if not isinstance(buff_action_readers, dict) or any(
            type(tag) is not int or not isinstance(reader, dict)
            for tag, reader in buff_action_readers.items()):
        raise ContextError(source, 0, 'tag-to-current-native-action-reader mapping',
                           type(buff_action_readers).__name__)
    if buff_action_prefixes is None:
        buff_action_prefixes = {}
    if not isinstance(buff_action_prefixes, dict) or any(
            type(tag) is not int or not isinstance(evidence, dict)
            for tag, evidence in buff_action_prefixes.items()):
        raise ContextError(source, 0, 'tag-to-current-native-action-prefix evidence mapping',
                           type(buff_action_prefixes).__name__)
    native_action_readers = {0xD5: buff_d5_reader, 0xD6: buff_d6_reader}
    native_action_readers.update(buff_action_readers)
    require(skilldata_reader.get('firstSkillDataField', {}).get('fieldName'),
            'actionGroupData', source, 0)
    require(skilldata_reader.get('inputSetSha256'), witness.get('inputSetSha256'), source, 0)
    members = skilldata_reader.get('actionGroupDataMembers')
    if not isinstance(members, list) or len(members) != 2:
        raise ContextError(source, 0, 'two native ActionGroupData member reads', members)
    require([row.get('fieldName') for row in members],
            ['passiveEventActions', 'timelineActions'], source, 0)
    require([row.get('serializedOrderIndex') for row in members], [0, 1], source, 0)
    require([row.get('readerMethodSpec', {}).get('index') for row in members],
            [610662, 610915], source, 0)
    first_generic = members[0].get('readerMethodSpec', {}).get('genericType', {})
    require(first_generic.get('typeName'), 'System.Collections.Generic.List`1', source, 0)
    require(first_generic.get('elementTypeName'),
            'Beyond.Gameplay.Core.AbilityActionMap', source, 0)
    skilldata_code_windows = skilldata_reader.get('codeWindows')
    if not isinstance(skilldata_code_windows, list):
        raise ContextError(source, 0, 'current SkillData/ActionGroupData code windows',
                           skilldata_code_windows)
    require(any((row.get('rva'), row.get('byteLength'), row.get('sha256')) ==
                (58581179, 2314,
                 'FEA359985EBF5DF75CC58D871469481F0F692B1768D84724FF5941D47CAD8132')
                for row in skilldata_code_windows), True, source, 0)
    skilldata_instructions = skilldata_reader.get('verifiedInstructionWindows')
    if not isinstance(skilldata_instructions, list):
        raise ContextError(source, 0, 'current SkillData verified instruction windows',
                           skilldata_instructions)
    expected_skilldata_instructions = {
        (65273925, '4080FD02', 'ActionGroupData member-count comparison against 2'),
        (65273975, '48894118', 'store passiveEventActions result at object offset +0x18'),
        (65274020, '48894110', 'store timelineActions result at object offset +0x10'),
    }
    actual_skilldata_instructions = {
        (row.get('rva'), row.get('rawHex'), row.get('role'))
        for row in skilldata_instructions
    }
    require(expected_skilldata_instructions <= actual_skilldata_instructions,
            True, source, 0)

    ability_methods = ability_map_reader.get('methods')
    if not isinstance(ability_methods, list):
        raise ContextError(source, 0, 'native AbilityActionMap method identities', ability_methods)
    ability_reader_methods = [row for row in ability_methods
                              if row.get('methodIndex') in (104445, 104446)]
    require(sorted(row['methodIndex'] for row in ability_reader_methods),
            [104445, 104446], source, 0)
    require(ability_map_reader.get('anonymousReadOrder', {}).get('mapMember2'),
            ['scalar32', 'nullable-sequence-array'], source, 0)
    ability_map_windows = ability_map_reader.get('codeWindows')
    if not isinstance(ability_map_windows, list):
        raise ContextError(source, 0, 'current AbilityActionMap code windows', ability_map_windows)
    require(any((row.get('startRva'), row.get('endRva'), row.get('sha256')) ==
                (63974160, 63974463,
                 'ADDDF617D14CF2A723E7E6CDD2978D46BC6557DEE539EA28A21A12619CCF42BB')
                for row in ability_map_windows), True, source, 0)
    sequence_contexts = [row for row in ability_map_reader.get('nestedContexts', [])
                         if row.get('typeName') == 'Beyond.Gameplay.Core.SequenceActionData']
    require(len(sequence_contexts), 1, source, 0)
    require(sequence_contexts[0].get('methodSpecIndex'), 610597, source, 0)

    expected_shared_contract = Path(__file__).with_name('buff_b4_native.json').resolve()
    shared_contract = Path(shared_list_reader.get('contractPath', '')).resolve()
    require(shared_contract, expected_shared_contract, source, 0)
    shared_contract_sha = hashlib.sha256(expected_shared_contract.read_bytes()).hexdigest().upper()
    require(shared_list_reader.get('contractSha256'), shared_contract_sha, source, 0)
    shared_code_windows = shared_list_reader.get('codeWindows')
    if not isinstance(shared_code_windows, list):
        raise ContextError(source, 0, 'current shared List<T> native code windows',
                           shared_code_windows)
    require(any((row.get('startRva'), row.get('endRva'), row.get('sha256')) ==
                (46828560, 46829514,
                 'CD9E5FC3BAB5502AC7D168F445CA3DC207C39D61A9CFF7D7F52F51A1F447B7C5')
                for row in shared_code_windows), True, source, 0)
    if not shared_list_reader.get('methods'):
        raise ContextError(source, 0, 'current shared list reader method identities',
                           shared_list_reader.get('methods'))
    sequence_methods = sequence_reader.get('methods')
    if not isinstance(sequence_methods, list):
        raise ContextError(source, 0, 'native SequenceActionData method identities', sequence_methods)
    require(sorted(row.get('methodIndex') for row in sequence_methods),
            [104346, 104347], source, 0)
    sequence_header_window = [row for row in sequence_reader.get('windows', [])
                             if row.get('rva') == 0x39C6B82]
    if len(sequence_header_window) != 1:
        raise ContextError(source, 0, 'one exact SequenceActionData count window',
                           len(sequence_header_window))
    require(sequence_header_window[0].get('rawHex'),
            '4080FE030F85DD030000', source, 0)
    if 'header 3 takes a signed dword count after the one-byte header' not in sequence_reader.get('boundary', '').lower():
        raise ContextError(source, 0, 'SequenceActionData header/count boundary statement',
                           sequence_reader.get('boundary'))

    expected_action_readers = (
        (0xD5, buff_d5_reader, 120788,
         'Beyond.MemoryPack.Beyond_Gameplay_Core_IntResourceHpCheckAction_DataForMemoryPack',
         16187, 106689, 0x4E67C83, 153753548, 153753943,
         '24DFDAE1E252056FB43AB54D51BFA7443249A2FFA932B4636ACEA7F01C3EF1EB'),
        (0xD6, buff_d6_reader, 120799,
         'Beyond.MemoryPack.Beyond_Gameplay_Core_IntResourceOnHpZeroAction_DataForMemoryPack',
         16189, 106690, 0x4E67CC6, 153754580, 153754975,
         '2256CCF5032B30A1906A9830B8D815D491B6963EA04330DA4E67BBE49D399F7F'),
    )
    route_rows = buff_routes.get('rows')
    if not isinstance(route_rows, list):
        raise ContextError(source, 0, 'current AbilityActionData union route rows', route_rows)
    action_union_reader_evidence_by_tag = {}
    for (tag, reader, method_index, wrapper_name, type_definition,
         usage_index, switch_target, start_rva, end_rva, window_sha) in expected_action_readers:
        matching_routes = [row for row in route_rows if row.get('tag') == tag]
        if len(matching_routes) != 1:
            raise ContextError(source, tag, f'exactly one current route for D5/D6 tag {tag:#x}',
                               len(matching_routes))
        route = matching_routes[0]
        require(route.get('switchTargetRva'), switch_target, source, tag)
        require(route.get('typeDefinition'), type_definition, source, tag)
        require(route.get('wrapperName'), wrapper_name, source, tag)
        operands = route.get('operands')
        if not isinstance(operands, list) or len(operands) != 1:
            raise ContextError(source, tag, 'one exact tag-to-wrapper type-usage operand', operands)
        require((operands[0].get('usageTag'), operands[0].get('registeredTypeIndex')),
                (1, usage_index), source, tag)

        methods = reader.get('methods')
        if not isinstance(methods, list):
            raise ContextError(source, tag, 'selected D5/D6 Deserialize module/token row', methods)
        selected_methods = [row for row in methods if row.get('methodIndex') == method_index]
        if len(selected_methods) != 1:
            raise ContextError(source, tag, f'exactly one method row {method_index}', len(selected_methods))
        method = selected_methods[0]
        require((method.get('declaringType'), method.get('name'), method.get('image')),
                (wrapper_name, 'Deserialize', 'MemoryPack.Beyond.dll'), source, tag)
        require(reader.get('anonymousReadOrder', {}).get('member4'),
                ['boolean', 'scalar32', 'scalar32', 'scalar32'], source, tag)
        code_windows = reader.get('codeWindows')
        if not isinstance(code_windows, list):
            raise ContextError(source, tag, 'selected D5/D6 native code windows', code_windows)
        if not any((row.get('startRva'), row.get('endRva'), row.get('sha256')) ==
                   (start_rva, end_rva, window_sha) for row in code_windows):
            raise ContextError(source, tag,
                               'hash-pinned selected D5/D6 reader positive path through RET',
                               code_windows)
        action_union_reader_evidence_by_tag[tag] = {
            'tag': tag,
            'switchTargetRva': switch_target,
            'wrapperName': wrapper_name,
            'registeredTypeIndex': usage_index,
            'methodIndex': method_index,
            'codeWindow': {'startRva': start_rva, 'endRva': end_rva,
                           'sha256': window_sha},
            'anonymousReadOrder': reader['anonymousReadOrder']['member4'],
            'contractSha256': reader.get('contractSha256'),
        }

    require(witness.get('wholeSkillDataClassification'), 'ambiguous', source, 0)
    require(witness.get('wholeSkillDataExactClosedRecords'), 0, source, 0)
    count_fields = {row['offset']: row['signedI32']
                    for row in witness.get('countI32Fields', [])}
    map_records = [row for row in witness.get('completedNestedRecords', [])
                   if row.get('kind') == 'anonymous-ability-action-map']
    all_union_records = sorted(
        [row for row in witness.get('completedNestedRecords', [])
         if row.get('kind') == 'union'], key=lambda row: row['start'])
    non_null_union_records = [row for row in all_union_records
                              if row.get('tag') != 0xFF]
    d5d6_union_records = [row for row in non_null_union_records
                          if row.get('tag') in (0xD5, 0xD6)]
    observed_union_headers = witness.get('completedActionUnionHeaderObservations')
    if not isinstance(observed_union_headers, list):
        raise ContextError(source, witness.get('parserCursor'),
                           'completed action union header observations',
                           observed_union_headers)
    native_reader_evidence_by_tag = {}
    for record in non_null_union_records:
        tag = record.get('tag')
        if type(tag) is not int:
            raise ContextError(source, record.get('start', 0),
                               'completed action union with integer tag', record)
        reader = native_action_readers.get(tag)
        if reader is None:
            raise ContextError(source, record.get('start', 0),
                               'current selected native reader for every consumed non-null tag',
                               tag)
        evidence = skilldata_action_union_static_reader_evidence(
            tag, reader, buff_routes,
            gameassembly_image_base=gameassembly_image_base, source=source)
        native_reader_evidence_by_tag[tag] = evidence

    observed_ids = set()
    for observation in observed_union_headers:
        if not isinstance(observation, dict):
            raise ContextError(source, witness.get('parserCursor'),
                               'action union header observation object', observation)
        record = next((row for row in non_null_union_records
                       if (row.get('tag'), row.get('start'), row.get('end')) ==
                       (observation.get('tag'), observation.get('start'), observation.get('end'))),
                      None)
        if record is None:
            raise ContextError(source, observation.get('start', 0),
                               'header observation belongs to a completed union range',
                               observation)
        observation_id = (observation['tag'], observation['start'], observation['end'])
        if observation_id in observed_ids:
            raise ContextError(source, observation['start'],
                               'one member-header observation per completed union',
                               observation)
        observed_ids.add(observation_id)
        reader_evidence = native_reader_evidence_by_tag[observation['tag']]
        require(observation.get('memberHeaderValue'),
                reader_evidence['rootMemberCount'], source,
                observation.get('memberHeaderOffset', observation['start']))
        tag_width = observation.get('tagWidth')
        expected_tag_width = (3 if observation.get('tagPrefixByte') == 0xFA else 1)
        require(tag_width, expected_tag_width, source, observation['start'])
        tag_encoding_hex = observation.get('tagEncodingHex')
        if not isinstance(tag_encoding_hex, str):
            raise ContextError(source, observation['start'],
                               'raw one-byte or FA-prefixed extended tag encoding',
                               tag_encoding_hex)
        try:
            tag_encoding = bytes.fromhex(tag_encoding_hex)
        except ValueError as exc:
            raise ContextError(source, observation['start'],
                               'hexadecimal action tag encoding', tag_encoding_hex) from exc
        require(len(tag_encoding), expected_tag_width, source, observation['start'])
        require(tag_encoding[0],
                0xFA if expected_tag_width == 3 else observation['tag'],
                source, observation['start'])
        decoded_tag = (struct.unpack_from('<H', tag_encoding, 1)[0]
                       if expected_tag_width == 3 else tag_encoding[0])
        require(decoded_tag, observation['tag'], source, observation['start'])
        require(observation.get('memberHeaderOffset'),
                observation['start'] + tag_width, source, observation['start'])
    for record in non_null_union_records:
        record_id = (record.get('tag'), record.get('start'), record.get('end'))
        if record_id not in observed_ids:
            tag_width = 3 if record['tag'] == 0xFA or record['tag'] > 0xFF else 1
            require(record.get('end') - record.get('start'), tag_width + 1,
                    source, record.get('start', 0))

    for tag in (0xD5, 0xD6):
        if tag in native_reader_evidence_by_tag:
            native_reader_evidence_by_tag[tag].update(
                action_union_reader_evidence_by_tag[tag])
    action_union_reader_evidence = [
        native_reader_evidence_by_tag[tag]
        for tag in dict.fromkeys(row['tag'] for row in non_null_union_records)
    ]
    action_union_prefix_evidence = []

    if witness.get('status') == 'passive-list-consumed-to-conditional-static-end':
        next_count = witness.get('nextMemberCountPeekOnly')
        if not isinstance(next_count, dict):
            raise ContextError(source, witness.get('parserCursor'),
                               'non-advancing timelineActions count peek', next_count)
        require(next_count.get('fieldName'), 'timelineActions.count', source, 15)
        require(next_count.get('consumed'), False, source, 15)
        cursor = witness.get('parserCursor')
        map_lists = [row for row in witness.get('completedNestedRecords', [])
                     if row.get('kind') == 'anonymous-ability-action-map-list']
        require([(row.get('start'), row.get('end')) for row in map_lists],
                [(2, cursor)], source, 2)
        require(len(map_records), witness.get('passiveEventActionsListCount'), source, 0)
        if not non_null_union_records and cursor == 15:
            require(len(map_records), witness.get('passiveEventActionsListCount'), source, 0)
            require(count_fields.get(11), 0, source, 11)
            require(next_count.get('offset'), cursor, source, cursor)
            require(next_count.get('signedI32'), 0, source, cursor)
            expected_disposition = (
                'empty SequenceActionData array branch reaches the conditional passiveEventActions end; '
                'timelineActions remains unread')
        elif sorted((row.get('tag'), row.get('start'), row.get('end'))
                    for row in d5d6_union_records) == [
                        (0xD5, 20, 35), (0xD6, 51, 66)
                    ] and len(non_null_union_records) == 2:
            require([(row.get('tag'), row.get('start'), row.get('end'))
                     for row in d5d6_union_records],
                    [(0xD5, 20, 35), (0xD6, 51, 66)], source, 20)
            require(cursor, 68, source, 68)
            require(witness.get('passiveEventActionsListCount'), 2, source, 2)
            require(count_fields, {2: 2, 11: 1, 16: 1, 42: 1, 47: 1}, source, 2)
            require(sorted((row.get('start'), row.get('end')) for row in map_records),
                    [(6, 37), (37, 68)], source, 6)
            sequence_records = sorted(
                [(row.get('start'), row.get('end'))
                 for row in witness.get('completedNestedRecords', [])
                 if row.get('kind') == 'sequence'])
            require(sequence_records, [(15, 37), (46, 68)], source, 15)
            require(next_count.get('offset'), cursor, source, cursor)
            require(next_count.get('signedI32'), 0, source, cursor)
            expected_disposition = (
                'two D5/D6 child ranges and both SequenceActionData entries reach the conditional '
                'passiveEventActions list end; timelineActions count is peek-only')
        else:
            require(type(cursor) is int and 15 <= cursor <= witness.get('hardLimit'),
                    True, source, 0)
            require(next_count.get('offset'), cursor, source, cursor)
            opaque = witness.get('opaqueByteRanges')
            expected_opaque = ([] if cursor == witness.get('hardLimit') else [{
                'start': cursor,
                'end': witness.get('hardLimit'),
                'kind': 'unconsumed-actiongroup-and-skilldata-bytes',
            }])
            require(opaque, expected_opaque, source, cursor)
            expected_disposition = (
                f'{len(non_null_union_records)} non-null child unions align to their selected native readers; '
                f'{len(map_records)} AbilityActionMap entries reach the conditional passiveEventActions '
                f'list end at {cursor}; timelineActions remains peek-only')
    elif witness.get('status') == 'stopped-before-first-nonnull-action-union':
        cursor = witness.get('parserCursor')
        first_union = witness.get('firstUnconsumedActionUnionByte')
        if not isinstance(first_union, dict):
            raise ContextError(source, cursor, 'first unconsumed nested action-union byte', first_union)
        require(first_union.get('offset'), cursor, source, cursor)
        require(first_union.get('tag') not in native_action_readers, True, source, cursor)
        require(first_union.get('tag'), witness.get('parserError', {}).get('actual'), source, cursor)
        require(first_union.get('consumed'), False, source, cursor)
        require(first_union.get('firstByte') not in (0xFF,), True, source, cursor)
        parser_error = witness.get('parserError')
        if not isinstance(parser_error, dict):
            raise ContextError(source, cursor, 'opaque diagnostic for unverified tag', parser_error)
        require(parser_error.get('category'), 'opaque-union', source, cursor)
        require(parser_error.get('offset'), cursor, source, cursor)
        map_lists = [row for row in witness.get('completedNestedRecords', [])
                     if row.get('kind') == 'anonymous-ability-action-map-list']
        require(map_lists, [], source, cursor)
        for parent_kind in ('anonymous-ability-action-map', 'sequence'):
            crossing = [row for row in witness.get('completedNestedRecords', [])
                        if row.get('kind') == parent_kind and
                        row.get('start', cursor) <= cursor < row.get('end', cursor)]
            require(crossing, [], source, cursor)
        require(witness.get('nextMemberCountPeekOnly'), None, source, cursor)
        require(witness.get('opaqueByteRanges'), [{
            'start': cursor,
            'end': witness.get('hardLimit'),
            'kind': 'unconsumed-actiongroup-and-skilldata-bytes',
        }], source, cursor)
        expected_disposition = (
            'SequenceActionData stops before the first unverified non-null action tag; '
            'parent list remains incomplete')
    elif witness.get('status') == 'stopped-after-verified-action-prefix':
        prefix = witness.get('actionUnionPrefixStop')
        if not isinstance(prefix, dict):
            raise ContextError(source, witness.get('parserCursor'),
                               'bounded C9 action-union prefix-stop witness', prefix)
        tag = prefix.get('tag')
        if tag not in buff_action_prefixes:
            raise ContextError(source, prefix.get('start', 0),
                               'exact current static reader prefix for consumed action tag', tag)
        prefix_evidence = buff_action_prefixes[tag]
        require(tag, prefix_evidence.get('tag'), source, prefix.get('start', 0))
        require(prefix.get('memberHeader'), prefix_evidence.get('memberHeader'),
                source, prefix.get('start', 0))
        require(prefix.get('sourceReadWidthsAfterHeader'),
                prefix_evidence.get('prefixSourceReadWidthsAfterHeader'),
                source, prefix.get('start', 0))
        start = prefix.get('start')
        cursor = witness.get('parserCursor')
        require(type(start) is int and type(cursor) is int and cursor > start,
                True, source, start if type(start) is int else 0)
        require(cursor - start,
                prefix_evidence.get('prefixByteLengthIncludingTagAndMemberHeader'),
                source, start)
        require(prefix.get('end'), cursor, source, cursor)
        require(prefix.get('consumedUnionRecord'), False, source, start)
        require(prefix.get('nextSourceReadType'),
                prefix_evidence.get('nestedSequenceTypeName'), source, cursor)
        require(prefix.get('nextSourceReadOffset'), cursor, source, cursor)
        require(prefix.get('nextSourceReadConsumed'), False, source, cursor)
        next_lead = prefix.get('nextSourceReadFirstByte')
        if next_lead not in (None, 3, 0xFF):
            raise ContextError(source, cursor,
                               'peeked next SequenceActionData lead is header 3, null FF, or beyond hardLimit',
                               next_lead)
        prefix_ranges = [row for row in witness.get('consumedByteRanges', [])
                         if row.get('start', -1) >= start and
                         row.get('end', cursor + 1) <= cursor]
        require([(row.get('start'), row.get('end'), row.get('kind'))
                 for row in prefix_ranges], [
                     (start, start + 1, 'union-tag'),
                     (start + 1, start + 2, 'member-header'),
                     (start + 2, start + 3, 'anonymous-byte'),
                     (start + 3, start + 7, 'anonymous-scalar32'),
                     (start + 7, start + 11, 'anonymous-scalar32'),
                     (start + 11, start + 15, 'anonymous-scalar32'),
                     (start + 15, start + 16, 'anonymous-byte'),
                 ], source, start)
        require(not any(row.get('kind') == 'union' and row.get('start') == start
                        for row in witness.get('completedNestedRecords', [])),
                True, source, start)
        for parent_kind in ('anonymous-ability-action-map',
                            'anonymous-ability-action-map-list', 'sequence'):
            crossing = [row for row in witness.get('completedNestedRecords', [])
                        if row.get('kind') == parent_kind and
                        row.get('start', cursor) <= start < row.get('end', start)]
            require(crossing, [], source, start)
        require(witness.get('nextMemberCountPeekOnly'), None, source, cursor)
        require(witness.get('opaqueByteRanges'), ([] if cursor == witness.get('hardLimit') else [{
            'start': cursor,
            'end': witness.get('hardLimit'),
            'kind': 'unconsumed-actiongroup-and-skilldata-bytes',
        }]), source, cursor)
        action_union_prefix_evidence.append(prefix_evidence)
        expected_disposition = (
            f'C9 tag and member-eight scalar prefix [ {start}, {cursor} ) align with the current '
            'IfElse reader; stop before its first SequenceActionData generic call, leaving the union '
            'and enclosing map/list incomplete')
    else:
        raise ContextError(source, 0,
                           'one recognized closed-list or opaque-union ActionGroupData branch',
                           witness.get('status'))
    return {
        'status': 'conditional-static-reader-alignment',
        'inputSetSha256': witness.get('inputSetSha256'),
        'logicalFileIdentity': witness.get('logicalFileIdentity'),
        'logicalSha256': witness.get('logicalSha256'),
        'hardLimit': witness.get('hardLimit'),
        'parserCursor': witness.get('parserCursor'),
        'consumedByteRanges': witness.get('consumedByteRanges'),
        'opaqueByteRanges': witness.get('opaqueByteRanges'),
        'actionGroupDataMemberOrder': ['passiveEventActions', 'timelineActions'],
        'passiveEventActionsElementType': 'Beyond.Gameplay.Core.AbilityActionMap',
        'abilityActionMapMemberOrder': ['scalar32', 'nullable-sequence-array'],
        'sequenceActionDataReaderEvidence': {
            'methodSpecIndex': sequence_contexts[0]['methodSpecIndex'],
            'headerCountWindowRva': sequence_header_window[0]['rva'],
            'headerCountWindowRawHex': sequence_header_window[0]['rawHex'],
        },
        'abilityActionUnionReaderEvidence': action_union_reader_evidence,
        'verifiedActionUnionReaderTags': [row['tag'] for row in action_union_reader_evidence],
        'abilityActionUnionPrefixReaderEvidence': action_union_prefix_evidence,
        'verifiedActionUnionPrefixTags': [row['tag'] for row in action_union_prefix_evidence],
        'completedActionUnionRanges': [
            {'tag': row['tag'], 'start': row['start'], 'end': row['end']}
            for row in non_null_union_records],
        'completedD5D6UnionRanges': [
            {'tag': row['tag'], 'start': row['start'], 'end': row['end']}
            for row in d5d6_union_records],
        'conditionalDisposition': expected_disposition,
        'runtimeProviderCacheSelection': 'unobserved',
        'actionGroupDataExactClosedRecords': 0,
        'wholeSkillDataClassification': 'ambiguous',
        'wholeSkillDataExactClosedRecords': 0,
        'boundary': ('The raw ActionGroupData passive-action samples align with current-build registered wrapper '
                     'routes and hash-pinned action readers, including the observed child member-header counts. '
                     'Child ranges and passiveEventActions list ends remain conditional static-reader evidence; '
                     'unknown tags stop at their first byte. Provider/cache selection is unobserved, timelineActions '
                     'is only peeked, and neither ActionGroupData nor whole SkillData is promoted.'),
    }


def skilldata_terminal_collision_evidence(
        corpus, *, source,
        logical_path='Data/Json/SkillData/Potential_test.json'):
    """Validate one current EOF collision and keep its candidate byte tilings.

    This checks the authenticated VFS corpus report, not source bytes or a live
    reader cursor.  It makes no decision between candidates.
    """
    input_set = corpus.get('inputSetSha256')
    if not isinstance(input_set, str) or len(input_set) != 64:
        raise ContextError(source, 0, 'current 64-hex SkillData inputSetSha256', input_set)
    rows = [row for row in corpus.get('files', [])
            if isinstance(row, dict) and row.get('virtualPath') == logical_path]
    if len(rows) != 1:
        raise ContextError(source, 0, f'exactly one current VFS row for {logical_path!r}',
                           len(rows))
    row = rows[0]

    def check(actual, expected, field, offset=0):
        if actual != expected:
            raise ContextError(source, offset, f'{logical_path}.{field} == {expected!r}', actual)

    def integer(value, field, offset=0):
        if type(value) is int and value >= 0:
            return value
        if isinstance(value, str):
            try:
                parsed = int(value, 0)
            except ValueError:
                parsed = -1
            if parsed >= 0:
                return parsed
        raise ContextError(source, offset, f'{logical_path}.{field} is a nonnegative byte offset',
                           value)

    def check_hash(value, field):
        if (not isinstance(value, str) or len(value) != 64 or
                any(ch not in '0123456789abcdefABCDEF' for ch in value)):
            raise ContextError(source, 0, f'{logical_path}.{field} is a 64-hex SHA-256',
                               value)

    def check_context(context, field, *, start, cursor, hard_limit, logical_sha):
        if not isinstance(context, dict):
            raise ContextError(source, 0, f'{logical_path}.{field} is an identity context',
                               type(context).__name__)
        check(context.get('inputSetSha256'), input_set, f'{field}.inputSetSha256')
        check(context.get('logicalFileIdentity'), logical_path,
              f'{field}.logicalFileIdentity')
        check(context.get('logicalSha256'), logical_sha, f'{field}.logicalSha256')
        check(context.get('startOffset'), start, f'{field}.startOffset')
        check(context.get('hardLimit'), hard_limit, f'{field}.hardLimit')
        check(context.get('parserCursor'), cursor, f'{field}.parserCursor')

    def tile(ranges, start, end, field):
        if not isinstance(ranges, list):
            raise ContextError(source, start, f'{logical_path}.{field} is a byte-range list',
                               type(ranges).__name__)
        cursor = start
        for index, span in enumerate(ranges):
            if not isinstance(span, dict):
                raise ContextError(source, cursor,
                                   f'{logical_path}.{field}[{index}] is a byte range', span)
            range_start, range_end = span.get('start'), span.get('end')
            if (type(range_start) is not int or type(range_end) is not int or
                    range_start != cursor or range_end <= range_start or range_end > end):
                raise ContextError(source, cursor,
                                   f'{logical_path}.{field}[{index}] continues [{start},{end})',
                                   span)
            cursor = range_end
        if cursor != end:
            raise ContextError(source, cursor,
                               f'{logical_path}.{field} tiles [{start},{end})', cursor)

    logical_sha = row.get('logicalSha256')
    check_hash(logical_sha, 'logicalSha256')
    check(row.get('boundaryClass'), 'ambiguous', 'boundaryClass')
    hard_limit = row.get('hardLimit')
    if type(hard_limit) is not int or hard_limit <= 0:
        raise ContextError(source, 0, f'{logical_path}.hardLimit is a positive byte limit',
                           hard_limit)
    parser_cursor = row.get('parserCursor')
    if type(parser_cursor) is not int or not (0 < parser_cursor < hard_limit):
        raise ContextError(source, 0,
                           f'{logical_path}.parserCursor is inside [0,{hard_limit})',
                           parser_cursor)
    check_context(row.get('boundaryContext'), 'boundaryContext', start=0,
                  cursor=parser_cursor, hard_limit=hard_limit, logical_sha=logical_sha)

    prefix = row.get('commonPrefixFraming')
    if not isinstance(prefix, dict):
        raise ContextError(source, 0, f'{logical_path}.commonPrefixFraming is present',
                           type(prefix).__name__)
    check(prefix.get('parserCursor'), parser_cursor, 'commonPrefixFraming.parserCursor')
    check(prefix.get('hardLimit'), hard_limit, 'commonPrefixFraming.hardLimit')
    check(integer(prefix.get('cursorOffset'), 'commonPrefixFraming.cursorOffset'),
          parser_cursor, 'commonPrefixFraming.cursorOffset')
    check_context(prefix.get('boundaryContext'), 'commonPrefixFraming.boundaryContext',
                  start=0, cursor=parser_cursor, hard_limit=hard_limit,
                  logical_sha=logical_sha)
    tile(prefix.get('byteRanges'), 0, parser_cursor, 'commonPrefixFraming.byteRanges')

    framing = row.get('framing')
    if not isinstance(framing, dict):
        raise ContextError(source, 0, f'{logical_path}.framing is present',
                           type(framing).__name__)
    check(framing.get('status'), 'ambiguous-exact-terminal-shape', 'framing.status')
    check(framing.get('memberCount'), 48, 'framing.memberCount')
    check(framing.get('wholeSchemaExact'), False, 'framing.wholeSchemaExact')
    check(framing.get('serializedFieldOrderStatus'), 'unresolved',
          'framing.serializedFieldOrderStatus')
    ambiguity = framing.get('ambiguity')
    if not isinstance(ambiguity, dict):
        raise ContextError(source, 0, f'{logical_path}.framing.ambiguity is present',
                           type(ambiguity).__name__)
    check(ambiguity.get('kind'), 'one-byte-bool-vs-counted-wrapper-collision',
          'framing.ambiguity.kind')
    check(ambiguity.get('resolutionStatus'), 'unresolved-both-exact-to-eof',
          'framing.ambiguity.resolutionStatus')
    check(ambiguity.get('sharedCountedRecordCounts'), [0, 0, 0],
          'framing.ambiguity.sharedCountedRecordCounts')

    candidates = framing.get('candidates')
    if not isinstance(candidates, list) or len(candidates) != 2:
        raise ContextError(source, parser_cursor,
                           f'{logical_path}.framing.candidates has exactly two shapes',
                           type(candidates).__name__ if not isinstance(candidates, list)
                           else len(candidates))
    check(framing.get('candidateCount'), len(candidates), 'framing.candidateCount')
    evidence_candidates = []
    normalized_starts = []
    expected_shape = [
        'bool', 'counted-member-record-list',
        'counted-nested-object-list-a', 'counted-nested-object-list-b', 'bool',
    ]
    for index, candidate in enumerate(candidates):
        field = f'framing.candidates[{index}]'
        if not isinstance(candidate, dict):
            raise ContextError(source, parser_cursor, f'{logical_path}.{field} is an object',
                               type(candidate).__name__)
        start = integer(candidate.get('startOffset'), f'{field}.startOffset', parser_cursor)
        end = integer(candidate.get('endOffset'), f'{field}.endOffset', start)
        expected_start = 518 + index
        check(start, expected_start, f'{field}.startOffset', start)
        if not (parser_cursor <= start < end == hard_limit):
            raise ContextError(source, start,
                               f'{logical_path}.{field} is EOF-anchored inside [{parser_cursor},{hard_limit})',
                               [start, end])
        check(candidate.get('status'), 'exact-eof-anchored-terminal-shape', f'{field}.status',
              start)
        check(candidate.get('exactToEof'), True, f'{field}.exactToEof', start)
        check(candidate.get('byteLength'), end - start, f'{field}.byteLength', start)
        check(candidate.get('parserCursor'), end, f'{field}.parserCursor', start)
        check(candidate.get('hardLimit'), hard_limit, f'{field}.hardLimit', start)
        check(candidate.get('boundaryClass'), 'ambiguous', f'{field}.boundaryClass', start)
        candidate_range = candidate.get('candidateRange')
        if not isinstance(candidate_range, dict):
            raise ContextError(source, start, f'{logical_path}.{field}.candidateRange is an object',
                               candidate_range)
        check(candidate_range.get('start'), start, f'{field}.candidateRange.start', start)
        check(candidate_range.get('end'), end, f'{field}.candidateRange.end', start)
        check(candidate_range.get('endExclusive'), True,
              f'{field}.candidateRange.endExclusive', start)
        check_context(candidate.get('boundaryContext'), f'{field}.boundaryContext',
                      start=start, cursor=end, hard_limit=hard_limit,
                      logical_sha=logical_sha)
        check(candidate.get('boundaryContext', {}).get('candidateRange'), [start, end],
              f'{field}.boundaryContext.candidateRange', start)

        shape = candidate.get('shape')
        check(shape, expected_shape, f'{field}.shape', start)
        members = candidate.get('members')
        if not isinstance(members, list) or len(members) != len(expected_shape):
            raise ContextError(source, start,
                               f'{logical_path}.{field}.members has five entries',
                               type(members).__name__ if not isinstance(members, list)
                               else len(members))
        byte_ranges = candidate.get('byteRanges')
        tile(byte_ranges, start, end, f'{field}.byteRanges')
        if len(byte_ranges) != len(members):
            raise ContextError(source, start,
                               f'{logical_path}.{field}.byteRanges has one range per member',
                               [len(byte_ranges), len(members)])
        expected_member_ranges = (
            (start, start + 1),
            (519 if index == 0 else 520, 524),
            (524, 528),
            (528, 532),
            (532, 533),
        )
        for member_index, (member, byte_range) in enumerate(zip(members, byte_ranges)):
            if not isinstance(member, dict) or not isinstance(byte_range, dict):
                raise ContextError(source, start,
                                   f'{logical_path}.{field}.members[{member_index}] and byte range are objects',
                                   [type(member).__name__, type(byte_range).__name__])
            member_range = member.get('range')
            if not isinstance(member_range, dict):
                raise ContextError(source, start,
                                   f'{logical_path}.{field}.members[{member_index}].range is an object',
                                   member_range)
            expected_member_start, expected_member_end = expected_member_ranges[member_index]
            expected_member_range = {
                'start': expected_member_start,
                'end': expected_member_end,
                'byteLength': expected_member_end - expected_member_start,
            }
            check(member_range, expected_member_range,
                  f'{field}.members[{member_index}].range', start)
            check(byte_range.get('start'), member_range.get('start'),
                  f'{field}.byteRanges[{member_index}].start', start)
            check(byte_range.get('end'), member_range.get('end'),
                  f'{field}.byteRanges[{member_index}].end', start)
            check(byte_range.get('kind'), member.get('kind'),
                  f'{field}.byteRanges[{member_index}].kind', start)
            check(byte_range.get('memberIndex'), member_index,
                  f'{field}.byteRanges[{member_index}].memberIndex', start)
        check(members[0].get('kind'), 'bool', f'{field}.members[0].kind', start)
        check(members[0].get('range'), {
            'start': start, 'end': start + 1, 'byteLength': 1,
        }, f'{field}.members[0].range', start)
        check(members[0].get('value'), index == 1, f'{field}.members[0].value', start)
        check(candidate.get('encoding'), 'one-member-wrapper' if index == 0 else 'counted',
              f'{field}.encoding', start)
        list_member = members[1]
        check(list_member.get('kind'), 'counted-member-record-list',
              f'{field}.members[1].kind', start)
        check(list_member.get('count'), 0, f'{field}.members[1].count', start)
        check(list_member.get('encoding'), 'one-member-wrapper' if index == 0 else 'counted',
              f'{field}.members[1].encoding', start)
        wrapper = list_member.get('wrapperRange')
        if index == 0:
            check(wrapper, {'start': start + 1, 'end': start + 2, 'byteLength': 1},
                  f'{field}.members[1].wrapperRange', start)
        else:
            check(wrapper, None, f'{field}.members[1].wrapperRange', start)
        count_range = list_member.get('countRange')
        if not isinstance(count_range, dict):
            raise ContextError(source, start, f'{logical_path}.{field}.members[1].countRange is an object',
                               count_range)
        check(count_range.get('start'), 520, f'{field}.members[1].countRange.start', start)
        check(count_range.get('end'), 524, f'{field}.members[1].countRange.end', start)
        for member_index in (2, 3):
            nested = members[member_index]
            check(nested.get('kind'), 'counted-nested-object-list',
                  f'{field}.members[{member_index}].kind', start)
            check(nested.get('count'), 0, f'{field}.members[{member_index}].count', start)
            nested_range = nested.get('range')
            nested_count_range = nested.get('countRange')
            if not isinstance(nested_range, dict) or not isinstance(nested_count_range, dict):
                raise ContextError(source, start,
                                   f'{logical_path}.{field}.members[{member_index}] has bounded range objects',
                                   [nested_range, nested_count_range])
            check(nested_range, nested_count_range,
                  f'{field}.members[{member_index}].range equals countRange', start)
            check(nested_range.get('byteLength'), 4,
                  f'{field}.members[{member_index}].range.byteLength', start)
        final_member = members[4]
        check(final_member.get('kind'), 'bool', f'{field}.members[4].kind', start)
        check(final_member.get('value'), False, f'{field}.members[4].value', start)
        check(final_member.get('range'), {
            'start': hard_limit - 1, 'end': hard_limit, 'byteLength': 1,
        }, f'{field}.members[4].range', start)
        opaque = candidate.get('opaqueByteRanges')
        check(opaque, [{
            'start': parser_cursor, 'end': start,
            'kind': 'opaque-between-prefix-and-terminal-candidate',
        }], f'{field}.opaqueByteRanges', start)
        normalized_starts.append(start)
        evidence_candidates.append({
            'encoding': candidate.get('encoding'),
            'start': start,
            'end': end,
            'byteLength': end - start,
            'parserCursor': end,
            'hardLimit': hard_limit,
            'boundaryContext': candidate.get('boundaryContext'),
            'candidateRange': candidate_range,
            'classification': candidate.get('boundaryClass'),
            'byteRanges': byte_ranges,
            'opaqueByteRanges': opaque,
            'terminalMembers': members,
        })

    check(normalized_starts[1] - normalized_starts[0], 1,
          'framing.candidates are shifted by one byte', normalized_starts[0])
    starts_as_hex = [candidate.get('startOffset') for candidate in candidates]
    check(ambiguity.get('candidateStartOffsets'), starts_as_hex,
          'framing.ambiguity.candidateStartOffsets', normalized_starts[0])
    if evidence_candidates[0]['terminalMembers'][2:] != evidence_candidates[1]['terminalMembers'][2:]:
        raise ContextError(source, normalized_starts[0],
                           f'{logical_path}.framing.candidates share the final three member ranges',
                           'different suffix manifests')

    envelope = framing.get('envelope')
    if not isinstance(envelope, dict):
        raise ContextError(source, 0, f'{logical_path}.framing.envelope is present',
                           type(envelope).__name__)
    check(integer(envelope.get('startOffset'), 'framing.envelope.startOffset'), 0,
          'framing.envelope.startOffset')
    check(integer(envelope.get('endOffset'), 'framing.envelope.endOffset'), hard_limit,
          'framing.envelope.endOffset', hard_limit)
    check(envelope.get('byteLength'), hard_limit, 'framing.envelope.byteLength')

    return {
        'inputSetSha256': input_set,
        'logicalFileIdentity': logical_path,
        'logicalSha256': logical_sha,
        'sourceRange': {'start': 0, 'end': hard_limit, 'endExclusive': True},
        'parserCursor': parser_cursor,
        'hardLimit': hard_limit,
        'consumedPrefixByteRanges': prefix.get('byteRanges'),
        'candidates': evidence_candidates,
        'classification': 'ambiguous',
        'resolutionStatus': ambiguity.get('resolutionStatus'),
        'sharedCountedRecordCounts': ambiguity.get('sharedCountedRecordCounts'),
        'exactClosedRecords': 0,
        'boundary': 'Both candidate byte tilings reach the same hard limit and remain ambiguous. This is a cross-check of the current VFS corpus report; it does not establish which terminal shape the selected runtime reader consumed.',
    }


def skilldata_terminal_sample_byte_witness(collision, raw, *, source):
    """Recheck the selected logical file's terminal bytes against the report."""
    logical_path = collision.get('logicalFileIdentity')
    logical_sha = collision.get('logicalSha256')
    hard_limit = collision.get('hardLimit')
    input_set = collision.get('inputSetSha256')
    if not isinstance(raw, bytes):
        raise ContextError(source, 0, 'raw current SkillData logical bytes', type(raw).__name__)
    if type(hard_limit) is not int or len(raw) != hard_limit:
        raise ContextError(source, 0, f'{logical_path} byte length equals hardLimit {hard_limit}',
                           len(raw))
    digest = hashlib.sha256(raw).hexdigest().upper()
    if digest != logical_sha:
        raise ContextError(source, 0, f'{logical_path} SHA-256 equals corpus identity',
                           digest)
    candidates = collision.get('candidates')
    if not isinstance(candidates, list) or len(candidates) != 2:
        raise ContextError(source, 0, f'{logical_path} retains both terminal candidates',
                           type(candidates).__name__ if not isinstance(candidates, list)
                           else len(candidates))
    first, shifted = candidates
    start = first.get('start')
    end = first.get('end')
    if type(start) is not int or type(end) is not int or end != hard_limit or end - start != 15:
        raise ContextError(source, 0, f'{logical_path} first candidate is 15 bytes to hardLimit',
                           [start, end, hard_limit])
    if shifted.get('start') != start + 1 or shifted.get('end') != hard_limit:
        raise ContextError(source, start,
                           f'{logical_path} second candidate begins one byte later and shares EOF',
                           [shifted.get('start'), shifted.get('end')])
    if end - start > len(raw) - start:
        raise ContextError(source, start, f'{logical_path} candidate lies inside raw source',
                           [start, end, len(raw)])

    first_bool = raw[start]
    wrapper_member_count = raw[start + 1]
    count_offsets = [start + 2, start + 6, start + 10]
    counts = []
    for offset in count_offsets:
        if offset + 4 > end:
            raise ContextError(source, offset, 'four-byte terminal list count inside hardLimit',
                               [offset, end])
        counts.append(struct.unpack_from('<i', raw, offset)[0])
    final_bool = raw[end - 1]
    if first_bool not in (0, 1) or final_bool not in (0, 1):
        raise ContextError(source, start,
                           'terminal boolean bytes are normalized zero or one',
                           [first_bool, final_bool])
    if wrapper_member_count != 1:
        raise ContextError(source, start + 1,
                           'GameplayTagList member header is one',
                           wrapper_member_count)
    if counts != [0, 0, 0]:
        raise ContextError(source, count_offsets[0],
                           'current terminal sample contains three signed zero counts',
                           counts)
    members = first.get('terminalMembers')
    if not isinstance(members, list) or len(members) != 5:
        raise ContextError(source, start, 'first candidate preserves five terminal members',
                           type(members).__name__ if not isinstance(members, list)
                           else len(members))
    if members[0].get('value') != bool(first_bool) or members[4].get('value') != bool(final_bool):
        raise ContextError(source, start,
                           'raw first/final booleans match the current candidate parse',
                           [first_bool, final_bool])
    shifted_members = shifted.get('terminalMembers')
    if (not isinstance(shifted_members, list) or len(shifted_members) != 5 or
            shifted_members[0].get('value') != bool(wrapper_member_count)):
        raise ContextError(source, start + 1,
                           'shifted candidate interprets the wrapper byte as its first boolean',
                           shifted_members)
    return {
        'inputSetSha256': input_set,
        'logicalFileIdentity': logical_path,
        'logicalSha256': digest,
        'byteLength': len(raw),
        'hardLimit': hard_limit,
        'candidateRange': {'start': start, 'end': end, 'endExclusive': True},
        'parserCursor': end,
        'terminalRawHex': raw[start:end].hex().upper(),
        'firstBooleanByte': {'offset': start, 'value': bool(first_bool)},
        'nestedMemberCountByte': {'offset': start + 1, 'value': wrapper_member_count},
        'signedListCounts': [
            {'offset': offset, 'value': count}
            for offset, count in zip(count_offsets, counts)
        ],
        'finalBooleanByte': {'offset': end - 1, 'value': bool(final_bool)},
        'boundary': 'The source bytes and corpus row agree for this logical identity and hard limit; this byte witness alone does not select a runtime formatter.',
    }


def select_skilldata_terminal_branch_samples(corpus, *, source):
    """Choose deterministic current files for every observed positive tail-list count."""
    input_set = corpus.get('inputSetSha256')
    if (not isinstance(input_set, str) or len(input_set) != 64 or
            any(ch not in '0123456789abcdefABCDEF' for ch in input_set)):
        raise ContextError(source, 0, '64-hex SkillData inputSetSha256', input_set)
    files = corpus.get('files')
    if not isinstance(files, list):
        raise ContextError(source, 0, 'current SkillData file row list', type(files).__name__)
    branch_fields = {
        1: 'tagDuringAttach.predefinedTag',
        2: 'toggleBuffs',
        3: 'uiRangeHints',
    }
    requirements = []
    for member_index, field_name in branch_fields.items():
        observed_counts = set()
        for row in files:
            if not isinstance(row, dict):
                continue
            candidates = row.get('framing', {}).get('candidates', [])
            if (not isinstance(candidates, list) or len(candidates) != 2 or
                    candidates[0].get('encoding') != 'one-member-wrapper'):
                continue
            members = candidates[0].get('members', [])
            if not isinstance(members, list) or len(members) != 5:
                continue
            count = members[member_index].get('count')
            if type(count) is int and count > 0:
                observed_counts.add(count)
        if not observed_counts:
            raise ContextError(source, 0,
                               f'current corpus has a positive {field_name} branch', 0)
        requirements.extend(
            {'fieldName': field_name, 'memberIndex': member_index, 'count': count}
            for count in sorted(observed_counts)
        )
    selected = []
    for requirement in requirements:
        matches = []
        for row in files:
            if not isinstance(row, dict):
                continue
            candidates = row.get('framing', {}).get('candidates', [])
            if not isinstance(candidates, list) or len(candidates) != 2:
                continue
            members = candidates[0].get('members', [])
            index = requirement['memberIndex']
            if (candidates[0].get('encoding') == 'one-member-wrapper' and
                    isinstance(members, list) and len(members) == 5 and
                    isinstance(members[index], dict) and
                    members[index].get('count') == requirement['count']):
                matches.append(row)
        if not matches:
            raise ContextError(source, 0,
                               f'current corpus has a positive {requirement["fieldName"]} branch with count {requirement["count"]}',
                               0)
        selected.append({**requirement, 'row': matches[0]})
    if len({sample['row'].get('virtualPath') for sample in selected}) != len(selected):
        raise ContextError(source, 0, 'distinct current SkillData branch sample identities',
                           [sample['row'].get('virtualPath') for sample in selected])
    return selected


def skilldata_shifted_terminal_wrapper_probe(raw, first_candidate_start,
                                             hard_limit, *, source):
    """Record how a one-byte-shifted SkillData tail reaches GameplayTagList."""
    if not isinstance(raw, bytes):
        raise ContextError(source, 0, 'raw sample bytes', type(raw).__name__)
    if (type(first_candidate_start) is not int or first_candidate_start < 0 or
            type(hard_limit) is not int or hard_limit != len(raw) or
            first_candidate_start + 1 >= hard_limit):
        raise ContextError(source, first_candidate_start
                           if type(first_candidate_start) is int else 0,
                           'first candidate start and hardLimit bound the raw sample',
                           [first_candidate_start, hard_limit, len(raw)])
    shifted_start = first_candidate_start + 1
    wrapper_offset = shifted_start + 1
    if wrapper_offset >= hard_limit:
        raise ContextError(source, wrapper_offset,
                           'shifted candidate has an in-limit GameplayTagList header',
                           hard_limit)
    header = raw[wrapper_offset]
    result = {
        'shiftedCandidateStart': shifted_start,
        'shiftedBooleanByte': {'offset': shifted_start,
                               'value': raw[shifted_start]},
        'gameplayTagListHeaderByte': {'offset': wrapper_offset,
                                      'value': header},
        'nestedListCount': None,
    }
    if header == 1:
        count_offset = wrapper_offset + 1
        count_end = count_offset + 4
        available = max(0, min(4, hard_limit - count_offset))
        count_bytes = raw[count_offset:count_offset + available]
        count_row = {
            'offset': count_offset,
            'availableByteLength': available,
            'rawHex': count_bytes.hex().upper(),
            'complete': available == 4,
        }
        if available == 4:
            count_row.update({
                'signedI32': struct.unpack('<i', count_bytes)[0],
                'remainingAfterCount': hard_limit - count_end,
            })
        result['nestedListCount'] = count_row
    return result


def skilldata_terminal_branch_sample_witness(corpus, selection, raw, *, source):
    """Reparse two EOF hypotheses from a byte-authenticated nonempty branch sample."""
    if not isinstance(selection, dict) or not isinstance(selection.get('row'), dict):
        raise ContextError(source, 0, 'selected SkillData branch row', selection)
    row = selection['row']
    logical_path = row.get('virtualPath')
    logical_sha = row.get('logicalSha256')
    input_set = corpus.get('inputSetSha256')
    corpus_rows = [candidate for candidate in corpus.get('files', [])
                   if isinstance(candidate, dict) and
                   candidate.get('virtualPath') == logical_path]
    if len(corpus_rows) != 1 or corpus_rows[0] != row:
        raise ContextError(source, 0, 'selected row is the unique current corpus identity',
                           [len(corpus_rows), logical_path])
    if not isinstance(logical_path, str) or not logical_path.startswith(
            'Data/Json/SkillData/'):
        raise ContextError(source, 0, 'logical SkillData sample identity', logical_path)
    if (not isinstance(input_set, str) or len(input_set) != 64 or
            any(ch not in '0123456789abcdefABCDEF' for ch in input_set)):
        raise ContextError(source, 0, '64-hex current SkillData inputSetSha256', input_set)
    if (not isinstance(logical_sha, str) or len(logical_sha) != 64 or
            any(ch not in '0123456789abcdefABCDEF' for ch in logical_sha)):
        raise ContextError(source, 0, '64-hex logical sample SHA-256', logical_sha)
    if (not isinstance(raw, bytes) or type(row.get('hardLimit')) is not int or
            len(raw) != row['hardLimit']):
        raise ContextError(source, 0, 'sample byte length equals current hardLimit',
                           [len(raw) if isinstance(raw, bytes) else type(raw).__name__,
                            row.get('hardLimit')])
    digest = hashlib.sha256(raw).hexdigest().upper()
    if digest != logical_sha:
        raise ContextError(source, 0, 'sample bytes match current logical SHA-256',
                           [logical_sha, digest])
    hard_limit = row['hardLimit']
    parser_cursor = row.get('parserCursor')
    context = row.get('boundaryContext')
    if type(parser_cursor) is not int or not 0 < parser_cursor < hard_limit:
        raise ContextError(source, 0, 'current structural prefix cursor inside hardLimit',
                           parser_cursor)
    for field, expected in (
            ('inputSetSha256', input_set), ('logicalFileIdentity', logical_path),
            ('logicalSha256', logical_sha), ('parserCursor', parser_cursor),
            ('hardLimit', hard_limit)):
        if not isinstance(context, dict) or context.get(field) != expected:
            raise ContextError(source, 0, f'boundaryContext.{field} matches current sample',
                               context.get(field) if isinstance(context, dict) else context)
    if row.get('boundaryClass') != 'ambiguous':
        raise ContextError(source, 0, 'branch sample remains corpus-classified ambiguous',
                           row.get('boundaryClass'))
    framing = row.get('framing')
    candidates = framing.get('candidates') if isinstance(framing, dict) else None
    if not isinstance(candidates, list) or len(candidates) != 2:
        raise ContextError(source, 0, 'two EOF-anchored branch candidates', candidates)
    first, shifted = candidates
    def offset(value, field):
        if type(value) is int and value >= 0:
            return value
        if isinstance(value, str):
            try:
                parsed = int(value, 0)
            except ValueError:
                parsed = -1
            if parsed >= 0:
                return parsed
        raise ContextError(source, 0, f'{field} is a bounded byte offset', value)

    start = offset(first.get('startOffset'), 'candidate[0].startOffset')
    shifted_start = offset(shifted.get('startOffset'), 'candidate[1].startOffset')
    if (shifted_start != start + 1 or start < parser_cursor or
            offset(first.get('endOffset'), 'candidate[0].endOffset') != hard_limit or
            offset(shifted.get('endOffset'), 'candidate[1].endOffset') != hard_limit or
            first.get('encoding') != 'one-member-wrapper' or
            shifted.get('encoding') != 'counted'):
        raise ContextError(source, start,
                           'wrapper/count candidates are shifted one byte and share hardLimit',
                           [first.get('startOffset'), shifted.get('startOffset'),
                            first.get('endOffset'), shifted.get('endOffset'),
                            first.get('encoding'), shifted.get('encoding')])
    for candidate_index, (candidate, candidate_start) in enumerate(
            ((first, start), (shifted, shifted_start))):
        candidate_context = candidate.get('boundaryContext')
        expected_candidate_range = [candidate_start, hard_limit]
        for field, expected in (
                ('inputSetSha256', input_set),
                ('logicalFileIdentity', logical_path),
                ('logicalSha256', logical_sha),
                ('startOffset', candidate_start),
                ('hardLimit', hard_limit),
                ('parserCursor', hard_limit),
                ('candidateRange', expected_candidate_range)):
            if (not isinstance(candidate_context, dict) or
                    candidate_context.get(field) != expected):
                raise ContextError(source, candidate_start,
                                   f'candidate[{candidate_index}].boundaryContext.{field} matches current sample',
                                   candidate_context.get(field)
                                   if isinstance(candidate_context, dict)
                                   else candidate_context)

    def tile(ranges, begin, end, label):
        if not isinstance(ranges, list):
            raise ContextError(source, begin, f'{label} is a bounded byte-range list',
                               type(ranges).__name__)
        cursor = begin
        for index, span in enumerate(ranges):
            if (not isinstance(span, dict) or type(span.get('start')) is not int or
                    type(span.get('end')) is not int or span['start'] != cursor or
                    span['end'] <= span['start'] or span['end'] > end):
                raise ContextError(source, cursor, f'{label}[{index}] continues [{begin},{end})',
                                   span)
            cursor = span['end']
        if cursor != end:
            raise ContextError(source, cursor, f'{label} tiles [{begin},{end})', cursor)

    def replay(candidate_report, candidate_start, expected_encoding):
        try:
            parsed_report = frame_skill_terminal_at(
                raw, candidate_start, source=logical_path)
        except SkillTerminalError as error:
            raise ContextError(source, candidate_start,
                               f'current raw sample reparses {expected_encoding} candidate',
                               error.diagnostics) from error
        parsed = [candidate for candidate in parsed_report.get('candidates', [])
                  if candidate.get('encoding') == expected_encoding and
                  candidate.get('end') == hard_limit]
        if len(parsed) != 1:
            raise ContextError(source, candidate_start,
                               f'one raw-parsed {expected_encoding} candidate ends at hardLimit',
                               [(candidate.get('encoding'), candidate.get('end'))
                                for candidate in parsed_report.get('candidates', [])])
        parsed_candidate = parsed[0]
        if (candidate_report.get('boundaryClass') != 'ambiguous' or
                candidate_report.get('exactToEof') is not True or
                candidate_report.get('parserCursor') != hard_limit or
                candidate_report.get('hardLimit') != hard_limit):
            raise ContextError(source, candidate_start,
                               'corpus candidate remains ambiguous and ends exactly at hardLimit',
                               candidate_report)
        candidate_range = candidate_report.get('candidateRange')
        if (not isinstance(candidate_range, dict) or
                candidate_range.get('start') != candidate_start or
                candidate_range.get('end') != hard_limit or
                candidate_range.get('endExclusive') is not True):
            raise ContextError(source, candidate_start,
                               'candidate range equals raw parser [start,hardLimit)',
                               candidate_range)
        if (parsed_candidate.get('start') != candidate_start or
                parsed_candidate.get('byteLength') != hard_limit - candidate_start):
            raise ContextError(source, candidate_start, 'raw parser candidate byte span',
                               [parsed_candidate.get('start'), parsed_candidate.get('end')])
        report_members = candidate_report.get('members')
        parsed_members = parsed_candidate.get('members')
        if (not isinstance(report_members, list) or len(report_members) != 5 or
                not isinstance(parsed_members, list) or len(parsed_members) != 5):
            raise ContextError(source, candidate_start,
                               'five current terminal members in report and raw parse',
                               [report_members, parsed_members])
        for member_index, (reported, parsed_member) in enumerate(
                zip(report_members, parsed_members)):
            if reported.get('range') != parsed_member.get('range'):
                raise ContextError(source, candidate_start,
                                   f'candidate member {member_index} raw/report byte range',
                                   [reported.get('range'), parsed_member.get('range')])
            if 'count' in parsed_member and reported.get('count') != parsed_member.get('count'):
                raise ContextError(source, candidate_start,
                                   f'candidate member {member_index} raw/report count',
                                   [reported.get('count'), parsed_member.get('count')])
            report_records = reported.get('records', [])
            parsed_records = parsed_member.get('records', [])
            if len(report_records) != len(parsed_records):
                raise ContextError(source, candidate_start,
                                   f'candidate member {member_index} raw/report record count',
                                   [len(report_records), len(parsed_records)])
            for record_index, (reported_record, parsed_record) in enumerate(
                    zip(report_records, parsed_records)):
                if (reported_record.get('range') != parsed_record.get('range') or
                        reported_record.get('memberCount') != parsed_record.get('memberCount')):
                    raise ContextError(source, candidate_start,
                                       f'candidate member {member_index} record {record_index} raw/report range/header',
                                       [reported_record, parsed_record])
        byte_ranges = candidate_report.get('byteRanges')
        tile(byte_ranges, candidate_start, hard_limit,
             f'{logical_path} {expected_encoding} candidate byteRanges')
        if len(byte_ranges) != 5:
            raise ContextError(source, candidate_start,
                               'candidate byte-range manifest has five outer members',
                               len(byte_ranges))
        return parsed_candidate

    parsed_first = replay(first, start, 'one-member-wrapper')
    parsed_shifted = replay(shifted, shifted_start, 'counted')
    wrapper_header = raw[start + 1]
    if wrapper_header != 1:
        raise ContextError(source, start + 1, 'GameplayTagList one-member raw header', wrapper_header)
    if raw[start] not in (0, 1) or raw[hard_limit - 1] not in (0, 1):
        raise ContextError(source, start, 'terminal bool bytes are zero or one',
                           [raw[start], raw[hard_limit - 1]])
    if (first['members'][0].get('value') != bool(raw[start]) or
            first['members'][4].get('value') != bool(raw[hard_limit - 1]) or
            shifted['members'][0].get('value') != bool(wrapper_header)):
        raise ContextError(source, start, 'raw bool/header bytes match both shifted candidate parses',
                           [first['members'][0], shifted['members'][0], first['members'][4]])

    list_counts = []
    for member_index in (1, 2, 3):
        member = first['members'][member_index]
        count_range = member.get('countRange')
        if (not isinstance(count_range, dict) or type(count_range.get('start')) is not int or
                count_range.get('end') != count_range.get('start') + 4 or
                count_range['end'] > hard_limit):
            raise ContextError(source, start,
                               f'terminal member {member_index} has an in-limit four-byte count range',
                               count_range)
        raw_count = struct.unpack_from('<I', raw, count_range['start'])[0]
        count_value = None if member_index == 1 and raw_count == 0xFFFFFFFF else raw_count
        if count_value != member.get('count'):
            raise ContextError(source, count_range['start'],
                               f'terminal member {member_index} raw count matches report',
                               [member.get('count'), count_value])
        list_counts.append({
            'memberIndex': member_index,
            'fieldName': ('tagDuringAttach.predefinedTag' if member_index == 1 else
                          'toggleBuffs' if member_index == 2 else 'uiRangeHints'),
            'countRange': count_range,
            'count': count_value,
            'recordRanges': [record.get('range') for record in member.get('records', [])],
            'recordHeaderMemberCounts': [
                record.get('memberCount') for record in member.get('records', [])
            ],
        })
    member_index = selection.get('memberIndex')
    expected_count = selection.get('count')
    if member_index not in (1, 2, 3) or type(expected_count) is not int or expected_count <= 0:
        raise ContextError(source, 0, 'selected positive SkillData list branch',
                           [member_index, expected_count])
    branch_count = first['members'][member_index].get('count')
    if branch_count != expected_count:
        raise ContextError(source, start,
                           f'selected {selection.get("fieldName")} count is {expected_count}',
                           branch_count)
    return {
        'inputSetSha256': input_set,
        'logicalFileIdentity': logical_path,
        'logicalSha256': digest,
        'sourceRange': {'start': 0, 'end': hard_limit, 'endExclusive': True},
        'parserCursor': parser_cursor,
        'hardLimit': hard_limit,
        'terminalCandidateRanges': [
            {'start': start, 'end': hard_limit, 'endExclusive': True},
            {'start': shifted_start, 'end': hard_limit, 'endExclusive': True},
        ],
        'shiftedCandidateTypeProbe': skilldata_shifted_terminal_wrapper_probe(
            raw, start, hard_limit, source=source),
        'rawWrapperHeaderByte': {'offset': start + 1, 'value': wrapper_header},
        'terminalBooleanBytes': [
            {'offset': start, 'value': bool(raw[start])},
            {'offset': hard_limit - 1, 'value': bool(raw[hard_limit - 1])},
        ],
        'listCounts': list_counts,
        'positiveBranch': {
            'fieldName': selection['fieldName'],
            'memberIndex': member_index,
            'count': branch_count,
            'recordRanges': [record.get('range') for record in
                             first['members'][member_index].get('records', [])],
            'recordHeaderMemberCounts': [record.get('memberCount') for record in
                                         first['members'][member_index].get('records', [])],
        },
        'rawParserReplay': {
            'oneMemberWrapperCandidate': {
                'start': parsed_first['start'], 'end': parsed_first['end'],
                'encoding': parsed_first['encoding'],
            },
            'shiftedCountedCandidate': {
                'start': parsed_shifted['start'], 'end': parsed_shifted['end'],
                'encoding': parsed_shifted['encoding'],
            },
        },
        'classification': 'ambiguous',
        'staticShapeDisposition': 'wrapper candidate matches the exact SkillData tail order; shifted counted candidate conflicts with the one-member wrapper if registered paths are selected',
        'exactClosedRecords': 0,
        'boundary': 'Current raw bytes, parser replay and report ranges agree for this nonempty branch sample. Both shifted hypotheses still reach hardLimit; this does not observe provider selection or an executed native cursor, and record internals remain anonymous where noted.',
    }


def skilldata_positive_branch_reader_replay(sample, raw, *, source):
    """Replay one positive terminal-list branch with its bounded nested reader."""
    if not isinstance(sample, dict) or not isinstance(raw, bytes):
        raise ContextError(source, 0, 'branch witness object and raw bytes',
                           [type(sample).__name__, type(raw).__name__])
    input_set = sample.get('inputSetSha256')
    logical_path = sample.get('logicalFileIdentity')
    digest = hashlib.sha256(raw).hexdigest().upper()
    hard_limit = sample.get('hardLimit')
    if not isinstance(input_set, str) or len(input_set) != 64:
        raise ContextError(source, 0, '64-character current inputSetSha256', input_set)
    if not isinstance(logical_path, str) or not logical_path.startswith('Data/Json/SkillData/'):
        raise ContextError(source, 0, 'logical SkillData VFS identity', logical_path)
    require(sample.get('logicalSha256'), digest, source)
    require(hard_limit, len(raw), source)
    require(sample.get('sourceRange'),
            {'start': 0, 'end': hard_limit, 'endExclusive': True}, source)
    require(sample.get('classification'), 'ambiguous', source)
    require(sample.get('exactClosedRecords'), 0, source)

    candidate_ranges = sample.get('terminalCandidateRanges')
    if (not isinstance(candidate_ranges, list) or len(candidate_ranges) != 2 or
            any(not isinstance(row, dict) for row in candidate_ranges)):
        raise ContextError(source, 0, 'two bounded terminal candidate ranges', candidate_ranges)
    start = candidate_ranges[0].get('start')
    for ordinal, row in enumerate(candidate_ranges):
        if (type(row.get('start')) is not int or row.get('end') != hard_limit or
                row.get('endExclusive') is not True or
                row.get('start') != start + ordinal):
            raise ContextError(source, start if type(start) is int else 0,
                               'two adjacent shifted [start, hardLimit) candidates', row)
    if type(start) is not int or start < 0 or start + 1 >= hard_limit:
        raise ContextError(source, 0, 'in-limit first terminal candidate start', start)

    branch = sample.get('positiveBranch')
    if not isinstance(branch, dict):
        raise ContextError(source, start, 'positive branch evidence object', branch)
    field_name = branch.get('fieldName')
    member_index = branch.get('memberIndex')
    count = branch.get('count')
    record_ranges = branch.get('recordRanges')
    header_counts = branch.get('recordHeaderMemberCounts')
    if (field_name not in ('tagDuringAttach.predefinedTag', 'toggleBuffs', 'uiRangeHints') or
            type(member_index) is not int or member_index not in (1, 2, 3) or
            type(count) is not int or count <= 0 or
            not isinstance(record_ranges, list) or len(record_ranges) != count or
            not isinstance(header_counts, list) or len(header_counts) != count):
        raise ContextError(source, start, 'positive bounded nested list branch',
                           [field_name, member_index, count, record_ranges, header_counts])
    expected_field_by_index = {
        1: 'tagDuringAttach.predefinedTag', 2: 'toggleBuffs', 3: 'uiRangeHints'}
    require(field_name, expected_field_by_index[member_index], source, start)
    count_rows = [row for row in sample.get('listCounts', [])
                  if isinstance(row, dict) and row.get('memberIndex') == member_index]
    if len(count_rows) != 1:
        raise ContextError(source, start, 'one raw count witness for selected list member',
                           count_rows)
    count_row = count_rows[0]
    require(count_row.get('fieldName'), field_name, source, start)
    require(count_row.get('count'), count, source, start)
    require(count_row.get('recordRanges'), record_ranges, source, start)
    require(count_row.get('recordHeaderMemberCounts'), header_counts, source, start)
    for ordinal, span in enumerate(record_ranges):
        if (not isinstance(span, dict) or type(span.get('start')) is not int or
                type(span.get('end')) is not int or span['start'] < start or
                span['end'] <= span['start'] or span['end'] > hard_limit):
            raise ContextError(source, start, 'nested record range within hardLimit', span)
        if ordinal and span['start'] != record_ranges[ordinal - 1].get('end'):
            raise ContextError(source, span['start'],
                               'selected sibling nested records are contiguous',
                               [record_ranges[ordinal - 1], span])

    replayed_records = []
    if field_name == 'tagDuringAttach.predefinedTag':
        count_range = count_row.get('countRange')
        if (not isinstance(count_range, dict) or
                type(count_range.get('start')) is not int or
                count_range.get('end') != count_range['start'] + 4):
            raise ContextError(source, start, 'four-byte wrapped GameplayTag count range',
                               count_range)
        reader_start = count_range['start'] - 1
        require(reader_start, start + 1, source, reader_start)
        require(raw[reader_start], 1, source, reader_start)
        try:
            parsed, cursor = read_skill_gameplay_tag_list_field(
                raw, reader_start, 'tagDuringAttach')
        except ValueError as error:
            raise ContextError(source, reader_start,
                               'bounded one-member GameplayTagList parser replay', str(error)) from error
        require(parsed.get('branch'), 'one-member-wrapper', source, reader_start)
        require(parsed.get('prefixMemberCount'), 1, source, reader_start)
        require(parsed.get('count'), count, source, reader_start)
        expected_cursor = record_ranges[-1]['end']
        require(cursor, expected_cursor, source, reader_start)
        parsed_tags = parsed.get('tags')
        if not isinstance(parsed_tags, list) or len(parsed_tags) != count:
            raise ContextError(source, reader_start, 'one parsed GameplayTag per bounded count',
                               parsed_tags)
        for ordinal, (tag, span, header) in enumerate(
                zip(parsed_tags, record_ranges, header_counts)):
            tag_start = int(tag.get('offset', '0'), 16)
            tag_end = tag_start + tag.get('byteLength', 0)
            require({'start': tag_start, 'end': tag_end},
                    {'start': span['start'], 'end': span['end']}, source, tag_start)
            require(tag.get('memberCount'), header, source, tag_start)
            replayed_records.append({
                'index': ordinal, 'recordRange': span,
                'memberCount': tag.get('memberCount'),
                'encoding': tag.get('encoding'),
                'tagId': tag.get('tagId'), 'tagHash': tag.get('tagHash'),
            })
        reader_row = {
            'reader': 'read_skill_gameplay_tag_list_field',
            'readerRange': {'start': reader_start, 'end': cursor, 'endExclusive': True},
            'wrapperMemberCount': parsed['prefixMemberCount'],
            'elementCount': parsed['count'],
            'elementRecords': replayed_records,
        }
    elif field_name == 'toggleBuffs':
        parser_field_order = None
        for ordinal, (span, header) in enumerate(zip(record_ranges, header_counts)):
            try:
                parsed, cursor = read_skill_toggle_buff_data(raw, span['start'], ordinal)
            except ValueError as error:
                raise ContextError(source, span['start'],
                                   'bounded ToggleBuffData reader replay', str(error)) from error
            require(cursor, span['end'], source, span['start'])
            require(parsed.get('memberCount'), header, source, span['start'])
            require(parsed.get('metadataFieldOrder'), ['buffs', 'conditions'],
                    source, span['start'])
            if parser_field_order is None:
                parser_field_order = parsed['metadataFieldOrder']
            else:
                require(parsed['metadataFieldOrder'], parser_field_order,
                        source, span['start'])
            replayed_records.append({
                'index': ordinal, 'recordRange': span,
                'memberCount': parsed['memberCount'],
                'byteLength': parsed['byteLength'],
                'buffsCount': parsed['buffsCount'],
                'conditionsCount': parsed['conditionsCount'],
            })
        reader_row = {
            'reader': 'read_skill_toggle_buff_data',
            'readerRange': {'start': record_ranges[0]['start'],
                            'end': record_ranges[-1]['end'], 'endExclusive': True},
            'parserFieldOrder': parser_field_order,
            'elementRecords': replayed_records,
        }
    else:
        for ordinal, (span, header) in enumerate(zip(record_ranges, header_counts)):
            try:
                parsed, cursor = read_skill_ui_range_hint_data(raw, span['start'], ordinal)
            except ValueError as error:
                raise ContextError(source, span['start'],
                                   'bounded UIRangeHintData/SkillHintShapeData reader replay',
                                   str(error)) from error
            require(cursor, span['end'], source, span['start'])
            require(parsed.get('memberCount'), header, source, span['start'])
            shape = parsed.get('shapeData')
            if not isinstance(shape, dict):
                raise ContextError(source, span['start'], 'nested SkillHintShapeData parse', shape)
            require(shape.get('memberCount'), 21, source, span['start'])
            shape_start = int(shape.get('offset', '0'), 16)
            shape_end = shape_start + shape.get('byteLength', 0)
            replayed_records.append({
                'index': ordinal, 'recordRange': span,
                'memberCount': parsed['memberCount'],
                'byteLength': parsed['byteLength'],
                'selectAll': parsed['selectAll'],
                'shapeData': {
                    'recordRange': {'start': shape_start, 'end': shape_end,
                                    'endExclusive': True},
                    'memberCount': shape['memberCount'],
                    'byteLength': shape['byteLength'],
                    'shapeRaw': shape.get('shapeRaw'),
                    'shapeName': shape.get('shapeName'),
                },
                'targetFactionRaw': parsed['targetFactionRaw'],
            })
        reader_row = {
            'reader': 'read_skill_ui_range_hint_data',
            'readerRange': {'start': record_ranges[0]['start'],
                            'end': record_ranges[-1]['end'], 'endExclusive': True},
            'parserFieldOrder': ['selectAll', 'shapeData', 'targetFaction'],
            'nestedShapeParserFieldOrder': [
                'angle', 'angleKey', 'centerBaseIsEndPoint', 'centerOffset',
                'centerOffsetXKey', 'centerOffsetZKey', 'extent', 'extentXKey',
                'extentZKey', 'fixedExtent', 'radius', 'radiusKey',
                'restrictEndPointInRange', 'shape', 'useAngleKey',
                'useCenterOffsetKey', 'useExtentKey', 'useRadiusKey',
                'useWidthKey', 'width', 'widthKey'],
            'elementRecords': replayed_records,
        }
    return {
        'inputSetSha256': input_set,
        'logicalFileIdentity': logical_path,
        'logicalSha256': digest,
        'hardLimit': hard_limit,
        'positiveFieldName': field_name,
        'conditionalOnTerminalCandidateStart': start,
        'terminalCandidateRanges': candidate_ranges,
        'shiftedCandidateTypeProbe': sample.get('shiftedCandidateTypeProbe'),
        'nestedReaderReplay': reader_row,
        'wholeSkillDataClassification': 'ambiguous',
        'wholeSkillDataExactClosedRecords': 0,
        'boundary': 'The bounded nested reader reaches the reported positive-list element end in these authenticated raw bytes. This does not resolve the one-byte-shifted parent tail, select a runtime provider or observe a live cursor.',
    }


def skilldata_shifted_candidate_reader_assessment(branch_replay,
                                                  gameplay_tag_list,
                                                  list_formatter, *, source):
    """Evaluate the shifted hypothesis against registered wrapper/count guards."""
    if not isinstance(branch_replay, dict) or not isinstance(gameplay_tag_list, dict):
        raise ContextError(source, 0, 'branch replay and GameplayTagList static evidence',
                           [type(branch_replay).__name__, type(gameplay_tag_list).__name__])
    hard_limit = branch_replay.get('hardLimit')
    start = branch_replay.get('conditionalOnTerminalCandidateStart')
    ranges = branch_replay.get('terminalCandidateRanges')
    probe = branch_replay.get('shiftedCandidateTypeProbe')
    if (type(hard_limit) is not int or type(start) is not int or
            not isinstance(ranges, list) or len(ranges) != 2 or
            not isinstance(probe, dict)):
        raise ContextError(source, 0, 'identity-bound shifted candidate byte probe',
                           [hard_limit, start, ranges, probe])
    expected_ranges = [
        {'start': start, 'end': hard_limit, 'endExclusive': True},
        {'start': start + 1, 'end': hard_limit, 'endExclusive': True},
    ]
    input_set = branch_replay.get('inputSetSha256')
    logical_path = branch_replay.get('logicalFileIdentity')
    logical_sha = branch_replay.get('logicalSha256')
    if (not isinstance(input_set, str) or len(input_set) != 64 or
            not isinstance(logical_path, str) or
            not logical_path.startswith('Data/Json/SkillData/') or
            not isinstance(logical_sha, str) or len(logical_sha) != 64):
        raise ContextError(source, start,
                           'current SkillData inputSet, logical identity and SHA-256',
                           [input_set, logical_path, logical_sha])
    require(ranges, expected_ranges, source, start)
    require(probe.get('shiftedCandidateStart'), start + 1, source, start + 1)
    header = gameplay_tag_list.get('headerEvidence')
    if not isinstance(header, dict):
        raise ContextError(source, start + 2, 'static GameplayTagList header evidence', header)
    header_width = header.get('headerByteWidth')
    accepted = header.get('acceptedNonNullHeaderByte')
    null_header = header.get('nullHeaderByte')
    require(header_width, 1, source, start + 2)
    require(accepted, 1, source, start + 2)
    require(null_header, 0xFF, source, start + 2)
    raw_header = probe.get('gameplayTagListHeaderByte')
    if (not isinstance(raw_header, dict) or
            raw_header.get('offset') != start + 2 or
            type(raw_header.get('value')) is not int or
            not 0 <= raw_header['value'] <= 0xFF):
        raise ContextError(source, start + 2,
                           'shifted candidate GameplayTagList header byte and offset',
                           raw_header)
    value = raw_header['value']
    assessment = {
        'inputSetSha256': input_set,
        'logicalFileIdentity': logical_path,
        'logicalSha256': logical_sha,
        'parserCursor': hard_limit,
        'hardLimit': hard_limit,
        'shiftedCandidateRange': expected_ranges[1],
        'readerFieldAfterShiftedBoolean': 'tagDuringAttach',
        'gameplayTagListHeaderByte': raw_header,
        'acceptedWrapperHeaders': [accepted, null_header],
        'runtimeProviderSelection': 'unobserved',
        'classification': 'conditional-on-registered-reader-and-provider-path',
    }
    if value not in (accepted, null_header):
        assessment.update({
            'status': 'outside-registered-GameplayTagList-header-path',
            'boundary': 'The registered GameplayTagList reader accepts only header 1 or null header 0xFF; this shifted byte is outside that path.',
        })
        return assessment
    if value == null_header:
        assessment.update({
            'status': 'not-rejected-by-null-wrapper-header',
            'boundary': 'The shifted candidate reaches the registered null-wrapper path; this probe alone does not distinguish it.',
        })
        return assessment

    count = probe.get('nestedListCount')
    if not isinstance(count, dict):
        raise ContextError(source, start + 3,
                           'one-byte wrapper header followed by bounded signed list count', count)
    if count.get('complete') is not True:
        assessment.update({
            'nestedListCount': count,
            'status': 'truncated-registered-list-count',
            'boundary': 'The registered non-null wrapper path requires a complete four-byte list count inside hardLimit.',
        })
        return assessment
    if (type(count.get('offset')) is not int or count.get('offset') != start + 3 or
            count.get('availableByteLength') != 4 or
            type(count.get('signedI32')) is not int or
            type(count.get('remainingAfterCount')) is not int or
            count['remainingAfterCount'] < 0):
        raise ContextError(source, start + 3,
                           'complete bounded signed list count and remaining byte budget', count)
    assessment['nestedListCount'] = count
    if list_formatter is None:
        assessment.update({
            'status': 'unresolved-list-formatter-selection',
            'boundary': 'The wrapper header is accepted, but no matching registered List<GameplayTag> count guard was supplied.',
        })
        return assessment
    if not isinstance(list_formatter, dict):
        raise ContextError(source, start + 3, 'registered List<GameplayTag> formatter evidence',
                           type(list_formatter).__name__)
    wrapper_inst = gameplay_tag_list.get('nestedReadInstantiation')
    formatter_inst = list_formatter.get('classInstantiation')
    if not isinstance(wrapper_inst, dict) or not isinstance(formatter_inst, dict):
        raise ContextError(source, start + 3,
                           'wrapper and formatter generic-instantiation evidence',
                           [wrapper_inst, formatter_inst])
    require(formatter_inst.get('index'), wrapper_inst.get('index'), source, start + 3)
    guard = list_formatter.get('fastHeaderGuard')
    if not isinstance(guard, dict):
        raise ContextError(source, start + 3, 'audited signed List<T> remaining-byte guard', guard)
    require(guard.get('countWidthBytes'), 4, source, start + 3)
    require(guard.get('signedCount'), True, source, start + 3)
    require(guard.get('remainingBytesComparedToCount'), True, source, start + 3)
    require(guard.get('rangeFailureCondition'), 'remaining < signed count', source, start + 3)
    require(guard.get('comparisonRva'), 0x3BA4130, source, start + 3)
    require(guard.get('comparisonRawHex'),
            '48634744488B4F18482BC84863C6483BC8', source, start + 3)
    require(guard.get('rangeFailureBranchRva'), 0x3BA4141, source, start + 3)
    require(guard.get('rangeFailureBranchRawHex'), '0F8CB4653201', source, start + 3)
    require(guard.get('rangeFailureTargetRva'), 0x4ECA6FB, source, start + 3)
    require(guard.get('rangeFailureBodyRawHex'),
            '33D28BCEE8900A8404CCCC', source, start + 3)
    if count['signedI32'] > count['remainingAfterCount']:
        assessment.update({
            'status': 'rejected-by-registered-list-count-bound',
            'listFormatterMethodSpecIndices': list_formatter.get('methodSpecIndices'),
            'listFormatterInstantiationIndex': formatter_inst.get('index'),
            'rangeFailureBranchRva': guard.get('rangeFailureBranchRva'),
            'rangeFailureTargetRva': guard.get('rangeFailureTargetRva'),
            'boundary': 'The shifted path reads a signed count greater than the bytes remaining after that count; the matching registered List<GameplayTag> body takes its bounded range-failure path before element iteration.',
        })
    else:
        assessment.update({
            'status': 'not-rejected-by-registered-list-count-bound',
            'boundary': 'The shifted path passes this bounded count comparison; more reader evidence is required.',
        })
    return assessment


def skilldata_nested_branch_static_alignment(branch_replay, nested_readers,
                                              gameplay_tag_list, *,
                                              list_formatter=None, source):
    """Require positive raw nested replays to match exact static reader schemas."""
    if not isinstance(branch_replay, dict) or not isinstance(nested_readers, dict):
        raise ContextError(source, 0, 'branch replay and static nested-reader evidence',
                           [type(branch_replay).__name__, type(nested_readers).__name__])
    if branch_replay.get('wholeSkillDataClassification') != 'ambiguous':
        raise ContextError(source, 0, 'whole SkillData sample remains ambiguous',
                           branch_replay.get('wholeSkillDataClassification'))
    if branch_replay.get('wholeSkillDataExactClosedRecords') != 0:
        raise ContextError(source, 0, 'no whole SkillData record credited as closed',
                           branch_replay.get('wholeSkillDataExactClosedRecords'))
    shifted_assessment = skilldata_shifted_candidate_reader_assessment(
        branch_replay, gameplay_tag_list, list_formatter, source=source)
    field_name = branch_replay.get('positiveFieldName')
    replay = branch_replay.get('nestedReaderReplay')
    records = replay.get('elementRecords') if isinstance(replay, dict) else None
    if not isinstance(records, list) or not records:
        raise ContextError(source, 0, 'at least one raw nested element replay', records)
    if field_name == 'tagDuringAttach.predefinedTag':
        wrapper_members = gameplay_tag_list.get('memberCount')
        require(wrapper_members, 1, source)
        header = gameplay_tag_list.get('headerEvidence')
        if not isinstance(header, dict):
            raise ContextError(source, 0, 'static GameplayTagList header evidence', header)
        require(header.get('acceptedNonNullHeaderByte'), 1, source)
        require(replay.get('wrapperMemberCount'), wrapper_members, source)
        require(replay.get('elementCount'), len(records), source)
        require(replay.get('reader'), 'read_skill_gameplay_tag_list_field', source)
        element_schema = nested_readers.get('gameplayTagElement')
        if not isinstance(element_schema, dict):
            raise ContextError(source, 0, 'registered GameplayTag element reader schema',
                               element_schema)
        native_element_count = element_schema.get('memberCountCheck', {}).get(
            'acceptedMemberCount')
        require(native_element_count, 1, source)
        require(element_schema.get('tagIdField', {}).get('fieldType', {}).get('wireType'),
                'System.Int32', source)
        require(element_schema.get('readerCall', {}).get('targetRva'), 0x2CA86B0, source)
        cursor_advancement = element_schema.get('cursorAdvancement')
        if not isinstance(cursor_advancement, dict):
            raise ContextError(source, 0, 'bounded int32/member-count cursor helper evidence',
                               cursor_advancement)
        native_record_width = cursor_advancement.get('validNormalPathByteWidth')
        require(native_record_width, 5, source)
        native_reader_method = element_schema.get('readerMethodIdentity', {})
        require(native_reader_method.get('methodIndex'), 104467, source)
        native_ranges = []
        for ordinal, row in enumerate(records):
            require(row.get('memberCount'), native_element_count, source, ordinal)
            span = row.get('recordRange')
            actual_width = span.get('end') - span.get('start') if isinstance(span, dict) else None
            require(actual_width, native_record_width, source, ordinal)
            native_ranges.append({
                'recordRange': span,
                'staticReaderEnd': span['start'] + native_record_width,
                'cursorByteWidth': native_record_width,
                'classification': 'exact-under-registered-reader-path',
            })
        raw_ids = []
        for ordinal, row in enumerate(records):
            raw_id = row.get('tagId')
            if type(raw_id) is not int or not 0 <= raw_id <= 0xFFFFFFFF:
                raise ContextError(source, ordinal,
                                   'GameplayTag raw id as an unsigned 32-bit bit pattern', raw_id)
            signed_id = raw_id if raw_id < 0x80000000 else raw_id - 0x100000000
            raw_ids.append({'rawU32': raw_id, 'rawHex': f'0x{raw_id:08X}',
                            'signedI32': signed_id})
        alignment = {
            'readerField': field_name,
            'rawWrapperMemberCount': replay['wrapperMemberCount'],
            'staticWrapperMemberCount': wrapper_members,
            'rawElementCount': replay['elementCount'],
            'staticSchema': gameplay_tag_list['typeName'],
            'rawElementMemberCounts': [row.get('memberCount') for row in records],
            'staticElementMemberCount': native_element_count,
            'nativeElementIdWireType': 'System.Int32',
            'staticReaderCursorDerivation': cursor_advancement['derivation'],
            'conditionalExactNativeElementRanges': native_ranges,
            'rawU32AndSignedI32Views': raw_ids,
        }
    elif field_name == 'toggleBuffs':
        schema = nested_readers.get('toggleBuffData')
        if not isinstance(schema, dict):
            raise ContextError(source, 0, 'exact ToggleBuffData reader schema', schema)
        member_count = schema.get('memberCountCompare', {}).get('memberCount')
        require(member_count, 2, source)
        field_order = [row.get('fieldName') for row in schema.get('members', [])]
        require(replay.get('parserFieldOrder'), field_order, source)
        require(replay.get('reader'), 'read_skill_toggle_buff_data', source)
        for ordinal, row in enumerate(records):
            require(row.get('memberCount'), member_count, source, ordinal)
        alignment = {
            'readerField': field_name,
            'rawRecordMemberCounts': [row.get('memberCount') for row in records],
            'staticMemberCount': member_count,
            'rawAndStaticFieldOrder': field_order,
        }
    elif field_name == 'uiRangeHints':
        schema = nested_readers.get('uiRangeHintData')
        shape_schema = nested_readers.get('skillHintShapeData')
        if not isinstance(schema, dict) or not isinstance(shape_schema, dict):
            raise ContextError(source, 0, 'exact UIRangeHintData and nested shape schemas',
                               [schema, shape_schema])
        member_count = schema.get('memberCountCompare', {}).get('memberCount')
        shape_count = shape_schema.get('memberCountCompare', {}).get('memberCount')
        require(member_count, 3, source)
        require(shape_count, 21, source)
        field_order = [row.get('fieldName') for row in schema.get('members', [])]
        shape_order = [row.get('fieldName') for row in shape_schema.get('serializedOrder', [])]
        require(replay.get('parserFieldOrder'), field_order, source)
        require(replay.get('nestedShapeParserFieldOrder'), shape_order, source)
        require(replay.get('reader'), 'read_skill_ui_range_hint_data', source)
        for ordinal, row in enumerate(records):
            require(row.get('memberCount'), member_count, source, ordinal)
            require(row.get('shapeData', {}).get('memberCount'), shape_count, source, ordinal)
        alignment = {
            'readerField': field_name,
            'rawRecordMemberCounts': [row.get('memberCount') for row in records],
            'staticMemberCount': member_count,
            'rawAndStaticFieldOrder': field_order,
            'nestedShapeMemberCounts': [row.get('shapeData', {}).get('memberCount')
                                        for row in records],
            'nestedShapeStaticMemberCount': shape_count,
            'rawAndStaticShapeFieldOrder': shape_order,
        }
    else:
        raise ContextError(source, 0, 'recognized positive SkillData nested reader field', field_name)
    return {
        'status': 'positive-raw-sample-matches-static-nested-reader-schema',
        'alignment': alignment,
        'shiftedCandidateAssessment': shifted_assessment,
        'wholeSkillDataClassification': 'ambiguous',
        'exactClosedWholeSkillDataRecords': 0,
        'boundary': ('For GameplayTag, the exact five-byte nested element endpoint follows from the registered reader plus its bounded one-byte/four-byte cursor helpers, and the source parser reaches the same end. Other nested endpoints are parser-to-schema cross-checks. All are conditional on the registered terminal path; none proves runtime provider selection or a live cursor.'),
    }


def skilldata_terminal_tail_layout(collision, sample_witness, tail_reads,
                                   tag_list_wrapper, *, source):
    """Compare exact terminal reader/type evidence to both current VFS shapes."""
    expected_reads = [
        (43, 'switchToCenterBeforeCast', 'bool', 0xA5, 0x37DE8C5, 0x2CA88C0, 0x37DE8E0),
        (44, 'tagDuringAttach', 'Beyond.Gameplay.Core.GameplayTagList',
         0xB8, 0x37DE8F3, 0x2DA5C90, 0x37DE90E),
        (45, 'toggleBuffs',
         'System.Collections.Generic.List`1<Beyond.Gameplay.Core.ToggleBuffData>',
         0xD8, 0x37DE92E, 0x381F8F0, 0x37DE949),
        (46, 'uiRangeHints',
         'System.Collections.Generic.List`1<Beyond.Gameplay.Core.UIRangeHintData>',
         0xC8, 0x37DE969, 0x381F8F0, 0x37DE984),
        (47, 'useAIExclusiveFrame', 'bool', 0x58, 0x37DE99D, 0x2CA88C0, 0x37DE9C2),
    ]
    if not isinstance(tail_reads, list) or len(tail_reads) != len(expected_reads):
        raise ContextError(source, 0, 'five exact terminal SkillData reader operations',
                           type(tail_reads).__name__ if not isinstance(tail_reads, list)
                           else len(tail_reads))
    actual_reads = []
    for row in tail_reads:
        if not isinstance(row, dict) or not isinstance(row.get('objectField'), dict):
            raise ContextError(source, 0, 'terminal SkillData reader rows include object fields',
                               row)
        actual_reads.append((
            row.get('serializedOrderIndex'), row.get('fieldName'), row.get('wireType'),
            row['objectField'].get('fieldOffset'), row.get('callInstructionRva'),
            row.get('readerTargetRva'), row.get('storeInstructionRva'),
        ))
    if actual_reads != expected_reads:
        raise ContextError(source, 0,
                           'terminal SkillData type/order/call/store rows match exact expectations',
                           actual_reads)

    if not isinstance(sample_witness, dict):
        raise ContextError(source, 0, 'authenticated current raw terminal byte witness',
                           type(sample_witness).__name__)
    for key in ('inputSetSha256', 'logicalFileIdentity', 'logicalSha256', 'hardLimit'):
        if sample_witness.get(key) != collision.get(key):
            raise ContextError(source, 0, f'terminal raw witness {key} equals corpus collision',
                               [sample_witness.get(key), collision.get(key)])
    if sample_witness.get('candidateRange') != collision['candidates'][0].get('candidateRange'):
        raise ContextError(source, 0, 'raw witness candidate range equals first corpus hypothesis',
                           sample_witness.get('candidateRange'))
    header = sample_witness.get('nestedMemberCountByte')
    if not isinstance(header, dict) or header.get('value') != 1:
        raise ContextError(source, 0, 'first candidate raw wrapper header is one',
                           header)

    if not isinstance(tag_list_wrapper, dict):
        raise ContextError(source, 0, 'exact GameplayTagList wrapper layout evidence',
                           type(tag_list_wrapper).__name__)
    expected_wrapper_type = 'Beyond.Gameplay.Core.GameplayTagList'
    if (tag_list_wrapper.get('typeName') != expected_wrapper_type or
            tag_list_wrapper.get('memberCount') != 1):
        raise ContextError(source, 0,
                           'GameplayTagList is the one-member SkillData tail wrapper',
                           [tag_list_wrapper.get('typeName'), tag_list_wrapper.get('memberCount')])
    member = tag_list_wrapper.get('member')
    expected_member_type = (
        'System.Collections.Generic.List`1<Beyond.Gameplay.Core.GameplayTag>')
    if (not isinstance(member, dict) or member.get('name') != 'predefinedTag' or
            member.get('wireType') != expected_member_type):
        raise ContextError(source, 0,
                           'GameplayTagList member is predefinedTag: List<GameplayTag>',
                           member)
    reader_identity = tag_list_wrapper.get('readerMethodIdentity')
    if (not isinstance(reader_identity, dict) or
            reader_identity.get('pointerVa') is None or
            reader_identity.get('name') != 'Deserialize' or
            reader_identity.get('declaringType') !=
            'Beyond.MemoryPack.Beyond_Gameplay_Core_GameplayTagListForMemoryPack'):
        raise ContextError(source, 0,
                           'wrapper reader method is the exact GameplayTagList Deserialize identity',
                           reader_identity)
    nested_type = tag_list_wrapper.get('nestedReadType')
    if nested_type != expected_member_type:
        raise ContextError(source, 0,
                           'wrapper reader MethodSpec reads its exact List<GameplayTag> member',
                           nested_type)
    header_evidence = tag_list_wrapper.get('headerEvidence')
    if (not isinstance(header_evidence, dict) or
            header_evidence.get('headerByteWidth') != 1 or
            header_evidence.get('acceptedNonNullHeaderByte') != 1 or
            header_evidence.get('nullHeaderByte') != 0xFF):
        raise ContextError(source, 0,
                           'wrapper reader consumes one header byte and accepts member count one',
                           header_evidence)

    candidates = collision.get('candidates')
    if not isinstance(candidates, list) or len(candidates) != 2:
        raise ContextError(source, 0, 'two terminal candidates remain available for comparison',
                           type(candidates).__name__ if not isinstance(candidates, list)
                           else len(candidates))
    first, shifted = candidates
    first_members = first.get('terminalMembers')
    shifted_members = shifted.get('terminalMembers')
    if not isinstance(first_members, list) or len(first_members) != 5:
        raise ContextError(source, 0, 'first terminal candidate has five member rows',
                           first_members)
    if not isinstance(shifted_members, list) or len(shifted_members) != 5:
        raise ContextError(source, 0, 'shifted terminal candidate has five member rows',
                           shifted_members)
    if (first.get('encoding') != 'one-member-wrapper' or
            first_members[1].get('wrapperRange') is None):
        raise ContextError(source, first.get('start', 0),
                           'first candidate carries the one-member GameplayTagList wrapper',
                           first.get('encoding'))
    if shifted.get('encoding') != 'counted' or shifted_members[1].get('wrapperRange') is not None:
        raise ContextError(source, shifted.get('start', 0),
                           'shifted candidate omits the required GameplayTagList wrapper',
                           shifted.get('encoding'))
    return {
        'tailReads': tail_reads,
        'nestedWrapperMemberCount': tag_list_wrapper.get('memberCount'),
        'gameplayTagListWrapper': tag_list_wrapper,
        'rawSampleByteWitness': sample_witness,
        'candidateComparison': [
            {
                'candidateRange': first.get('candidateRange'),
                'status': 'static-type-and-reader-order match, conditional on registered reader paths being selected',
                'fieldSequence': [name for _, name, *_ in expected_reads],
                'rawWrapperHeaderByte': header,
            },
            {
                'candidateRange': shifted.get('candidateRange'),
                'status': 'statically incompatible with the one-member GameplayTagList wrapper if its registered reader path is selected',
                'conflict': 'The shifted candidate treats the raw wrapper header byte 1 as switchToCenterBeforeCast and omits the nested wrapper header.',
            },
        ],
        'wholeFileBoundary': 'The terminal field group is independently matched to the current source bytes, but the bytes between the proven [0,10) prefix and this tail remain opaque. Do not classify the whole SkillData file as closed.',
        'runtimeProviderSelection': 'unobserved',
        'runtimeCursor': 'unobserved',
        'classification': 'static-terminal-shape-match-with-conditional-shifted-candidate-conflict',
        'exactClosedRecords': 0,
    }


def skilldata_cursor_hook_call_sites(pe, *, source):
    """Verify exact SkillData E8 edges and the post-CALL return RVAs.

    The native observer classifies the return address from _ReturnAddress(),
    not the start of the E8 instruction.
    """
    sites = []
    for name, instruction_rva in (
            ('firstTerminalByte', 0x37DE8C5),
            ('finalTerminalByte', 0x37DE99D)):
        raw = pe.bytes_at_va(pe.image_base + instruction_rva, 5)
        require(raw[:1], b'\xE8', source, instruction_rva)
        target = relative_branch_target(
            raw, pe.image_base + instruction_rva, source=source)
        require(target, pe.image_base + 0x2CA88C0, source, instruction_rva)
        return_rva = instruction_rva + len(raw)
        sites.append({
            'name': name,
            'callInstructionRva': instruction_rva,
            'instructionByteLength': len(raw),
            'rawHex': raw.hex().upper(),
            'targetRva': target - pe.image_base,
            'returnAddressRva': return_rva,
            'classificationBasis': '_ReturnAddress() after the five-byte E8 rel32 call',
        })
    return {
        'sites': sites,
        'level': 'exact selected-build direct helper call and post-CALL return address',
        'boundary': 'These checks validate the observer allow-list coordinates against the selected SkillData body. They do not prove that either call executes for a current VFS file or provide its runtime cursor.',
    }


def skilldata_static_reader_order(pe, md, modules, image_owners, table, reg, specs_raw,
                                  corpus, representative_sample_raw, wrapper_evidence,
                                  *, source):
    """Pin the first SkillData reader field and nested ActionGroupData order.

    Static AOT method, MethodSpec, field-offset and bounded-code joins are
    exact-build evidence. They do not establish which formatter/provider ran
    for a VFS file, so the empty-list end stays conditional.
    """
    selected_methods = module_methods(pe, md, modules, image_owners, [
        (102566, 'Beyond.MemoryPack.Beyond_Gameplay_Core_SkillDataForMemoryPack', 'Deserialize', 0x37DE060),
        (102567, 'Beyond.MemoryPack.Beyond_Gameplay_Core_SkillDataForMemoryPack+Beyond_Gameplay_Core_SkillDataForMemoryPackFormatter', 'Deserialize', 0x37DDF70),
        (104262, 'Beyond.MemoryPack.Beyond_Gameplay_Core_ActionGroupDataForMemoryPack', 'Deserialize', 0x3E3FFE0),
        (104263, 'Beyond.MemoryPack.Beyond_Gameplay_Core_ActionGroupDataForMemoryPack+Beyond_Gameplay_Core_ActionGroupDataForMemoryPackFormatter', 'Deserialize', 0x3E3FF80),
    ], source=source, expected_image='MemoryPack.Beyond.dll')
    code_windows = []
    for rva, length, expected in (
        (0x37DE060, 0x5B, '0926899BA44C601CEBAC2B4E70580B397CDDAB4FC60060C1E8DC0EF99A2555FB'),
        (0x37DE0BB, 0x90A, 'FEA359985EBF5DF75CC58D871469481F0F692B1768D84724FF5941D47CAD8132'),
        (0x3E3FFE0, 0x13F, 'D2C4A8B7F40CDB99154F7EE9EFA9FB85CD8F2F086932F03C1BC2FF8568E1AB4E'),
    ):
        raw = pe.bytes_at_va(pe.image_base + rva, length)
        digest = hashlib.sha256(raw).hexdigest().upper()
        require(digest, expected, source, rva)
        code_windows.append({'rva': rva, 'byteLength': length, 'sha256': digest})
    instruction_windows = []
    for rva, raw_hex, role in (
        (0x37DE0CF, '4080FD30', 'SkillData member-count comparison against 48'),
        (0x37DE101, '488981C0000000', 'store first SkillData result at object offset +0xC0'),
        (0x3E40045, '4080FD02', 'ActionGroupData member-count comparison against 2'),
        (0x3E40077, '48894118', 'store passiveEventActions result at object offset +0x18'),
        (0x3E400A4, '48894110', 'store timelineActions result at object offset +0x10'),
    ):
        raw = pe.bytes_at_va(pe.image_base + rva, len(bytes.fromhex(raw_hex)))
        require(raw, bytes.fromhex(raw_hex), source, rva)
        instruction_windows.append({'rva': rva, 'rawHex': raw.hex().upper(), 'role': role})
    formatter_thunks = []
    for rva, target in ((0x37DDFAC, 0x37DE060), (0x3E3FFBC, 0x3E3FFE0)):
        raw = pe.bytes_at_va(pe.image_base + rva, 5)
        actual = relative_branch_target(raw, pe.image_base + rva, source=source) - pe.image_base
        require(actual, target, source, rva)
        formatter_thunks.append({'rva': rva, 'rawHex': raw.hex().upper(),
                                 'targetRva': target, 'kind': 'conditional tail jump after formatter initialization'})

    def type_index(full_name, expected_image):
        matches = [index for index, item in enumerate(md.types) if md.type_full_name(item) == full_name]
        if len(matches) != 1:
            raise ContextError(source, 0, f'one metadata type definition named {full_name}', matches)
        index = matches[0]
        image_name = md.string(md.images[image_owners[index]].name_index)
        require(image_name, expected_image, source, index)
        return index

    def field_layout(type_def_index, field_names):
        require(reg['fieldOffsetsCount'], len(md.types), source, int(reg['fieldOffsets'], 16))
        definition = md.types[type_def_index]
        table_base = int(reg['fieldOffsets'], 16)
        vector = pe.u64_at_va(table_base + type_def_index * 8)
        require(vector != 0, True, source, table_base + type_def_index * 8)
        result = {}
        for local_index in range(definition.field_count):
            field_index = definition.field_start + local_index
            field = md.fields[field_index]
            name = md.string(field.name_index)
            if name not in field_names:
                continue
            raw_offset = pe.bytes_at_va(vector + local_index * 4, 4)
            offset = struct.unpack('<i', raw_offset)[0]
            result[name] = {'metadataFieldIndex': field_index, 'fieldOffset': offset,
                            'metadataTypeIndex': field.type_index}
        for name in field_names:
            if name not in result:
                raise ContextError(source, type_def_index,
                                   f'field {name!r} in type definition {type_def_index}', 'missing')
        return result

    def field_wire_identity(field_name, layout):
        field = md.fields[layout['metadataFieldIndex']]
        type_index = field.type_index
        if type(type_index) is not int or not 0 <= type_index < reg['typesCount']:
            raise ContextError(source, layout['metadataFieldIndex'],
                               'field type index inside registered IL2CPP type table', type_index)
        type_slot = int(reg['types'], 16) + type_index * 8
        type_pointer = pe.u64_at_va(type_slot)
        if type_pointer == 0:
            raise ContextError(source, type_slot, 'non-null field type pointer', type_pointer)
        raw = pe.bytes_at_va(type_pointer, 16)
        kind = raw[10]
        identity = {
            'metadataTypeIndex': type_index,
            'typePointerVa': type_pointer,
            'typeRawHex': raw.hex().upper(),
            'typeKind': kind,
        }
        primitive_names = {
            0x02: 'bool', 0x03: 'System.Char',
            0x04: 'System.SByte', 0x05: 'System.Byte',
            0x06: 'System.Int16', 0x07: 'System.UInt16',
            0x08: 'System.Int32', 0x09: 'System.UInt32',
            0x0A: 'System.Int64', 0x0B: 'System.UInt64',
            0x0C: 'System.Single', 0x0D: 'System.Double',
            0x0E: 'System.String',
        }
        if kind in primitive_names:
            identity['wireType'] = primitive_names[kind]
        elif kind in (0x11, 0x12):
            definition = struct.unpack_from('<Q', raw)[0]
            if definition >= len(md.types):
                raise ContextError(source, type_pointer,
                                   'bounded direct field type definition', definition)
            identity.update({
                'typeDefinitionIndex': definition,
                'wireType': md.type_full_name(md.types[definition]),
            })
        elif kind == 0x15:
            carrier_pointer = struct.unpack_from('<Q', raw)[0]
            carrier_raw = pe.bytes_at_va(carrier_pointer, 32)
            base_pointer = struct.unpack_from('<Q', carrier_raw)[0]
            base_raw = pe.bytes_at_va(base_pointer, 16)
            carrier = generic_type_carrier(
                raw, carrier_raw, base_raw, type_pointer=type_pointer,
                type_count=len(md.types), source=source)
            inst = table.resolve_pointer(carrier['classInstantiationPointerVa'])
            if len(inst.arguments) != 1:
                raise ContextError(source, inst.record_va,
                                   'one concrete generic list element type', len(inst.arguments))
            element = inst.arguments[0]
            element_raw = bytes.fromhex(element.raw_type_record_hex)
            element_kind = element_raw[10]
            element_definition = struct.unpack_from('<Q', element_raw)[0]
            if element_kind not in (0x11, 0x12) or element_definition >= len(md.types):
                raise ContextError(source, element.type_pointer_va,
                                   'bounded direct class/value list element type',
                                   [element_kind, element_definition])
            base_name = md.type_full_name(md.types[carrier['baseDefinitionIndex']])
            element_name = md.type_full_name(md.types[element_definition])
            identity.update({
                'typeDefinitionIndex': carrier['baseDefinitionIndex'],
                'typeName': base_name,
                'wireType': f'{base_name}<{element_name}>',
                'classCarrier': carrier,
                'genericInstantiation': inst.as_dict(),
                'elementTypeDefinitionIndex': element_definition,
                'elementTypeName': element_name,
                'elementRawTypeRecordHex': element.raw_type_record_hex,
            })
        else:
            raise ContextError(source, type_pointer,
                               'boolean, direct class/value or generic-list field type',
                               hex(kind))
        return identity

    skill_type = type_index('Beyond.Gameplay.Core.SkillData', 'Gameplay.Beyond.dll')
    action_group_type = type_index('Beyond.Gameplay.Core.ActionGroupData', 'Gameplay.Beyond.dll')
    skill_fields = field_layout(skill_type, {
        'actionGroupData', 'switchToCenterBeforeCast', 'tagDuringAttach',
        'toggleBuffs', 'uiRangeHints', 'useAIExclusiveFrame',
    })
    action_fields = field_layout(action_group_type, {'passiveEventActions', 'timelineActions'})
    require(skill_fields['actionGroupData']['fieldOffset'], 0xC0, source, skill_fields['actionGroupData']['metadataFieldIndex'])
    require(action_fields['passiveEventActions']['fieldOffset'], 0x18, source, action_fields['passiveEventActions']['metadataFieldIndex'])
    require(action_fields['timelineActions']['fieldOffset'], 0x10, source, action_fields['timelineActions']['metadataFieldIndex'])

    def call_method_spec(load_rva, call_rva, expected_method_index, expected_method_name, expected_target_rva):
        instruction = pe.bytes_at_va(pe.image_base + load_rva, 7)
        cell = rip_qword_load_target(instruction, pe.image_base + load_rva, source=source)
        raw_usage = pe.bytes_at_va(cell, 8)
        context = usage_method_spec(
            raw_usage, specs_raw, len(md.methods), table.count, source=source,
            usage_offset=cell, records_offset=int(reg['methodSpecs'], 16))
        require(context['definition'], expected_method_index, source, cell)
        method = md.methods[context['definition']]
        owner = md.types[method.declaring_type]
        require((md.type_full_name(owner), md.string(method.name_index)),
                ('MemoryPack.MemoryPackReader', expected_method_name), source, cell)
        target = relative_branch_target(
            pe.bytes_at_va(pe.image_base + call_rva, 5), pe.image_base + call_rva, source=source)
        require(target, pe.image_base + expected_target_rva, source, call_rva)
        context['methodIdentity'] = {
            'methodIndex': context['definition'], 'token': method.token,
            'declaringType': md.type_full_name(owner), 'name': md.string(method.name_index),
        }
        context['loadRva'] = load_rva
        context['callRva'] = call_rva
        context['targetRva'] = expected_target_rva
        inst = table.resolve(context['methodInstantiationIndex'])
        require(len(inst.arguments), 1, source, inst.record_va)
        type_arg = inst.arguments[0]
        type_raw = bytes.fromhex(type_arg.raw_type_record_hex)
        type_kind = type_raw[10]
        type_index_or_pointer = struct.unpack_from('<Q', type_raw)[0]
        if type_kind in (0x11, 0x12):
            require(type_index_or_pointer < len(md.types), True, source, type_arg.type_pointer_va)
            context['genericType'] = {
                'typeDefinitionIndex': type_index_or_pointer,
                'typeName': md.type_full_name(md.types[type_index_or_pointer]),
                'rawTypeRecordHex': type_arg.raw_type_record_hex,
            }
        elif type_kind == 0x15:
            carrier_raw = pe.bytes_at_va(type_index_or_pointer, 32)
            base_pointer = struct.unpack_from('<Q', carrier_raw)[0]
            base_raw = pe.bytes_at_va(base_pointer, 16)
            carrier = generic_type_carrier(
                type_raw, carrier_raw, base_raw, type_pointer=type_arg.type_pointer_va,
                type_count=len(md.types), source=source)
            base_name = md.type_full_name(md.types[carrier['baseDefinitionIndex']])
            require(base_name, 'System.Collections.Generic.List`1', source, base_pointer)
            element_inst = table.resolve_pointer(carrier['classInstantiationPointerVa'])
            require(len(element_inst.arguments), 1, source, element_inst.record_va)
            element_arg = element_inst.arguments[0]
            element_raw = bytes.fromhex(element_arg.raw_type_record_hex)
            element_kind = element_raw[10]
            element_index = struct.unpack_from('<Q', element_raw)[0]
            require(element_kind in (0x11, 0x12), True, source, element_arg.type_pointer_va)
            require(element_index < len(md.types), True, source, element_arg.type_pointer_va)
            context['genericType'] = {
                'typeDefinitionIndex': carrier['baseDefinitionIndex'],
                'typeName': base_name,
                'elementTypeDefinitionIndex': element_index,
                'elementTypeName': md.type_full_name(md.types[element_index]),
                'rawTypeRecordHex': type_arg.raw_type_record_hex,
                'elementRawTypeRecordHex': element_arg.raw_type_record_hex,
            }
        else:
            raise ContextError(source, type_arg.type_pointer_va,
                               'direct class or List<T> generic type argument', hex(type_kind))
        return context

    action_group_call = call_method_spec(0x37DE0D9, 0x37DE0E6, 428464, 'ReadValue', 0x2DA5C90)
    require(action_group_call['index'], 619840, source, action_group_call['usageVa'])
    require(action_group_call['genericType']['typeName'], 'Beyond.Gameplay.Core.ActionGroupData',
            source, action_group_call['usageVa'])
    require(action_group_call['genericType']['typeDefinitionIndex'], action_group_type,
            source, action_group_call['usageVa'])
    list_calls = [
        call_method_spec(0x3E4004F, 0x3E4005C, 428462, 'ReadPackable', 0x381F8F0),
        call_method_spec(0x3E40084, 0x3E40091, 428462, 'ReadPackable', 0x381F8F0),
    ]
    require([row['index'] for row in list_calls], [610662, 610915], source)
    for row in list_calls:
        require(row['genericType']['typeName'], 'System.Collections.Generic.List`1', source, row['usageVa'])
    require(list_calls[0]['genericType']['elementTypeName'],
            'Beyond.Gameplay.Core.AbilityActionMap', source)
    require(list_calls[1]['genericType']['elementTypeName'],
            'Beyond.Gameplay.Core.TimelineAction+TimelineActionData', source)
    require(action_group_call['genericType']['typeName'], 'Beyond.Gameplay.Core.ActionGroupData', source)

    # Continue the second ActionGroupData list through the concrete timeline
    # element reader. These are exact static reader/type joins; formatter and
    # provider selection for any current VFS file remain unobserved.
    timeline_action_type = type_index(
        'Beyond.Gameplay.Core.TimelineAction+TimelineActionData',
        'Gameplay.Beyond.dll')
    require(timeline_action_type, 9199, source, timeline_action_type)
    timeline_action_fields = field_layout(timeline_action_type, {
        '_startFrame', '_endFrame', '_sequenceActionData', 'forceSyncAnimData',
    })
    force_sync_type = type_index(
        'Beyond.Gameplay.Core.TimelineAction+ForceSyncAnimData',
        'Gameplay.Beyond.dll')
    require(force_sync_type, 9198, source, force_sync_type)
    force_sync_fields = field_layout(force_sync_type, {
        'forceSync', 'montageName', 'targetFrame', 'playbackSpeed',
    })
    timeline_field_expectations = (
        ('_endFrame', 0x14, 'System.Int32'),
        ('_sequenceActionData', 0x18,
         'Beyond.Gameplay.Core.SequenceActionData'),
        ('_startFrame', 0x10, 'System.Int32'),
        ('forceSyncAnimData', 0x20,
         'Beyond.Gameplay.Core.TimelineAction+ForceSyncAnimData'),
    )
    timeline_field_rows = {}
    for field_name, field_offset, wire_type in timeline_field_expectations:
        field = timeline_action_fields[field_name]
        require(field['fieldOffset'], field_offset, source,
                field['metadataFieldIndex'])
        identity = field_wire_identity(field_name, field)
        require(identity['wireType'], wire_type, source,
                field['metadataFieldIndex'])
        timeline_field_rows[field_name] = {
            'typeDefinitionIndex': timeline_action_type,
            **field,
            'fieldType': identity,
        }
    force_sync_field_expectations = (
        ('forceSync', 0x10, 'bool'),
        ('montageName', 0x18, 'System.String'),
        ('playbackSpeed', 0x24, 'System.Single'),
        ('targetFrame', 0x20, 'System.Int32'),
    )
    force_sync_field_rows = {}
    for field_name, field_offset, wire_type in force_sync_field_expectations:
        field = force_sync_fields[field_name]
        require(field['fieldOffset'], field_offset, source,
                field['metadataFieldIndex'])
        identity = field_wire_identity(field_name, field)
        require(identity['wireType'], wire_type, source,
                field['metadataFieldIndex'])
        force_sync_field_rows[field_name] = {
            'typeDefinitionIndex': force_sync_type,
            **field,
            'fieldType': identity,
        }

    timeline_reader_methods = module_methods(pe, md, modules, image_owners, [
        (104653,
         'Beyond.MemoryPack.Beyond_Gameplay_Core_TimelineAction_TimelineActionDataForMemoryPack',
         'Deserialize', 0x32CCF70),
        (104654,
         'Beyond.MemoryPack.Beyond_Gameplay_Core_TimelineAction_TimelineActionDataForMemoryPack+'
         'Beyond_Gameplay_Core_TimelineAction_TimelineActionDataForMemoryPackFormatter',
         'Deserialize', 0x32CE8C0),
        (107909,
         'Beyond.MemoryPack.Beyond_Gameplay_Core_TimelineAction_ForceSyncAnimDataForMemoryPack',
         'Deserialize', 0x32CE4B0),
        (107910,
         'Beyond.MemoryPack.Beyond_Gameplay_Core_TimelineAction_ForceSyncAnimDataForMemoryPack+'
         'Beyond_Gameplay_Core_TimelineAction_ForceSyncAnimDataForMemoryPackFormatter',
         'Deserialize', 0x32CE860),
    ], source=source, expected_image='MemoryPack.Beyond.dll')
    timeline_reader_code_windows = []
    for start_rva, end_rva, expected_sha, role in (
        (0x32CCF70, 0x32CD277,
         'CB497F6362D9DA9396D6533F6CC037536FC9499D67848F1E8BBBAC8AA2F03688',
         'TimelineActionData Deserialize: selected source-read path and bounded failure/return fragments'),
        (0x32CE4B0, 0x32CE75C,
         '1FB17BEDE173176E0BC082E7C315267B6FC6F3CE76796DB90A627E9B0E9D7767',
         'ForceSyncAnimData Deserialize: selected source-read path and bounded failure/return fragments'),
        (0x32CE860, 0x32CE8C0,
         '1F6F3F32B14A6DCBB87743E94C1DB14106B3AB3EE17D6C6EBB14F7DB0347A3EB',
         'ForceSyncAnimData formatter forwarding window'),
        (0x32CE8C0, 0x32CE920,
         'D0D022A7D27D843AD4BFFE86FEC8A5FA07037249273A8ECB5AEC0167FEF98F33',
         'TimelineActionData formatter forwarding window'),
    ):
        raw = pe.bytes_at_va(pe.image_base + start_rva, end_rva - start_rva)
        digest = hashlib.sha256(raw).hexdigest().upper()
        require(digest, expected_sha, source, start_rva)
        timeline_reader_code_windows.append({
            'startRva': start_rva,
            'endRva': end_rva,
            'byteLength': end_rva - start_rva,
            'sha256': digest,
            'role': role,
        })

    timeline_sequence_read = call_method_spec(
        0x32CD07F, 0x32CD089, 428464, 'ReadValue', 0x2DA5C90)
    require(timeline_sequence_read['index'], 619962, source,
            timeline_sequence_read['usageVa'])
    require(timeline_sequence_read['genericType']['typeDefinitionIndex'], 9202,
            source, timeline_sequence_read['usageVa'])
    require(timeline_sequence_read['genericType']['typeName'],
            'Beyond.Gameplay.Core.SequenceActionData', source,
            timeline_sequence_read['usageVa'])
    timeline_force_sync_read = call_method_spec(
        0x32CD16F, 0x32CD179, 428464, 'ReadValue', 0x2DA5C90)
    require(timeline_force_sync_read['index'], 620038, source,
            timeline_force_sync_read['usageVa'])
    require(timeline_force_sync_read['genericType']['typeDefinitionIndex'], 9198,
            source, timeline_force_sync_read['usageVa'])
    require(timeline_force_sync_read['genericType']['typeName'],
            'Beyond.Gameplay.Core.TimelineAction+ForceSyncAnimData', source,
            timeline_force_sync_read['usageVa'])

    def timeline_helper_call(call_rva, target_rva, role):
        raw = pe.bytes_at_va(pe.image_base + call_rva, 5)
        require(raw[:1], b'\xE8', source, call_rva)
        require(relative_branch_target(raw, pe.image_base + call_rva, source=source),
                pe.image_base + target_rva, source, call_rva)
        return {'callInstructionRva': call_rva,
                'callInstructionHex': raw.hex().upper(),
                'targetRva': target_rva,
                'role': role}

    timeline_reader_instructions = []
    for rva, expected_hex, role in (
        (0x32CD04E, '4080FE04', 'TimelineActionData accepts member-count header 4 on this path'),
        (0x32CD079, '894614', 'store endFrame result at object offset +0x14'),
        (0x32CD0BC, '49894018', 'store SequenceActionData result at object offset +0x18'),
        (0x32CD126, '448B30', 'load the startFrame DWORD from the current cursor'),
        (0x32CD142, '4883435004', 'advance the startFrame source cursor by four bytes'),
        (0x32CD147, '83434004', 'advance the consumed counter for startFrame by four'),
        (0x32CD14B, '83434404', 'advance the total counter for startFrame by four'),
        (0x32CD168, '44897010', 'store startFrame at object offset +0x10'),
        (0x32CD19B, '49894020', 'store ForceSyncAnimData result at object offset +0x20'),
        (0x32CE57E, '4080FE04', 'ForceSyncAnimData accepts member-count header 4 on this path'),
        (0x32CE5A9, '884610', 'store forceSync byte at object offset +0x10'),
        (0x32CE5D9, '49894018', 'store montageName result at object offset +0x18'),
        (0x32CE635, 'F30F1030', 'load playbackSpeed float32 from the current cursor'),
        (0x32CE652, '4883435004', 'advance playbackSpeed source cursor by four bytes'),
        (0x32CE67B, 'F30F117024', 'store playbackSpeed float32 at object offset +0x24'),
        (0x32CE69A, '8B28', 'load targetFrame int32 from the current cursor'),
        (0x32CE6B5, '4883435004', 'advance targetFrame source cursor by four bytes'),
        (0x32CE6D8, '896820', 'store targetFrame int32 at object offset +0x20'),
    ):
        raw = pe.bytes_at_va(pe.image_base + rva, len(bytes.fromhex(expected_hex)))
        require(raw, bytes.fromhex(expected_hex), source, rva)
        timeline_reader_instructions.append({
            'rva': rva, 'rawHex': raw.hex().upper(), 'role': role,
        })
    timeline_direct_calls = [
        timeline_helper_call(0x32CD05E, 0x2CA86B0,
                             'read endFrame int32'),
        timeline_helper_call(0x32CE58E, 0x2CA88C0,
                             'read forceSync boolean'),
        timeline_helper_call(0x32CE5B2, 0x2CA8700,
                             'read montageName string'),
    ]
    timeline_action_data_reader = {
        'elementTypeDefinitionIndex': timeline_action_type,
        'elementTypeName': md.type_full_name(md.types[timeline_action_type]),
        'listReaderMethodSpec': list_calls[1],
        'methods': timeline_reader_methods,
        'codeWindows': timeline_reader_code_windows,
        'serializedMembers': [
            {'serializedOrderIndex': 0, 'fieldName': '_endFrame',
             'objectField': timeline_field_rows['_endFrame'],
             'reader': timeline_direct_calls[0]},
            {'serializedOrderIndex': 1, 'fieldName': '_sequenceActionData',
             'objectField': timeline_field_rows['_sequenceActionData'],
             'readerMethodSpec': timeline_sequence_read},
            {'serializedOrderIndex': 2, 'fieldName': '_startFrame',
             'objectField': timeline_field_rows['_startFrame'],
             'reader': {'kind': 'inline-int32', 'byteWidth': 4,
                        'verifiedInstructions': [
                            row for row in timeline_reader_instructions
                            if row['rva'] in (0x32CD126, 0x32CD142,
                                             0x32CD147, 0x32CD14B)]}},
            {'serializedOrderIndex': 3, 'fieldName': 'forceSyncAnimData',
             'objectField': timeline_field_rows['forceSyncAnimData'],
             'readerMethodSpec': timeline_force_sync_read},
        ],
        'forceSyncAnimDataReader': {
            'typeDefinitionIndex': force_sync_type,
            'typeName': md.type_full_name(md.types[force_sync_type]),
            'serializedMembers': [
                {'serializedOrderIndex': 0, 'fieldName': 'forceSync',
                 'objectField': force_sync_field_rows['forceSync'],
                 'reader': timeline_direct_calls[1]},
                {'serializedOrderIndex': 1, 'fieldName': 'montageName',
                 'objectField': force_sync_field_rows['montageName'],
                 'reader': timeline_direct_calls[2]},
                {'serializedOrderIndex': 2, 'fieldName': 'playbackSpeed',
                 'objectField': force_sync_field_rows['playbackSpeed'],
                 'reader': {'kind': 'inline-float32', 'byteWidth': 4,
                            'verifiedInstructions': [
                                row for row in timeline_reader_instructions
                                if row['rva'] in (0x32CE635, 0x32CE652,
                                                 0x32CE67B)]}},
                {'serializedOrderIndex': 3, 'fieldName': 'targetFrame',
                 'objectField': force_sync_field_rows['targetFrame'],
                 'reader': {'kind': 'inline-int32', 'byteWidth': 4,
                            'verifiedInstructions': [
                                row for row in timeline_reader_instructions
                                if row['rva'] in (0x32CE69A, 0x32CE6B5,
                                                 0x32CE6D8)]}},
            ],
            'verifiedInstructionWindows': [
                row for row in timeline_reader_instructions
                if row['rva'] in (0x32CE57E, 0x32CE5A9, 0x32CE5D9)],
        },
        'verifiedInstructionWindows': timeline_reader_instructions,
        'sequenceActionDataReaderReference': {
            'reportKey': 'selectedBuffSequenceReadOrder',
            'methodIndex': 104346,
            'rootRva': 0x39C6AA0,
            'rootCodeWindowSha256': '6444AF67AF86E7809AF5A50AE6DEE922B699DCB1CA686DC81F4C3584AB817B90',
        },
        'level': 'exact current-build module/token, generic MethodSpec, TypeDef field-offset and selected source-read code joins',
        'runtimeProviderSelection': 'unobserved',
        'runtimeCursor': 'unobserved',
        'boundary': ('The exact static list element type is TimelineActionData. Its selected Deserialize normal path reads endFrame, '
                     'SequenceActionData, startFrame and ForceSyncAnimData in that order. ForceSyncAnimData reads forceSync, '
                     'montageName, playbackSpeed and targetFrame; the two trailing scalar members each advance four bytes. '
                     'This establishes a native reader order and widths for those scalar fields only. The list/formatter/provider '
                     'chosen for current VFS files, dynamic string extent, successful runtime cursor and enclosing record/EOF '
                     'remain unobserved; these static paths do not close a SkillData parent.'),
    }

    terminal_method_calls = {
        'tagDuringAttach': call_method_spec(
            0x37DE8E9, 0x37DE8F3, 428464, 'ReadValue', 0x2DA5C90),
        'toggleBuffs': call_method_spec(
            0x37DE921, 0x37DE92E, 428462, 'ReadPackable', 0x381F8F0),
        'uiRangeHints': call_method_spec(
            0x37DE95C, 0x37DE969, 428462, 'ReadPackable', 0x381F8F0),
    }
    require(terminal_method_calls['tagDuringAttach']['genericType']['typeName'],
            'Beyond.Gameplay.Core.GameplayTagList', source)
    for field_name, element_name in (
            ('toggleBuffs', 'Beyond.Gameplay.Core.ToggleBuffData'),
            ('uiRangeHints', 'Beyond.Gameplay.Core.UIRangeHintData')):
        generic = terminal_method_calls[field_name]['genericType']
        require(generic['typeName'], 'System.Collections.Generic.List`1',
                source, terminal_method_calls[field_name]['usageVa'])
        require(generic['elementTypeName'], element_name,
                source, terminal_method_calls[field_name]['usageVa'])

    cursor_hook_sites = skilldata_cursor_hook_call_sites(pe, source=source)
    tail_field_expectations = [
        (43, 'switchToCenterBeforeCast', 'bool', 0xA5, 0x37DE8C5,
         0x2CA88C0, 0x37DE8E0, '8881A5000000', None),
        (44, 'tagDuringAttach', 'Beyond.Gameplay.Core.GameplayTagList', 0xB8,
         0x37DE8F3, 0x2DA5C90, 0x37DE90E, '488981B8000000',
         terminal_method_calls['tagDuringAttach']),
        (45, 'toggleBuffs',
         'System.Collections.Generic.List`1<Beyond.Gameplay.Core.ToggleBuffData>',
         0xD8, 0x37DE92E, 0x381F8F0, 0x37DE949, '488981D8000000',
         terminal_method_calls['toggleBuffs']),
        (46, 'uiRangeHints',
         'System.Collections.Generic.List`1<Beyond.Gameplay.Core.UIRangeHintData>',
         0xC8, 0x37DE969, 0x381F8F0, 0x37DE984, '488981C8000000',
         terminal_method_calls['uiRangeHints']),
        (47, 'useAIExclusiveFrame', 'bool', 0x58, 0x37DE99D,
         0x2CA88C0, 0x37DE9C2, '884158', None),
    ]
    tail_reads = []
    for order_index, field_name, expected_wire_type, expected_offset, call_rva, target_rva, store_rva, store_hex, method_spec in tail_field_expectations:
        field = skill_fields[field_name]
        require(field['fieldOffset'], expected_offset, source,
                field['metadataFieldIndex'])
        field_type = field_wire_identity(field_name, field)
        require(field_type['wireType'], expected_wire_type, source,
                field['metadataFieldIndex'])
        if method_spec is not None:
            generic = method_spec['genericType']
            if field_type['typeKind'] == 0x15:
                require(field_type['typeDefinitionIndex'], generic['typeDefinitionIndex'],
                        source, field['metadataFieldIndex'])
                require(field_type['elementTypeDefinitionIndex'],
                        generic['elementTypeDefinitionIndex'], source,
                        field['metadataFieldIndex'])
            else:
                require(field_type['typeDefinitionIndex'],
                        generic['typeDefinitionIndex'], source,
                        field['metadataFieldIndex'])
        store_raw = pe.bytes_at_va(pe.image_base + store_rva, len(bytes.fromhex(store_hex)))
        require(store_raw, bytes.fromhex(store_hex), source, store_rva)
        call_raw = pe.bytes_at_va(pe.image_base + call_rva, 5)
        if method_spec is None:
            helper_site = next(site for site in cursor_hook_sites['sites']
                               if site['callInstructionRva'] == call_rva)
            require(helper_site['targetRva'], target_rva, source, call_rva)
        else:
            require(method_spec['targetRva'], target_rva, source, call_rva)
        tail_reads.append({
            'serializedOrderIndex': order_index,
            'fieldName': field_name,
            'wireType': field_type['wireType'],
            'fieldType': field_type,
            'objectField': {
                'metadataFieldIndex': field['metadataFieldIndex'],
                'fieldOffset': field['fieldOffset'],
                'metadataTypeIndex': field['metadataTypeIndex'],
            },
            'callInstructionRva': call_rva,
            'callInstructionHex': call_raw.hex().upper(),
            'readerTargetRva': target_rva,
            'readerOperation': ('native-bool-read-helper' if method_spec is None else
                                method_spec['methodIdentity']['name']),
            'readerMethodSpec': method_spec,
            'storeInstructionRva': store_rva,
            'storeInstructionHex': store_raw.hex().upper(),
        })

    gameplay_tag_list_type = type_index(
        'Beyond.Gameplay.Core.GameplayTagList', 'Gameplay.Beyond.dll')
    gameplay_tag_list_definition = md.types[gameplay_tag_list_type]
    require(gameplay_tag_list_definition.field_count, 1, source, gameplay_tag_list_type)
    wrapper_fields = field_layout(gameplay_tag_list_type, {'predefinedTag'})
    wrapper_member_field = wrapper_fields['predefinedTag']
    wrapper_member_type = field_wire_identity('predefinedTag', wrapper_member_field)
    if wrapper_member_type['typeKind'] != 0x15:
        raise ContextError(source, wrapper_member_field['metadataFieldIndex'],
                           'GameplayTagList.predefinedTag is a generic List<GameplayTag>',
                           wrapper_member_type)
    require(wrapper_member_type['wireType'],
            'System.Collections.Generic.List`1<Beyond.Gameplay.Core.GameplayTag>',
            source, wrapper_member_field['metadataFieldIndex'])
    wrapper_nested_arguments = wrapper_evidence.get('elementInstantiation', {}).get('arguments')
    if (not isinstance(wrapper_nested_arguments, (list, tuple)) or
            len(wrapper_nested_arguments) != 1):
        raise ContextError(source, 0, 'wrapper reader nested list has one generic element argument',
                           wrapper_nested_arguments)
    require(wrapper_member_type['elementRawTypeRecordHex'],
            wrapper_nested_arguments[0].get('raw_type_record_hex'),
            source, wrapper_member_field['metadataFieldIndex'])
    wrapper_method_identities = wrapper_evidence.get('methodIdentities')
    if not isinstance(wrapper_method_identities, list) or len(wrapper_method_identities) != 2:
        raise ContextError(source, 0, 'both exact GameplayTagList reader and formatter identities',
                           wrapper_method_identities)
    gameplay_tag_wrapper = {
        'typeDefinitionIndex': gameplay_tag_list_type,
        'typeName': md.type_full_name(gameplay_tag_list_definition),
        'memberCount': gameplay_tag_list_definition.field_count,
        'member': {
            'name': 'predefinedTag',
            'metadataFieldIndex': wrapper_member_field['metadataFieldIndex'],
            'fieldOffset': wrapper_member_field['fieldOffset'],
            'wireType': wrapper_member_type['wireType'],
            'fieldType': wrapper_member_type,
        },
        'readerMethodIdentity': wrapper_method_identities[0],
        'formatterMethodIdentity': wrapper_method_identities[1],
        'nestedReadType': wrapper_member_type['wireType'],
        'nestedReadInstantiation': wrapper_evidence['elementInstantiation'],
        'headerEvidence': wrapper_evidence['wrapperFraming'],
        'headerCodeWindows': wrapper_evidence['headerCodeWindows'],
    }

    nested_reader_methods = module_methods(pe, md, modules, image_owners, [
        (104420, 'Beyond.MemoryPack.Beyond_Gameplay_Core_ToggleBuffDataForMemoryPack',
         'Deserialize', 0x4438A40),
        (104433, 'Beyond.MemoryPack.Beyond_Gameplay_Core_UIRangeHintDataForMemoryPack',
         'Deserialize', 0x3A60AE0),
        (107721, 'Beyond.MemoryPack.Beyond_Gameplay_SkillHintShapeDataForMemoryPack',
         'Deserialize', 0x3997B70),
        (104467, 'Beyond.MemoryPack.Beyond_Gameplay_Core_GameplayTagForMemoryPack',
         'Deserialize', 0x40EFC30),
    ], source=source, expected_image='MemoryPack.Beyond.dll')
    nested_code_windows = []
    for rva, length, expected in (
            (0x4438A40, 0xB3, '79E10BB093386D263DED64AF51B082F0CDEF758DCB7C779AAAB6411839036CC1'),
            (0x3A60AE0, 0xD4, '98CCCC5E6DB50926C87C91CD5465CFAF1FB033DF01AD43ED3490BF760EDE3204'),
            (0x3997B70, 0x33F, '07D6FE9927BF0D51DC1B5BAC8E185C68B695890BCCEF3B780B3F7960AAAAC299'),
            (0x40EFC30, 0x66, '20E91A6A12C8F0744F68C6B10AF26032F7030FA75C62AD17CDCFDF986A18EF89')):
        raw = pe.bytes_at_va(pe.image_base + rva, length)
        digest = hashlib.sha256(raw).hexdigest().upper()
        require(digest, expected, source, rva)
        nested_code_windows.append({'rva': rva, 'byteLength': length,
                                    'sha256': digest, 'includesNormalReturn': True})

    def direct_reader_call(call_rva, target_rva, role):
        raw = pe.bytes_at_va(pe.image_base + call_rva, 5)
        require(raw[:1], b'\xE8', source, call_rva)
        target = relative_branch_target(raw, pe.image_base + call_rva, source=source)
        require(target, pe.image_base + target_rva, source, call_rva)
        return {'callInstructionRva': call_rva, 'callInstructionHex': raw.hex().upper(),
                'targetRva': target_rva, 'role': role}

    def nested_field(type_def_index, field_rows, field_name, expected_offset, expected_wire):
        field = field_rows[field_name]
        require(field['fieldOffset'], expected_offset, source,
                field['metadataFieldIndex'])
        identity = field_wire_identity(field_name, field)
        require(identity['wireType'], expected_wire, source,
                field['metadataFieldIndex'])
        return {'typeDefinitionIndex': type_def_index,
                'metadataFieldIndex': field['metadataFieldIndex'],
                'metadataTypeIndex': field['metadataTypeIndex'],
                'fieldOffset': field['fieldOffset'], 'fieldType': identity}

    toggle_type = type_index('Beyond.Gameplay.Core.ToggleBuffData',
                             'Gameplay.Beyond.dll')
    toggle_definition = md.types[toggle_type]
    require(toggle_definition.field_count, 2, source, toggle_type)
    toggle_fields = field_layout(toggle_type, {'buffs', 'conditions'})
    toggle_buff_field = nested_field(
        toggle_type, toggle_fields, 'buffs', 0x18,
        'System.Collections.Generic.List`1<Beyond.Gameplay.Core.BuffInput>')
    toggle_condition_field = nested_field(
        toggle_type, toggle_fields, 'conditions', 0x10,
        'System.Collections.Generic.List`1<Beyond.Gameplay.Core.Abilities.Condition.ConditionBase>')
    toggle_buff_read = call_method_spec(
        0x4438A95, 0x4438AA2, 428462, 'ReadPackable', 0x381F8F0)
    toggle_condition_read = call_method_spec(
        0x4438ABE, 0x4438ACB, 428462, 'ReadPackable', 0x381F8F0)
    for name, read, element_name in (
            ('buffs', toggle_buff_read, 'Beyond.Gameplay.Core.BuffInput'),
            ('conditions', toggle_condition_read,
             'Beyond.Gameplay.Core.Abilities.Condition.ConditionBase')):
        require(read['genericType']['typeName'],
                'System.Collections.Generic.List`1', source, read['usageVa'])
        require(read['genericType']['elementTypeName'], element_name,
                source, read['usageVa'])
    toggle_schema = {
        'typeDefinitionIndex': toggle_type,
        'typeName': md.type_full_name(toggle_definition),
        'memberCountCompare': {
            'rva': 0x4438A8B, 'rawHex': '4080FD02', 'memberCount': 2},
        'members': [
            {'serializedOrderIndex': 0, 'fieldName': 'buffs',
             'objectField': toggle_buff_field, 'readerMethodSpec': toggle_buff_read,
             'setterCall': direct_reader_call(0x4438AB9, 0x3209E50, 'store buffs result')},
            {'serializedOrderIndex': 1, 'fieldName': 'conditions',
             'objectField': toggle_condition_field,
             'readerMethodSpec': toggle_condition_read,
             'setterCall': direct_reader_call(0x4438ADE, 0x3207AC0,
                                               'store conditions result')},
        ],
        'sourceParserOrder': ['buffs', 'conditions'],
    }

    gameplay_tag_type = type_index('Beyond.Gameplay.Core.GameplayTag',
                                   'Gameplay.Beyond.dll')
    gameplay_tag_definition = md.types[gameplay_tag_type]
    require(gameplay_tag_definition.field_count, 4, source, gameplay_tag_type)
    gameplay_tag_fields = field_layout(gameplay_tag_type, {'tagId'})
    gameplay_tag_id_field = nested_field(
        gameplay_tag_type, gameplay_tag_fields, 'tagId', 0x10, 'System.Int32')
    tag_cursor_helper_windows = []
    for rva, length, expected in (
            (0x2CA8860, 0x57,
             'CA6788FE028DC684758CD40833EFA107116A7BF664BFBF1746D792E52114639F'),
            (0x2CA86B0, 0x50,
             '2358C208F5DDD372AF9E5401907272C1FB2A6E4C49E211689FFC047A2872BB65')):
        raw = pe.bytes_at_va(pe.image_base + rva, length)
        digest = hashlib.sha256(raw).hexdigest().upper()
        require(digest, expected, source, rva)
        tag_cursor_helper_windows.append({'rva': rva, 'byteLength': length,
                                          'sha256': digest})
    tag_cursor_instruction_rows = []
    for rva, raw_hex, operation, byte_width in (
            (0x2CA886F, '83793001', 'require at least one remaining byte', 0),
            (0x2CA8883, '0FB608', 'load one member-count byte', 1),
            (0x2CA8894, '48FF4350', 'advance cursor pointer by one byte', 1),
            (0x2CA8898, 'FF4340', 'increment consumed counter by one byte', 0),
            (0x2CA889B, 'FF4344', 'increment total counter by one byte', 0),
            (0x2CA889E, '897B30', 'store remaining length after subtracting one', 0),
            (0x2CA86BF, '83793004', 'require at least four remaining bytes', 0),
            (0x2CA86D0, '8B30', 'load one little-endian int32', 4),
            (0x2CA86DE, '4883435004', 'advance cursor pointer by four bytes', 4),
            (0x2CA86E3, '83434004', 'increment consumed counter by four bytes', 0),
            (0x2CA86E7, '83434404', 'increment total counter by four bytes', 0),
            (0x2CA86EB, '897B30', 'store remaining length after subtracting four', 0)):
        expected_raw = bytes.fromhex(raw_hex)
        actual_raw = pe.bytes_at_va(pe.image_base + rva, len(expected_raw))
        require(actual_raw, expected_raw, source, rva)
        tag_cursor_instruction_rows.append({
            'rva': rva, 'rawHex': actual_raw.hex().upper(),
            'operation': operation, 'byteWidth': byte_width,
        })
    gameplay_tag_reader = {
        'typeDefinitionIndex': gameplay_tag_type,
        'typeName': md.type_full_name(gameplay_tag_definition),
        'fieldCount': gameplay_tag_definition.field_count,
        'readerMethodIdentity': next(
            row for row in nested_reader_methods if row['methodIndex'] == 104467),
        'memberCountCheck': {
            'rva': 0x40EFC6D, 'rawHex': '807C243001',
            'acceptedMemberCount': 1,
        },
        'tagIdField': gameplay_tag_id_field,
        'readerCall': direct_reader_call(0x40EFC7E, 0x2CA86B0,
                                         'read int32/unmanaged tagId'),
        'storeInstruction': {
            'rva': 0x40EFC88, 'rawHex': '894310',
            'objectFieldOffset': 0x10,
            'wireType': gameplay_tag_id_field['fieldType']['wireType'],
        },
        'cursorAdvancement': {
            'helperCodeWindows': tag_cursor_helper_windows,
            'verifiedInstructions': tag_cursor_instruction_rows,
            'validNormalPathByteWidth': 5,
            'derivation': 'The count helper reads and advances one byte; the int32 helper requires four remaining bytes, reads a four-byte value, and advances cursor/consumed/total by four. The generated reader accepts count one before calling the int32 helper.',
        },
        'normalReturnPathWindow': {
            'rva': 0x40EFC30, 'byteLength': 0x66,
            'sha256': nested_code_windows[-1]['sha256'],
            'normalReturnRva': 0x40EFC95,
            'coldFailureTargetsOutsideWindow': [0xF7A932, 0xF7A95D, 0xF7A997],
        },
        'boundary': 'The registered generated GameplayTag reader accepts member count one on this normal path, consumes a raw int32 and stores it to tagId. Cold malformed-header handlers are outside the pinned normal-return window; this is not runtime list-element dispatch evidence.',
    }
    header_read = direct_reader_call(0x40EFC56, 0x2CA8860,
                                     'read one-byte member count')
    require(pe.bytes_at_va(pe.image_base + 0x40EFC6D, 5),
            bytes.fromhex('807C243001'), source, 0x40EFC6D)
    require(pe.bytes_at_va(pe.image_base + 0x40EFC88, 3),
            bytes.fromhex('894310'), source, 0x40EFC88)
    gameplay_tag_reader['memberCountReadCall'] = header_read

    ui_range_type = type_index('Beyond.Gameplay.Core.UIRangeHintData',
                               'Gameplay.Beyond.dll')
    ui_range_definition = md.types[ui_range_type]
    require(ui_range_definition.field_count, 3, source, ui_range_type)
    ui_range_fields = field_layout(ui_range_type, {'selectAll', 'shapeData', 'targetFaction'})
    ui_select_field = nested_field(ui_range_type, ui_range_fields, 'selectAll', 0x14, 'bool')
    ui_shape_field = nested_field(ui_range_type, ui_range_fields, 'shapeData', 0x18,
                                  'Beyond.Gameplay.SkillHintShapeData')
    ui_faction_field = nested_field(ui_range_type, ui_range_fields, 'targetFaction', 0x10,
                                    'Beyond.Gameplay.Core.FactionType')
    ui_shape_read = call_method_spec(
        0x3A60B57, 0x3A60B64, 428464, 'ReadValue', 0x2DA5C90)
    ui_faction_read = call_method_spec(
        0x3A60B80, 0x3A60B8D, 428448, 'ReadUnmanaged', 0x2CA86B0)
    require(ui_shape_read['genericType']['typeName'],
            'Beyond.Gameplay.SkillHintShapeData', source, ui_shape_read['usageVa'])
    require(ui_faction_read['genericType']['typeName'],
            'Beyond.Gameplay.Core.FactionType', source, ui_faction_read['usageVa'])
    ui_range_schema = {
        'typeDefinitionIndex': ui_range_type,
        'typeName': md.type_full_name(ui_range_definition),
        'memberCountCompare': {
            'rva': 0x3A60B2B, 'rawHex': '4080FD03', 'memberCount': 3},
        'members': [
            {'serializedOrderIndex': 0, 'fieldName': 'selectAll',
             'objectField': ui_select_field,
             'readerCall': direct_reader_call(0x3A60B3B, 0x2CA88C0,
                                               'read boolean member'),
             'setterCall': direct_reader_call(0x3A60B52, 0x50816CC,
                                               'store selectAll')},
            {'serializedOrderIndex': 1, 'fieldName': 'shapeData',
             'objectField': ui_shape_field, 'readerMethodSpec': ui_shape_read,
             'setterCall': direct_reader_call(0x3A60B7B, 0x3209E50,
                                               'store shapeData')},
            {'serializedOrderIndex': 2, 'fieldName': 'targetFaction',
             'objectField': ui_faction_field, 'readerMethodSpec': ui_faction_read,
             'setterCall': direct_reader_call(0x3A60B9F, 0x507E454,
                                               'store targetFaction')},
        ],
        'sourceParserOrder': ['selectAll', 'shapeData', 'targetFaction'],
    }

    shape_type = type_index('Beyond.Gameplay.SkillHintShapeData',
                            'Gameplay.Beyond.dll')
    shape_definition = md.types[shape_type]
    require(shape_definition.field_count, 21, source, shape_type)
    shape_field_names = {
        'angle', 'angleKey', 'centerBaseIsEndPoint', 'centerOffset',
        'centerOffsetXKey', 'centerOffsetZKey', 'extent', 'extentXKey',
        'extentZKey', 'fixedExtent', 'radius', 'radiusKey',
        'restrictEndPointInRange', 'shape', 'useAngleKey',
        'useCenterOffsetKey', 'useExtentKey', 'useRadiusKey',
        'useWidthKey', 'width', 'widthKey'}
    shape_fields = field_layout(shape_type, shape_field_names)
    shape_field_layout = {
        'shape': (0x10, 'Beyond.Gameplay.SkillHintShape'),
        'fixedExtent': (0x14, 'bool'),
        'centerBaseIsEndPoint': (0x15, 'bool'),
        'restrictEndPointInRange': (0x16, 'bool'),
        'useCenterOffsetKey': (0x17, 'bool'),
        'centerOffset': (0x18, 'UnityEngine.Vector2'),
        'centerOffsetXKey': (0x20, 'System.String'),
        'centerOffsetZKey': (0x28, 'System.String'),
        'useExtentKey': (0x30, 'bool'),
        'extent': (0x34, 'UnityEngine.Vector2'),
        'extentXKey': (0x40, 'System.String'),
        'extentZKey': (0x48, 'System.String'),
        'useWidthKey': (0x50, 'bool'),
        'width': (0x54, 'System.Single'),
        'widthKey': (0x58, 'System.String'),
        'useRadiusKey': (0x60, 'bool'),
        'radius': (0x64, 'System.Single'),
        'radiusKey': (0x68, 'System.String'),
        'useAngleKey': (0x70, 'bool'),
        'angle': (0x74, 'System.Single'),
        'angleKey': (0x78, 'System.String'),
    }
    shape_field_contracts = {}
    for name, (offset, wire_type) in shape_field_layout.items():
        shape_field_contracts[name] = nested_field(
            shape_type, shape_fields, name, offset, wire_type)

    shape_operations = [
        ('angle', 'System.Single', 0x3997BCB, 0x2CA8BB0, 0x3997BE2, 0x507E524, None, None),
        ('angleKey', 'System.String', 0x3997BED, 0x2CA8700, 0x3997C04, 0x320C9C0, None, None),
        ('centerBaseIsEndPoint', 'bool', 0x3997C0F, 0x2CA88C0, 0x3997C26, 0x50816E8, None, None),
        ('centerOffset', 'UnityEngine.Vector2', 0x3997C38, 0x3D7E030, 0x3997C4F, 0x5081704,
         0x3997C2B, 'UnityEngine.Vector2'),
        ('centerOffsetXKey', 'System.String', 0x3997C5A, 0x2CA8700, 0x3997C71, 0x3207A90, None, None),
        ('centerOffsetZKey', 'System.String', 0x3997C7C, 0x2CA8700, 0x3997C93, 0x320AC10, None, None),
        ('extent', 'UnityEngine.Vector2', 0x3997CA5, 0x3D7E030, 0x3997CBC, 0x508160C,
         0x3997C98, 'UnityEngine.Vector2'),
        ('extentXKey', 'System.String', 0x3997CC7, 0x2CA8700, 0x3997CDE, 0x3209DF0, None, None),
        ('extentZKey', 'System.String', 0x3997CE9, 0x2CA8700, 0x3997D00, 0x320BA00, None, None),
        ('fixedExtent', 'bool', 0x3997D0B, 0x2CA88C0, 0x3997D22, 0x50816CC, None, None),
        ('radius', 'System.Single', 0x3997D2D, 0x2CA8BB0, 0x3997D44, 0x5081400, None, None),
        ('radiusKey', 'System.String', 0x3997D4F, 0x2CA8700, 0x3997D66, 0x320C900, None, None),
        ('restrictEndPointInRange', 'bool', 0x3997D71, 0x2CA88C0, 0x3997D88, 0x50816B0, None, None),
        ('shape', 'Beyond.Gameplay.SkillHintShape', 0x3997D9A, 0x2CA86B0, 0x3997DB0, 0x507E454,
         0x3997D8D, 'Beyond.Gameplay.SkillHintShape'),
        ('useAngleKey', 'bool', 0x3997DBB, 0x2CA88C0, 0x3997DD2, 0x507E544, None, None),
        ('useCenterOffsetKey', 'bool', 0x3997DDD, 0x2CA88C0, 0x3997DF4, 0x5081694, None, None),
        ('useExtentKey', 'bool', 0x3997DFF, 0x2CA88C0, 0x3997E16, 0x507DEC8, None, None),
        ('useRadiusKey', 'bool', 0x3997E21, 0x2CA88C0, 0x3997E38, 0x507E5F8, None, None),
        ('useWidthKey', 'bool', 0x3997E43, 0x2CA88C0, 0x3997E5A, 0x507EFF0, None, None),
        ('width', 'System.Single', 0x3997E65, 0x2CA8BB0, 0x3997E7C, 0x5081674, None, None),
        ('widthKey', 'System.String', 0x3997E87, 0x2CA8700, 0x3997E9A, 0x320BA60, None, None),
    ]
    shape_serialized_rows = []
    for order_index, (name, wire_type, read_rva, read_target, store_rva,
                      store_target, spec_load_rva, spec_type_name) in enumerate(shape_operations):
        field_contract = shape_field_contracts[name]
        require(field_contract['fieldType']['wireType'], wire_type, source,
                field_contract['metadataFieldIndex'])
        method_spec = None
        if spec_load_rva is not None:
            method_spec = call_method_spec(
                spec_load_rva, read_rva, 428448, 'ReadUnmanaged', read_target)
            require(method_spec['genericType']['typeName'], spec_type_name,
                    source, method_spec['usageVa'])
        else:
            direct_reader_call(read_rva, read_target, f'read {name}')
        setter = direct_reader_call(store_rva, store_target, f'store {name}')
        shape_serialized_rows.append({
            'serializedOrderIndex': order_index,
            'fieldName': name,
            'wireType': wire_type,
            'objectField': field_contract,
            'readerMethodSpec': method_spec,
            'readerCall': {'callInstructionRva': read_rva,
                           'targetRva': read_target,
                           'role': 'MemoryPackReader.ReadUnmanaged generic' if method_spec else
                                   'primitive reader helper'},
            'setterCall': setter,
        })
    shape_schema = {
        'typeDefinitionIndex': shape_type,
        'typeName': md.type_full_name(shape_definition),
        'memberCountCompare': {
            'rva': 0x3997BBB, 'rawHex': '4080FD15', 'memberCount': 21},
        'serializedOrder': shape_serialized_rows,
        'metadataStorageOrder': [
            md.string(md.fields[shape_definition.field_start + index].name_index)
            for index in range(shape_definition.field_count)],
        'sourceParserOrder': [row[0] for row in shape_operations],
    }
    nested_terminal_readers = {
        'status': 'static-registered-reader-layout',
        'methods': nested_reader_methods,
        'codeWindows': nested_code_windows,
        'gameplayTagElement': gameplay_tag_reader,
        'toggleBuffData': toggle_schema,
        'uiRangeHintData': ui_range_schema,
        'skillHintShapeData': shape_schema,
        'boundary': 'The exact generated nested reader bodies, MethodSpecs, declared field types/offsets and parser order align for the authenticated build. The GameplayTag element path accepts member count one, then bounded helpers advance one header byte and four System.Int32 bytes; its five-byte endpoint agrees with the source parser under this static path. The parser preserves the id bytes as unsigned raw/hash and signed views. Other rows are static registered paths too; current per-file live selection and parent cursor remain unobserved.',
    }

    crosscheck = skilldata_corpus_branch_evidence(corpus, source='reports/animestudio/skilldata_current_latest.json')
    terminal_collision = skilldata_terminal_collision_evidence(
        corpus, source='reports/animestudio/skilldata_current_latest.json')
    terminal_sample = skilldata_terminal_sample_byte_witness(
        terminal_collision, representative_sample_raw,
        source='export_full/structured/StreamingAssets/Data/Json/SkillData/Potential_test.json')
    terminal_tail_layout = skilldata_terminal_tail_layout(
        terminal_collision, terminal_sample, tail_reads, gameplay_tag_wrapper,
        source=source)
    empty_count = crosscheck['branchCounts']['bothListsEmpty']
    return {
        'status': 'static-reader-order-conditional-cursor',
        'inputSetSha256': crosscheck['inputSetSha256'],
        'methods': selected_methods,
        'codeWindows': code_windows,
        'verifiedInstructionWindows': instruction_windows,
        'formatterThunkEdges': formatter_thunks,
        'firstSkillDataField': {
            'serializedOrderIndex': 0,
            'fieldName': 'actionGroupData',
            'objectField': {'typeDefinitionIndex': skill_type, **skill_fields['actionGroupData']},
            'readerMethodSpec': action_group_call,
            'staticEvidence': 'SkillData Deserialize validates top-level header 48, calls ReadValue<Core.ActionGroupData>, then stores the returned object to Core.SkillData+0xC0 before the next member reader call.',
        },
        'actionGroupDataMembers': [
            {'serializedOrderIndex': index, 'fieldName': name,
             'objectField': {'typeDefinitionIndex': action_group_type, **action_fields[name]},
             'readerMethodSpec': call}
            for index, (name, call) in enumerate((('passiveEventActions', list_calls[0]),
                                                   ('timelineActions', list_calls[1])))
        ],
        'timelineActionDataReader': timeline_action_data_reader,
        'currentVfsBranchCrossCheck': crosscheck,
        'representativeTerminalShapeCollision': terminal_collision,
        'representativeTerminalSampleByteWitness': terminal_sample,
        'representativeTerminalTailLayout': terminal_tail_layout,
        'nestedTerminalReaders': nested_terminal_readers,
        'cursorHookCallSites': cursor_hook_sites,
        'conditionalEmptyObjectRange': {
            'start': 1, 'end': 10, 'endExclusive': True,
            'candidateFiles': empty_count,
            'status': 'conditional-on-provider-selection',
            'formatterCandidateReportKey': 'selectedListFormatterCandidate',
            'condition': 'The ordinary provider resolves both List<T> queries to the audited MemoryPack.Formatters.ListFormatter<T> candidate; each zero count consumes its four-byte collection header and returns without an element body.',
        },
        'exactClosedActionGroupDataRecords': 0,
        'level': 'exact selected-build generated-reader module/token, body-window, MethodSpec, generic field type, object-field-offset and current positive-branch byte-range joins',
        'boundary': 'The five terminal SkillData reads and nested GameplayTag, ToggleBuffData, UIRangeHintData and SkillHintShapeData readers join exact registered static bodies, MethodSpecs, declared IL2CPP field types/offsets and current source bytes. Selected branches cover every positive list-count shape observed in the authenticated corpus. GameplayTag elements match five-byte native paths; other nested parsers match their reported ends and field order. Under the registered wrapper/List<GameplayTag> path, shifted candidates with wrapper bytes 0 or 3 leave the supported header path, while the count-one case produces a signed list count of 0x01000000 with only 13 bytes remaining and takes the pinned count-range failure path. Runtime provider/cache selection and an executed parent cursor are still unobserved, so this is conditional static evidence, not a promoted whole-file endpoint. The intervening [10,518) bytes stay opaque, [1,10) remains conditional on the two generic list formatter paths, no whole SkillData record is closed, and all 2,621 whole-file terminal candidates remain ambiguous. The authenticated SkillData corpus is not re-streamed by this audit.',
    }


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
    terminal_branch_selections = select_skilldata_terminal_branch_samples(
        corpus, source=str(corpus_path))
    skill_sample_path = (ROOT / 'export_full/structured/StreamingAssets/Data/Json/'
                         'SkillData/Potential_test.json')
    skill_sample_raw = skill_sample_path.read_bytes()
    terminal_branch_sample_paths = [
        ROOT / 'export_full/structured/StreamingAssets' /
        Path(*selection['row']['virtualPath'].split('/'))
        for selection in terminal_branch_selections
    ]
    actiongroup_branch_census_rows = []
    for row in corpus.get('files', []):
        record_lists = row.get('commonPrefixFraming', {}).get('recordLists', [])
        if (record_lists and type(record_lists[0].get('count')) is int and
                record_lists[0]['count'] > 0):
            actiongroup_branch_census_rows.append(row)
    actiongroup_branch_census_sample_paths = [
        ROOT / 'export_full/structured/StreamingAssets' /
        Path(*row['virtualPath'].split('/'))
        for row in actiongroup_branch_census_rows
    ]
    actiongroup_branch_sample_identities = [
        'Data/Json/SkillData/eny_0045_agtrinit_state0_passive.json',
        'Data/Json/SkillData/abilityentity_int_doodad_passive.json',
        'Data/Json/SkillData/chr_0030_zhuangfy_talent1.json',
        'Data/Json/SkillData/sk_wpn_funnel_0006.json',
        'Data/Json/SkillData/sk_wpn_claym_0003.json',
        'Data/Json/SkillData/abilityentity_interact_mud_carpet_passive.json',
    ]
    actiongroup_branch_sample_paths = [
        ROOT / 'export_full/structured/StreamingAssets' / Path(*logical_path.split('/'))
        for logical_path in actiongroup_branch_sample_identities
    ]
    skill_terminal_path = Path(__file__).with_name('memorypack') / 'skill_terminal.py'
    skill_buff_path = Path(__file__).with_name('memorypack') / 'buff.py'
    skill_core_path = Path(__file__).with_name('memorypack') / 'core.py'
    buff_actions_path = Path(__file__).with_name('memorypack') / 'buff_actions.py'
    buff_path=ROOT/'reports/animestudio/buffdata_current_latest.json'
    buff_sha=sha(buff_path);buff_corpus=json.loads(buff_path.read_text(encoding='utf-8'))
    verify_family_report_inputs(buff_corpus,expected_format='animestudio-buffdata-current-vfs-corpus',label='BuffData')
    require(buff_corpus['inputSetSha256'],corpus['inputSetSha256'],buff_path)
    require(buff_corpus['status'],'complete',buff_path)
    mapper_path = ROOT / 'tools/endfield-il2cpp/map_body_targets_to_gameassembly.py'
    catalog_path = ROOT / 'tools/endfield-il2cpp/catalog_option_flow_metadata.py'
    sources = [Path(__file__), Path(__file__).with_name('il2cpp_context.py'),
               mapper_path, catalog_path, ROOT / 'scripts/common.py',
               skill_terminal_path, skill_buff_path, skill_core_path, buff_actions_path,
               skill_sample_path, *terminal_branch_sample_paths,
               *actiongroup_branch_sample_paths,
               *actiongroup_branch_census_sample_paths,
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
               Path(__file__).with_name('buff_44_native.json'),
               Path(__file__).with_name('buff_10f_native.json'),
               Path(__file__).with_name('buff_9b_native.json'),
               Path(__file__).with_name('buff_c5_native.json'),
               Path(__file__).with_name('buff_119_native.json'),
               Path(__file__).with_name('buff_0a_native.json'),
               Path(__file__).with_name('buff_7a_native.json'),
               Path(__file__).with_name('buff_88_native.json'),
               Path(__file__).with_name('buff_48_native.json'),
               Path(__file__).with_name('buff_5a_native.json'),
               Path(__file__).with_name('buff_c4_native.json'),
               Path(__file__).with_name('buff_145_native.json'),
               Path(__file__).with_name('buff_de_native.json'),
               Path(__file__).with_name('buff_bd_native.json'),
               Path(__file__).with_name('buff_6a_native.json'),
               Path(__file__).with_name('buff_24_native.json'),
               Path(__file__).with_name('buff_16b_native.json'),
               Path(__file__).with_name('buff_7e_native.json'),
               Path(__file__).with_name('buff_35_native.json'),
               Path(__file__).with_name('buff_ea_native.json'),
               Path(__file__).with_name('buff_61_native.json'),
               Path(__file__).with_name('buff_3f_native.json'),
               Path(__file__).with_name('buff_14d_native.json'),
               Path(__file__).with_name('buff_73_native.json'),
               Path(__file__).with_name('buff_5d_native.json'),
               Path(__file__).with_name('buff_42_native.json'),
               Path(__file__).with_name('buff_27_native.json'),
               Path(__file__).with_name('buff_95_native.json'),
               Path(__file__).with_name('buff_74_native.json'),
               Path(__file__).with_name('buff_16d_native.json'),
               Path(__file__).with_name('buff_160_native.json'),
               Path(__file__).with_name('buff_89_native.json'),
               Path(__file__).with_name('buff_171_native.json'),
               Path(__file__).with_name('buff_132_native.json'),
               Path(__file__).with_name('buff_d4_native.json'),
               Path(__file__).with_name('buff_d5_native.json'),
               Path(__file__).with_name('buff_d6_native.json'),
               Path(__file__).with_name('buff_60_native.json'),
               Path(__file__).with_name('buff_126_native.json'),
               Path(__file__).with_name('buff_1c_native.json'),
               Path(__file__).with_name('buff_06_native.json'),
               Path(__file__).with_name('buff_142_native.json'),
               Path(__file__).with_name('buff_03_native.json'),
               Path(__file__).with_name('buff_51_native.json'),
               Path(__file__).with_name('buff_5e_native.json'),
               Path(__file__).with_name('buff_13b_native.json'),
               Path(__file__).with_name('buff_84_native.json'),
               Path(__file__).with_name('buff_174_native.json'),
               Path(__file__).with_name('buff_41_native.json'),
               Path(__file__).with_name('buff_a9_native.json'),
               Path(__file__).with_name('buff_62_native.json'),
               Path(__file__).with_name('buff_13c_native.json'),
               Path(__file__).with_name('buff_90_native.json'),
               Path(__file__).with_name('buff_bb_native.json'),
               Path(__file__).with_name('buff_0b_native.json'),
               Path(__file__).with_name('buff_2b_native.json'),
               Path(__file__).with_name('buff_115_native.json'),
               Path(__file__).with_name('buff_151_native.json'),
               Path(__file__).with_name('buff_13f_native.json'),
               Path(__file__).with_name('buff_140_native.json'),
               Path(__file__).with_name('buff_98_native.json'),
               Path(__file__).with_name('buff_176_native.json'),
               Path(__file__).with_name('buff_93_native.json'),
               Path(__file__).with_name('buff_175_native.json'),
               Path(__file__).with_name('buff_fc_native.json'),
               Path(__file__).with_name('buff_83_native.json'),
               Path(__file__).with_name('buff_13a_native.json'),
               Path(__file__).with_name('buff_86_native.json'),
               Path(__file__).with_name('buff_63_native.json'),
               Path(__file__).with_name('buff_6b_native.json'),
               Path(__file__).with_name('buff_77_native.json'),
               Path(__file__).with_name('buff_188_native.json'),
               Path(__file__).with_name('buff_40_native.json'),
               Path(__file__).with_name('buff_187_native.json'),
               Path(__file__).with_name('buff_139_native.json'),
               Path(__file__).with_name('buff_18a_native.json'),
               Path(__file__).with_name('buff_135_native.json'),
               Path(__file__).with_name('buff_122_native.json'),
               Path(__file__).with_name('buff_5c_native.json'),
               Path(__file__).with_name('buff_183_native.json'),
               Path(__file__).with_name('buff_2f_native.json'),
               Path(__file__).with_name('buff_15c_native.json'),
               Path(__file__).with_name('buff_16f_native.json'),
               Path(__file__).with_name('buff_05_native.json'),
               Path(__file__).with_name('buff_3a_native.json'),
               Path(__file__).with_name('buff_4c_native.json'),
               Path(__file__).with_name('buff_150_native.json'),
               Path(__file__).with_name('buff_a7_native.json'),
               Path(__file__).with_name('buff_19e_native.json'),
               Path(__file__).with_name('buff_08_native.json'),
               Path(__file__).with_name('buff_120_native.json'),
               Path(__file__).with_name('buff_9f_native.json'),
               Path(__file__).with_name('buff_1b_native.json'),
               Path(__file__).with_name('buff_87_native.json'),
               Path(__file__).with_name('buff_52_native.json'),
               Path(__file__).with_name('buff_8e_native.json'),
               Path(__file__).with_name('finder_0a_native.json'),
               Path(__file__).with_name('finder_15_native.json'),
               Path(__file__).with_name('finder_0e_native.json'),
               Path(__file__).with_name('buff_125_native.json'),
               Path(__file__).with_name('buff_124_native.json'),
               Path(__file__).with_name('buff_14f_native.json'),
               Path(__file__).with_name('buff_71_native.json'),
               Path(__file__).with_name('buff_70_native.json'),
               Path(__file__).with_name('finder_10_native.json'),
               Path(__file__).with_name('finder_01_native.json'),
               Path(__file__).with_name('validator_01_native.json'),
               Path(__file__).with_name('buff_root_prefix_native.json'),
               Path(__file__).with_name('buff_root_fifth_native.json'),
               Path(__file__).with_name('buff_root_sixth_native.json'),
               Path(__file__).with_name('buff_159_native.json'),
               Path(__file__).with_name('buff_16_native.json'),
               Path(__file__).with_name('buff_178_native.json'),
               Path(__file__).with_name('buff_c1_native.json'),
               Path(__file__).with_name('buff_101_native.json'),
               Path(__file__).with_name('buff_c7_native.json'),
               Path(__file__).with_name('buff_19b_native.json'),
               Path(__file__).with_name('buff_128_native.json'),
               Path(__file__).with_name('buff_164_native.json'),
               Path(__file__).with_name('buff_cf_native.json'),
               Path(__file__).with_name('buff_12b_native.json'),
               Path(__file__).with_name('buff_2c_native.json'),
               Path(__file__).with_name('buff_damage_lists_native.json'),
               Path(__file__).with_name('buff_calc5_native.json'),
               Path(__file__).with_name('buff_calc1_native.json'),
               Path(__file__).with_name('finder_00_native.json'),
               Path(__file__).with_name('validator_02_native.json'),
               Path(__file__).with_name('postprocessor_08_native.json'),
               Path(__file__).with_name('buff_127_native.json'),
               Path(__file__).with_name('buff_ab_native.json'),
               Path(__file__).with_name('buff_f6_native.json'),
               Path(__file__).with_name('buff_17c_native.json'),
               Path(__file__).with_name('buff_186_native.json'),
               Path(__file__).with_name('buff_b9_native.json'),
               Path(__file__).with_name('buff_f4_native.json'),
               Path(__file__).with_name('buff_133_native.json'),
               Path(__file__).with_name('buff_14a_native.json'),
               Path(__file__).with_name('buff_15d_native.json'),
               Path(__file__).with_name('buff_37_native.json'),
               Path(__file__).with_name('buff_12a_native.json'),
               Path(__file__).with_name('buff_144_native.json'),
               Path(__file__).with_name('buff_15b_native.json'),
               Path(__file__).with_name('buff_07_native.json'),
               Path(__file__).with_name('buff_18b_native.json'),
               Path(__file__).with_name('buff_19c_native.json'),
               Path(__file__).with_name('buff_8a_native.json'),
               Path(__file__).with_name('postprocessor_01_native.json'),
               Path(__file__).with_name('buff_14b_native.json'),
               Path(__file__).with_name('buff_166_native.json'),
               Path(__file__).with_name('buff_16c_native.json'),
               Path(__file__).with_name('buff_85_native.json'),
               Path(__file__).with_name('buff_94_native.json'),
               Path(__file__).with_name('buff_179_native.json'),
               Path(__file__).with_name('buff_158_native.json'),
               Path(__file__).with_name('buff_15a_native.json'),
               Path(__file__).with_name('buff_192_native.json'),
               Path(__file__).with_name('buff_bc_native.json'),
               Path(__file__).with_name('buff_14e_native.json'),
               Path(__file__).with_name('buff_0d_native.json'),
               Path(__file__).with_name('buff_0c_native.json'),
               Path(__file__).with_name('buff_26_native.json'),
               Path(__file__).with_name('buff_10c_native.json'),
               Path(__file__).with_name('buff_e0_native.json'),
               Path(__file__).with_name('buff_172_native.json'),
               Path(__file__).with_name('buff_28_native.json'),
               Path(__file__).with_name('buff_102_native.json'),
               Path(__file__).with_name('buff_18e_native.json'),
               Path(__file__).with_name('buff_ce_native.json'),
               Path(__file__).with_name('buff_17_native.json'),
               Path(__file__).with_name('buff_ad_native.json'),
               Path(__file__).with_name('buff_198_native.json'),
               Path(__file__).with_name('buff_197_native.json'),
               Path(__file__).with_name('buff_91_native.json'),
               Path(__file__).with_name('buff_184_native.json'),
               Path(__file__).with_name('buff_df_native.json'),
               Path(__file__).with_name('buff_1f_native.json'),
               Path(__file__).with_name('buff_b7_native.json'),
               Path(__file__).with_name('buff_f0_native.json'),
               Path(__file__).with_name('buff_55_native.json'),
               Path(__file__).with_name('buff_36_native.json'),
               Path(__file__).with_name('buff_20_native.json'),
               Path(__file__).with_name('buff_a8_native.json'),
               Path(__file__).with_name('buff_23_native.json'),
               Path(__file__).with_name('buff_16a_native.json'),
               Path(__file__).with_name('buff_6f_native.json'),
               Path(__file__).with_name('buff_161_native.json'),
               Path(__file__).with_name('buff_c0_native.json'),
               Path(__file__).with_name('buff_11c_native.json'),
               Path(__file__).with_name('buff_8c_native.json'),
               Path(__file__).with_name('buff_4e_native.json')]
    source_hashes = {str(p): sha(p) for p in dict.fromkeys(sources)}
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
    wrapper_evidence=wrapper_consumer(pe,md,modules,image_owners,reg,table,
                                      source=str(gate.gameassembly))
    nested_context=nested_reader_context(pe,md,modules,image_owners,reg,table,
                                         source=str(gate.gameassembly),metadata_source=str(gate.metadata))
    list_candidate=list_formatter_candidate(pe,md,modules,image_owners,reg,code,table,spec_records,methods_raw,
                                            source=str(gate.gameassembly))
    skilldata_reader_order=skilldata_static_reader_order(
        pe,md,modules,image_owners,table,reg,specs_raw,corpus,skill_sample_raw,
        wrapper_evidence,source=str(gate.gameassembly))
    branch_sample_rows = []
    for selection, path in zip(terminal_branch_selections,
                               terminal_branch_sample_paths):
        raw = path.read_bytes()
        source_name = str(path.relative_to(ROOT))
        sample = skilldata_terminal_branch_sample_witness(
            corpus, selection, raw, source=source_name)
        nested_replay = skilldata_positive_branch_reader_replay(
            sample, raw, source=source_name)
        native_alignment = skilldata_nested_branch_static_alignment(
            nested_replay,
            skilldata_reader_order['nestedTerminalReaders'],
            skilldata_reader_order['representativeTerminalTailLayout']['gameplayTagListWrapper'],
            list_formatter=list_candidate,
            source=source_name)
        sample['nestedReaderReplay'] = nested_replay
        sample['nativeNestedReaderAlignment'] = native_alignment
        branch_sample_rows.append(sample)
    skilldata_reader_order['representativeTerminalBranchSamples'] = branch_sample_rows
    skilldata_reader_order['terminalListBranchSampleCoverage'] = [
        {
            'fieldName': selection['fieldName'],
            'memberIndex': selection['memberIndex'],
            'count': selection['count'],
            'logicalFileIdentity': selection['row']['virtualPath'],
            'logicalSha256': selection['row']['logicalSha256'],
            'hardLimit': selection['row']['hardLimit'],
            'candidateRange': selection['row']['framing']['candidates'][0].get('candidateRange'),
        }
        for selection in terminal_branch_selections
    ]
    list_dispatch=list_element_dispatch(pe,source=str(gate.gameassembly))
    list_shared=list_element_shared_context(pe,table,reg,code,spec_records,methods_raw,source=str(gate.gameassembly))
    list_null_probe=list_element_null_probe(pe,source=str(gate.gameassembly))
    list_value_flow=list_element_value_flow(pe,source=str(gate.gameassembly))
    element_provider=element_provider_state_flow(pe,source=str(gate.gameassembly))
    buff_routes=buff_union_routes(pe,md,reg,modules,image_owners,source=str(gate.gameassembly))
    buff_forwarding=buff_ifelse_forwarding(pe,md,reg,table,source=str(gate.gameassembly))
    buff_order=buff_ifelse_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly))
    buff_c9_prefix_evidence = skilldata_action_union_c9_prefix_reader_evidence(
        buff_order, buff_routes, gameassembly_image_base=pe.image_base,
        source=str(gate.gameassembly))
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
    buff_119=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_119_native.json'))
    buff_0a=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_0a_native.json'))
    buff_7a=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_7a_native.json'))
    buff_88=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_88_native.json'))
    buff_48=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_48_native.json'))
    buff_5a=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_5a_native.json'))
    buff_7e=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_7e_native.json'))
    buff_35=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_35_native.json'))
    buff_ea=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_ea_native.json'))
    buff_61=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_61_native.json'))
    buff_3f=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_3f_native.json'))
    buff_14d=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_14d_native.json'))
    buff_73=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_73_native.json'))
    buff_5d=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_5d_native.json'))
    buff_42=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_42_native.json'))
    buff_27=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_27_native.json'))
    buff_95=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_95_native.json'))
    buff_74=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_74_native.json'))
    buff_16d=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_16d_native.json'))
    buff_160=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_160_native.json'))
    buff_89=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_89_native.json'))
    buff_171=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_171_native.json'))
    buff_132=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_132_native.json'))
    buff_d4=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_d4_native.json'))
    buff_60=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_60_native.json'))
    buff_126=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_126_native.json'))
    buff_1c=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_1c_native.json'))
    buff_06=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_06_native.json'))
    buff_142=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_142_native.json'))
    buff_03=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_03_native.json'))
    buff_51=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_51_native.json'))
    buff_5e=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_5e_native.json'))
    buff_13b=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_13b_native.json'))
    buff_84=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_84_native.json'))
    buff_174=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_174_native.json'))
    buff_41=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_41_native.json'))
    buff_a9=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_a9_native.json'))
    buff_62=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_62_native.json'))
    buff_13c=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_13c_native.json'))
    buff_90=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_90_native.json'))
    buff_bb=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_bb_native.json'))
    buff_0b=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_0b_native.json'))
    buff_0c=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_0c_native.json'))
    buff_26=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_26_native.json'))
    buff_10c=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_10c_native.json'))
    buff_2b=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_2b_native.json'))
    buff_115=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_115_native.json'))
    buff_151=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_151_native.json'))
    buff_13f=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_13f_native.json'))
    buff_140=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_140_native.json'))
    buff_98=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_98_native.json'))
    buff_176=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_176_native.json'))
    buff_93=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_93_native.json'))
    buff_175=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_175_native.json'))
    buff_fc=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_fc_native.json'))
    buff_83=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_83_native.json'))
    buff_13a=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_13a_native.json'))
    buff_86=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_86_native.json'))
    buff_63=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_63_native.json'))
    buff_6b=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_6b_native.json'))
    buff_77=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_77_native.json'))
    buff_188=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_188_native.json'))
    buff_40=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_40_native.json'))
    buff_187=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_187_native.json'))
    buff_139=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_139_native.json'))
    buff_18a=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_18a_native.json'))
    buff_135=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_135_native.json'))
    buff_122=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_122_native.json'))
    buff_5c=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_5c_native.json'))
    buff_183=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_183_native.json'))
    buff_2f=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_2f_native.json'))
    buff_15c=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_15c_native.json'))
    buff_16f=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_16f_native.json'))
    buff_05=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_05_native.json'))
    buff_3a=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_3a_native.json'))
    buff_4c=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_4c_native.json'))
    buff_150=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_150_native.json'))
    buff_a7=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_a7_native.json'))
    buff_19e=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_19e_native.json'))
    buff_08=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_08_native.json'))
    buff_120=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_120_native.json'))
    buff_9f=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_9f_native.json'))
    buff_1b=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_1b_native.json'))
    buff_87=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_87_native.json'))
    buff_52=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_52_native.json'))
    buff_8e=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_8e_native.json'))
    finder_0a=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('finder_0a_native.json'))
    finder_15=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('finder_15_native.json'))
    finder_0e=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('finder_0e_native.json'))
    buff_125=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_125_native.json'))
    buff_124=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_124_native.json'))
    buff_14f=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_14f_native.json'))
    buff_71=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_71_native.json'))
    buff_70=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_70_native.json'))
    finder_10=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('finder_10_native.json'))
    finder_00=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('finder_00_native.json'))
    finder_01=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('finder_01_native.json'))
    postprocessor_01=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('postprocessor_01_native.json'))
    postprocessor_08=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('postprocessor_08_native.json'))
    validator_02=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('validator_02_native.json'))
    validator_01=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('validator_01_native.json'))
    buff_root_prefix=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_root_prefix_native.json'))
    buff_root_fifth=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_root_fifth_native.json'))
    buff_root_sixth=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_root_sixth_native.json'))
    buff_159=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_159_native.json'))
    buff_16=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_16_native.json'))
    buff_178=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_178_native.json'))
    buff_c1=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_c1_native.json'))
    buff_101=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_101_native.json'))
    buff_c7=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_c7_native.json'))
    buff_19b=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_19b_native.json'))
    buff_128=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_128_native.json'))
    buff_164=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_164_native.json'))
    buff_cf=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_cf_native.json'))
    buff_12b=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_12b_native.json'))
    buff_calc1=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_calc1_native.json'))
    buff_calc5=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_calc5_native.json'))
    buff_damage_lists=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_damage_lists_native.json'))
    buff_2c=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_2c_native.json'))
    buff_127=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_127_native.json'))
    buff_ab=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_ab_native.json'))
    buff_f6=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_f6_native.json'))
    buff_17c=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_17c_native.json'))
    buff_186=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_186_native.json'))
    buff_b9=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_b9_native.json'))
    buff_f4=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_f4_native.json'))
    buff_133=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_133_native.json'))
    buff_14a=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_14a_native.json'))
    buff_15d=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_15d_native.json'))
    buff_37=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_37_native.json'))
    buff_12a=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_12a_native.json'))
    buff_144=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_144_native.json'))
    buff_15b=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_15b_native.json'))
    buff_07=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_07_native.json'))
    buff_18b=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_18b_native.json'))
    buff_19c=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_19c_native.json'))
    buff_8a=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_8a_native.json'))
    buff_14b=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_14b_native.json'))
    buff_166=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_166_native.json'))
    buff_16c=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_16c_native.json'))
    buff_85=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_85_native.json'))
    buff_94=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_94_native.json'))
    buff_179=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_179_native.json'))
    buff_158=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_158_native.json'))
    buff_15a=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_15a_native.json'))
    buff_192=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_192_native.json'))
    buff_bc=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_bc_native.json'))
    buff_14e=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_14e_native.json'))
    buff_e0=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_e0_native.json'))
    buff_0d=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_0d_native.json'))
    buff_172=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_172_native.json'))
    buff_28=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_28_native.json'))
    buff_102=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_102_native.json'))
    buff_18e=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_18e_native.json'))
    buff_ce=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_ce_native.json'))
    buff_17=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_17_native.json'))
    buff_ad=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_ad_native.json'))
    buff_d5=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_d5_native.json'))
    buff_d6=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_d6_native.json'))
    buff_198=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_198_native.json'))
    buff_197=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_197_native.json'))
    buff_91=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_91_native.json'))
    buff_184=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_184_native.json'))
    buff_df=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_df_native.json'))
    buff_1f=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_1f_native.json'))
    buff_b7=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_b7_native.json'))
    buff_f0=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_f0_native.json'))
    buff_55=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_55_native.json'))
    buff_36=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_36_native.json'))
    buff_20=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_20_native.json'))
    buff_a8=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_a8_native.json'))
    buff_23=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_23_native.json'))
    buff_16a=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_16a_native.json'))
    buff_6f=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_6f_native.json'))
    buff_161=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_161_native.json'))
    buff_c0=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_c0_native.json'))
    buff_11c=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_11c_native.json'))
    buff_8c=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_8c_native.json'))
    buff_4e=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_4e_native.json'))
    buff_16b=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_16b_native.json'))
    buff_24=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_24_native.json'))
    buff_6a=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_6a_native.json'))
    buff_bd=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_bd_native.json'))
    buff_de=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_de_native.json'))
    buff_145=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_145_native.json'))
    buff_c4=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_c4_native.json'))
    buff_c5=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_c5_native.json'))
    buff_9b=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_9b_native.json'))
    buff_10f=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=Path(__file__).with_name('buff_10f_native.json'))
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
    buff_action_readers = skilldata_action_readers_from_locals(
        locals(), source=str(gate.gameassembly))
    verified_action_tags = set(buff_action_readers)
    buff_action_prefixes = {0xC9: buff_c9_prefix_evidence}
    verified_action_prefix_tags = set(buff_action_prefixes)
    for reader in buff_action_readers.values():
        contract_path = Path(reader['contractPath']).resolve()
        source_hashes[str(contract_path)] = sha(contract_path)

    actiongroup_branch_census_files = []
    actiongroup_branch_class_counts = {}
    actiongroup_branch_status_counts = {}
    actiongroup_completed_tag_counts = {}
    actiongroup_first_unverified_tag_counts = {}
    actiongroup_prefix_stop_tag_counts = {}
    actiongroup_reader_evidence_by_tag = {}
    actiongroup_opaque_bytes_after_cursor = 0
    actiongroup_c9_candidate_status_counts = {}
    actiongroup_c9_candidate_file_count = 0
    actiongroup_c9_candidate_sequence_range_count = 0
    for row, path in zip(actiongroup_branch_census_rows,
                         actiongroup_branch_census_sample_paths):
        logical_path = row['virtualPath']
        raw = path.read_bytes()
        source_name = str(path.relative_to(ROOT))
        witness = skilldata_actiongroup_branch_sample_witness(
            corpus, logical_path, raw, source=source_name,
            verified_action_tags=verified_action_tags,
            verified_action_prefix_tags=verified_action_prefix_tags)
        alignment = skilldata_actiongroup_branch_static_alignment(
            witness, skilldata_reader_order, buff_ad, buff_b4, buff_sequence,
            buff_d5, buff_d6, buff_routes, source=source_name,
            buff_action_readers=buff_action_readers,
            buff_action_prefixes=buff_action_prefixes,
            gameassembly_image_base=pe.image_base)
        c9_candidate = None
        if witness['status'] == 'stopped-after-verified-action-prefix':
            c9_candidate = skilldata_actiongroup_c9_nested_sequence_candidate_replay(
                witness, raw, buff_c9_prefix_evidence, buff_sequence,
                buff_action_readers, buff_routes, source=source_name,
                gameassembly_image_base=pe.image_base)
            actiongroup_c9_candidate_file_count += 1
            actiongroup_c9_candidate_status_counts[c9_candidate['status']] = (
                actiongroup_c9_candidate_status_counts.get(c9_candidate['status'], 0) + 1)
            actiongroup_c9_candidate_sequence_range_count += len(
                c9_candidate['candidateSequenceRanges'])
        actiongroup_branch_class_counts[witness['boundaryClass']] = (
            actiongroup_branch_class_counts.get(witness['boundaryClass'], 0) + 1)
        actiongroup_branch_status_counts[witness['status']] = (
            actiongroup_branch_status_counts.get(witness['status'], 0) + 1)
        actiongroup_opaque_bytes_after_cursor += sum(
            byte_range['end'] - byte_range['start']
            for byte_range in witness.get('opaqueByteRanges', []))
        for union_range in alignment['completedActionUnionRanges']:
            tag_label = f"0x{union_range['tag']:X}"
            actiongroup_completed_tag_counts[tag_label] = (
                actiongroup_completed_tag_counts.get(tag_label, 0) + 1)
        first_unconsumed = witness.get('firstUnconsumedActionUnionByte')
        if isinstance(first_unconsumed, dict):
            tag_label = f"0x{first_unconsumed['tag']:X}"
            actiongroup_first_unverified_tag_counts[tag_label] = (
                actiongroup_first_unverified_tag_counts.get(tag_label, 0) + 1)
        prefix_stop = witness.get('actionUnionPrefixStop')
        if isinstance(prefix_stop, dict):
            tag_label = f"0x{prefix_stop['tag']:X}"
            actiongroup_prefix_stop_tag_counts[tag_label] = (
                actiongroup_prefix_stop_tag_counts.get(tag_label, 0) + 1)
        for evidence in alignment['abilityActionUnionReaderEvidence']:
            actiongroup_reader_evidence_by_tag.setdefault(evidence['tag'], evidence)
        actiongroup_branch_census_files.append({
            'inputSetSha256': witness['inputSetSha256'],
            'logicalFileIdentity': witness['logicalFileIdentity'],
            'logicalSha256': witness['logicalSha256'],
            'hardLimit': witness['hardLimit'],
            'parserCursor': witness['parserCursor'],
            'status': witness['status'],
            'boundaryClass': witness['boundaryClass'],
            'consumedByteRanges': witness['consumedByteRanges'],
            'completedActionUnionRanges': alignment['completedActionUnionRanges'],
            'actionUnionPrefixStop': witness['actionUnionPrefixStop'],
            'firstUnconsumedActionUnionByte': witness['firstUnconsumedActionUnionByte'],
            'opaqueByteRanges': witness['opaqueByteRanges'],
            'wholeSkillDataClassification': witness['wholeSkillDataClassification'],
            'wholeSkillDataExactClosedRecords': witness['wholeSkillDataExactClosedRecords'],
            'conditionalReaderTags': alignment['verifiedActionUnionReaderTags'],
            'conditionalPrefixReaderTags': alignment['verifiedActionUnionPrefixTags'],
            'conditionalC9NestedSequenceCandidate': c9_candidate,
        })

    actiongroup_branch_census = {
        'inputSetSha256': corpus['inputSetSha256'],
        'sampleSelection': 'current SkillData corpus rows whose first common-prefix record list count is positive',
        'selectedFiles': len(actiongroup_branch_census_rows),
        'hashMatchedCurrentVfsFiles': len(actiongroup_branch_census_files),
        'boundaryClassCounts': actiongroup_branch_class_counts,
        'parserStatusCounts': actiongroup_branch_status_counts,
        'conditionalPassiveEventActionsListEnds': actiongroup_branch_status_counts.get(
            'passive-list-consumed-to-conditional-static-end', 0),
        'stoppedAtUnverifiedUnion': actiongroup_branch_status_counts.get(
            'stopped-before-first-nonnull-action-union', 0),
        'unsupported': actiongroup_branch_status_counts.get('unsupported-structural-prefix', 0),
        'ambiguousWholeSkillDataFiles': len(actiongroup_branch_census_files),
        'exactClosedActionGroupDataRecords': 0,
        'exactClosedWholeSkillDataRecords': 0,
        'opaqueBytesAfterConditionalCursor': actiongroup_opaque_bytes_after_cursor,
        'completedActionUnionTagCounts': dict(sorted(actiongroup_completed_tag_counts.items())),
        'firstUnverifiedActionUnionTagCounts': dict(sorted(actiongroup_first_unverified_tag_counts.items())),
        'stoppedAfterActionUnionPrefixTagCounts': dict(
            sorted(actiongroup_prefix_stop_tag_counts.items())),
        'candidateOnlyC9Files': actiongroup_c9_candidate_file_count,
        'candidateOnlyC9SequenceStatusCounts': dict(
            sorted(actiongroup_c9_candidate_status_counts.items())),
        'candidateOnlyC9SequenceRanges': actiongroup_c9_candidate_sequence_range_count,
        'exactClosedC9UnionRecords': 0,
        'exactClosedSequenceRecords': 0,
        'verifiedActionReaderContractsAvailable': len(buff_action_readers),
        'verifiedActionReaderPrefixEvidenceAvailable': [buff_c9_prefix_evidence],
        'verifiedActionReaderEvidenceUsed': [
            actiongroup_reader_evidence_by_tag[tag]
            for tag in sorted(actiongroup_reader_evidence_by_tag)],
        'files': actiongroup_branch_census_files,
        'boundary': ('This bounded subcorpus follows only the first ActionGroupData passiveEventActions list. '
                     'A list-end count means its child maps and sequences align to the selected static readers; '
                     'the following timelineActions member remains a non-advancing peek. Where a current C9 '
                     'header-eight normal path is selected, only its tag/member-header/14-byte scalar prefix '
                     'is consumed, stopping before its first generic SequenceActionData call. Unknown other '
                     'tags remain opaque at their first byte. Every enclosing ActionGroupData and whole SkillData '
                     'file remains ambiguous; no exact closed parent record is counted.'),
    }
    actiongroup_branch_sample_rows = []
    for logical_path, path in zip(actiongroup_branch_sample_identities,
                                  actiongroup_branch_sample_paths):
        raw = path.read_bytes()
        source_name = str(path.relative_to(ROOT))
        witness = skilldata_actiongroup_branch_sample_witness(
            corpus, logical_path, raw, source=source_name,
            verified_action_tags=verified_action_tags,
            verified_action_prefix_tags=verified_action_prefix_tags)
        witness['nativeReaderAlignment'] = skilldata_actiongroup_branch_static_alignment(
            witness, skilldata_reader_order, buff_ad, buff_b4, buff_sequence,
            buff_d5, buff_d6, buff_routes, source=source_name,
            buff_action_readers=buff_action_readers,
            buff_action_prefixes=buff_action_prefixes,
            gameassembly_image_base=pe.image_base)
        witness['conditionalC9NestedSequenceCandidate'] = (
            skilldata_actiongroup_c9_nested_sequence_candidate_replay(
                witness, raw, buff_c9_prefix_evidence, buff_sequence,
                buff_action_readers, buff_routes, source=source_name,
                gameassembly_image_base=pe.image_base)
            if witness['status'] == 'stopped-after-verified-action-prefix' else None)
        actiongroup_branch_sample_rows.append(witness)
    skilldata_reader_order['representativeActionGroupBranchSamples'] = actiongroup_branch_sample_rows
    skilldata_reader_order['actionGroupBranchSampleCensus'] = actiongroup_branch_census
    skilldata_reader_order['actionGroupBranchSampleBoundary'] = (
        'The current positive-list subcorpus is replayed through every hash-pinned direct action reader whose '
        'registered wrapper route and root member header match. For C9, only the exact header-eight scalar '
        'prefix through the first generic SequenceActionData callsite is consumed. A separate candidate-only '
        'replay records the three nested sequence call ranges against the current sequence and child-action '
        'reader windows; C9 provider/cache selection remains unobserved, so those ranges never advance the '
        'authoritative parser cursor. timelineActions is only peeked after a conditional list end; the parent '
        'ActionGroupData and whole SkillData records remain ambiguous.'
    )
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
        'selectedSkillDataReaderOrder':skilldata_reader_order,
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
        'selectedBuff10FReadOrder':buff_10f,
        'selectedBuff9BReadOrder':buff_9b,
        'selectedBuffC5ReadOrder':buff_c5,
        'selectedBuff119ReadOrder':buff_119,
        'selectedBuff0AReadOrder':buff_0a,
        'selectedBuff7AReadOrder':buff_7a,
        'selectedBuff88ReadOrder':buff_88,
        'selectedBuff48ReadOrder':buff_48,
        'selectedBuff5AReadOrder':buff_5a,
        'selectedBuffC4ReadOrder':buff_c4,
        'selectedBuff145ReadOrder':buff_145,
        'selectedBuffDEReadOrder':buff_de,
        'selectedBuffBDReadOrder':buff_bd,
        'selectedBuff6AReadOrder':buff_6a,
        'selectedBuff24ReadOrder':buff_24,
        'selectedBuff16BReadOrder':buff_16b,
        'selectedBuff7EReadOrder':buff_7e,
        'selectedBuff35ReadOrder':buff_35,
        'selectedBuffEAReadOrder':buff_ea,
        'selectedBuff61ReadOrder':buff_61,
        'selectedBuff3FReadOrder':buff_3f,
        'selectedBuff14DReadOrder':buff_14d,
        'selectedBuff73ReadOrder':buff_73,
        'selectedBuff5DReadOrder':buff_5d,
        'selectedBuff42ReadOrder':buff_42,
        'selectedBuff27ReadOrder':buff_27,
        'selectedBuff95ReadOrder':buff_95,
        'selectedBuff74ReadOrder':buff_74,
        'selectedBuff16DReadOrder':buff_16d,
        'selectedBuff160ReadOrder':buff_160,
        'selectedBuff89ReadOrder':buff_89,
        'selectedBuff171ReadOrder':buff_171,
        'selectedBuff132ReadOrder':buff_132,
        'selectedBuffD4ReadOrder':buff_d4,
        'selectedBuff60ReadOrder':buff_60,
        'selectedBuff126ReadOrder':buff_126,
        'selectedBuff1CReadOrder':buff_1c,
        'selectedBuff06ReadOrder':buff_06,
        'selectedBuff142ReadOrder':buff_142,
        'selectedBuff03ReadOrder':buff_03,
        'selectedBuff51ReadOrder':buff_51,
        'selectedBuff5EReadOrder':buff_5e,
        'selectedBuff13BReadOrder':buff_13b,
        'selectedBuff84ReadOrder':buff_84,
        'selectedBuff174ReadOrder':buff_174,
        'selectedBuff41ReadOrder':buff_41,
        'selectedBuffA9ReadOrder':buff_a9,
        'selectedBuff62ReadOrder':buff_62,
        'selectedBuff13CReadOrder':buff_13c,
        'selectedBuff90ReadOrder':buff_90,
        'selectedBuffBBReadOrder':buff_bb,
        'selectedBuff0BReadOrder':buff_0b,
        'selectedBuff0CReadOrder':buff_0c,
        'selectedBuff26ReadOrder':buff_26,
        'selectedBuff10CReadOrder':buff_10c,
        'selectedBuff2BReadOrder':buff_2b,
        'selectedBuff115ReadOrder':buff_115,
        'selectedBuff151ReadOrder':buff_151,
        'selectedBuff13FReadOrder':buff_13f,
        'selectedBuff140ReadOrder':buff_140,
        'selectedBuff98ReadOrder':buff_98,
        'selectedBuff176ReadOrder':buff_176,
        'selectedBuff93ReadOrder':buff_93,
        'selectedBuff175ReadOrder':buff_175,
        'selectedBuffFCReadOrder':buff_fc,
        'selectedBuff83ReadOrder':buff_83,
        'selectedBuff13AReadOrder':buff_13a,
        'selectedBuff86ReadOrder':buff_86,
        'selectedBuff63ReadOrder':buff_63,
        'selectedBuff6BReadOrder':buff_6b,
        'selectedBuff77ReadOrder':buff_77,
        'selectedBuff188ReadOrder':buff_188,
        'selectedBuff40ReadOrder':buff_40,
        'selectedBuff187ReadOrder':buff_187,
        'selectedBuff139ReadOrder':buff_139,
        'selectedBuff18AReadOrder':buff_18a,
        'selectedBuff135ReadOrder':buff_135,
        'selectedBuff122ReadOrder':buff_122,
        'selectedBuff5CReadOrder':buff_5c,
        'selectedBuff183ReadOrder':buff_183,
        'selectedBuff2FReadOrder':buff_2f,
        'selectedBuff15CReadOrder':buff_15c,
        'selectedBuff16FReadOrder':buff_16f,
        'selectedBuff05ReadOrder':buff_05,
        'selectedBuff3AReadOrder':buff_3a,
        'selectedBuff4CReadOrder':buff_4c,
        'selectedBuff150ReadOrder':buff_150,
        'selectedBuffA7ReadOrder':buff_a7,
        'selectedBuff19EReadOrder':buff_19e,
        'selectedBuff08ReadOrder':buff_08,
        'selectedBuff120ReadOrder':buff_120,
        'selectedBuff9FReadOrder':buff_9f,
        'selectedBuff1BReadOrder':buff_1b,
        'selectedBuff87ReadOrder':buff_87,
        'selectedBuff52ReadOrder':buff_52,
        'selectedBuff8EReadOrder':buff_8e,
        'selectedFinder0AReadOrder':finder_0a,
        'selectedFinder15ReadOrder':finder_15,
        'selectedFinder0EReadOrder':finder_0e,
        'selectedBuff125ReadOrder':buff_125,
        'selectedBuff124ReadOrder':buff_124,
        'selectedBuff14FReadOrder':buff_14f,
        'selectedBuff71ReadOrder':buff_71,
        'selectedBuff70ReadOrder':buff_70,
        'selectedFinder10ReadOrder':finder_10,
        'selectedFinder01ReadOrder':finder_01,
        'selectedFinder00ReadOrder':finder_00,
        'selectedValidator01ReadOrder':validator_01,
        'selectedValidator02ReadOrder':validator_02,
        'selectedPostprocessor08ReadOrder':postprocessor_08,
        'selectedPostprocessor01ReadOrder':postprocessor_01,
        'selectedBuffRootPrefixReadOrder':buff_root_prefix,
        'selectedBuffRootFifthReadOrder':buff_root_fifth,
        'selectedBuffRootSixthReadOrder':buff_root_sixth,
        'selectedBuff159ReadOrder':buff_159,
        'selectedBuff16ReadOrder':buff_16,
        'selectedBuff178ReadOrder':buff_178,
        'selectedBuffC1ReadOrder':buff_c1,
        'selectedBuff101ReadOrder':buff_101,
        'selectedBuffC7ReadOrder':buff_c7,
        'selectedBuff19BReadOrder':buff_19b,
        'selectedBuff128ReadOrder':buff_128,
        'selectedBuff164ReadOrder':buff_164,
        'selectedBuffCFReadOrder':buff_cf,
        'selectedBuff12BReadOrder':buff_12b,
        'selectedBuff2CReadOrder':buff_2c,
        'selectedBuffABReadOrder':buff_ab,
        'selectedBuffF6ReadOrder':buff_f6,
        'selectedBuff17CReadOrder':buff_17c,
        'selectedBuff186ReadOrder':buff_186,
        'selectedBuffB9ReadOrder':buff_b9,
        'selectedBuffF4ReadOrder':buff_f4,
        'selectedBuff133ReadOrder':buff_133,
        'selectedBuff14AReadOrder':buff_14a,
        'selectedBuff15DReadOrder':buff_15d,
        'selectedBuff37ReadOrder':buff_37,
        'selectedBuff12AReadOrder':buff_12a,
        'selectedBuff144ReadOrder':buff_144,
        'selectedBuff15BReadOrder':buff_15b,
        'selectedBuff07ReadOrder':buff_07,
        'selectedBuff18BReadOrder':buff_18b,
        'selectedBuff19CReadOrder':buff_19c,
        'selectedBuff8AReadOrder':buff_8a,
        'selectedBuff14BReadOrder':buff_14b,
        'selectedBuff166ReadOrder':buff_166,
        'selectedBuff16CReadOrder':buff_16c,
        'selectedBuff85ReadOrder':buff_85,
        'selectedBuff94ReadOrder':buff_94,
        'selectedBuff179ReadOrder':buff_179,
        'selectedBuff158ReadOrder':buff_158,
        'selectedBuff15AReadOrder':buff_15a,
        'selectedBuff192ReadOrder':buff_192,
        'selectedBuffBCReadOrder':buff_bc,
        'selectedBuff14EReadOrder':buff_14e,
        'selectedBuff0DReadOrder':buff_0d,
        'selectedBuffE0ReadOrder':buff_e0,
        'selectedBuff172ReadOrder':buff_172,
        'selectedBuff28ReadOrder':buff_28,
        'selectedBuff102ReadOrder':buff_102,
        'selectedBuff18eReadOrder':buff_18e,
        'selectedBuffCeReadOrder':buff_ce,
        'selectedBuff17ReadOrder':buff_17,
        'selectedBuffAdReadOrder':buff_ad,
        'selectedBuffD5ReadOrder':buff_d5,
        'selectedBuffD6ReadOrder':buff_d6,
        'selectedBuff198ReadOrder':buff_198,
        'selectedBuff197ReadOrder':buff_197,
        'selectedBuff91ReadOrder':buff_91,
        'selectedBuff184ReadOrder':buff_184,
        'selectedBuffDfReadOrder':buff_df,
        'selectedBuff1fReadOrder':buff_1f,
        'selectedBuffB7ReadOrder':buff_b7,
        'selectedBuffF0ReadOrder':buff_f0,
        'selectedBuff55ReadOrder':buff_55,
        'selectedBuff36ReadOrder':buff_36,
        'selectedBuff20ReadOrder':buff_20,
        'selectedBuffA8ReadOrder':buff_a8,
        'selectedBuff23ReadOrder':buff_23,
        'selectedBuff16AReadOrder':buff_16a,
        'selectedBuff6FReadOrder':buff_6f,
        'selectedBuff161ReadOrder':buff_161,
        'selectedBuffC0ReadOrder':buff_c0,
        'selectedBuff11CReadOrder':buff_11c,
        'selectedBuff8CReadOrder':buff_8c,
        'selectedBuff4EReadOrder':buff_4e,
        'selectedBuff127ReadOrder':buff_127,
        'selectedBuffDamageListsReadOrder':buff_damage_lists,
        'selectedBuffCalc5ReadOrder':buff_calc5,
        'selectedBuffCalc1ReadOrder':buff_calc1,
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
        def diagnostic_default(value):
            if isinstance(value, bytes):
                return {'byteLength': len(value), 'hex': value.hex().upper()}
            if isinstance(value, Path):
                return str(value)
            return repr(value)
        print(json.dumps(
            {'status': 'failed',
             'diagnostic': getattr(error, 'diagnostics',
                                   getattr(error, 'diagnostic', str(error)))},
            default=diagnostic_default), file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False))
    return int(report['status'] == 'failed')


if __name__ == '__main__':
    raise SystemExit(main())
