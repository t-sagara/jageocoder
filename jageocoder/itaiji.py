import json
import os

from jageocoder.strlib import strlib

class Converter(object):

    def __init__(self):
        itaiji_dic_json = os.path.join(
            os.path.dirname(__file__), 'itaiji_dic.json')
        
        with open(itaiji_dic_json, 'r', encoding='utf-8') as f:
            itaiji_dic = json.load(f)

        src_str, dst_str = '', ''
        for src, dst in itaiji_dic.items():
            src_str += src
            dst_str += dst

        self.trans_itaiji = str.maketrans(src_str, dst_str)
        self.trans_h2z = str.maketrans({chr(0x0021 + i): chr(0xFF01 + i) for i in range(94)})
        self.trans_z2h = str.maketrans({chr(0xFF01 + i): chr(0x21 + i) for i in range(94)})


    def standardize(self, notation):

        if notation is None or len(notation) == 0:
            return notation
        
        # 先頭の '字', '大字', '小字' を除去
        if notation[0:1] == '字':
            notation = notation[1:]
        elif notation[0:2] in ('大字', '小字',):
            notation = notation[2:]

        notation = notation.translate(
            self.trans_itaiji).translate(self.trans_z2h)

        prectype, ctype, nctype = 0, 0, 0
        new_notation = ""
        i = 0

        while i < len(notation):
            c = notation[i]
            prectype = ctype
            ctype = nctype

            if i == len(notation) - 1:
                nctype = 0
            else:
                nctype = strlib.get_ctype(notation[i + 1])
                # print("-> next:{}, nctype:{}".format(notation[i + 1], nctype))

            if c in 'ケヶガがツッつ' and \
               prectype not in (4, 5) and nctype not in (4, 5):
                ctype = prectype
                i += 1
                continue

            # print("c:{}, prectype:{}, nctype:{}".format(
            #     c, prectype, nctype))

            if c in 'ノの' and prectype in(0, 2, 6) and nctype in (0, 2, 6):
                new_notation += '-'
                ctype = 0
                i += 1
                continue

            if strlib.get_numeric_char(c):
                ninfo = strlib.get_number(notation[i:])
                new_notation += str(ninfo['n']) + '.'
                i += ninfo['i']
                ctype = 0
                continue

            new_notation += c
            i += 1

        return new_notation

converter = Converter()
