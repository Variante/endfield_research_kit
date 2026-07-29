# DynamicScene mission-control / LevelScript identity audit

This report uses installed DynamicStreaming FlatBuffers and exported LevelScript data only. Exact numeric equality is retained as a typed cross-system candidate; promotion still requires runtime namespace/owner semantics.

## Counts

- fb_main files decoded: 457
- grids decoded: 4717
- mission-controlled roots: 387
- roots whose IdComp.logicId equals an exported LevelScript id: 125
- identity-matched roots with Story playback: 72
- matching Story playback occurrences: 216
- decode errors: 0
- duplicate scene/grid ids: 5

## Story-bearing exact identity candidates

| Scene | logicId / scriptId | Mission conditions | Story playback | Source |
|---|---:|---|---|---|
| dung01_rdg001 | 13000020000 | c6m3_q#closeFire | dlg_c6m1_21, radio_c6m1_8d4 | `Data/DynamicStreaming/PC/Scene/dung01_rdg001/fb_main_4_0004_0004.bytes` |
| dung02_dg002 | 24900160005 | e9m2 | dlg_e9m2_7d2, radio_e9m2_42, radio_e9m2_9 | `Data/DynamicStreaming/PC/Scene/dung02_dg002/fb_main_7_0000_0000.bytes` |
| dung02_rdg005 | 34700030004 | c33m2 | dlg_c33m2_29 | `Data/DynamicStreaming/PC/Scene/dung02_rdg005/fb_main_5_0002_0002.bytes` |
| dung02_rdg005 | 34700030005 | c33m2 | radio_c33m2_8, radio_c33m2_57 | `Data/DynamicStreaming/PC/Scene/dung02_rdg005/fb_main_7_0000_0000.bytes` |
| dung02_rdg008 | 35600010004 | e11m5 | dlg_e11m5_3, dlg_e11m5_3, dlg_e11m5_14, dlg_e11m5_14, radio_e11m5_7, dlg_e11m5_15, dlg_e11m5_15, dlg_e11m5_16, dlg_e11m5_16, dlg_e11m5_17, dlg_e11m5_17 | `Data/DynamicStreaming/PC/Scene/dung02_rdg008/fb_main_7_0000_0000.bytes` |
| indie_dg007 | 26200020001 | e8m4_q#5d3 | dlg_e8m4_2 | `Data/DynamicStreaming/PC/Scene/indie_dg007/fb_main_4_0004_0004.bytes` |
| map01 | 200210000 | c6m1 | dlg_c6m1_10 | `Data/DynamicStreaming/PC/Scene/map01/fb_main_4_0002_0003.bytes` |
| map01 | 2100050017 | e1m8 | radio_e1m1_3d5 | `Data/DynamicStreaming/PC/Scene/map01/fb_main_5_0002_0002.bytes` |
| map01 | 2100060003 | e1m2_q#5, e1m2_q#7 | dlg_e1m2_8, cutscene_e1m3_1, dlg_e1m2_9 | `Data/DynamicStreaming/PC/Scene/map01/fb_main_4_0003_0003.bytes` |
| map01 | 2100060006 | e1m2 | radio_e1m2_10d5, radio_e1m2_11, radio_e1m2_10 | `Data/DynamicStreaming/PC/Scene/map01/fb_main_4_0003_0003.bytes` |
| map01 | 2100130002 | e1m3_q#30 | dlg_e1m3_16, dlg_e1m3_15, cutscene_e1m3_2 | `Data/DynamicStreaming/PC/Scene/map01/fb_main_4_0003_0003.bytes` |
| map01 | 2100130010 | e1m3_q#78 | radio_e1m3_9 | `Data/DynamicStreaming/PC/Scene/map01/fb_main_4_0003_0003.bytes` |
| map01 | 2100140001 | e1m9_q#Deco_startDigWork, e2m1_q#Deco_finishDigWork | radio_e1m9_2d1 | `Data/DynamicStreaming/PC/Scene/map01/fb_main_7_0000_0000.bytes` |
| map01 | 2100140004 | e2m4, e1m9_q#Deco_updateFleet | dlg_e1m9_1, remotecomm_e1m9_1, dlg_e1m9_1d7 | `Data/DynamicStreaming/PC/Scene/map01/fb_main_5_0001_0002.bytes` |
| map01 | 2100180001 | sm1l1m1, sm1l2m4 | dlg_sm1l1m2_3d8, dlg_sm1l1m2_4 | `Data/DynamicStreaming/PC/Scene/map01/fb_main_4_0002_0003.bytes` |
| map01 | 2100600001 | c33m1_q#6, c33m1_q#15 | radio_c33m1_14 | `Data/DynamicStreaming/PC/Scene/map01/fb_main_7_0000_0000.bytes` |
| map01 | 2100600002 | c33m1_q#33 | dlg_c33m1_1 | `Data/DynamicStreaming/PC/Scene/map01/fb_main_7_0000_0000.bytes` |
| map01 | 2100770001 | hidden53, a1m13_q#1 | dlg_a1m13_1, dlg_a1m13_1, dlg_a1m13_2, dlg_a1m13_2, dlg_a1m13_2, dlg_a1m13_2, dlg_a1m13_2, dlg_a1m13_2, dlg_a1m13_3, dlg_a1m13_3, dlg_a1m13_3, dlg_a1m13_4, dlg_a1m13_4, dlg_a1m13_4, dlg_a1m13_4, dlg_a1m13_4, dlg_a1m13_5, dlg_a1m13_5, dlg_a1m13_5, dlg_a1m13_5, dlg_a1m13_5, dlg_a1m13_6, dlg_a1m13_6, dlg_a1m13_6, dlg_a1m13_6, dlg_a1m13_6, dlg_a1m13_OpenUI | `Data/DynamicStreaming/PC/Scene/map01/fb_main_5_0002_0001.bytes` |
| map01 | 2800010002 | e3m4 | dlg_e3m1_1 | `Data/DynamicStreaming/PC/Scene/map01/fb_main_7_0000_0000.bytes` |
| map01 | 2800280000 | c6m1_q#4, c6m1_q#teleport002 | radio_c6m1_1 | `Data/DynamicStreaming/PC/Scene/map01/fb_main_5_0001_0002.bytes` |
| map01 | 2800340001 | c33m1_q#12, c33m1d5_q#32 | dlg_c33m1_13033 | `Data/DynamicStreaming/PC/Scene/map01/fb_main_7_0000_0000.bytes` |
| map01 | 2800340004 | c33m1d5_q#14, c33m1d5_q#32 | radio_c33m1_37 | `Data/DynamicStreaming/PC/Scene/map01/fb_main_7_0000_0000.bytes` |
| map01 | 3400310003 | c16m2d5_q#13 | dlg_c16m2_2, remotecomm_c16m2_1 | `Data/DynamicStreaming/PC/Scene/map01/fb_main_4_0005_0003.bytes` |
| map01 | 3500150002 | sm1l6m1_q#4d2 | radio_sm1l6m1_5, dlg_sm1l6m1_4 | `Data/DynamicStreaming/PC/Scene/map01/fb_main_4_0004_0004.bytes` |
| map01 | 3500240001 | c16m3d5_q#11, c16m3d5_q#14 | dlg_c16m3_2, radio_c16m3_9 | `Data/DynamicStreaming/PC/Scene/map01/fb_main_4_0004_0004.bytes` |
| map01 | 3500290001 | c28m1 | dlg_c28m1_1 | `Data/DynamicStreaming/PC/Scene/map01/fb_main_5_0002_0002.bytes` |
| map01 | 3500290006 | c28m1 | dlg_c28m1_3 | `Data/DynamicStreaming/PC/Scene/map01/fb_main_4_0005_0004.bytes` |
| map01 | 3500290007 | c28m1 | dlg_c28m1_6 | `Data/DynamicStreaming/PC/Scene/map01/fb_main_4_0005_0004.bytes` |
| map02 | 10100070000 | e5m2 | radio_e5m2_5, radio_e5m2_7, radio_e5m2_1, radio_e5m2_2 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_4_0001_0001.bytes` |
| map02 | 10100170006 | sm2l1m5, sm2l1m5_q#11 | radio_sm2l1m5_6 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_4_0002_0001.bytes` |
| map02 | 10100210001 | f1m18d1_q#9, f1m18d1_q#6 | dlg_f1m18d1_3 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_4_0002_0001.bytes` |
| map02 | 10100220002 | f1m18d2 | radio_f1m18d2_3 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_4_0002_0001.bytes` |
| map02 | 10100220003 | f1m18d2_q#13, f1m18d2_q#1 | dlg_f1m18d2_6, radio_f1m18d2_5 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_4_0002_0001.bytes` |
| map02 | 10100272002 | c27m1 | dlg_c27m1_13 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_4_0002_0001.bytes` |
| map02 | 10100282001 | c27m3, c27m3_q#3 | dlg_c27m3_6 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_7_0000_0000.bytes` |
| map02 | 10100420001 | sm2l2m2_q#13 | radio_sm2l2m2_9, radio_sm2l2m2_8 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_4_0002_0000.bytes` |
| map02 | 10100460001 | m1m49_q#2, m1m49_q#5 | radio_m1m42_6, radio_m1m42_1, radio_m1m42_2, radio_m1m42_5 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_7_0000_0000.bytes` |
| map02 | 10100470001 | m1m50_q#2, m1m50_q#3 | radio_m1m42_6, radio_m1m42_1, radio_m1m42_4, radio_m1m42_3 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_7_0000_0000.bytes` |
| map02 | 22800070002 | sm2l2m1_q#20, sm2l2m1_q#6 | radio_sm2l2m1_2, radio_sm2l2m1_11 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_4_0001_0003.bytes` |
| map02 | 22800080000 | e6m1, e6m1_q#1 | radio_e6m1_1, radio_e6m1_2 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_5_0001_0001.bytes` |
| map02 | 22800100000 | e6m3d5 | radio_e6m3_2 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_4_0001_0003.bytes` |
| map02 | 22800130002 | sm2l2m4 | dlg_sm2l2m4_2 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_4_0002_0004.bytes` |
| map02 | 22800130004 | sm2l2m4 | radio_sm2l2m4_1, radio_sm2l2m4_3 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_7_0000_0000.bytes` |
| map02 | 22800190006 | sm2l2m6, sm2l2m6_q#9 | radio_sm2l2m6_1 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_4_0001_0003.bytes` |
| map02 | 22800213001 | sm2l2m2, sm2l2m2_q#5 | radio_sm2l2m2_26, radio_sm2l2m2_28, radio_sm2l2m2_29, dlg_sm2l2m2_9, radio_sm2l2m2_30, radio_sm2l2m2_25 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_5_0000_0001.bytes` |
| map02 | 22800220000 | e5m3_q#7, e5m3_q#8 | dlg_e5m3_0d7, cutscene_e5m3_1, cutscene_e5m3_1, dlg_e5m3_1 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_4_0002_0002.bytes` |
| map02 | 22800220003 | e5m3 | dlg_e5m3_5 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_4_0001_0003.bytes` |
| map02 | 22800410001 | e6m4 | cutscene_map02_lv002_xueyuan_1, cutscene_map02_lv002_xueyuan_1, cutscene_map02_lv002_xueyuan_all, cutscene_map02_lv002_xueyuan_all, cutscene_map02_lv002_xueyuan_all, cutscene_map02_lv002_xueyuan_2, cutscene_map02_lv002_xueyuan_2, cutscene_map02_lv002_xueyuan_3, cutscene_map02_lv002_xueyuan_3 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_7_0000_0000.bytes` |
| map02 | 22800430001 | f1m19d1_q#17, f1m19d1_q#21 | radio_f1m19d1_2, radio_f1m19d1_2, radio_f1m19d1_3, radio_f1m19d1_3 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_7_0000_0000.bytes` |
| map02 | 22800450001 | e10m1_q#10 | dlg_e10m1_1 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_7_0000_0000.bytes` |
| map02 | 22800630001 | m1m47 | radio_m1m42_6, radio_m1m42_1, radio_m1m42_2, radio_m1m42_4 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_4_0002_0002.bytes` |
| map02 | 22800640001 | m1m48_q#2, m1m48_q#3 | radio_m1m42_6, radio_m1m42_1, radio_m1m42_2, radio_m1m42_4 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_7_0000_0000.bytes` |
| map02 | 23100070002 | e11m2_q#1 | dlg_e11m2_2, dlg_e11m2_2, remotecomm_e11m2_1, dlg_e11m2_6, dlg_e11m2_3 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_7_0000_0000.bytes` |
| map02 | 23100350001 | f1m32_q#Main1Complete | cutscene_f1m32_rift_main1_complete | `Data/DynamicStreaming/PC/Scene/map02/fb_main_7_0000_0000.bytes` |
| map02 | 23100350002 | f1m32_q#Main2Complete | cutscene_f1m32_rift_main2_complete | `Data/DynamicStreaming/PC/Scene/map02/fb_main_7_0000_0000.bytes` |
| map02 | 23100350003 | f1m32_q#Main3Complete | dlg_f1m32_DapanShow, dlg_f1m32_5, cutscene_f1m32_rift_main3_complete | `Data/DynamicStreaming/PC/Scene/map02/fb_main_7_0000_0000.bytes` |
| map02 | 23100350004 | f1m32_q#Side1Complete | cutscene_f1m32_rift_side1_complete, dlg_f1m32_MifuShow, dlg_f1m32_9 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_7_0000_0000.bytes` |
| map02 | 23100350005 | f1m32_q#Side2Complete | cutscene_f1m32_rift_side2_complete, dlg_f1m32_HezhiqiShow, dlg_f1m32_10 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_7_0000_0000.bytes` |
| map02 | 23100350006 | f1m32_q#Side1Complete | dlg_f1m32_LizhiyanShow, dlg_f1m32_11, dlg_f1m32_12 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_7_0000_0000.bytes` |
| map02 | 23200013031 | sm2l5m1_q#24 | radio_sm2l5m1_21, radio_sm2l5m1_22, radio_sm2l5m1_23 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_5_0002_0001.bytes` |
| map02 | 23300000023 | e7m4 | radio_e7m4_12, radio_e7m4_10, radio_e7m4_14, radio_e7m4_20, radio_e7m4_8, radio_e7m4_15, radio_e7m4_11, radio_e7m4_16, radio_e7m4_18, radio_e7m4_19, radio_e7m4_17, cutscene_e7m4_2, dlg_e7m4_2, radio_e7m4_4, radio_e7m4_4, radio_e7m4_4, radio_e7m4_7, radio_e7m4_9 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_4_0003_0001.bytes` |
| map02 | 23300030002 | e7m3, e7m3_q#12 | radio_e7m3_19, radio_e7m3_6 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_4_0003_0001.bytes` |
| map02 | 23300030003 | e7m3, e7m3_q#12 | cutscene_e7m3_1, dlg_e7m3_4, dlg_e7m3_17, dlg_e7m3_17 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_4_0003_0001.bytes` |
| map02 | 23300040001 | e7m4_q#1, e7m4_q#13 | dlg_e7m4_5, radio_e7m4_5, radio_e7m4_6 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_7_0000_0000.bytes` |
| map02 | 23300040003 | e7m4 | dlg_e7m4_6 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_7_0000_0000.bytes` |
| map02 | 23300060001 | sm2l3m3, sm2l3m1_q#4 | radio_sm2l3m1_9 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_4_0003_0002.bytes` |
| map02 | 23300060003 | sm2l3m1_q#2 | radio_sm2l3m1_14, radio_sm2l3m1_15, dlg_sm2l3m1_2 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_4_0003_0001.bytes` |
| map02 | 23300060005 | sm2l3m1_q#6, sm2l3m1_q#6 | dlg_sm2l3m1_3, radio_sm2l3m1_5, radio_sm2l3m1_12, dlg_sm2l3m1_5, radio_sm2l3m1_8, radio_sm2l3m1_16 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_4_0003_0002.bytes` |
| map02 | 23300070000 | sm2l3m4_q#1 | dlg_sm2l3m4_3d5, radio_sm2l3m4_1d5, dlg_sm2l3m4_3, radio_sm2l3m4_1 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_4_0002_0001.bytes` |
| map02 | 23300070002 | sm2l3m4_q#8 | radio_sm2l3m4_4, dlg_sm2l3m4_5, radio_sm2l3m4_10 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_4_0003_0001.bytes` |
| map02 | 23300130004 | sm2l3m2_q#6 | dlg_sm2l3m2_1 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_4_0003_0002.bytes` |
| map02 | 25000160001 | m1m75 | radio_m1m75_1, radio_m1m75_2, radio_m1m75_3, radio_m1m75_4, radio_m1m75_5 | `Data/DynamicStreaming/PC/Scene/map02/fb_main_7_0000_0000.bytes` |

## Evidence boundary

`IdComp.logicId` is an authored DynamicScene identity and the exported LevelScript dictionary/file key is an authored script identity. Their numeric equality is exact original-data evidence, but this audit does not assume the two identity namespaces are equivalent. Native ownership or a serialized typed carrier must establish that before Story edges are promoted.

- Classification: `exact_cross_reference_not_runtime_owner`
- Mission graph action: `none`
- Direct runtime bridge found: `false`
