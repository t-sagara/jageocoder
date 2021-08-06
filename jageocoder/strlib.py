import re
from typing import Union


class Strlib(object):

    def __init__(self):
        self.hyphen = ("\u002D\uFE63\uFF0D\u2010\u2011\u2043\u02D6"
                       "\u2212\u2012\u2013\u2014\u2015\uFE58\u30FC")
        self.kansuji = "〇一二三四五六七八九"
        self.arabic = "０１２３４５６７８９"

        self.re_en = re.compile(r'[a-zA-Z]')
        self.re_ascii = re.compile(r'[\u0021-\u007e]')
        self.re_hira = re.compile(r'[\u3041-\u309F]')
        self.re_kata = re.compile(r'[\u30A1-\u30FF]')
        self.re_cjk = re.compile(r'[\u4E00-\u9FFF]')

    def is_hyphen(self, c: str) -> bool:
        """
        Check if the c is a hyphen.

        Parameters
        ----------
        c: str
            Characters to be checked.

        Return
        ------
        bool
            Return True if c is a hyphen, otherwise False.

        Examples
        --------
        >>> from jageocoder.strlib import strlib
        >>> strlib.is_hyphen('-')
        True
        >>> strlib.is_hyphen(',')
        False
        """
        return (c in self.hyphen)

    def is_kansuji(self, c: str) -> bool:
        """
        Check if the c is a kansuji.

        Parameters
        ----------
        c: str
            Characters to be checked.

        Return
        ------
        bool
            Return True if c is a kansuji, otherwise False.

        Examples
        --------
        >>> from jageocoder.strlib import strlib
        >>> strlib.is_kansuji('八')
        True
        >>> strlib.is_kansuji('８')
        False
        """
        return (c in self.kansuji)

    def is_arabic_number(self, c: str) -> bool:
        """
        Check if the c is an Arabic number.

        Parameters
        ----------
        c: str
            Characters to be checked.

        Return
        ------
        bool
            Return True if c is an Arabic number,
            otherwise False.

        Examples
        --------
        >>> from jageocoder.strlib import strlib
        >>> strlib.is_arabic_number('八')
        False
        >>> strlib.is_arabic_number('８')
        True
        """
        return (c in self.arabic)

    def get_numeric_char(self, c: str) -> Union[int, bool]:
        """
        Returns the integer value represented by the character c.
        When c is not a numerical characters, return False.

        Parameters
        ----------
        c: str
            Characters to be examined.

        Return
        ------
        int, False
            Return the int value represented by c,
            otherwise False.

        Examples
        --------
        >>> from jageocoder.strlib import strlib
        >>> strlib.get_numeric_char('八')
        8
        >>> strlib.get_numeric_char('千')
        1000
        >>> strlib.get_numeric_char('萬')
        False
        """
        pos = '0123456789'.find(c)
        if pos >= 0:
            return pos

        pos = self.kansuji.find(c)
        if pos >= 0:
            return pos

        pos = self.arabic.find(c)
        if pos >= 0:
            return pos

        if c == '十':
            return 10

        if c == '百':
            return 100

        if c == '千':
            return 1000

        if c == '万':
            return 10000

        return False

    def get_number(self, string: str) -> dict:
        """
        Parses a string as a number.

        Parameters
        ----------
        string: str
            String to be examined.

        Return
        ------
        dict
            Returns the dict which contains the integer value
            represented by the string ("n"), and the position
            where the string was used as a value ("i").

        Examples
        --------
        >>> from jageocoder.strlib import strlib
        >>> strlib.get_number('２-')
        {'n': 2, 'i': 1}
        >>> strlib.get_number('1234a')
        {'n': 1234, 'i': 4}
        >>> strlib.get_number('0015')
        {'n': 15, 'i': 4}
        >>> strlib.get_number('２４')
        {'n': 24, 'i': 2}
        >>> strlib.get_number('一三五')
        {'n': 135, 'i': 3}
        >>> strlib.get_number('二千四十五万円')
        {'n': 20450000, 'i': 6}
        >>> strlib.get_number('こんにちは')
        {'n': 0, 'i': 0}
        """
        total = 0
        curval = 0
        mode = -1   # -1: unset, 0: parsing arabic, 1: parsing kansuji

        pos = 0
        for i, c in enumerate(string):
            if c in '0123456789' or self.is_arabic_number(c):
                k = self.get_numeric_char(c)
                curval = curval * 10 + k
                mode = 0
                pos += 1

            elif mode == 0:
                break

            elif self.is_kansuji(c):
                k = self.get_numeric_char(c)
                if total + curval == 0 and k == 0:
                    break

                curval = curval * 10 + k
                mode = 1
                pos += 1
            elif c in '十百千万':
                k = self.get_numeric_char(c)
                curval = 1 if curval == 0 else curval
                total = total * k if total % k > 0 else total
                total += curval * k
                curval = 0
                mode = 1
                pos += 1

            else:
                break

        total += curval
        return {"n": total, "i": pos}

    def get_ctype(self, c: str) -> int:
        """
        Get the character type of c.

        Parameters
        ----------
        c: str
            The character to be checked.

        Return
        ------
        int
            The type number.

        Examples
        --------
        >>> from jageocoder.strlib import strlib
        >>> strlib.get_ctype('２')
        2
        >>> strlib.get_ctype('あ')
        4
        >>> strlib.get_ctype('ン')
        5
        >>> strlib.get_ctype('ﾁ')
        -1
        >>> strlib.get_ctype('Q')
        6
        >>> strlib.get_ctype('!')
        0
        >>> strlib.get_ctype('5')
        0
        >>> strlib.get_ctype('５')
        2
        >>> strlib.get_ctype('碧')
        1
        """
        if self.re_hira.match(c):
            return 4  # ひらがな
        elif self.re_kata.match(c):
            return 5  # カタカナ
        elif self.re_en.match(c):
            return 6  # 半角アルファベット
        elif self.re_ascii.match(c):
            return 0  # アスキー文字
        elif c in self.arabic or c in self.kansuji:
            return 2  # 数字
        elif self.re_cjk.match(c):
            return 1  # 漢字

        return -1  # 不明


strlib = Strlib()  # singleton
