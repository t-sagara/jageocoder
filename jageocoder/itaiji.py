import json
import os
from typing import Union

from jageocoder.strlib import strlib


class Converter(object):

    optional_prefixes = ['字', '大字', '小字']
    optional_postfixes = ['条', '線', '丁', '丁目', '番', '番地', '号']

    def __init__(self):
        """
        Initialize the converter.

        Attributes
        ----------
        trans_itaiji: table
            The character mapping table from src to dst.
        """
        itaiji_dic_json = os.path.join(
            os.path.dirname(__file__), 'itaiji_dic.json')

        with open(itaiji_dic_json, 'r', encoding='utf-8') as f:
            itaiji_dic = json.load(f)

        src_str, dst_str = '', ''
        for src, dst in itaiji_dic.items():
            src_str += src
            dst_str += dst

        self.trans_itaiji = str.maketrans(src_str, dst_str)
        self.trans_h2z = str.maketrans(
            {chr(0x0021 + i): chr(0xFF01 + i) for i in range(94)})
        self.trans_z2h = str.maketrans(
            {chr(0xFF01 + i): chr(0x21 + i) for i in range(94)})

    def check_optional_prefixes(self, notation: str) -> int:
        """
        Check optional prefixes in the notation and
        return the length of the prefix string.

        Parameters
        ----------
        notation : str
            The address notation to be checked.

        Return
        ------
        The length of optional prefixes string.

        Examples
        --------
        >>> from jageocoder.itaiji import converter
        >>> converter.check_optional_prefixes('大字道仏')
        2
        >>> converter.check_optional_prefixes('字貝取')
        1
        """
        for prefix in self.__class__.optional_prefixes:
            if notation.startswith(prefix):
                return len(prefix)

        return 0

    def check_optional_postfixes(self, notation):
        """
        Check optional postfixes in the notation and
        return the length of the postfix string.

        Parameters
        ----------
        notation : str
            The address notation to be checked.

        Return
        ------
        The length of optional postfixes string.

        Examples
        --------
        >>> from jageocoder.itaiji import converter
        >>> converter.check_optional_postfixes('1番地')
        2
        >>> converter.check_optional_postfixes('15号')
        1
        """
        for postfix in self.__class__.optional_postfixes:
            if notation.endswith(postfix):
                return len(postfix)

        return 0

    def standardize(self, notation: Union[str, None]) -> str:
        """
        Standardize an address notation.

        Parameters
        ----------
        notation : str
            The address notation to be standardized.

        Return
        ------
        str
            The standardized address notation string.
        """
        if notation is None or len(notation) == 0:
            return notation

        l_optional_prefix = self.check_optional_prefixes(notation)
        notation = notation[l_optional_prefix:]

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

            # Omit characters that may be omitted if they are
            # sandwiched between kanji.
            if c in 'ケヶガがツッつ' and \
               prectype not in (4, 5) and nctype not in (4, 5):
                ctype = prectype
                i += 1
                continue

            # 'ノ' and 'の' between numbers or ascii letters
            # are treated as hyphens.
            if c in 'ノの' and prectype in (0, 2, 6) and nctype in (0, 2, 6):
                new_notation += '-'
                ctype = 0
                i += 1
                continue

            # Replace hyphen-like characters with '-'
            if strlib.is_hyphen(c):
                new_notation += '-'
                ctype = 0
                i += 1
                continue

            # Replace numbers including Chinese characters
            # with number + '.' in the notation.
            if strlib.get_numeric_char(c):
                ninfo = strlib.get_number(notation[i:])
                new_notation += str(ninfo['n']) + '.'
                i += ninfo['i']
                if i < len(notation) and notation[i] == '.':
                    i += 1
                ctype = 0
                continue

            new_notation += c
            i += 1

        return new_notation


# Create the singleton object of a converter that normalizes address strings
converter = Converter()
