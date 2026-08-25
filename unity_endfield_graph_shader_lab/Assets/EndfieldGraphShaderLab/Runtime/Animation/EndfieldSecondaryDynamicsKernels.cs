using System;
using System.IO;
using System.IO.Compression;
using System.Runtime.CompilerServices;
using System.Security.Cryptography;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Source translations of individually closed original solver kernels.
    /// These methods remain disconnected from transform writeback until the
    /// complete active Endminf stage set is translated and verified.
    /// </summary>
    public static class EndfieldSecondaryDynamicsKernels
    {
        private const string FloatSinCosReducerTableHex =
            "83f9223e889cdc31e14fa9243ffaea170ee60b3ddf8d8db03e602da43ffaea170" +
            "ee60b3ddf8d8db03e602da43ffaea17dc603e3bf5ddd8aed90356a2eaa3af15d" +
            "c603e3bf5ddd8aed90356a2eaa3af15dc603e3bf5ddd8aed90356a2eaa3af15d" +
            "c603e3bf5ddd8aed90356a2eaa3af156e83793a2a889c2d9df02721aa8fbe14" +
            "6e83793a2a889c2d9df02721aa8fbe14dd06f339abef46adc51eb0a0ade00294" +
            "b90d66395341642c157bc09f2d2b3891721bcc385341642c157bc09f2d2b3891" +
            "e53618386bf5ddaa0c2a769b6f9afa0e27b7c136542a88290c2a769b6f9afa0e" +
            "27b7c136542a88290c2a769b6f9afa0e27b7c136542a88290c2a769b6f9afa0e" +
            "4e6e0336542a88290c2a769b6f9afa0e91935b33e14fa9243ffaea1790c8328b" +
            "91935b33e14fa9243ffaea1790c8328b91935b33e14fa9243ffaea1790c8328b" +
            "91935b33e14fa9243ffaea1790c8328b91935b33e14fa9243ffaea1790c8328b" +
            "91935b33e14fa9243ffaea1790c8328b2227b732e14fa9243ffaea1790c8328b" +
            "889cdc31e14fa9243ffaea1790c8328b889cdc31e14fa9243ffaea1790c8328b" +
            "10393931e14fa9243ffaea1790c8328b41e46430853fa5230b2e289603775309" +
            "41e46430853fa5230b2e28960377530983c8c92ff68035a30b2e289603775309" +
            "0591132f14fe94220b2e2896037753092a889c2d9df02721aa8fbe14f2233288" +
            "2a889c2d9df02721aa8fbe14f22332882a889c2d9df02721aa8fbe14f2233288" +
            "5341642c157bc09f2d2b3891db06ee045341642c157bc09f2d2b3891db06ee04" +
            "5341642c157bc09f2d2b3891db06ee04a582c82bac13fe1e2d2b3891db06ee04" +
            "4a05112bac13fe1e2d2b3891db06ee04542a88290c2a769b6f9afa0e76927c81" +
            "542a88290c2a769b6f9afa0e76927c81542a88290c2a769b6f9afa0e76927c81" +
            "40a582270c2a769b6f9afa0e76927c8140a582270c2a769b6f9afa0e76927c81" +
            "40a582270c2a769b6f9afa0e76927c8140a582270c2a769b6f9afa0e76927c81" +
            "e14fa9243ffaea1790c8328b15db0600e14fa9243ffaea1790c8328b15db0600" +
            "e14fa9243ffaea1790c8328b15db0600e14fa9243ffaea1790c8328b15db0600" +
            "e14fa9243ffaea1790c8328b15db0600e14fa9243ffaea1790c8328b15db0600" +
            "853fa5230b2e28960377530915db0000853fa5230b2e28960377530915db0000" +
            "14fe94220b2e28960377530915db000014fe94220b2e28960377530915db0000" +
            "9df02721aa8fbe14f2233288eb2400809df02721aa8fbe14f2233288eb240080" +
            "9df02721aa8fbe14f2233288eb24008075c21f20a73efa13c98f4887eb040080" +
            "75c21f20a73efa13c98f4887eb040080ac13fe1e2d2b3891db06ee0415000000" +
            "ac13fe1e2d2b3891db06ee0415000000ac13fe1e2d2b3891db06ee0415000000" +
            "58277c1e2d2b3891db06ee0415000000b04ef81d2d2b3891db06ee0415000000" +
            "5f9d703da7a98f3027c90fa36233b596bf3ae13cb2ac60b027c90fa36233b596" +
            "7d75423c6f9afa2e76927ca1e2c9ac14faea843b6f9afa2e76927ca1e2c9ac14" +
            "485f1d3924b22cac96625b1e7987cd91485f1d3924b22cac96625b1e7987cd91" +
            "485f1d3924b22cac96625b1e7987cd91485f1d3924b22cac96625b1e7987cd91" +
            "485f1d3924b22cac96625b1e7987cd913ffaea3790c832ab96625b1e7987cd91" +
            "3ffaea3790c832ab96625b1e7987cd913ffaea3790c832ab96625b1e7987cd91" +
            "7df45537e06e9a2a96625b1e7987cd91fbe8ab363f224baaaa75129d1de2c910" +
            "eaa3af3503775329ad14db1c8e77d88feaa3af3503775329ad14db1c8e77d88f" +
            "aa8fbe34f22332a84dad939bc8219e0eaa8fbe34f22332a84dad939bc8219e0e" +
            "a73efa33c98f48a7676a1d9a410e710da73efa33c98f48a7676a1d9a410e710d" +
            "4d7d7433dbc05d26322bc519410e710d9afae832dbc05d26322bc519410e710d" +
            "35f5513292fc08a53653eb98f01b6f8b6aeaa33192fc08a53653eb98f01b6f8b" +
            "a7a98f3027c90fa36233b59684208709a7a98f3027c90fa36233b59684208709" +
            "6f9afa2e76927ca1e2c9ac14801064076f9afa2e76927ca1e2c9ac1480106407" +
            "6f9afa2e76927ca1e2c9ac14801064076f9afa2e76927ca1e2c9ac1480106407" +
            "de34752e76927ca1e2c9ac1480106407bc69ea2d76927ca1e2c9ac1480106407" +
            "77d3542d96625b1e7987cd91f30f8204eea6a92c96625b1e7987cd91f30f8204" +
            "b89ba62b96625b1e7987cd91f30f8204b89ba62b96625b1e7987cd91f30f8204" +
            "e06e9a2a96625b1e7987cd91f30f82040700000008000000090000000a000000";

        // Exact zlib-compressed 3,876-double table used by Simulation Start's
        // source-transcribed spring sine and normal-cone cosine helpers.
        private const string SimulationStartTrigTableZlibBase64 =
            "eNrtmHlYTVvcx1NponmeNCgNUqmkDpWQWRGvoYsUV0ghIUNKdQ2VJhFJdQ2FiwaEIpkSckndDJEuIUWpS4amd6/V3v2xen7PPpzO5b7P+/fn7NNa3/Vb30/7" +
            "hBTd9DF3v+ZQNtZ9//t0/+HFE7J8qnyNbZVeagnbXisdIqFrcPbyxt8dXLUCV19JcR2+Z5dnRcFTBa75EW0/P/ViL4fErzV/yLfrDTc85bpM/dxtmxf+ku8D" +
            "X/ic4Tc/FII26OKwtPZghvNnoeGelmec47R+P1c3Kz5Iptp8CBuf0Dt2Z8V8ewfnaWiDz4b1s55Wp/fF45y7ZkSTdMhbq3gcgAnIjRVHO/uGqjrIzZ6xwvG6" +
            "b57fNgNqhbeHZnyqpf6CudV0421JT0SEQJ7q6lhdbf3Qnl98xGEUQAHIq1yOUgl721f5ooT7D/uvcWomqQBm2AuuLaVGvI1TLeOy6PDDnC4uEYROeJh99diF" +
            "sy/3vp6b3yi17+hqv7MHZIydHwiYnWbjCu1oAgxA7vx5GnXCfe2tVwydHPjhDCdE4/nN4wreQy/UXeQovXxmycaT3qdPl7H9Ygdxzt8ogOd2jwueWn0sSeBQ" +
            "l27nbKMZXbxcHG3glB011LG/9jbIrWopHLYsrTzn2CiFkdffuJ3ilWfiDUTyjc/bjwJYZ/cQB2DFkcEBVFszPB8H4GmHWsfqoyxnhBiagCtd/MNfaAOD7Qxz" +
            "JJ9MnvbMtt0xZtTwvbusZzWepCbAypJXPg7V5vT3w8s44zeN3v3b+WXBDeoNmbY56jPQCZRb8Jt/KJlp0Gq0a7ibEV6gba7IZ2oEW86MT+aM1pmelP2zc8g7" +
            "5yUHVn6c52PBxiHvcMtJbzynvfFkHFqgQjavnPRKLe2V/ngB9YPZOOmVebRXfPXOelzPS+aZJ6XZf60Nuwtya6p1/hK/NOz9whnhPkJrbcj14dqVPzkMtU6O" +
            "5Bwb8vlKqpVmGiQNq/RAGzQ7J6aY7h3ckHda4/yO6qOjpmddWIIC2AbyNai2968Yhmvb2rzb95O9f5Lu9fsr0QrrzX80J73T01ykPu1odH4tB7eS575uXIq6" +
            "dFqBf3FILz17XuSj53IiE/KK+JtzsU+2rDZn45B3uOW+QmiDQZz85ReuLlqqeZbp7ad6h16M8aswY+OPcQC+HO0ineTiCTrdvh+3jtbcbt5gnqcu7b40+wkg" +
            "h7zDcMg73HLIK/8Wd8UB/Gn7WdRRqnHhmm78EA7gIshxLSces63Wwids7Xk9r/KPBbKWEcuWr6y2zs7YjQPYZct4S432VunkkRxfvQQz3Cql/rZT8AJVrb+V" +
            "k14ZR3vlkFPOWRu/iRlsnPTKOdoLK94M0NEcqmvGKye9Q/LOWv3HJtuwgxrhk0Os49KlpooNyRZYEvtuUNTbk2wc8o7gOf+dMVF5prxyZ1S7K87aRDl9oSZg" +
            "5ZC4iszncxv0LRiOWqeiYH+XF3RpLwjhDaaz8gCLgddzNkeAnPQOySHv6OMPDGLluLbVx4Ec8g7Dod5fO95CIMHXc9B/nUPeYTjkHW659lY0AVtATnpHjO71" +
            "vIlxvc75W7Jy0jskl8EbtPluTnqn2/OEN57QvSlRazpepCrOhN+c9M63ctIbPc1Jr3wrJ70TTnvn0czRFa+C/I+z8VsOKIBRXV65T3uF4/hU/6bAJBPSOz3N" +
            "D7SGUldA0NoXb/CcBeOlcWMMjuTprRsIeaOnOOSVnuILp6IAkkBeiAPYNqTa+njAgw1OFsETh1L/ujWaMhzyTuUrT3dZn1/+IL0gSHshNtJ5ytrxngP5zUkv" +
            "6NFeuKejuj+1/r7xj+b5HDQBj6yY96nHr4JOFzU3nygI2BcR6HT62MbVJtQVuAJy6tKgE7Qq3IFOaOzguL4Fh/eFCZsGSd2sEV6dbswrJ3t/Dd370vgD+j89" +
            "J3s/l+79hvevYyKdq4x+dk5dOmoC7oL8PQ7gEsipS/lXlmGGJa5l9RnmZXPRCfcZVD6s1VbvYKjRNVS7U5NBHr724swbByIt42Ki1G/62JhTl141eOInE4Yr" +
            "NazPiHJaZ5l98Xpsxbh+mV/DF1e0RqcdT5eRVlm+yuOoMdVqmhGelqjV4iq0zVPr4xYKmD7teh7yhp9EY3CjtcFRXjnplYe0V7jlkBduZ1X+fVfnkSG/OeQd" +
            "4yyNOs12DVb+BNXyX7+DHPLOv8X98A+lbt28wnDIOwyHvHNqjRo1gjXpbHyc71VqxEW/m5PeiaG9w6yPjY/BATwdjGvXP9J0y0L/kNyJFgPTr/kdX/v5H4Mo" +
            "HMDtwYkdJboVv8w5+dzHtFmxROmPRe+snHX63UvXuOlDTcBZkEPeifwVfWAeK3+CA9gBctQ6ig3rQe6Hf4j8dTDpLYaT3tlEe4czefvLWQ3zDdi4xlB0woMG" +
            "j0O1L/d80LdyDg5AffAkVJs7Mwf1M0cnPPWYeGE2dcJVaf44AFGQk96Ror3TsCpRjrrDA9h4Z+0+Afm4GyiAIpDjWp6VBXLSC/W0F/xTSuNnRR3mO4e8ElJj" +
            "n26UpcHKIe9wyyHvMBzyxliZp6+t9Av1fzTPHY8moNAMtYaFgJcJbo04WSOG1+AN/vHdnPTOLdo71jigWP1JqHZjN5qhVsn5onW8zOa3gIKAvCPu/bfVr0p0" +
            "ZeW7feWoK7DEjLp0CXpC2t2+3xT/UOnazQunQ/yeOZnnHIK80VMc8kpPcdIb2bQ3SiRuBSpf3sN/DniHWR/pnTTaOwlf1Rz9Uw7qsXEVHEAAyHHt3vcw5egd" +
            "lC+bKziQ6f1JCidSn6wtOQh549/i40SqqCugBnLIO13PA17hlpNeEaO9kjcanWACz5z0Qj3the1r5tZ6C2/u/6M55I3YxQ8O548ZwTOHvLJ65IG5CV+P6fLK" +
            "Ie8wHPIOt3wEquU5t0AeggM4bZKNalV1rlF9HpqA2sODmtdsP6AYdoD0yhi699Pk5d7llq3VZeOkN3qaQ965YYI20PsAG/fHAdiAHPIOw6HebrdZlHV24vTf" +
            "/5/zxiHvMJz0xm7aG5tfTDLQe/yrDq8c8k5JYsHKNHk/bV455I2e4pA3eoqjVpEv22GMW6VO0wDXpsyd/tzyz6vQBGwAOa7lKV4gv5YyyoLjONmY8VYu7a3c" +
            "+DZqQmamsvEtDlupCeAYtyahCfg0gOSkd7bR3oksF46y3D9CezjeoLCx0uVZ5c4v4tPOTUQBzTy4CS/wHy02TnonhvYOt5zsdX+616s/OXkL3pj903PSOya0" +
            "d1Zo17g2v7BJ4ZUvvHiVmoAJIC9cv5WaACsjsQMt1AQ06ZPrg7zjuMn99IAVGqyc9EYh7Y1HQ2X8jVouJ/Ob716AArhiOI9+n0p6EzY6z1RR1znmmfIJ8Qv9" +
            "Mjs3wDe+jWqN96/nG+JaLdXTL9zrPO503X0dDg4ohmcOeWHsK+EvgSVfNX80d/W0pa6AuGFaPpqQa3okJ70TTHvnZpL2JTO3/v2s9NEJ3jXILXtAjehGPTmb" +
            "P6kRHaQTXSze1HLgpSavfOkEkxvrt14yMHRzPN+gO+7QQoeo2W/fNaWG78tarl2Tvb+Map2PUhkgT8O1nGzw1hW9sU/TI7nzNBRApME8/EJnpmfYsrLYc/mN" +
            "1OlPIgOFHLfux7W7NgDkpHfu0b0ftXohNWJDNUkv/Gx8Ew6gjwHplXs21+88HFqQBHmH4ZB3uOVPXqMJuAPy3LtLqAnI7eaV215Jzxe9/SUJ8g7D7wWiDW75" +
            "bj76ky11wosHDNB7vPpoxt+6+WZu8jZ/HtJSL86KKhb31GDj23AAU0EOecdqyJ4FmntL1fnNhUtQAOIgh7zDcNIrI2iv9BTHtRp/RD8R1aqru26zpPDcW5ve" +
            "JqucalJNP7duHxsnvfOQ9g7DIS+kWKIFzFbnN4e8ETp4YMrK8GH7eOXUpaJOWEgf1+rcdJ0iurcn4AU8VWPjuDZXPdarsikV375mR49z0jtjaO8YBP5ZNj/q" +
            "jBrpHfJ5Nk56JYr2yv4PttNCbXfzzNcczZAd/WlJN6/Y5MwvvuU1JxHyDsMhr4x0/pp09LKJGq881/TjkJCafnpLBW9QE1KmXR5rS01IvCbDce2WSOodF9fw" +
            "4uhkac/C4l/Zxd92BtAf4qjVZEe/7uaVMUXjqRN4qAp5h1t+7+TEwB3auSBHraTmeKibN1p1qw/d3btUFfIKt5z0wi3aC29GfCpUihTfy29OekON9kake1jS" +
            "B1t51Z+dg14p2Vy/Y1DAHn7zWlS7H3fpMu9TJIe8wy2HvCMVVkOdoAgrt9qPJsAZ5Is4OiUnJ9rpolZMLGjsR106jbqi4+pVeZ+disa7q+DaTjDu8koy7ZUv" +
            "FyOoE1BQIb1Dcj+8wQ86qDUSsqOTQ2hvDJU5IPRUvS6BjZPe+VYOeSffGn3Am2cOeYdbjlpH7t16kEPeYThqlZjFY3UYrw2gvfZ79SfTTbJ+ymyc9E4S7R1R" +
            "/UtrGyNGsPIBK9AEqOtwLAyKGiIKNf3uv54k+SpA7W0q+gONSpNwACIgt8Y/NNZqk14pkpqwqeH5WVYOeYfhkFe45ZAXBG0az2yWsdvNbw55o9FhzZSmDaJK" +
            "vHLSCzW0Fx73QgvI3PWj+fsItIE7fONVVGtpeOWCHPIOw1vzF0+usgnVoi4VdYLmGvNwwG9URgwTMMi3ns/KIa/0StUMlndvieeVU5eOCmAUyCHv9BQPwQGI" +
            "aZFeYTjkHYaTXvlMe6U9aHtHVuh9BX5zXLvyR0BOesea9o6uwGLRqmsJ8VBv124VoHb4z87/Oie9kkp7RaihY2Jr9CAFXjnpHRHaO30udJg1OogoQF7Z07uy" +
            "I+Fzijwbr8UbPKaJWlGt2OObOeSdgpQ3VEJtcZBXuOWQF9p7nSpo6bgix2/OwRvU0qypfEiN+KW938r9jvdfFdIqpRkZs9Pea2lBt+9/hQNo02C89J72EsNx" +
            "7TbVgRy1jnz1A5Dj2o259N38CtVKSdoZGlL+y5dd3uO0tx/VSupijbsapPEEyIXYogCSNVBrpVj+T7fnRVahACI1nivrGAT+aaV6reOh482Gd4rM831xAOtA" +
            "Dnln7WKxz5ZtqbGQV3qKk70uQPfyf4WTXulpzqFaqTx2rzrzPlWPakvzkEJkwLqgApP5sv5paAJCQQ555bWUZK+gNPdYXjl16cxvcEaqd9ZqkzL593Gtlsuq" +
            "66FajbmqjGt1TbDCoDEXLjjMb5bhlUPecIuQNaNmnO88HgdwC+SkdwRp7+SoNDa1Bz+SIb0jQXvHe/Dzl229rrJyyDuKp5X6z6uUZuWQdxgOeWPnx8P+9fdi" +
            "ovnNw3AAqiAXs32zKk1ECOSQd+Zk58f/qTmBZw55h+FQ7/9XOOQdhpNeqae9cj8t9YxKo6s0Gye9s4buvd3CCcfNDi+IYuOkV3qaX8ABlIK88roZNcLHVYJR" +
            "Lca5K/Y0z0e1+2FvlxdIvlH5EnUFQkFOeqWneT6q5Z3OKgLm6I1fsNv6qUtJTYBdlzde0d64FVcV9/GwQlQrDsAY5KR3SA55x+ex/WOF0yJSbJz0igntldTJ" +
            "FWP3heRI8soNO3+o7Nb7vQdMDJlYvnYHr5y6lNQEbAc55B2G015Rp72isrTTKwrty1BAYbK8ctorarRXlBU6vaJw61QKlVCezI/mtDfUaG/sjuv0xk5R9QHm" +
            "s+UmxfCbaw9DJ5zy3XwEqmXlaJAHdwYAcoFHVC3PXQbz7NC4Z3mzQN6+AP1S66imbY7emHspk5z2hhrtDSXaGztTRNAHrkTzm9PeUaW9o0R7R55bvg3V8rMK" +
            "kMt1oABuqFKXXimgI0gpxrr3ievbDLr4JKp14ltPqtK9uIvuxbjYt0syPQSFWPmez1rUBOwHOa7dpgiQz38eRE3AWpDT3vluLiCPAnCB+YD2G1IT7GGOAzCB" +
            "OQ5AFead3gE57Q0V2hu7aG/Elflcabp56pIUr5z2igrtFcVlnV6R6ylOe0WF9ooC7RXZvhELXUIlp0Wxcbr3VejeVxDu7P3YubP0NqgtM/zpuQiqbS11FcP9" +
            "w6yEW8/HkxzyDsNN3rdfutZRo0y/jykkt6EPCMtqH0yvCHt5UJKNu1W1URNQorzn/vlRowqC4kkOeWVy1RxqBcY7+M1x7TZGgxy1kvvzIJAX4ACWgzx4NgrA" +
            "HeSCqHblXLp6X4Tu/UWCr6/oPvonUnjR5k8d+vYgFytGE2ACchkcgArISe+QnPRCMt3LW39FH1jHd056o6c56Z1v5QFBaAKWg5y6lNQEuCuhVlLqLyWPWill" +
            "cp70qyXNCz74/9L3VRsKwEWp84XwTlx2+uUt4pMWRY+4arF5lUevyOIWIWoCHEC+55MoNQFmIDfFP1RqKTWXoABK5OR2u1BXMFy6uPTtjZo3Y/rOq9SiJkBa" +
            "aZmWj4RbRKxcYubGprde06TnJy9yGOOi3PdCZwCKEMe1+74e5O9xAE9BjlrnVMFtxft4gbPkcsRvG9zdpCTd8RIFVNbn2m0UwFmQy6HW6Z2smK13bmGgkV1c" +
            "OKpt+YdRSqkeewvOx0SwcV0cQKRi2ruDkx29HeWeDDBJGd7yRaolIf1RdMmpPmM6A+jmlVxBKxN5m7ERkHcYDnkl50jQusS2zxL/dU56Zw7tDaO5vdR2iz8J" +
            "Z+Okd0gOeeWXqSjhUTxzXMtawSAne3sS3dthJwypFZZv/7/OjRejX4o75B+ab75J/esWQ3LXe27UFWiQj/dy2JcTndbteVy7TZXyU3DA4d24syP6JfaO/BWq" +
            "tXYLe8UUb4pM9pUXkfx06KRT2+2r4okh5Z7XbufJJw9veXQ60F/mcXRJqc8VC0nmeVy7CenyqFVKm6fKkM/j2p0XJX+Lag1rHy2Zpah2993rOx1/gdt2Nn7a" +
            "CAWwEeSLp6EAloCc9M4W2gtJusuc3khobye90dMc8o6CjdPD8Pu7trHxTTiAVrlmKzwB0YtnDVhhamIRyfCvOIAaubCXO6kJSOv2POQdhkNe+Lc46ZV22isP" +
            "o1e71LqFifGbk975SnvH3aHc7qi3hxjklXupBUZXZlRv5Tc/vaSFOuHabr2vaWW4IjzzN1a+uBQF8BfIIa9wy9Gl85FIlK15Y+3xpXq81Ldy0juGtHcY3nwK" +
            "bXC+LGqV3S5SUrlKH81cTmVIqLjnbzq+wVWUjXd7H6K90rkAga0/Ow/AG3wh870c8kpfec7iKVX+W3jlkHcYDnmHWw55h+Gkd5pp76xvfn77QfRvImwc8obm" +
            "h7fXEzI6evOb41p+LCUz/A5aYGjf7PrxcyO+DhUv/HwlTEot/jfUSo9Ot0lDfJb9OmoC6kCOa7e0HOSQd8Q6P8DKIe8wHPIOtxzX8iN/aXOXU1oH0wd245BX" +
            "uOVP8AYGSuPaVS6MmFKl4DFwwtoe45B3up4nvDOP9k5rUmjyxc+6vdl47mQ0AS+kyi6hE47q0/RxwdOduQPE1qWsundK+Zkw5JU6mcjG38R3hPHKj1SgADJA" +
            "7nwWBZAsdQAHML1P8QMUgIQYw3FtJ++QCscbHNxnT4ZWXXLZR1GGD3+KAtgA8vU4gEVdXtGgvZEjdVnFfc+IMNI738rvl6IALKUYL5Ec8k5OuY7Kiz7/hPLK" +
            "VexQAK2SELfAAbzp1vvjja63JIWeFFpItU7mxvsgh7zRU7wdbyBIkrp0iqkequHmv4eK9HbO2rLE+8Qo80KvUF7518EoAF/JeBxQfwmS49rNnCOZXHaGOuGv" +
            "4tSloa7ICREzo8MBKaumCKHWsfYYD3LIO8cmTjCqfN0qCHmlp7hVC9pgTd9cg9WDat2TxVO9zPI3to3jmpPe0aC9Y70andBxQcgL4oYDH7vVCYT8aA55xbDX" +
            "r06/eF/czCuHvMNwyDvccsg7DA+mWkfFrq3P9/L2JjQBtX2aUe0rHRbrxgHvMBzyCrec9E4A7Z1LzQ/K9A+H9eKV41pWCQT5lA4UwFKQk96ppb0hER+cfeCE" +
            "02bSK9/KIW9sb3vsPi2hWoDffNlUFMDfIIe8oZ3l3uJdG8d37o9aaVEKyGvd0ARESeSj2n3aX/TkGbSBotDWbWgDXgK4lhMDQX7EGwXgDXLXB2gCZkig1tOq" +
            "axcZR3uJ4ROo1klIt+3yxmLaG6uqnFOF4xWD2TjpHZKTXjGlvbJDCwUgIcArtz+KAqgWJ72E/76CQDDkFW455JWe4mtc0AREim/0GCkqKWGyhbpU1AkWhWAu" +
            "LBBc2xmA+Mi78zZ++TpYhOSolaZ2eIqTXsNcQCCY9IoY7RXEBXqAF+ENan03j0G1XCYNcu06FECHGMTtcQANYriWmw73LkhDE+LetX906R4cqBTzl0InvLU3" +
            "+XzrLPRL7R2Qf81CAeSK3bOteRRhtrwbh7xDcQHEIe9wyyHvcMtJL+TTXqDuD+IC/OaQd3Zo9eKKQ95h+Dxcqw9Ewz/ZitptiBV++6A9MfeQVS9uOXWpqBO+" +
            "KHoIb2CmcCauZTmuOa7dncdA/v5l3Y1cg10gL0S1nOzfzQurMBUIZuOQV7jlkDckO7nA/wLHBheP";

        private static readonly float[] FloatSinCosReducerTable = BuildFloatSinCosReducerTable();
        private static readonly double[] SimulationStartTrigTable = BuildSimulationStartTrigTable();

        public struct Double3
        {
            public double x;
            public double y;
            public double z;

            public Double3(double x, double y, double z)
            {
                this.x = x;
                this.y = y;
                this.z = z;
            }
        }

        public struct Float3
        {
            public float x;
            public float y;
            public float z;

            public Float3(float x, float y, float z)
            {
                this.x = x;
                this.y = y;
                this.z = z;
            }
        }

        public struct Float4
        {
            public float x;
            public float y;
            public float z;
            public float w;

            public Float4(float x, float y, float z, float w)
            {
                this.x = x;
                this.y = y;
                this.z = z;
                this.w = w;
            }
        }

        public struct CapsuleColliderWork
        {
            public byte flag;
            public Double3 aabbMin;
            public Double3 aabbMax;
            public float radius0;
            public float radius1;
            public Double3 old0;
            public Double3 old1;
            public Double3 next0;
            public Double3 next1;
            public Float4 inverseOldRotation;
            public Float4 rotation;
        }

        public struct ColliderStartInput
        {
            public byte flag;
            public Float3 size;
            public Float3 framePosition;
            public Float4 frameRotation;
            public Float3 frameScale;
            public Float3 oldFramePosition;
            public Float4 oldFrameRotation;
            public float frameInterpolation;
            public float centerMoveRatio;
            public float centerRotationRatio;
        }

        // Logical layout of the native 184-byte WorkData element. The managed
        // port intentionally exposes fields rather than an opaque byte buffer.
        public struct ColliderStartWorkData
        {
            public Double3 aabbMin;
            public Double3 aabbMax;
            public float radius0;
            public float radius1;
            public Double3 old0;
            public Double3 old1;
            public Double3 next0;
            public Double3 next1;
            public Float4 inverseOldRotation;
            public Float4 rotation;
        }

        public struct ColliderStartState
        {
            public Float3 nowPosition;
            public Float4 nowRotation;
            public Float3 oldPosition;
            public Float4 oldRotation;
            public ColliderStartWorkData workData;
        }

        public static bool StartCapsuleCollider(
            ColliderStartInput input,
            ref ColliderStartState state)
        {
            if (((~input.flag) & 0x30) != 0)
                return false;

            int colliderType = input.flag & 0x0f;
            if (colliderType < 2 || colliderType > 6)
                throw new NotSupportedException(
                    "Collider Start is transcribed only for Endminf capsule branches 2-6.");

            Float3 nowPosition = LerpFloat3Binary32(
                input.oldFramePosition, input.framePosition, input.frameInterpolation);
            Float4 nowRotation = NormalizeFloat4Binary32(SlerpQuaternionBinary32(
                input.oldFrameRotation, input.frameRotation, input.frameInterpolation));
            Float3 oldPosition = LerpFloat3Binary32(
                state.oldPosition, nowPosition, input.centerMoveRatio);

            // The native core publishes this normalized value, but deliberately
            // keeps the pre-normalized interpolation for old endpoint rotation
            // and inversion below.
            Float4 oldRotationRaw = SlerpQuaternionBinary32(
                state.oldRotation, nowRotation, input.centerRotationRatio);
            Float4 oldRotation = NormalizeFloat4Binary32(oldRotationRaw);

            state.nowPosition = nowPosition;
            state.nowRotation = nowRotation;
            state.oldPosition = oldPosition;
            state.oldRotation = oldRotation;

            Float3 axis;
            switch (colliderType)
            {
                case 2:
                case 5:
                    axis = new Float3(1.0f, 0.0f, 0.0f);
                    break;
                case 3:
                case 6:
                    axis = new Float3(0.0f, 1.0f, 0.0f);
                    break;
                case 4:
                    axis = new Float3(0.0f, 0.0f, 1.0f);
                    break;
                default:
                    throw new InvalidOperationException("Unreachable capsule branch.");
            }

            float scaleX = MultiplyBinary32(input.frameScale.x, axis.x);
            float scaleY = MultiplyBinary32(input.frameScale.y, axis.y);
            float scaleZ = MultiplyBinary32(input.frameScale.z, axis.z);
            float axisScale = AddBinary32(AddBinary32(scaleX, scaleY), scaleZ);
            Float3 direction;
            if (axisScale == 0.0f)
            {
                direction = new Float3(0.0f, 0.0f, 0.0f);
            }
            else
            {
                float sign = axisScale < 0.0f ? -1.0f : 1.0f;
                direction = new Float3(
                    MultiplyBinary32(axis.x, sign),
                    MultiplyBinary32(axis.y, sign),
                    MultiplyBinary32(axis.z, sign));
            }
            if ((input.flag & 0x80) != 0)
                direction = new Float3(-direction.x, -direction.y, -direction.z);

            float absoluteScale = Math.Abs(axisScale);
            float radius0 = MultiplyBinary32(input.size.x, absoluteScale);
            float radius1 = MultiplyBinary32(input.size.y, absoluteScale);
            float length = MultiplyBinary32(input.size.z, absoluteScale);
            float separation0;
            float separation1;
            if (colliderType < 5)
            {
                float half = MultiplyBinary32(length, 0.5f);
                separation0 = Math.Max(SubtractBinary32(half, radius0), 0.0f);
                separation1 = Math.Max(SubtractBinary32(half, radius1), 0.0f);
            }
            else
            {
                separation0 = 0.0f;
                separation1 = Math.Max(
                    SubtractBinary32(SubtractBinary32(length, radius0), radius1), 0.0f);
            }

            Float3 local0 = new Float3(
                MultiplyBinary32(direction.x, separation0),
                MultiplyBinary32(direction.y, separation0),
                MultiplyBinary32(direction.z, separation0));
            Float3 local1 = new Float3(
                MultiplyBinary32(direction.x, separation1),
                MultiplyBinary32(direction.y, separation1),
                MultiplyBinary32(direction.z, separation1));
            Float3 oldOffset0 = RotateQuaternionColliderStartBinary32(oldRotationRaw, local0);
            Float3 oldOffset1 = RotateQuaternionColliderStartBinary32(oldRotationRaw, local1);
            Float3 nextOffset0 = RotateQuaternionColliderStartBinary32(nowRotation, local0);
            Float3 nextOffset1 = RotateQuaternionColliderStartBinary32(nowRotation, local1);
            Float3 old0 = AddFloat3Binary32(oldPosition, oldOffset0);
            Float3 old1 = SubtractFloat3Binary32(oldPosition, oldOffset1);
            Float3 next0 = AddFloat3Binary32(nowPosition, nextOffset0);
            Float3 next1 = SubtractFloat3Binary32(nowPosition, nextOffset1);

            Float3 lower = new Float3(
                Min4Binary32(SubtractBinary32(old0.x, radius0), SubtractBinary32(next0.x, radius0),
                    SubtractBinary32(old1.x, radius1), SubtractBinary32(next1.x, radius1)),
                Min4Binary32(SubtractBinary32(old0.y, radius0), SubtractBinary32(next0.y, radius0),
                    SubtractBinary32(old1.y, radius1), SubtractBinary32(next1.y, radius1)),
                Min4Binary32(SubtractBinary32(old0.z, radius0), SubtractBinary32(next0.z, radius0),
                    SubtractBinary32(old1.z, radius1), SubtractBinary32(next1.z, radius1)));
            Float3 upper = new Float3(
                Max4Binary32(AddBinary32(old0.x, radius0), AddBinary32(next0.x, radius0),
                    AddBinary32(old1.x, radius1), AddBinary32(next1.x, radius1)),
                Max4Binary32(AddBinary32(old0.y, radius0), AddBinary32(next0.y, radius0),
                    AddBinary32(old1.y, radius1), AddBinary32(next1.y, radius1)),
                Max4Binary32(AddBinary32(old0.z, radius0), AddBinary32(next0.z, radius0),
                    AddBinary32(old1.z, radius1), AddBinary32(next1.z, radius1)));

            float normSquared = DotFloat4Binary32(oldRotationRaw, oldRotationRaw);
            float inverseNormSquared = DivideBinary32(1.0f, normSquared);
            Float4 scaledInverse = new Float4(
                MultiplyBinary32(oldRotationRaw.x, inverseNormSquared),
                MultiplyBinary32(oldRotationRaw.y, inverseNormSquared),
                MultiplyBinary32(oldRotationRaw.z, inverseNormSquared),
                MultiplyBinary32(oldRotationRaw.w, inverseNormSquared));

            state.workData = new ColliderStartWorkData
            {
                aabbMin = new Double3(lower.x, lower.y, lower.z),
                aabbMax = new Double3(upper.x, upper.y, upper.z),
                radius0 = radius0,
                radius1 = radius1,
                old0 = new Double3(old0.x, old0.y, old0.z),
                old1 = new Double3(old1.x, old1.y, old1.z),
                next0 = new Double3(next0.x, next0.y, next0.z),
                next1 = new Double3(next1.x, next1.y, next1.z),
                inverseOldRotation = new Float4(
                    -scaledInverse.x, -scaledInverse.y, -scaledInverse.z, scaledInverse.w),
                rotation = nowRotation,
            };
            return true;
        }

        /// <summary>
        /// Exact Collider End snapshot stage: selected colliders publish their
        /// current transform as the previous transform for the next step.
        /// Validation is completed before publication so malformed managed
        /// inputs cannot produce a partial snapshot.
        /// </summary>
        public static void FinishColliderSnapshots(
            int[] jobColliderIndexList,
            Double3[] nowPositions,
            Float4[] nowRotations,
            Double3[] oldPositions,
            Float4[] oldRotations,
            int indexCount)
        {
            // The native job dereferences no array when *_indexCount <= 0.
            if (indexCount <= 0)
                return;

            if (jobColliderIndexList == null)
                throw new ArgumentNullException(nameof(jobColliderIndexList));
            if (nowPositions == null)
                throw new ArgumentNullException(nameof(nowPositions));
            if (nowRotations == null)
                throw new ArgumentNullException(nameof(nowRotations));
            if (oldPositions == null)
                throw new ArgumentNullException(nameof(oldPositions));
            if (oldRotations == null)
                throw new ArgumentNullException(nameof(oldRotations));
            if (indexCount > jobColliderIndexList.Length)
                throw new ArgumentOutOfRangeException(nameof(indexCount));

            // Validate the complete selected range before the first write.
            for (int offset = 0; offset < indexCount; offset++)
            {
                int colliderIndex = jobColliderIndexList[offset];
                if (colliderIndex < 0 ||
                    colliderIndex >= nowPositions.Length ||
                    colliderIndex >= nowRotations.Length ||
                    colliderIndex >= oldPositions.Length ||
                    colliderIndex >= oldRotations.Length)
                {
                    throw new ArgumentOutOfRangeException(
                        nameof(jobColliderIndexList),
                        "Collider End selected an index outside one or more transform arrays.");
                }
            }

            for (int offset = 0; offset < indexCount; offset++)
            {
                int colliderIndex = jobColliderIndexList[offset];
                oldPositions[colliderIndex] = nowPositions[colliderIndex];
                oldRotations[colliderIndex] = nowRotations[colliderIndex];
            }
        }

        public static bool ProjectTether(
            Double3 rootNext,
            ref Double3 childNext,
            Double3 rootBasic,
            Double3 childBasic,
            float compressionLimit,
            float stretchLimit,
            ref Double3 childVelocityPosition)
        {
            double dx = rootNext.x - childNext.x;
            double dy = rootNext.y - childNext.y;
            double dz = rootNext.z - childNext.z;
            double currentLength = Math.Sqrt(dx * dx + dy * dy + dz * dz);
            if (currentLength < 9.99999993922529e-9)
                return false;

            double bdx = rootBasic.x - childBasic.x;
            double bdy = rootBasic.y - childBasic.y;
            double bdz = rootBasic.z - childBasic.z;
            double basicLength = Math.Sqrt(bdx * bdx + bdy * bdy + bdz * bdz);
            if (basicLength == 0.0)
                return false;

            double ratio = currentLength / basicLength;
            double targetRatio;
            double activation;
            float compressionThresholdFloat = SubtractBinary32(1.0f, compressionLimit);
            double compressionThreshold = compressionThresholdFloat;
            if (compressionThreshold > ratio)
            {
                targetRatio = compressionThreshold;
                activation = Math.Min(
                    Math.Max((targetRatio - ratio) / 0.30000001192092896, 0.0),
                    1.0);
            }
            else
            {
                float stretchThresholdFloat = AddBinary32(1.0f, stretchLimit);
                double stretchThreshold = stretchThresholdFloat;
                if (ratio <= stretchThreshold)
                    return false;
                targetRatio = stretchThreshold;
                activation = Math.Min(
                    Math.Max((ratio - targetRatio) / 0.30000001192092896, 0.0),
                    1.0);
            }

            double signedError = currentLength - basicLength * targetRatio;
            double nx = dx / currentLength;
            double ny = dy / currentLength;
            double nz = dz / currentLength;
            double correctionMagnitude = activation * signedError;
            double cx = nx * correctionMagnitude;
            double cy = ny * correctionMagnitude;
            double cz = nz * correctionMagnitude;

            childNext.x += cx;
            childNext.y += cy;
            childNext.z += cz;
            childVelocityPosition.x += cx * 0.699999988079071;
            childVelocityPosition.y += cy * 0.699999988079071;
            childVelocityPosition.z += cz * 0.699999988079071;
            return true;
        }

        public static int ProjectDistance(
            int particle,
            Double3[] nextPositions,
            Double3[] basePositions,
            Double3[] velocityPositions,
            byte[] attributes,
            float[] depths,
            float[] frictions,
            ushort[] neighborParticles,
            float[] signedRestLengths,
            float simulationPowerY,
            float[] restorationStiffness,
            float velocityAttenuation,
            float animationPoseRatio,
            float initScaleX,
            float scaleRatio,
            int teamFlag)
        {
            if (neighborParticles == null || signedRestLengths == null ||
                neighborParticles.Length == 0)
                return 0;
            if (neighborParticles.Length != signedRestLengths.Length)
                throw new ArgumentException("Distance neighbor/rest arrays differ in length.");
            if (restorationStiffness == null || restorationStiffness.Length != 16)
                throw new ArgumentException("Distance restoration curve must contain 16 samples.");

            float depth = depths[particle];
            float clampedDepth = Math.Min(Math.Max(depth, 0.0f), 1.0f);
            float coordinate = MultiplyBinary32(clampedDepth, 15.0f);
            int curveIndex = (int)coordinate;
            int nextCurveIndex = Math.Min(curveIndex + 1, 15);
            const float CurveStep = 0.06666667014360428f;
            float fraction = DivideBinary32(
                SubtractBinary32(depth, MultiplyBinary32(curveIndex, CurveStep)),
                CurveStep);
            float curve = AddBinary32(
                restorationStiffness[curveIndex],
                MultiplyBinary32(
                    fraction,
                    SubtractBinary32(
                        restorationStiffness[nextCurveIndex],
                        restorationStiffness[curveIndex])));
            curve = Math.Min(Math.Max(curve, 0.0f), 1.0f);
            float baseStiffness = MultiplyBinary32(simulationPowerY, curve);
            float currentWeight = DistanceWeight(
                attributes[particle], depths[particle], frictions[particle], teamFlag);
            float scale = MultiplyBinary32(initScaleX, scaleRatio);

            Double3 current = nextPositions[particle];
            double sumX = 0.0;
            double sumY = 0.0;
            double sumZ = 0.0;
            int accepted = 0;
            for (int index = 0; index < neighborParticles.Length; index++)
            {
                int neighbor = neighborParticles[index];
                float signedRest = signedRestLengths[index];
                float stiffness = signedRest > 0.0f
                    ? baseStiffness
                    : MultiplyBinary32(baseStiffness, 0.5f);
                stiffness = Math.Min(Math.Max(stiffness, 0.0f), 1.0f);

                double dx = nextPositions[neighbor].x - current.x;
                double dy = nextPositions[neighbor].y - current.y;
                double dz = nextPositions[neighbor].z - current.z;
                double length = Math.Sqrt(dx * dx + dy * dy + dz * dz);
                if (length < 9.99999993922529e-9)
                    continue;

                double bdx = basePositions[neighbor].x - basePositions[particle].x;
                double bdy = basePositions[neighbor].y - basePositions[particle].y;
                double bdz = basePositions[neighbor].z - basePositions[particle].z;
                double baseLength = Math.Sqrt(bdx * bdx + bdy * bdy + bdz * bdz);
                float referenceFloat = MultiplyBinary32(Math.Abs(signedRest), scale);
                double reference = referenceFloat;
                double target = reference + (baseLength - reference) * animationPoseRatio;
                float neighborWeight = DistanceWeight(
                    attributes[neighbor], depths[neighbor], frictions[neighbor], teamFlag);
                double weightSum = AddBinary32(currentWeight, neighborWeight);
                sumX += DistanceCorrectionComponent(
                    dx, length, stiffness, target, weightSum, currentWeight);
                sumY += DistanceCorrectionComponent(
                    dy, length, stiffness, target, weightSum, currentWeight);
                sumZ += DistanceCorrectionComponent(
                    dz, length, stiffness, target, weightSum, currentWeight);
                accepted++;
            }

            if (accepted == 0)
                return 0;
            double inverseCount = 1.0 / accepted;
            double correctionX = sumX * inverseCount;
            double correctionY = sumY * inverseCount;
            double correctionZ = sumZ * inverseCount;
            nextPositions[particle] = new Double3(
                current.x + correctionX,
                current.y + correctionY,
                current.z + correctionZ);
            Double3 velocity = velocityPositions[particle];
            velocityPositions[particle] = new Double3(
                velocity.x + correctionX * velocityAttenuation,
                velocity.y + correctionY * velocityAttenuation,
                velocity.z + correctionZ * velocityAttenuation);
            return accepted;
        }

        public static int ProjectPointCapsules(
            ref Double3 nextPosition,
            ref Double3 velocityPosition,
            ref float friction,
            out Float3 collisionNormal,
            float particleRadius,
            CapsuleColliderWork[] colliders,
            bool boneSpring)
        {
            Double3 original = nextPosition;
            double addX = 0.0;
            double addY = 0.0;
            double addZ = 0.0;
            float addNormalX = 0.0f;
            float addNormalY = 0.0f;
            float addNormalZ = 0.0f;
            float contactNormalX = 0.0f;
            float contactNormalY = 0.0f;
            float contactNormalZ = 0.0f;
            double minimumDistance = double.MaxValue;
            int penetratingCount = 0;
            bool contactFound = false;

            if (colliders != null)
            {
                foreach (CapsuleColliderWork collider in colliders)
                {
                    int type = collider.flag & 0x0f;
                    if ((collider.flag & 0x30) != 0x30 || type < 2 || type > 7)
                        continue;
                    double expandedRadius = particleRadius * 2.0;
                    if (original.x + expandedRadius < collider.aabbMin.x ||
                        original.y + expandedRadius < collider.aabbMin.y ||
                        original.z + expandedRadius < collider.aabbMin.z ||
                        original.x - expandedRadius > collider.aabbMax.x ||
                        original.y - expandedRadius > collider.aabbMax.y ||
                        original.z - expandedRadius > collider.aabbMax.z)
                        continue;

                    double ux = collider.old1.x - collider.old0.x;
                    double uy = collider.old1.y - collider.old0.y;
                    double uz = collider.old1.z - collider.old0.z;
                    double denominator = (ux * ux + uy * uy) + uz * uz;
                    float t = 0.0f;
                    if (denominator != 0.0)
                    {
                        double px = original.x - collider.old0.x;
                        double py = original.y - collider.old0.y;
                        double pz = original.z - collider.old0.z;
                        t = (float)(((px * ux + py * uy) + pz * uz) / denominator);
                        t = Math.Min(Math.Max(t, 0.0f), 1.0f);
                    }
                    float colliderRadius = AddBinary32(
                        collider.radius0,
                        MultiplyBinary32(
                            SubtractBinary32(collider.radius1, collider.radius0), t));
                    double td = t;
                    double oldCenterX = collider.old0.x + ux * td;
                    double oldCenterY = collider.old0.y + uy * td;
                    double oldCenterZ = collider.old0.z + uz * td;
                    Float3 local = RotateQuaternionBinary32(
                        collider.inverseOldRotation,
                        new Float3(
                            (float)(original.x - oldCenterX),
                            (float)(original.y - oldCenterY),
                            (float)(original.z - oldCenterZ)));
                    Float3 transportedFloat = RotateQuaternionBinary32(collider.rotation, local);
                    double tx = transportedFloat.x;
                    double ty = transportedFloat.y;
                    double tz = transportedFloat.z;
                    double transportedLength = Math.Sqrt((tx * tx + ty * ty) + tz * tz);
                    double nx = tx / transportedLength;
                    double ny = ty / transportedLength;
                    double nz = tz / transportedLength;
                    double newCenterX = collider.next0.x + (collider.next1.x - collider.next0.x) * td;
                    double newCenterY = collider.next0.y + (collider.next1.y - collider.next0.y) * td;
                    double newCenterZ = collider.next0.z + (collider.next1.z - collider.next0.z) * td;
                    float surfaceRadius = AddBinary32(colliderRadius, particleRadius);
                    double surfaceX = newCenterX + nx * surfaceRadius;
                    double surfaceY = newCenterY + ny * surfaceRadius;
                    double surfaceZ = newCenterZ + nz * surfaceRadius;
                    double distance = ((original.x - surfaceX) * nx +
                        (original.y - surfaceY) * ny) + (original.z - surfaceZ) * nz;
                    float nxf = (float)nx;
                    float nyf = (float)ny;
                    float nzf = (float)nz;
                    if (distance <= 0.0)
                    {
                        addX += -nx * distance;
                        addY += -ny * distance;
                        addZ += -nz * distance;
                        addNormalX = AddBinary32(addNormalX, nxf);
                        addNormalY = AddBinary32(addNormalY, nyf);
                        addNormalZ = AddBinary32(addNormalZ, nzf);
                        penetratingCount++;
                    }
                    if (distance <= particleRadius)
                    {
                        contactNormalX = AddBinary32(contactNormalX, nxf);
                        contactNormalY = AddBinary32(contactNormalY, nyf);
                        contactNormalZ = AddBinary32(contactNormalZ, nzf);
                        minimumDistance = Math.Min(minimumDistance, distance);
                        contactFound = true;
                    }
                }
            }

            if (penetratingCount > 0)
            {
                float inverseCount = DivideBinary32(1.0f, penetratingCount);
                float averageX = MultiplyBinary32(addNormalX, inverseCount);
                float averageY = MultiplyBinary32(addNormalY, inverseCount);
                float averageZ = MultiplyBinary32(addNormalZ, inverseCount);
                float normalLength = SqrtBinary32(AddBinary32(
                    AddBinary32(MultiplyBinary32(averageX, averageX), MultiplyBinary32(averageY, averageY)),
                    MultiplyBinary32(averageZ, averageZ)));
                if (normalLength >= 1.0e-8f)
                {
                    float weight = Math.Min(normalLength, 1.0f);
                    nextPosition.x += addX / penetratingCount * weight;
                    nextPosition.y += addY / penetratingCount * weight;
                    nextPosition.z += addZ / penetratingCount * weight;
                }
                if (boneSpring)
                {
                    velocityPosition.x += addX;
                    velocityPosition.y += addY;
                    velocityPosition.z += addZ;
                }
            }

            collisionNormal = new Float3(0, 0, 0);
            if (contactFound && particleRadius > 0.0f)
            {
                float normalLengthSquared = AddBinary32(
                    AddBinary32(
                        MultiplyBinary32(contactNormalX, contactNormalX),
                        MultiplyBinary32(contactNormalY, contactNormalY)),
                    MultiplyBinary32(contactNormalZ, contactNormalZ));
                if (normalLengthSquared > 1.0e-6f)
                {
                    double ratio = Math.Min(Math.Max(minimumDistance / particleRadius, 0.0), 1.0);
                    friction = Math.Max(friction, (float)(1.0 - ratio));
                    collisionNormal = NormalizeFloat3Binary32(
                        new Float3(contactNormalX, contactNormalY, contactNormalZ));
                }
            }
            return penetratingCount;
        }

        public static void ProjectAngle(
            byte[] attributes,
            int[] parentIndices,
            float[] depths,
            float[] frictions,
            Double3[] basicPositions,
            Float4[] basicRotations,
            Double3[] nextPositions,
            Double3[] velocityPositions,
            bool restoration,
            float[] restorationCurve,
            float restorationVelocityAttenuation,
            float restorationGravityFalloff,
            bool limit,
            float[] limitCurve,
            float limitStiffness,
            float simulationPowerW,
            float gravityDot,
            Float4[] rotations,
            float[] lengths,
            Float3[] localPositions,
            Float4[] localRotations,
            Float3[] restorationVectors)
        {
            int count = attributes.Length;
            if (count < 2 || parentIndices.Length != count || depths.Length != count ||
                frictions.Length != count || basicPositions.Length != count ||
                basicRotations.Length != count || nextPositions.Length != count ||
                velocityPositions.Length != count || rotations.Length != count ||
                lengths.Length != count || localPositions.Length != count ||
                localRotations.Length != count || restorationVectors.Length != count)
                throw new ArgumentException("Angle arrays must have one entry per baseline particle.");
            if ((restoration && (restorationCurve == null || restorationCurve.Length != 16)) ||
                (limit && (limitCurve == null || limitCurve.Length != 16)))
                throw new ArgumentException("Angle curves must contain 16 samples.");

            for (int child = 0; child < count; child++)
            {
                rotations[child] = basicRotations[child];
                int parent = parentIndices[child];
                if (parent < 0)
                    continue;
                if (parent >= count)
                    throw new ArgumentException("Angle parent index is outside the baseline.");
                if (limit)
                {
                    lengths[child] = (float)LengthDouble3(
                        SubtractDouble3(nextPositions[parent], nextPositions[child]));
                    Double3 basicDirection = NormalizeDouble3(
                        SubtractDouble3(basicPositions[child], basicPositions[parent]));
                    Double3 local = RotateQuaternionDouble(
                        InverseQuaternionBinary32(basicRotations[parent]), basicDirection);
                    localPositions[child] = new Float3((float)local.x, (float)local.y, (float)local.z);
                    localRotations[child] = MultiplyQuaternionBinary32(
                        InverseQuaternionBinary32(basicRotations[parent]), basicRotations[child]);
                }
                if (restoration)
                {
                    Double3 rest = SubtractDouble3(basicPositions[child], basicPositions[parent]);
                    restorationVectors[child] = new Float3((float)rest.x, (float)rest.y, (float)rest.z);
                }
            }

            for (int sweep = 0; sweep < 3; sweep++)
            {
                float t = AddBinary32(MultiplyBinary32(MultiplyBinary32(sweep, 0.5f), 0.4f), 0.1f);
                float oneMinusT = SubtractBinary32(1.0f, t);
                for (int child = 1; child < count; child++)
                {
                    if ((attributes[child] & 2) == 0)
                        continue;
                    int parent = parentIndices[child];
                    Double3 p = nextPositions[child];
                    Double3 q = nextPositions[parent];
                    double childMobility = AngleMobility(frictions[child]);
                    double parentMobility = AngleMobility(frictions[parent]);
                    if (limit)
                    {
                    Double3 u = RotateQuaternionDouble(rotations[parent], ToDouble3(localPositions[child]));
                    Double3 d = SubtractDouble3(p, q);
                    double currentLength = LengthDouble3(d);
                    double blendLength = currentLength + 0.5 * (lengths[child] - currentLength);
                    Double3 direction = MultiplyDouble3(d, 1.0 / currentLength);
                    Double3 unconstrained = MultiplyDouble3(direction, blendLength);
                    float limitRadians = MultiplyBinary32(
                        SampleAngleCurve(depths[child], limitCurve), 0.01745329238474369f);
                    double phi = AcosBurstDouble(Math.Min(Math.Max(
                        DotDouble3(unconstrained, u) /
                        (LengthDouble3(unconstrained) * LengthDouble3(u)), -1.0), 1.0));
                    Double3 constrained = unconstrained;
                    if (phi > limitRadians)
                    {
                        Double3 vn = NormalizeDouble3(unconstrained);
                        Double3 un = NormalizeDouble3(u);
                        double psi = AcosBurstDouble(Math.Min(Math.Max(DotDouble3(vn, un), -1.0), 1.0));
                        double beta = phi + limitStiffness * (limitRadians - phi);
                        if (beta < psi)
                        {
                            double theta = psi * ((psi - beta) / psi);
                            constrained = RotateQuaternionDouble(
                                RotationBetweenDouble(vn, un, theta), unconstrained);
                        }
                    }
                    Double3 childTarget = AddDouble3(q, AddDouble3(
                        MultiplyDouble3(unconstrained, 0.4000000059604645),
                        MultiplyDouble3(constrained, 0.6000000238418579)));
                    Double3 childCorrection = MultiplyDouble3(
                        SubtractDouble3(childTarget, p), childMobility);
                    nextPositions[child] = AddDouble3(p, childCorrection);
                    velocityPositions[child] = AddDouble3(
                        velocityPositions[child], MultiplyDouble3(childCorrection, 0.8999999761581421));
                    if ((attributes[parent] & 2) != 0)
                    {
                        Double3 parentCorrection = MultiplyDouble3(
                            SubtractDouble3(unconstrained, constrained),
                            parentMobility * 0.4000000059604645);
                        nextPositions[parent] = AddDouble3(q, parentCorrection);
                        velocityPositions[parent] = AddDouble3(
                            velocityPositions[parent], MultiplyDouble3(parentCorrection, 0.8999999761581421));
                    }
                    Double3 updatedDirection = SubtractDouble3(nextPositions[child], nextPositions[parent]);
                    Float4 baseRotation = MultiplyQuaternionBinary32(rotations[parent], localRotations[child]);
                    Float4 deltaRotation = RotationBetweenDouble(u, updatedDirection, null);
                    rotations[child] = MultiplyQuaternionBinary32(deltaRotation, baseRotation);
                    }

                    if (restoration)
                    {
                    p = nextPositions[child];
                    q = nextPositions[parent];
                    Double3 d = SubtractDouble3(p, q);
                    Double3 rest = ToDouble3(restorationVectors[child]);
                    Double3 dn = NormalizeDouble3(d);
                    Double3 rn = NormalizeDouble3(rest);
                    double angle = AcosBurstDouble(Math.Min(Math.Max(DotDouble3(dn, rn), -1.0), 1.0));
                    float strength = Math.Min(Math.Max(
                        SampleAngleCurve(depths[child], restorationCurve), 0.0f), 1.0f);
                    strength = Math.Min(Math.Max(
                        MultiplyBinary32(strength, simulationPowerW), 0.0f), 1.0f);
                    float gravityMix = AddBinary32(
                        SubtractBinary32(1.0f, restorationGravityFalloff),
                        MultiplyBinary32(gravityDot, restorationGravityFalloff));
                    strength = MultiplyBinary32(strength, gravityMix);
                    Double3 rotated = RotateQuaternionDouble(
                        RotationBetweenDouble(dn, rn, angle * strength), d);
                    Double3 weightedCurrent = AddDouble3(q, MultiplyDouble3(d, t));
                    Double3 childTarget = AddDouble3(
                        weightedCurrent, MultiplyDouble3(rotated, oneMinusT));
                    Double3 childCorrection = MultiplyDouble3(
                        SubtractDouble3(childTarget, p), parentMobility);
                    nextPositions[child] = AddDouble3(p, childCorrection);
                    velocityPositions[child] = AddDouble3(
                        velocityPositions[child],
                        MultiplyDouble3(childCorrection, restorationVelocityAttenuation));
                    if ((attributes[parent] & 2) != 0)
                    {
                        Double3 parentDelta = SubtractDouble3(
                            SubtractDouble3(weightedCurrent, MultiplyDouble3(rotated, t)), q);
                        Double3 parentCorrection = MultiplyDouble3(parentDelta, childMobility);
                        nextPositions[parent] = AddDouble3(q, parentCorrection);
                        velocityPositions[parent] = AddDouble3(
                            velocityPositions[parent],
                            MultiplyDouble3(parentCorrection, restorationVelocityAttenuation));
                    }
                    }
                }
            }
        }

        public static void UpdateBasicPosture(
            int[] parentIndices,
            byte[] attributes,
            Float3[] localPositions,
            Float4[] localRotations,
            Float3[] basePositions,
            Float4[] baseRotations,
            Float3[] stepPositions,
            Float4[] stepRotations,
            Float3 initScale,
            float scaleRatio,
            Float3 negativeScaleDirection,
            Float4 negativeScaleQuaternion,
            float animationPoseRatio)
        {
            if (animationPoseRatio > 0.99f)
                return;
            for (int vertex = 0; vertex < parentIndices.Length; vertex++)
            {
                int parent = parentIndices[vertex];
                if ((attributes[vertex] & 2) != 0 && parent >= 0)
                {
                    Float3 local = localPositions[vertex];
                    Float3 scaled = new Float3(
                        MultiplyBinary32(MultiplyBinary32(MultiplyBinary32(local.x, negativeScaleDirection.x), initScale.x), scaleRatio),
                        MultiplyBinary32(MultiplyBinary32(MultiplyBinary32(local.y, negativeScaleDirection.y), initScale.y), scaleRatio),
                        MultiplyBinary32(MultiplyBinary32(MultiplyBinary32(local.z, negativeScaleDirection.z), initScale.z), scaleRatio));
                    Float3 rotated = RotateQuaternionBinary32(stepRotations[parent], scaled);
                    stepPositions[vertex] = new Float3(
                        AddBinary32(stepPositions[parent].x, rotated.x),
                        AddBinary32(stepPositions[parent].y, rotated.y),
                        AddBinary32(stepPositions[parent].z, rotated.z));
                    Float4 authored = localRotations[vertex];
                    authored = new Float4(
                        MultiplyBinary32(negativeScaleQuaternion.x, authored.x),
                        MultiplyBinary32(negativeScaleQuaternion.y, authored.y),
                        MultiplyBinary32(negativeScaleQuaternion.z, authored.z),
                        MultiplyBinary32(negativeScaleQuaternion.w, authored.w));
                    stepRotations[vertex] = MultiplyQuaternionBinary32(stepRotations[parent], authored);
                }
                else
                {
                    stepRotations[vertex] = NormalizeFloat4Binary32(stepRotations[vertex]);
                }
            }
            if (animationPoseRatio <= 1.0e-8f)
                return;
            for (int vertex = 0; vertex < parentIndices.Length; vertex++)
            {
                Float3 step = stepPositions[vertex];
                Float3 authored = basePositions[vertex];
                stepPositions[vertex] = new Float3(
                    AddBinary32(step.x, MultiplyBinary32(animationPoseRatio, SubtractBinary32(authored.x, step.x))),
                    AddBinary32(step.y, MultiplyBinary32(animationPoseRatio, SubtractBinary32(authored.y, step.y))),
                    AddBinary32(step.z, MultiplyBinary32(animationPoseRatio, SubtractBinary32(authored.z, step.z))));
                stepRotations[vertex] = SlerpQuaternionBinary32(
                    stepRotations[vertex], baseRotations[vertex], animationPoseRatio);
            }
        }

        /// <summary>
        /// Source transcription of Simulation Start's complete verified zero-wind
        /// domain. Wind state is intentionally absent from this API so callers
        /// cannot silently treat the unrecovered nonzero-wind branch as exact.
        /// </summary>
        public static void StartSimulationParticleZeroWind(
            float simulationPowerZ,
            float simulationDeltaTime,
            byte attribute,
            float depth,
            Double3 transformPosition,
            Float4 transformRotation,
            Double3 oldTransformPosition,
            Float4 oldTransformRotation,
            Double3 oldPosition,
            Float3 velocity,
            float frameInterpolation,
            float teamTime,
            int teamFlag,
            float gravityRatio,
            float scaleRatio,
            float velocityWeight,
            int forceMode,
            Float3 impactForce,
            float gravity,
            Float3 gravityDirection,
            float[] dampingCurve,
            int normalAxis,
            float inertiaDepth,
            Double3 centerOldWorldPosition,
            Float3 centerStepVector,
            Float4 centerStepRotation,
            Float3 centerInertiaVector,
            Float4 centerInertiaRotation,
            float springPower,
            float springLimitDistance,
            float springNormalLimitRatio,
            float springNoise,
            out Double3 basePosition,
            out Float4 baseRotation,
            out Double3 stepBasicPosition,
            out Float4 stepBasicRotation,
            out Double3 velocityPosition,
            out Double3 nextPosition)
        {
            if (dampingCurve == null || dampingCurve.Length != 16)
                throw new ArgumentException("Simulation Start damping curve must contain 16 samples.");

            float interpolation = frameInterpolation;
            basePosition = new Double3(
                oldTransformPosition.x + interpolation * (transformPosition.x - oldTransformPosition.x),
                oldTransformPosition.y + interpolation * (transformPosition.y - oldTransformPosition.y),
                oldTransformPosition.z + interpolation * (transformPosition.z - oldTransformPosition.z));
            baseRotation = NormalizeFloat4Binary32(SlerpQuaternionBinary32(
                oldTransformRotation, transformRotation, interpolation));
            stepBasicPosition = basePosition;
            stepBasicRotation = baseRotation;

            if ((attribute & 2) == 0 && (teamFlag & 0x2000) == 0)
            {
                velocityPosition = basePosition;
                nextPosition = basePosition;
                return;
            }

            float inertiaFactor = MultiplyBinary32(
                SubtractBinary32(1.0f, MultiplyBinary32(depth, depth)), inertiaDepth);
            Float3 translation = new Float3(
                AddBinary32(centerInertiaVector.x, MultiplyBinary32(
                    inertiaFactor, SubtractBinary32(centerStepVector.x, centerInertiaVector.x))),
                AddBinary32(centerInertiaVector.y, MultiplyBinary32(
                    inertiaFactor, SubtractBinary32(centerStepVector.y, centerInertiaVector.y))),
                AddBinary32(centerInertiaVector.z, MultiplyBinary32(
                    inertiaFactor, SubtractBinary32(centerStepVector.z, centerInertiaVector.z))));
            Float3 relative = new Float3(
                (float)(oldPosition.x - centerOldWorldPosition.x),
                (float)(oldPosition.y - centerOldWorldPosition.y),
                (float)(oldPosition.z - centerOldWorldPosition.z));
            Float4 inertiaRotation = SlerpQuaternionBinary32(
                centerInertiaRotation, centerStepRotation, inertiaFactor);
            Float3 rotatedRelative = RotateQuaternionBinary32(inertiaRotation, relative);
            velocityPosition = new Double3(
                centerOldWorldPosition.x + rotatedRelative.x + translation.x,
                centerOldWorldPosition.y + rotatedRelative.y + translation.y,
                centerOldWorldPosition.z + rotatedRelative.z + translation.z);
            Float3 inertiaVelocity = RotateQuaternionBinary32(inertiaRotation, velocity);
            inertiaVelocity = new Float3(
                MultiplyBinary32(inertiaVelocity.x, velocityWeight),
                MultiplyBinary32(inertiaVelocity.y, velocityWeight),
                MultiplyBinary32(inertiaVelocity.z, velocityWeight));

            float dampingSample = SampleAngleCurve(depth, dampingCurve);
            float damping = Math.Min(Math.Max(
                SubtractBinary32(1.0f, MultiplyBinary32(dampingSample, simulationPowerZ)),
                0.0f), 1.0f);
            Float3 damped = new Float3(
                MultiplyBinary32(inertiaVelocity.x, damping),
                MultiplyBinary32(inertiaVelocity.y, damping),
                MultiplyBinary32(inertiaVelocity.z, damping));
            float gravityScale = MultiplyBinary32(gravity, gravityRatio);
            Float3 acceleration = new Float3(
                MultiplyBinary32(gravityDirection.x, gravityScale),
                MultiplyBinary32(gravityDirection.y, gravityScale),
                MultiplyBinary32(gravityDirection.z, gravityScale));
            if (forceMode == 1 || forceMode == 2)
            {
                float oneMinusDepth = SubtractBinary32(1.0f, depth);
                float denominator = AddBinary32(
                    1.0f, MultiplyBinary32(5.0f, MultiplyBinary32(oneMinusDepth, oneMinusDepth)));
                acceleration = new Float3(
                    AddBinary32(acceleration.x, DivideBinary32(impactForce.x, denominator)),
                    AddBinary32(acceleration.y, DivideBinary32(impactForce.y, denominator)),
                    AddBinary32(acceleration.z, DivideBinary32(impactForce.z, denominator)));
            }
            else if (forceMode == 10 || forceMode == 11)
            {
                acceleration = new Float3(
                    AddBinary32(acceleration.x, impactForce.x),
                    AddBinary32(acceleration.y, impactForce.y),
                    AddBinary32(acceleration.z, impactForce.z));
            }

            float accelerationScale = MultiplyBinary32(simulationDeltaTime, scaleRatio);
            Float3 newVelocity = new Float3(
                AddBinary32(damped.x, MultiplyBinary32(acceleration.x, accelerationScale)),
                AddBinary32(damped.y, MultiplyBinary32(acceleration.y, accelerationScale)),
                AddBinary32(damped.z, MultiplyBinary32(acceleration.z, accelerationScale)));
            Float3 displacement = new Float3(
                MultiplyBinary32(newVelocity.x, simulationDeltaTime),
                MultiplyBinary32(newVelocity.y, simulationDeltaTime),
                MultiplyBinary32(newVelocity.z, simulationDeltaTime));
            Double3 predicted = new Double3(
                velocityPosition.x + displacement.x,
                velocityPosition.y + displacement.y,
                velocityPosition.z + displacement.z);
            nextPosition = predicted;

            if ((teamFlag & 0x2000) == 0 || (attribute & 1) == 0)
                return;

            double limit = MultiplyBinary32(scaleRatio, springLimitDistance);
            Double3 constrained = new Double3(
                predicted.x - basePosition.x,
                predicted.y - basePosition.y,
                predicted.z - basePosition.z);
            double constrainedLength = LengthDouble3(constrained);
            if (constrainedLength > limit)
                constrained = MultiplyDouble3(constrained, limit / constrainedLength);

            if (springNormalLimitRatio < 1.0f)
            {
                Double3 normal = SimulationStartNormalAxis(normalAxis);
                double parallel = constrained.x * normal.x;
                parallel += constrained.y * normal.y;
                parallel += constrained.z * normal.z;
                Double3 tangent = new Double3(
                    constrained.x - parallel * normal.x,
                    constrained.y - parallel * normal.y,
                    constrained.z - parallel * normal.z);
                double angle = AsinSimulationStartDouble(LengthDouble3(tangent) / limit);
                double threshold = limit * springNormalLimitRatio * SimulationStartCosBinary64(angle);
                if (Math.Abs(parallel) > threshold)
                {
                    double excess = Math.Abs(parallel) - threshold;
                    if (parallel < 0.0)
                        excess = -excess;
                    constrained = new Double3(
                        constrained.x - excess * normal.x,
                        constrained.y - excess * normal.y,
                        constrained.z - excess * normal.z);
                }
            }

            double phase = predicted.x;
            phase += predicted.y;
            phase += predicted.z;
            float phaseTime = AddBinary32(
                teamTime, MultiplyBinary32(49.61980056762695f, 0.0f));
            phase += 2.451200008392334 * phaseTime;
            double power = springPower;
            double noise = MultiplyBinary32(springNoise, 0.6000000238418579f);
            double springFactor = Math.Max(
                0.0, power + power * noise * SimulationStartSinBinary64(phase));
            double retained = 1.0 - springFactor;
            nextPosition = new Double3(
                basePosition.x + constrained.x * retained,
                basePosition.y + constrained.y * retained,
                basePosition.z + constrained.z * retained);
        }

        public static void SimulationStartSinCosBinary64(
            double value, out double sine, out double cosine)
        {
            sine = SimulationStartSinBinary64(value);
            cosine = SimulationStartCosBinary64(value);
        }

        public static void FinishSimulationParticle(
            bool active,
            float deltaTime,
            float scaleRatio,
            float velocityWeight,
            float particleSpeedLimit,
            float centrifugalAcceleration,
            float dynamicFriction,
            float staticFrictionParameter,
            float depth,
            Double3 centerPosition,
            float centerAngularVelocity,
            Float3 centerRotationAxis,
            ref Double3 nextPosition,
            Double3 previousPosition,
            ref Double3 velocityPosition,
            ref Float3 velocity,
            ref Float3 realVelocity,
            ref float friction,
            ref float staticFriction,
            Float3 collisionNormal)
        {
            double dt = deltaTime;
            Double3 corrected = nextPosition;
            if (!active)
            {
                velocity = new Float3(0.0f, 0.0f, 0.0f);
            }
            else
            {
                Double3 correctedVelocityPosition = velocityPosition;
                float normalSquared = DotFloat3Binary32(collisionNormal, collisionNormal);
                float threshold = MultiplyBinary32(scaleRatio, staticFrictionParameter);
                double accumulatedStaticFriction = staticFriction;
                if (normalSquared > 1.0e-8f && friction > 0.0f && threshold > 0.0f)
                {
                    Double3 delta = SubtractDouble3(nextPosition, previousPosition);
                    double normalDistance = DotFloatDouble3(collisionNormal, delta);
                    Double3 tangent = new Double3(
                        delta.x - collisionNormal.x * normalDistance,
                        delta.y - collisionNormal.y * normalDistance,
                        delta.z - collisionNormal.z * normalDistance);
                    double tangentSpeed = LengthDouble3(tangent) / dt;
                    if (threshold > tangentSpeed)
                        accumulatedStaticFriction += 0.03999999910593033;
                    else
                        accumulatedStaticFriction -= Math.Max(
                            (tangentSpeed - threshold) / 0.20000000298023224,
                            0.05000000074505806);
                    accumulatedStaticFriction = Math.Min(Math.Max(accumulatedStaticFriction, 0.0), 1.0);
                    Double3 correction = MultiplyDouble3(tangent, accumulatedStaticFriction);
                    corrected = SubtractDouble3(nextPosition, correction);
                    correctedVelocityPosition = SubtractDouble3(velocityPosition, correction);
                }
                else
                {
                    accumulatedStaticFriction = Math.Min(
                        Math.Max(accumulatedStaticFriction - 0.05000000074505806, 0.0), 1.0);
                }
                staticFriction = (float)accumulatedStaticFriction;

                Double3 velocity0 = MultiplyDouble3(
                    SubtractDouble3(corrected, correctedVelocityPosition), 1.0 / dt);
                double speed0Squared = DotDouble3(velocity0, velocity0);
                Float3 direction0 = speed0Squared > 1.0e-8
                    ? NormalizeDouble3ToFloatBinary32(velocity0)
                    : new Float3(0.0f, 0.0f, 0.0f);
                Double3 velocity1 = velocity0;
                if (friction > 1.0e-8f && normalSquared > 1.0e-8f &&
                    dynamicFriction > 0.0f && speed0Squared >= 1.0e-8)
                {
                    float hemisphere = AddBinary32(
                        MultiplyBinary32(DotFloat3Binary32(collisionNormal, direction0), 0.5f), 0.5f);
                    float directionalLoss = SubtractBinary32(
                        1.0f, MultiplyBinary32(hemisphere, hemisphere));
                    float strength = Math.Min(Math.Max(
                        MultiplyBinary32(dynamicFriction, friction), 0.0f), 1.0f);
                    float attenuation = MultiplyBinary32(strength, directionalLoss);
                    velocity1 = new Double3(
                        velocity0.x - velocity0.x * attenuation,
                        velocity0.y - velocity0.y * attenuation,
                        velocity0.z - velocity0.z * attenuation);
                }

                Double3 velocity2 = velocity1;
                if (particleSpeedLimit >= 0.0f)
                {
                    float scaledLimit = MultiplyBinary32(particleSpeedLimit, scaleRatio);
                    double speed = LengthDouble3(velocity1);
                    if (!(speed <= scaledLimit || speed <= 9.999999717180685e-10))
                        velocity2 = MultiplyDouble3(velocity1, scaledLimit / speed);
                }

                Double3 finalVelocity = velocity2;
                if (centerAngularVelocity > 1.0e-8f && centrifugalAcceleration > 1.0e-8f &&
                    speed0Squared >= 1.0e-8)
                {
                    Double3 radialInput = new Double3(
                        (float)(corrected.x - centerPosition.x),
                        (float)(corrected.y - centerPosition.y),
                        (float)(corrected.z - centerPosition.z));
                    double axial = DotFloatDouble3(centerRotationAxis, radialInput);
                    Double3 radial = new Double3(
                        radialInput.x - centerRotationAxis.x * axial,
                        radialInput.y - centerRotationAxis.y * axial,
                        radialInput.z - centerRotationAxis.z * axial);
                    double radialLength = LengthDouble3(radial);
                    if (radialLength > 1.0e-8)
                    {
                        Double3 radialDirection = MultiplyDouble3(radial, 1.0 / radialLength);
                        Double3 tangentCross = new Double3(
                            centerRotationAxis.y * radialDirection.z - centerRotationAxis.z * radialDirection.y,
                            centerRotationAxis.z * radialDirection.x - centerRotationAxis.x * radialDirection.z,
                            centerRotationAxis.x * radialDirection.y - centerRotationAxis.y * radialDirection.x);
                        Double3 tangent = MultiplyDouble3(tangentCross, 1.0 / LengthDouble3(tangentCross));
                        double alignment = Math.Min(Math.Max(
                            tangent.x * direction0.x + tangent.y * direction0.y + tangent.z * direction0.z,
                            0.0), 1.0);
                        float depthFactor = AddBinary32(SubtractBinary32(1.0f, depth), 1.0f);
                        float angularTerm = MultiplyBinary32(
                            MultiplyBinary32(centerAngularVelocity, depthFactor), centerAngularVelocity);
                        double magnitude = radialLength * angularTerm * alignment;
                        magnitude *= centrifugalAcceleration * 0.019999999552965164;
                        finalVelocity = new Double3(
                            velocity2.x + radialDirection.x * magnitude,
                            velocity2.y + radialDirection.y * magnitude,
                            velocity2.z + radialDirection.z * magnitude);
                    }
                }

                velocity = new Float3(
                    (float)(finalVelocity.x * velocityWeight),
                    (float)(finalVelocity.y * velocityWeight),
                    (float)(finalVelocity.z * velocityWeight));
                friction = MultiplyBinary32(friction, 0.6000000238418579f);
            }

            realVelocity = new Float3(
                (float)((corrected.x - previousPosition.x) / dt),
                (float)((corrected.y - previousPosition.y) / dt),
                (float)((corrected.z - previousPosition.z) / dt));
            nextPosition = corrected;
        }

        private static Double3 SimulationStartNormalAxis(int axis)
        {
            switch (axis)
            {
                case 0: return new Double3(1.0, 0.0, 0.0);
                case 1: return new Double3(0.0, 1.0, 0.0);
                case 2: return new Double3(0.0, 0.0, 1.0);
                case 3: return new Double3(-1.0, 0.0, 0.0);
                case 4: return new Double3(0.0, -1.0, 0.0);
                case 5: return new Double3(0.0, 0.0, -1.0);
                default: throw new ArgumentOutOfRangeException(nameof(axis));
            }
        }

        private static double AsinSimulationStartDouble(double value)
        {
            double absolute = Math.Abs(value);
            double y;
            double root;
            if (absolute < 0.5)
            {
                y = MultiplyBinary64(value, value);
                root = absolute;
            }
            else
            {
                y = MultiplyBinary64(SubtractBinary64(1.0, absolute), 0.5);
                root = Math.Sqrt(y);
            }
            double y2 = MultiplyBinary64(y, y);
            double t0 = AddBinary64(
                AddBinary64(0.006606077476277171,
                    MultiplyBinary64(0.019290454772679107, y)),
                MultiplyBinary64(y2, AddBinary64(
                    -0.015819182433299966,
                    MultiplyBinary64(0.031615876506539346, y))));
            double t1 = AddBinary64(
                AddBinary64(0.022371761819320483,
                    MultiplyBinary64(0.017359569912236146, y)),
                MultiplyBinary64(y2, AddBinary64(
                    0.013887151845016092,
                    MultiplyBinary64(0.012153605255773773, y))));
            double polynomial = AddBinary64(
                0.16666666666664975,
                MultiplyBinary64(0.07500000000378582, y));
            polynomial = AddBinary64(polynomial,
                MultiplyBinary64(y2, AddBinary64(
                    0.044642856813771024,
                    MultiplyBinary64(0.030381959280381322, y))));
            double y4 = MultiplyBinary64(y2, y2);
            polynomial = AddBinary64(polynomial, MultiplyBinary64(y4, t1));
            double y6 = MultiplyBinary64(y4, y2);
            double y8 = MultiplyBinary64(y6, y2);
            polynomial = AddBinary64(polynomial, MultiplyBinary64(y8, t0));
            double result = AddBinary64(
                root,
                MultiplyBinary64(MultiplyBinary64(root, y), polynomial));
            if (absolute >= 0.5)
            {
                result = value >= 0.0
                    ? SubtractBinary64(Math.PI * 0.5, MultiplyBinary64(2.0, result))
                    : AddBinary64(-Math.PI * 0.5, MultiplyBinary64(2.0, result));
            }
            return absolute < 0.5
                ? DoubleFromBits((DoubleBits(result) & 0x7fffffffffffffffUL) |
                    (DoubleBits(value) & 0x8000000000000000UL))
                : result;
        }

        private static double SimulationStartSinBinary64(double value)
        {
            ulong inputBits = DoubleBits(value);
            double absolute = DoubleFromBits(inputBits & 0x7fffffffffffffffUL);
            double reduced;
            if (absolute < 15.0)
            {
                double scaled = MultiplyBinary64(value, DoubleFromBits(0x3fd45f306dc9c883UL));
                int n = (int)AddBinary64(scaled, scaled < 0.0 ? -0.5 : 0.5);
                double nd = n;
                reduced = AddBinary64(
                    AddBinary64(value, MultiplyBinary64(nd, DoubleFromBits(0xc00921fb54442d18UL))),
                    MultiplyBinary64(nd, DoubleFromBits(0xbca1a62633145c07UL)));
                if ((n & 1) != 0)
                    reduced = XorDoubleSign(reduced);
            }
            else if (absolute < 100000000000000.0)
            {
                double highN = TruncateBinary64(MultiplyBinary64(
                    value, DoubleFromBits(0x3e545f306dc9c883UL)));
                double highScaled = MultiplyBinary64(highN, 16777216.0);
                double scaled = SubtractBinary64(
                    MultiplyBinary64(value, DoubleFromBits(0x3fd45f306dc9c883UL)), highScaled);
                int lowN = (int)AddBinary64(scaled, scaled < 0.0 ? -0.5 : 0.5);
                double low = lowN;
                reduced = SubtractBinary64(value,
                    MultiplyBinary64(highScaled, DoubleFromBits(0x400921fb50000000UL)));
                reduced = SubtractBinary64(reduced,
                    MultiplyBinary64(low, DoubleFromBits(0x400921fb50000000UL)));
                reduced = SubtractBinary64(reduced,
                    MultiplyBinary64(highScaled, DoubleFromBits(0x3e6110b460000000UL)));
                reduced = SubtractBinary64(reduced,
                    MultiplyBinary64(low, DoubleFromBits(0x3e6110b460000000UL)));
                reduced = SubtractBinary64(reduced,
                    MultiplyBinary64(highScaled, DoubleFromBits(0x3ca1a62630000000UL)));
                reduced = SubtractBinary64(reduced,
                    MultiplyBinary64(low, DoubleFromBits(0x3ca1a62630000000UL)));
                reduced = AddBinary64(reduced, MultiplyBinary64(
                    AddBinary64(highScaled, low), DoubleFromBits(0xbaf8a2e03707344aUL)));
                if ((lowN & 1) != 0)
                    reduced = XorDoubleSign(reduced);
            }
            else if ((inputBits & 0x7ff0000000000000UL) != 0x7ff0000000000000UL)
            {
                SimulationStartLargeReduce(inputBits, out int n, out double hi, out double lo);
                int positive = hi > 0.0 ? 1 : 0;
                if ((n & 1) != 0)
                {
                    ulong sign = DoubleBits(hi) & 0x8000000000000000UL;
                    double pio2 = DoubleFromBits(0xbff921fb54442d18UL ^ sign);
                    double pio2Low = DoubleFromBits(0xbc91a62633145c07UL ^ sign);
                    double summed = AddBinary64(hi, pio2);
                    double correction = AddBinary64(
                        AddBinary64(
                            SubtractBinary64(hi, SubtractBinary64(summed, pio2)),
                            SubtractBinary64(pio2, SubtractBinary64(summed, hi))),
                        AddBinary64(pio2Low, lo));
                    hi = summed;
                    lo = correction;
                }
                int selector = positive + 2 * (n & 3) + 1;
                reduced = AddBinary64(hi, lo);
                if (((selector >> 2) & 1) != 0)
                    reduced = XorDoubleSign(reduced);
            }
            else
            {
                return DoubleFromBits(0x7ff8000000000000UL);
            }
            return SimulationStartSinPolynomial(reduced, inputBits);
        }

        private static double SimulationStartCosBinary64(double value)
        {
            ulong inputBits = DoubleBits(value);
            double absolute = DoubleFromBits(inputBits & 0x7fffffffffffffffUL);
            double reduced;
            if (absolute < 15.0)
            {
                double scaled = AddBinary64(
                    MultiplyBinary64(value, DoubleFromBits(0x3fd45f306dc9c883UL)), -0.5);
                int n = (int)AddBinary64(scaled, scaled < 0.0 ? -0.5 : 0.5);
                int selector = 2 * n + 1;
                double nd = selector;
                reduced = AddBinary64(
                    AddBinary64(value, MultiplyBinary64(nd, DoubleFromBits(0xbff921fb54442d18UL))),
                    MultiplyBinary64(nd, DoubleFromBits(0xbc91a62633145c07UL)));
                if ((selector & 2) == 0)
                    reduced = XorDoubleSign(reduced);
            }
            else if (absolute < 100000000000000.0)
            {
                double highN = TruncateBinary64(AddBinary64(
                    MultiplyBinary64(value, DoubleFromBits(0x3e645f306dc9c883UL)),
                    DoubleFromBits(0xbe545f306dc9c883UL)));
                double scaled = AddBinary64(
                    MultiplyBinary64(value, DoubleFromBits(0x3fd45f306dc9c883UL)), -0.5);
                scaled = AddBinary64(scaled, MultiplyBinary64(highN, -8388608.0));
                int lowN = (int)AddBinary64(scaled, scaled < 0.0 ? -0.5 : 0.5);
                int selector = 2 * lowN + 1;
                double highScaled = MultiplyBinary64(highN, 16777216.0);
                double low = selector;
                reduced = SubtractBinary64(value,
                    MultiplyBinary64(highScaled, DoubleFromBits(0x3ff921fb50000000UL)));
                reduced = SubtractBinary64(reduced,
                    MultiplyBinary64(low, DoubleFromBits(0x3ff921fb50000000UL)));
                reduced = SubtractBinary64(reduced,
                    MultiplyBinary64(highScaled, DoubleFromBits(0x3e5110b460000000UL)));
                reduced = SubtractBinary64(reduced,
                    MultiplyBinary64(low, DoubleFromBits(0x3e5110b460000000UL)));
                reduced = SubtractBinary64(reduced,
                    MultiplyBinary64(highScaled, DoubleFromBits(0x3c91a62630000000UL)));
                reduced = SubtractBinary64(reduced,
                    MultiplyBinary64(low, DoubleFromBits(0x3c91a62630000000UL)));
                reduced = AddBinary64(reduced, MultiplyBinary64(
                    AddBinary64(highScaled, low), DoubleFromBits(0xbae8a2e03707344aUL)));
                if ((selector & 2) == 0)
                    reduced = XorDoubleSign(reduced);
            }
            else if ((inputBits & 0x7ff0000000000000UL) != 0x7ff0000000000000UL)
            {
                SimulationStartLargeReduce(inputBits, out int n, out double hi, out double lo);
                int positive = hi > 0.0 ? 1 : 0;
                if ((n & 1) == 0)
                {
                    ulong sign = hi <= 0.0 ? 0x8000000000000000UL : 0UL;
                    double pio2 = DoubleFromBits(0xbff921fb54442d18UL ^ sign);
                    double pio2Low = DoubleFromBits(0xbc91a62633145c07UL ^ sign);
                    double summed = AddBinary64(hi, pio2);
                    double correction = AddBinary64(
                        AddBinary64(
                            SubtractBinary64(hi, SubtractBinary64(summed, pio2)),
                            SubtractBinary64(pio2, SubtractBinary64(summed, hi))),
                        AddBinary64(pio2Low, lo));
                    hi = summed;
                    lo = correction;
                }
                int selector = positive + 2 * (n & 3) + 7;
                reduced = AddBinary64(hi, lo);
                if (((selector >> 1) & 2) == 0)
                    reduced = XorDoubleSign(reduced);
            }
            else
            {
                return DoubleFromBits(0x7ff8000000000000UL);
            }
            return SimulationStartSinPolynomial(reduced, 0UL);
        }

        private static double SimulationStartSinPolynomial(double reduced, ulong inputBits)
        {
            if (inputBits == 0x8000000000000000UL)
                return DoubleFromBits(inputBits);
            double z = MultiplyBinary64(reduced, reduced);
            double z2 = MultiplyBinary64(z, z);
            double z4 = MultiplyBinary64(z2, z2);
            double p0 = AddBinary64(
                MultiplyBinary64(z, DoubleFromBits(0xbc62622b22d526beUL)),
                DoubleFromBits(0x3ce94fa618796592UL));
            double p1 = AddBinary64(
                MultiplyBinary64(z, DoubleFromBits(0xbd6ae7ea531357bfUL)),
                DoubleFromBits(0x3de6124601c23966UL));
            double high = MultiplyBinary64(z4,
                AddBinary64(p1, MultiplyBinary64(z2, p0)));
            double p2 = AddBinary64(
                MultiplyBinary64(z, DoubleFromBits(0xbe5ae64567cb5786UL)),
                DoubleFromBits(0x3ec71de3a5568a50UL));
            double p3 = AddBinary64(
                MultiplyBinary64(z, DoubleFromBits(0xbf2a01a01a019fc7UL)),
                DoubleFromBits(0x3f8111111111110fUL));
            double low = AddBinary64(p3, MultiplyBinary64(z2, p2));
            double polynomial = AddBinary64(AddBinary64(low, high), 0.0);
            polynomial = AddBinary64(
                MultiplyBinary64(z, polynomial), DoubleFromBits(0xbfc5555555555555UL));
            return AddBinary64(reduced,
                MultiplyBinary64(z, MultiplyBinary64(reduced, polynomial)));
        }

        private static void SimulationStartLargeReduce(
            ulong inputBits, out int quadrant, out double radiansHigh, out double radiansLow)
        {
            ulong exponent = (inputBits >> 52) & 0x7ffUL;
            ulong shift = (exponent < 0x6bcUL ? 1UL : 0UL) << 58;
            ulong normalizedBits = unchecked(inputBits + 0xfc00000000000000UL + shift);
            double x0 = DoubleFromBits(normalizedBits);
            int index = exponent >= 0x436UL ? 4 * (int)exponent - 0x10d8 : 0;

            double tab0 = SimulationStartTrigTable[index];
            double xHigh = DoubleFromBits(normalizedBits & 0xfffffffff8000000UL);
            double xLow = SubtractBinary64(x0, xHigh);
            double tab0High = DoubleFromBits(DoubleBits(tab0) & 0xfffffffff8000000UL);
            double tab0Low = SubtractBinary64(tab0, tab0High);
            double product0 = MultiplyBinary64(tab0, x0);
            double error0 = SubtractBinary64(MultiplyBinary64(xHigh, tab0High), product0);
            error0 = AddBinary64(MultiplyBinary64(xLow, tab0High), error0);
            error0 = AddBinary64(MultiplyBinary64(tab0Low, xHigh), error0);
            error0 = AddBinary64(MultiplyBinary64(xLow, tab0Low), error0);

            double coarse0 = MultiplyBinary64(
                TruncateBinary64(MultiplyBinary64(product0, Math.Pow(2.0, -28.0))),
                Math.Pow(2.0, 28.0));
            double remainder0 = SubtractBinary64(product0, coarse0);
            int positive0 = product0 > 0.0 ? 1 : 0;
            int q0 = (((positive0 + (int)MultiplyBinary64(remainder0, 8.0) + 3) & 7) - 3) >> 1;
            double half0 = DoubleFromBits(
                (DoubleBits(product0) & 0x8000000000000000UL) | 0x3fe0000000000000UL);
            double rounded0 = MultiplyBinary64(
                TruncateBinary64(AddBinary64(MultiplyBinary64(4.0, remainder0), half0)), 0.25);
            double reduced0 = SubtractBinary64(remainder0, rounded0);
            if (Math.Abs(reduced0) > 0.25)
                reduced0 = SubtractBinary64(reduced0, half0);
            if (Math.Abs(reduced0) > 10000000000.0)
                reduced0 = DoubleFromBits(DoubleBits(reduced0) & 0x8000000000000000UL);
            bool exact0 = Math.Abs(product0) == 0.12499999999999999;
            if (exact0)
                reduced0 = product0;

            double savedError0 = error0;
            double sum0 = AddBinary64(error0, reduced0);
            double tab1 = SimulationStartTrigTable[index + 1];
            double tab1High = DoubleFromBits(DoubleBits(tab1) & 0xfffffffff8000000UL);
            double tab1Low = SubtractBinary64(tab1, tab1High);
            double product1 = MultiplyBinary64(tab1, x0);
            double sum1 = AddBinary64(product1, sum0);
            int positive1 = sum1 > 0.0 ? 1 : 0;
            double half1 = DoubleFromBits(
                (DoubleBits(sum1) & 0x8000000000000000UL) | 0x3fe0000000000000UL);
            double coarse1 = MultiplyBinary64(
                TruncateBinary64(MultiplyBinary64(sum1, Math.Pow(2.0, -28.0))),
                Math.Pow(2.0, 28.0));
            double remainder1 = SubtractBinary64(sum1, coarse1);
            double rounded1 = MultiplyBinary64(
                TruncateBinary64(AddBinary64(MultiplyBinary64(4.0, remainder1), half1)), 0.25);
            double reduced1 = SubtractBinary64(remainder1, rounded1);
            if (Math.Abs(reduced1) > 0.25)
                reduced1 = SubtractBinary64(reduced1, half1);
            int q1 = (((positive1 + (int)MultiplyBinary64(remainder1, 8.0) + 3) & 7) - 3) >> 1;
            if (Math.Abs(reduced1) > 10000000000.0)
                reduced1 = DoubleFromBits(DoubleBits(reduced1) & 0x8000000000000000UL);
            bool exact1 = Math.Abs(sum1) == 0.12499999999999999;
            if (exact1)
                reduced1 = sum1;
            quadrant = (exact0 ? 0 : q0) + (exact1 ? 0 : q1);

            double product1Error = SubtractBinary64(
                MultiplyBinary64(tab1High, xHigh), product1);
            product1Error = AddBinary64(MultiplyBinary64(tab1High, xLow), product1Error);
            product1Error = AddBinary64(MultiplyBinary64(tab1Low, xHigh), product1Error);
            product1Error = AddBinary64(MultiplyBinary64(tab1Low, xLow), product1Error);
            double sum1MinusSum0 = SubtractBinary64(sum1, sum0);
            double reduced0Tail = SubtractBinary64(reduced0, sum0);
            double recoveredSum0 = SubtractBinary64(sum1, sum1MinusSum0);
            reduced0Tail = AddBinary64(reduced0Tail, savedError0);
            reduced0Tail = AddBinary64(product1Error, reduced0Tail);
            double sum0Tail = SubtractBinary64(sum0, recoveredSum0);
            double product1Tail = SubtractBinary64(product1, sum1MinusSum0);
            sum0Tail = AddBinary64(product1Tail, sum0Tail);
            reduced0Tail = AddBinary64(reduced0Tail, sum0Tail);
            double combined = AddBinary64(reduced0Tail, reduced1);
            double combinedError = AddBinary64(
                SubtractBinary64(reduced1, combined), reduced0Tail);

            double tab2 = SimulationStartTrigTable[index + 2];
            double tab2High = DoubleFromBits(DoubleBits(tab2) & 0xfffffffff8000000UL);
            double tab2Low = SubtractBinary64(tab2, tab2High);
            double product2 = MultiplyBinary64(tab2, x0);
            double product2Error = SubtractBinary64(
                MultiplyBinary64(xHigh, tab2High), product2);
            product2Error = AddBinary64(MultiplyBinary64(tab2Low, xHigh), product2Error);
            product2Error = AddBinary64(MultiplyBinary64(xLow, tab2High), product2Error);
            product2Error = AddBinary64(MultiplyBinary64(xLow, tab2Low), product2Error);
            double tail = AddBinary64(
                AddBinary64(MultiplyBinary64(x0, SimulationStartTrigTable[index | 3]), product2Error),
                combinedError);
            double leading = AddBinary64(product2, combined);
            double recoveredCombined = SubtractBinary64(leading, combined);
            double leadingError = AddBinary64(
                SubtractBinary64(product2, recoveredCombined),
                SubtractBinary64(combined, SubtractBinary64(leading, recoveredCombined)));
            tail = AddBinary64(tail, leadingError);
            double reducedHigh = AddBinary64(tail, leading);
            double reducedLow = AddBinary64(tail, SubtractBinary64(leading, reducedHigh));

            if (Math.Abs(x0) < 0.7)
            {
                radiansHigh = x0;
                radiansLow = 0.0;
                return;
            }
            double splitHigh = DoubleFromBits(DoubleBits(reducedHigh) & 0xfffffffff8000000UL);
            double splitLow = SubtractBinary64(reducedHigh, splitHigh);
            double tau = DoubleFromBits(0x401921fb54442d18UL);
            double tauHigh = DoubleFromBits(0x401921fb50000000UL);
            double tauMiddle = DoubleFromBits(0x3e7110b460000000UL);
            double tauLow = DoubleFromBits(0x3cb1a62633145c07UL);
            radiansHigh = MultiplyBinary64(reducedHigh, tau);
            double radiansError = SubtractBinary64(
                MultiplyBinary64(splitHigh, tauHigh), radiansHigh);
            radiansError = AddBinary64(MultiplyBinary64(splitLow, tauHigh), radiansError);
            radiansError = AddBinary64(MultiplyBinary64(splitHigh, tauMiddle), radiansError);
            radiansError = AddBinary64(MultiplyBinary64(splitLow, tauMiddle), radiansError);
            radiansError = AddBinary64(MultiplyBinary64(reducedHigh, tauLow), radiansError);
            radiansLow = AddBinary64(MultiplyBinary64(reducedLow, tau), radiansError);
        }

        private static double[] BuildSimulationStartTrigTable()
        {
            byte[] compressed = Convert.FromBase64String(SimulationStartTrigTableZlibBase64);
            var tableBytes = new byte[3876 * sizeof(double)];
            using (var source = new MemoryStream(compressed, 2, compressed.Length - 6, false))
            using (var inflater = new DeflateStream(source, CompressionMode.Decompress))
            {
                int offset = 0;
                while (offset < tableBytes.Length)
                {
                    int read = inflater.Read(tableBytes, offset, tableBytes.Length - offset);
                    if (read == 0)
                        throw new InvalidDataException("Simulation Start trig table ended early.");
                    offset += read;
                }
                if (inflater.ReadByte() != -1)
                    throw new InvalidDataException("Simulation Start trig table has trailing data.");
            }
            byte[] digest;
            using (SHA256 sha = SHA256.Create())
                digest = sha.ComputeHash(tableBytes);
            string hash = BitConverter.ToString(digest).Replace("-", "").ToLowerInvariant();
            if (!string.Equals(
                hash, "f76922848d66989df9746d647c9a012a90ff827eb83ca3c30c7c6c647271c1dc",
                StringComparison.Ordinal))
                throw new InvalidDataException("Simulation Start trig table SHA-256 differs.");
            var table = new double[3876];
            Buffer.BlockCopy(tableBytes, 0, table, 0, tableBytes.Length);
            return table;
        }

        private static double XorDoubleSign(double value)
        {
            return DoubleFromBits(DoubleBits(value) ^ 0x8000000000000000UL);
        }

        private static double TruncateBinary64(double value)
        {
            return (double)(long)value;
        }

        private static ulong DoubleBits(double value)
        {
            return BitConverter.ToUInt64(BitConverter.GetBytes(value), 0);
        }

        private static double DoubleFromBits(ulong bits)
        {
            return BitConverter.ToDouble(BitConverter.GetBytes(bits), 0);
        }

        private static float SampleAngleCurve(float depth, float[] values)
        {
            float clamped = Math.Min(Math.Max(depth, 0.0f), 1.0f);
            float scaled = MultiplyBinary32(clamped, 15.0f);
            int index = (int)scaled;
            const float step = 0.06666667014360428f;
            float fraction = DivideBinary32(
                SubtractBinary32(depth, MultiplyBinary32(index, step)), step);
            int first = Math.Min(Math.Max(index, 0), 15);
            int second = Math.Min(Math.Max(index + 1, 0), 15);
            return AddBinary32(
                values[first],
                MultiplyBinary32(fraction, SubtractBinary32(values[second], values[first])));
        }

        private static float AngleMobility(float friction)
        {
            return DivideBinary32(1.0f, AddBinary32(1.0f, MultiplyBinary32(3.0f, friction)));
        }

        private static double AcosBurstDouble(double value)
        {
            double x = Math.Min(Math.Max(value, -1.0), 1.0);
            double absolute = Math.Abs(x);
            double asin;
            if (absolute < 0.5)
            {
                asin = AsinBurstPolynomialDouble(absolute, absolute * absolute);
            }
            else
            {
                double y = (1.0 - absolute) * 0.5;
                asin = Math.PI * 0.5 - 2.0 * AsinBurstPolynomialDouble(Math.Sqrt(y), y);
            }
            if (x < 0.0)
                asin = -asin;
            return Math.PI * 0.5 - asin;
        }

        private static double AsinBurstPolynomialDouble(double s, double y)
        {
            const double a0 = 0.031615876506539346;
            const double a1 = 0.012153605255773773;
            const double a2 = 0.019290454772679107;
            const double a3 = 0.017359569912236146;
            const double b0 = -0.015819182433299966;
            const double b1 = 0.013887151845016092;
            const double b2 = 0.006606077476277171;
            const double b3 = 0.022371761819320483;
            const double c0 = 0.07500000000378582;
            const double c1 = 0.16666666666664975;
            const double d0 = 0.030381959280381322;
            const double d1 = 0.044642856813771024;
            double y2 = y * y;
            double t0 = b2 + a2 * y + y2 * (b0 + a0 * y);
            double t1 = b3 + a3 * y + y2 * (b1 + a1 * y);
            double p = c1 + c0 * y + y2 * (d1 + d0 * y) +
                y2 * y2 * t1 + Math.Pow(y2, 4.0) * t0;
            return s + s * y * p;
        }

        private static Float4 RotationBetweenDouble(
            Double3 source, Double3 target, double? requestedAngle)
        {
            Double3 sourceNormal = NormalizeDouble3(source);
            Double3 targetNormal = NormalizeDouble3(target);
            double cosine = Math.Min(Math.Max(DotDouble3(sourceNormal, targetNormal), -1.0), 1.0);
            double angle = requestedAngle ?? AcosBurstDouble(cosine);
            if (Math.Abs(1.0 - cosine) < 9.999999974752427e-7)
                return new Float4(0.0f, 0.0f, 0.0f, 1.0f);
            Double3 axis;
            if (Math.Abs(1.0 + cosine) < 9.999999974752427e-7)
            {
                Double3 helper = Math.Abs(sourceNormal.x) > Math.Abs(sourceNormal.y)
                    ? new Double3(1.0, 1.0, 1.0)
                    : new Double3(1.0, 0.0, 0.0);
                axis = NormalizeDouble3(CrossDouble3(sourceNormal, helper));
                if (!requestedAngle.HasValue)
                    angle = 3.1415927410125732;
            }
            else
            {
                axis = NormalizeDouble3(CrossDouble3(sourceNormal, targetNormal));
            }
            return AxisAngleBinary32(axis, angle);
        }

        private static Float4 AxisAngleBinary32(Double3 axis, double angle)
        {
            float x = (float)axis.x;
            float y = (float)axis.y;
            float z = (float)axis.z;
            float half = MultiplyBinary32((float)angle, 0.5f);
            FloatSinCosBinary32(half, out float sine, out float cosine);
            return new Float4(
                MultiplyBinary32(x, sine),
                MultiplyBinary32(y, sine),
                MultiplyBinary32(z, sine),
                cosine);
        }

        private static Float4 InverseQuaternionBinary32(Float4 value)
        {
            return new Float4(-value.x, -value.y, -value.z, value.w);
        }

        private static Double3 RotateQuaternionDouble(Float4 q, Double3 value)
        {
            Double3 xyz = new Double3(q.x, q.y, q.z);
            Double3 t = MultiplyDouble3(CrossDouble3(xyz, value), 2.0);
            return AddDouble3(value, AddDouble3(MultiplyDouble3(t, q.w), CrossDouble3(xyz, t)));
        }

        private static Double3 CrossDouble3(Double3 a, Double3 b)
        {
            return new Double3(
                a.y * b.z - a.z * b.y,
                a.z * b.x - a.x * b.z,
                a.x * b.y - a.y * b.x);
        }

        private static Double3 NormalizeDouble3(Double3 value)
        {
            return MultiplyDouble3(value, 1.0 / LengthDouble3(value));
        }

        private static Double3 AddDouble3(Double3 a, Double3 b)
        {
            return new Double3(a.x + b.x, a.y + b.y, a.z + b.z);
        }

        private static Double3 ToDouble3(Float3 value)
        {
            return new Double3(value.x, value.y, value.z);
        }

        public static void FloatSinCosBinary32(float value, out float sine, out float cosine)
        {
            uint inputBits = FloatBits(value);
            float absolute = FloatFromBits(inputBits & 0x7fffffffu);
            int quadrant;
            float reduced;
            if (absolute < 125.0f)
            {
                float scaled = MultiplyBinary32(value, FloatFromBits(0x3f22f983u));
                quadrant = (int)AddBinary32(scaled, scaled < 0.0f ? -0.5f : 0.5f);
                float n = quadrant;
                reduced = AddBinary32(
                    AddBinary32(
                        AddBinary32(value, MultiplyBinary32(n, FloatFromBits(0xbfc90e00u))),
                        MultiplyBinary32(n, FloatFromBits(0xb86d5000u))),
                    MultiplyBinary32(n, FloatFromBits(0xb0885a31u)));
            }
            else if (absolute < 39000.0f)
            {
                float scaled = MultiplyBinary32(value, FloatFromBits(0x3f22f983u));
                quadrant = (int)AddBinary32(scaled, scaled < 0.0f ? -0.5f : 0.5f);
                float n = quadrant;
                reduced = AddBinary32(
                    AddBinary32(
                        AddBinary32(
                            AddBinary32(value, MultiplyBinary32(n, FloatFromBits(0xbfc90000u))),
                            MultiplyBinary32(n, FloatFromBits(0xb9fd8000u))),
                        MultiplyBinary32(n, FloatFromBits(0xb4a88000u))),
                    MultiplyBinary32(n, FloatFromBits(0xae85a309u)));
            }
            else if ((inputBits & 0x7f800000u) != 0x7f800000u)
            {
                FloatSinCosLargeReduce(inputBits, out quadrant, out float hi, out float lo);
                reduced = AddBinary32(hi, lo);
            }
            else
            {
                quadrant = 0;
                reduced = FloatFromBits(0x7fc00000u);
            }

            float square = MultiplyBinary32(reduced, reduced);
            sine = FloatFromBits(0x80000000u);
            if (inputBits != 0x80000000u)
            {
                float polynomial = AddBinary32(
                    MultiplyBinary32(square, FloatFromBits(0xb94ca65bu)),
                    FloatFromBits(0x3c08839au));
                polynomial = AddBinary32(
                    MultiplyBinary32(square, polynomial), FloatFromBits(0xbe2aaaa2u));
                sine = AddBinary32(
                    reduced, MultiplyBinary32(reduced, MultiplyBinary32(square, polynomial)));
            }
            float cosinePolynomial = AddBinary32(
                MultiplyBinary32(square, FloatFromBits(0xb491ed89u)), FloatFromBits(0x37d0078bu));
            cosinePolynomial = AddBinary32(
                MultiplyBinary32(square, cosinePolynomial), FloatFromBits(0xbab60b58u));
            cosinePolynomial = AddBinary32(
                MultiplyBinary32(square, cosinePolynomial), FloatFromBits(0x3d2aaaaau));
            cosinePolynomial = AddBinary32(MultiplyBinary32(square, cosinePolynomial), -0.5f);
            cosine = AddBinary32(MultiplyBinary32(square, cosinePolynomial), 1.0f);

            float outSine;
            float outCosine;
            if ((quadrant & 1) != 0)
            {
                outCosine = sine;
                outSine = (quadrant & 2) != 0 ? XorFloatSign(cosine) : cosine;
            }
            else
            {
                outCosine = cosine;
                outSine = (quadrant & 2) != 0 ? XorFloatSign(sine) : sine;
            }
            if (((quadrant + 1) & 2) != 0)
                outCosine = XorFloatSign(outCosine);
            sine = outSine;
            cosine = outCosine;
        }

        private static void FloatSinCosLargeReduce(
            uint inputBits, out int quadrant, out float reducedHigh, out float reducedLow)
        {
            int exponent = (int)((inputBits >> 23) & 0xffu);
            uint shift = (uint)(exponent < 0xda ? 1 : 0) << 29;
            uint normalizedBits = unchecked(shift + inputBits - 0x20000000u);
            float x0 = FloatFromBits(normalizedBits);
            int tableIndex = exponent >= 0x98 ? 4 * exponent - 0x260 : 0;

            float tab0 = FloatSinCosReducerTable[tableIndex];
            float xhi = FloatFromBits(normalizedBits & 0xfffff000u);
            float xlo = SubtractBinary32(x0, xhi);
            float tab0hi = FloatFromBits(FloatBits(tab0) & 0xfffff000u);
            float tab0lo = SubtractBinary32(tab0, tab0hi);
            float product0 = MultiplyBinary32(tab0, x0);
            float error0 = SubtractBinary32(MultiplyBinary32(xhi, tab0hi), product0);
            error0 = AddBinary32(MultiplyBinary32(xlo, tab0hi), error0);
            error0 = AddBinary32(MultiplyBinary32(tab0lo, xhi), error0);
            error0 = AddBinary32(MultiplyBinary32(xlo, tab0lo), error0);

            float coarse = MultiplyBinary32(TruncateBinary32(MultiplyBinary32(0.0009765625f, product0)), 1024.0f);
            float remainder0 = SubtractBinary32(product0, coarse);
            int positive0 = product0 > 0.0f ? 1 : 0;
            int q0 = (((positive0 + (int)MultiplyBinary32(remainder0, 8.0f) + 3) & 7) - 3) >> 1;
            float half0 = FloatFromBits((FloatBits(product0) & 0x80000000u) | 0x3f000000u);
            float rounded0 = MultiplyBinary32(
                TruncateBinary32(AddBinary32(MultiplyBinary32(4.0f, remainder0), half0)), 0.25f);
            float reduced0 = SubtractBinary32(remainder0, rounded0);
            if (AbsoluteBinary32(reduced0) > 0.125f)
                reduced0 = SubtractBinary32(reduced0, half0);
            if (AbsoluteBinary32(reduced0) > 10000000000.0f)
                reduced0 = FloatFromBits(FloatBits(reduced0) & 0x80000000u);
            bool exact0 = AbsoluteBinary32(product0) == FloatFromBits(0x3dffffffu);
            if (exact0)
                reduced0 = product0;

            float savedError0 = error0;
            float sum0 = AddBinary32(error0, reduced0);
            float tab1 = FloatSinCosReducerTable[tableIndex + 1];
            float product1 = MultiplyBinary32(tab1, x0);
            float sum1 = AddBinary32(product1, sum0);
            float coarse1 = MultiplyBinary32(TruncateBinary32(MultiplyBinary32(0.0009765625f, sum1)), 1024.0f);
            float remainder1 = SubtractBinary32(sum1, coarse1);
            int carriedQ0 = exact0 ? 0 : q0;
            float tab1hi = FloatFromBits(FloatBits(tab1) & 0xfffff000u);
            int positive1 = sum1 > 0.0f ? 1 : 0;
            float half1 = FloatFromBits((FloatBits(sum1) & 0x80000000u) | 0x3f000000u);
            float rounded1 = MultiplyBinary32(
                TruncateBinary32(AddBinary32(MultiplyBinary32(4.0f, remainder1), half1)), 0.25f);
            float reduced1 = SubtractBinary32(remainder1, rounded1);
            if (AbsoluteBinary32(reduced1) > 0.125f)
                reduced1 = SubtractBinary32(reduced1, half1);
            int q1 = (((positive1 + (int)MultiplyBinary32(remainder1, 8.0f) + 3) & 7) - 3) >> 1;
            bool exact1 = AbsoluteBinary32(sum1) == FloatFromBits(0x3dffffffu);
            if (AbsoluteBinary32(reduced1) > 10000000000.0f)
                reduced1 = FloatFromBits(FloatBits(reduced1) & 0x80000000u);
            if (exact1)
                reduced1 = sum1;
            quadrant = carriedQ0 + (exact1 ? 0 : q1);

            if (AbsoluteBinary32(FloatFromBits(normalizedBits & 0x7fffffffu)) < FloatFromBits(0x3f333333u))
            {
                reducedHigh = x0;
                reducedLow = 0.0f;
                return;
            }

            float productHi = MultiplyBinary32(xhi, tab1hi);
            float tab1lo = SubtractBinary32(tab1, tab1hi);
            float productError = SubtractBinary32(productHi, product1);
            productError = AddBinary32(MultiplyBinary32(xlo, tab1hi), productError);
            productError = AddBinary32(MultiplyBinary32(tab1lo, xhi), productError);
            float sum1Tail = SubtractBinary32(sum1, sum0);
            float reduced0Tail = SubtractBinary32(reduced0, sum0);
            productError = AddBinary32(MultiplyBinary32(tab1lo, xlo), productError);
            float recoveredProduct1 = SubtractBinary32(sum1, sum1Tail);
            reduced0Tail = AddBinary32(reduced0Tail, savedError0);
            reduced0Tail = AddBinary32(productError, reduced0Tail);
            float sum0Tail = SubtractBinary32(sum0, recoveredProduct1);
            float product1Tail = SubtractBinary32(product1, sum1Tail);
            sum0Tail = AddBinary32(product1Tail, sum0Tail);
            reduced0Tail = AddBinary32(reduced0Tail, sum0Tail);
            float combined = AddBinary32(reduced0Tail, reduced1);
            float combineError = SubtractBinary32(reduced1, combined);
            combineError = AddBinary32(reduced0Tail, combineError);

            float tab2 = FloatSinCosReducerTable[tableIndex + 2];
            float tab2hi = FloatFromBits(FloatBits(tab2) & 0xfffff000u);
            float tab2lo = SubtractBinary32(tab2, tab2hi);
            float product2 = MultiplyBinary32(tab2, x0);
            float product2Error = SubtractBinary32(MultiplyBinary32(xhi, tab2hi), product2);
            product2Error = AddBinary32(MultiplyBinary32(tab2lo, xhi), product2Error);
            product2Error = AddBinary32(MultiplyBinary32(xlo, tab2hi), product2Error);
            product2Error = AddBinary32(MultiplyBinary32(xlo, tab2lo), product2Error);
            float product3 = MultiplyBinary32(x0, FloatSinCosReducerTable[tableIndex | 3]);
            float tail = AddBinary32(AddBinary32(product3, product2Error), combineError);
            float leading = AddBinary32(product2, combined);
            float recoveredCombined = SubtractBinary32(leading, combined);
            float leadingError = SubtractBinary32(product2, recoveredCombined);
            leadingError = AddBinary32(
                leadingError, SubtractBinary32(combined, SubtractBinary32(leading, recoveredCombined)));
            tail = AddBinary32(tail, leadingError);
            reducedHigh = AddBinary32(leading, tail);
            reducedLow = AddBinary32(tail, SubtractBinary32(leading, reducedHigh));

            float splitHigh = FloatFromBits(FloatBits(reducedHigh) & 0xfffff000u);
            float splitLow = SubtractBinary32(reducedHigh, splitHigh);
            float radiansHigh = MultiplyBinary32(reducedHigh, FloatFromBits(0x40c90fdbu));
            float radiansError = SubtractBinary32(
                MultiplyBinary32(splitHigh, FloatFromBits(0x40c90000u)), radiansHigh);
            radiansError = AddBinary32(MultiplyBinary32(splitLow, FloatFromBits(0x40c90000u)), radiansError);
            radiansError = AddBinary32(MultiplyBinary32(splitHigh, FloatFromBits(0x3afdb000u)), radiansError);
            radiansError = AddBinary32(MultiplyBinary32(splitLow, FloatFromBits(0x3afdb000u)), radiansError);
            radiansError = AddBinary32(MultiplyBinary32(reducedHigh, FloatFromBits(0xb43bbd2eu)), radiansError);
            reducedLow = AddBinary32(MultiplyBinary32(reducedLow, FloatFromBits(0x40c90fdbu)), radiansError);
            reducedHigh = radiansHigh;
        }

        private static float[] BuildFloatSinCosReducerTable()
        {
            var table = new float[416];
            for (int index = 0; index < table.Length; index++)
            {
                int offset = index * 8;
                uint bits = uint.Parse(
                    FloatSinCosReducerTableHex.Substring(offset + 6, 2) +
                    FloatSinCosReducerTableHex.Substring(offset + 4, 2) +
                    FloatSinCosReducerTableHex.Substring(offset + 2, 2) +
                    FloatSinCosReducerTableHex.Substring(offset, 2),
                    System.Globalization.NumberStyles.HexNumber,
                    System.Globalization.CultureInfo.InvariantCulture);
                table[index] = FloatFromBits(bits);
            }
            return table;
        }

        private static float AbsoluteBinary32(float value)
        {
            return FloatFromBits(FloatBits(value) & 0x7fffffffu);
        }

        private static float XorFloatSign(float value)
        {
            return FloatFromBits(FloatBits(value) ^ 0x80000000u);
        }

        private static float TruncateBinary32(float value)
        {
            return (float)(int)value;
        }

        private static uint FloatBits(float value)
        {
            return BitConverter.ToUInt32(BitConverter.GetBytes(value), 0);
        }

        private static float FloatFromBits(uint bits)
        {
            return BitConverter.ToSingle(BitConverter.GetBytes(bits), 0);
        }

        private static Float4 SlerpQuaternionBinary32(Float4 a, Float4 b, float t)
        {
            float dot = DotFloat4Binary32(a, b);
            if (dot < 0.0f)
            {
                b = new Float4(-b.x, -b.y, -b.z, -b.w);
                dot = -dot;
            }
            if (dot >= 0.9995f)
            {
                return NormalizeFloat4Binary32(new Float4(
                    AddBinary32(a.x, MultiplyBinary32(t, SubtractBinary32(b.x, a.x))),
                    AddBinary32(a.y, MultiplyBinary32(t, SubtractBinary32(b.y, a.y))),
                    AddBinary32(a.z, MultiplyBinary32(t, SubtractBinary32(b.z, a.z))),
                    AddBinary32(a.w, MultiplyBinary32(t, SubtractBinary32(b.w, a.w)))));
            }
            float theta = AcosBurstBinary32(dot);
            float inverseSin = DivideBinary32(
                1.0f,
                SqrtBinary32(SubtractBinary32(1.0f, MultiplyBinary32(dot, dot))));
            float weightA = MultiplyBinary32(
                inverseSin,
                SinBurstBoundedBinary32(MultiplyBinary32(SubtractBinary32(1.0f, t), theta)));
            float weightB = MultiplyBinary32(
                inverseSin,
                SinBurstBoundedBinary32(MultiplyBinary32(t, theta)));
            return new Float4(
                AddBinary32(MultiplyBinary32(a.x, weightA), MultiplyBinary32(b.x, weightB)),
                AddBinary32(MultiplyBinary32(a.y, weightA), MultiplyBinary32(b.y, weightB)),
                AddBinary32(MultiplyBinary32(a.z, weightA), MultiplyBinary32(b.z, weightB)),
                AddBinary32(MultiplyBinary32(a.w, weightA), MultiplyBinary32(b.w, weightB)));
        }

        private static Float3 LerpFloat3Binary32(Float3 a, Float3 b, float t)
        {
            return new Float3(
                AddBinary32(a.x, MultiplyBinary32(t, SubtractBinary32(b.x, a.x))),
                AddBinary32(a.y, MultiplyBinary32(t, SubtractBinary32(b.y, a.y))),
                AddBinary32(a.z, MultiplyBinary32(t, SubtractBinary32(b.z, a.z))));
        }

        private static Float3 AddFloat3Binary32(Float3 a, Float3 b)
        {
            return new Float3(
                AddBinary32(a.x, b.x), AddBinary32(a.y, b.y), AddBinary32(a.z, b.z));
        }

        private static Float3 SubtractFloat3Binary32(Float3 a, Float3 b)
        {
            return new Float3(
                SubtractBinary32(a.x, b.x),
                SubtractBinary32(a.y, b.y),
                SubtractBinary32(a.z, b.z));
        }

        private static Float3 RotateQuaternionColliderStartBinary32(Float4 q, Float3 value)
        {
            float crossX = SubtractBinary32(
                MultiplyBinary32(q.y, value.z), MultiplyBinary32(q.z, value.y));
            float crossY = SubtractBinary32(
                MultiplyBinary32(q.z, value.x), MultiplyBinary32(q.x, value.z));
            float crossZ = SubtractBinary32(
                MultiplyBinary32(q.x, value.y), MultiplyBinary32(q.y, value.x));
            float tx = AddBinary32(crossX, crossX);
            float ty = AddBinary32(crossY, crossY);
            float tz = AddBinary32(crossZ, crossZ);
            float secondX = SubtractBinary32(MultiplyBinary32(q.y, tz), MultiplyBinary32(q.z, ty));
            float secondY = SubtractBinary32(MultiplyBinary32(q.z, tx), MultiplyBinary32(q.x, tz));
            float secondZ = SubtractBinary32(MultiplyBinary32(q.x, ty), MultiplyBinary32(q.y, tx));
            return new Float3(
                AddBinary32(AddBinary32(value.x, MultiplyBinary32(q.w, tx)), secondX),
                AddBinary32(AddBinary32(value.y, MultiplyBinary32(q.w, ty)), secondY),
                AddBinary32(AddBinary32(value.z, MultiplyBinary32(q.w, tz)), secondZ));
        }

        private static float Min4Binary32(float a, float b, float c, float d)
        {
            return Math.Min(Math.Min(Math.Min(a, b), c), d);
        }

        private static float Max4Binary32(float a, float b, float c, float d)
        {
            return Math.Max(Math.Max(Math.Max(a, b), c), d);
        }

        private static float SinBurstBoundedBinary32(float value)
        {
            if (float.IsNaN(value) || float.IsInfinity(value) || Math.Abs(value) >= 125.0f)
                throw new ArgumentOutOfRangeException(nameof(value), "Pinned BasicPosture sine fast path exceeded.");
            float quotient = MultiplyBinary32(value, 0.31830987334251404f);
            int rounded = (int)AddBinary32(quotient, quotient < 0.0f ? -0.5f : 0.5f);
            float roundedFloat = rounded;
            float reduced = AddBinary32(value, MultiplyBinary32(roundedFloat, -3.1414794921875f));
            reduced = AddBinary32(reduced, MultiplyBinary32(roundedFloat, -0.0001131594181060791f));
            reduced = AddBinary32(reduced, MultiplyBinary32(roundedFloat, -1.984187258941006e-09f));
            float signed = (rounded & 1) != 0 ? -reduced : reduced;
            float square = MultiplyBinary32(reduced, reduced);
            float polynomial = AddBinary32(
                MultiplyBinary32(square, 2.6083159809786594e-06f), -0.00019810690719168633f);
            polynomial = AddBinary32(MultiplyBinary32(square, polynomial), 0.00833307858556509f);
            polynomial = AddBinary32(MultiplyBinary32(square, polynomial), -0.16666659712791443f);
            return AddBinary32(signed, MultiplyBinary32(square, MultiplyBinary32(signed, polynomial)));
        }

        private static float AcosBurstBinary32(float value)
        {
            float absolute = Math.Abs(value);
            float polynomialInput;
            float root;
            if (absolute < 0.5f)
            {
                polynomialInput = MultiplyBinary32(value, value);
                root = absolute;
            }
            else
            {
                polynomialInput = MultiplyBinary32(0.5f, SubtractBinary32(1.0f, absolute));
                root = absolute == 1.0f ? 0.0f : SqrtBinary32(polynomialInput);
            }
            float polynomial = AddBinary32(MultiplyBinary32(polynomialInput, 0.04197454825043678f), 0.024240460246801376f);
            polynomial = AddBinary32(MultiplyBinary32(polynomialInput, polynomial), 0.04547423869371414f);
            polynomial = AddBinary32(MultiplyBinary32(polynomialInput, polynomial), 0.07495029270648956f);
            polynomial = AddBinary32(MultiplyBinary32(polynomialInput, polynomial), 0.16666772961616516f);
            float signedRoot = value < 0.0f ? -root : root;
            float asin = AddBinary32(signedRoot, MultiplyBinary32(polynomialInput, MultiplyBinary32(signedRoot, polynomial)));
            if (absolute < 0.5f)
                return SubtractBinary32(1.5707963705062866f, asin);
            float doubled = AddBinary32(root, MultiplyBinary32(polynomialInput, MultiplyBinary32(root, polynomial)));
            doubled = AddBinary32(doubled, doubled);
            return value < 0.0f ? SubtractBinary32(3.1415927410125732f, doubled) : doubled;
        }

        private static float DotFloat4Binary32(Float4 a, Float4 b)
        {
            return AddBinary32(
                AddBinary32(MultiplyBinary32(a.x, b.x), MultiplyBinary32(a.y, b.y)),
                AddBinary32(MultiplyBinary32(a.z, b.z), MultiplyBinary32(a.w, b.w)));
        }

        private static Float4 NormalizeFloat4Binary32(Float4 value)
        {
            float inverse = DivideBinary32(1.0f, SqrtBinary32(DotFloat4Binary32(value, value)));
            return new Float4(
                MultiplyBinary32(value.x, inverse), MultiplyBinary32(value.y, inverse),
                MultiplyBinary32(value.z, inverse), MultiplyBinary32(value.w, inverse));
        }

        private static Float4 MultiplyQuaternionBinary32(Float4 a, Float4 b)
        {
            return new Float4(
                AddBinary32(AddBinary32(MultiplyBinary32(a.w, b.x), MultiplyBinary32(a.x, b.w)), SubtractBinary32(MultiplyBinary32(a.y, b.z), MultiplyBinary32(a.z, b.y))),
                AddBinary32(AddBinary32(MultiplyBinary32(a.w, b.y), MultiplyBinary32(a.y, b.w)), SubtractBinary32(MultiplyBinary32(a.z, b.x), MultiplyBinary32(a.x, b.z))),
                AddBinary32(AddBinary32(MultiplyBinary32(a.w, b.z), MultiplyBinary32(a.z, b.w)), SubtractBinary32(MultiplyBinary32(a.x, b.y), MultiplyBinary32(a.y, b.x))),
                SubtractBinary32(SubtractBinary32(SubtractBinary32(MultiplyBinary32(a.w, b.w), MultiplyBinary32(a.x, b.x)), MultiplyBinary32(a.y, b.y)), MultiplyBinary32(a.z, b.z)));
        }

        private static Float3 RotateQuaternionBinary32(Float4 q, Float3 v)
        {
            float tx = MultiplyBinary32(2.0f, SubtractBinary32(
                MultiplyBinary32(q.y, v.z), MultiplyBinary32(q.z, v.y)));
            float ty = MultiplyBinary32(2.0f, SubtractBinary32(
                MultiplyBinary32(q.z, v.x), MultiplyBinary32(q.x, v.z)));
            float tz = MultiplyBinary32(2.0f, SubtractBinary32(
                MultiplyBinary32(q.x, v.y), MultiplyBinary32(q.y, v.x)));
            float cx = SubtractBinary32(MultiplyBinary32(q.y, tz), MultiplyBinary32(q.z, ty));
            float cy = SubtractBinary32(MultiplyBinary32(q.z, tx), MultiplyBinary32(q.x, tz));
            float cz = SubtractBinary32(MultiplyBinary32(q.x, ty), MultiplyBinary32(q.y, tx));
            return new Float3(
                AddBinary32(AddBinary32(v.x, MultiplyBinary32(q.w, tx)), cx),
                AddBinary32(AddBinary32(v.y, MultiplyBinary32(q.w, ty)), cy),
                AddBinary32(AddBinary32(v.z, MultiplyBinary32(q.w, tz)), cz));
        }

        private static Float3 NormalizeFloat3Binary32(Float3 value)
        {
            float lengthSquared = AddBinary32(
                AddBinary32(MultiplyBinary32(value.x, value.x), MultiplyBinary32(value.y, value.y)),
                MultiplyBinary32(value.z, value.z));
            float inverse = DivideBinary32(1.0f, SqrtBinary32(lengthSquared));
            return new Float3(
                MultiplyBinary32(value.x, inverse),
                MultiplyBinary32(value.y, inverse),
                MultiplyBinary32(value.z, inverse));
        }

        private static float DotFloat3Binary32(Float3 a, Float3 b)
        {
            return AddBinary32(
                AddBinary32(MultiplyBinary32(a.x, b.x), MultiplyBinary32(a.y, b.y)),
                MultiplyBinary32(a.z, b.z));
        }

        private static Float3 NormalizeDouble3ToFloatBinary32(Double3 value)
        {
            Float3 rounded = new Float3((float)value.x, (float)value.y, (float)value.z);
            float inverse = DivideBinary32(1.0f, SqrtBinary32(DotFloat3Binary32(rounded, rounded)));
            return new Float3(
                MultiplyBinary32(rounded.x, inverse),
                MultiplyBinary32(rounded.y, inverse),
                MultiplyBinary32(rounded.z, inverse));
        }

        private static double DotFloatDouble3(Float3 a, Double3 b)
        {
            return (a.x * b.x + a.y * b.y) + a.z * b.z;
        }

        private static double DotDouble3(Double3 a, Double3 b)
        {
            return (a.x * b.x + a.y * b.y) + a.z * b.z;
        }

        private static double LengthDouble3(Double3 value)
        {
            return Math.Sqrt(DotDouble3(value, value));
        }

        private static Double3 SubtractDouble3(Double3 a, Double3 b)
        {
            return new Double3(a.x - b.x, a.y - b.y, a.z - b.z);
        }

        private static Double3 MultiplyDouble3(Double3 value, double scalar)
        {
            return new Double3(value.x * scalar, value.y * scalar, value.z * scalar);
        }

        private static float DistanceWeight(
            byte attribute,
            float depth,
            float friction,
            int teamFlag)
        {
            float denominator;
            if ((attribute & 2) != 0)
            {
                denominator = AddBinary32(MultiplyBinary32(friction, 3.0f), 1.0f);
                float remainingDepth = SubtractBinary32(1.0f, depth);
                denominator = AddBinary32(
                    denominator,
                    MultiplyBinary32(
                        MultiplyBinary32(remainingDepth, remainingDepth),
                        5.0f));
            }
            else
            {
                denominator = (teamFlag & 0x2000) != 0 ? 10.0f : 50.0f;
            }
            return DivideBinary32(1.0f, denominator);
        }

        private static double DistanceCorrectionComponent(
            double delta,
            double length,
            float stiffness,
            double target,
            double weightSum,
            float currentWeight)
        {
            double correction = delta * (1.0 / length);
            correction *= stiffness;
            correction *= length - target;
            correction /= weightSum;
            correction *= currentWeight;
            return correction;
        }

        // Mono may retain an intermediate Single expression in wider
        // precision. The no-inline ABI boundary reproduces Burst's explicit
        // vaddss/vsubss binary32 rounding before conversion to binary64.
        [MethodImpl(MethodImplOptions.NoInlining)]
        private static float AddBinary32(float left, float right)
        {
            return left + right;
        }

        [MethodImpl(MethodImplOptions.NoInlining)]
        private static float SubtractBinary32(float left, float right)
        {
            return left - right;
        }

        [MethodImpl(MethodImplOptions.NoInlining)]
        private static float MultiplyBinary32(float left, float right)
        {
            return left * right;
        }

        [MethodImpl(MethodImplOptions.NoInlining)]
        private static float DivideBinary32(float left, float right)
        {
            return left / right;
        }

        [MethodImpl(MethodImplOptions.NoInlining)]
        private static float SqrtBinary32(float value)
        {
            return (float)Math.Sqrt(value);
        }

        [MethodImpl(MethodImplOptions.NoInlining)]
        private static double AddBinary64(double left, double right)
        {
            return left + right;
        }

        [MethodImpl(MethodImplOptions.NoInlining)]
        private static double SubtractBinary64(double left, double right)
        {
            return left - right;
        }

        [MethodImpl(MethodImplOptions.NoInlining)]
        private static double MultiplyBinary64(double left, double right)
        {
            return left * right;
        }
    }
}
