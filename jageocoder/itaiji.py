import json
from logging import getLogger
import os
import re
from typing import List, Tuple, Optional

import jaconv

from jageocoder.address import AddressLevel
from jageocoder.strlib import strlib

logger = getLogger(__name__)


class Converter(object):
    """
    Attributes
    ----------
    trans_itaiji: table
        The character mapping table from src to dst.
    """

    kana_letters = (strlib.HIRAGANA, strlib.KATAKANA)
    latin1_letters = (strlib.ASCII, strlib.NUMERIC, strlib.ALPHABET)
    trans_itaiji = None
    trans_h2z = None
    trans_z2h = None

    @classmethod
    def read_itaiji_table(cls) -> None:
        if cls.trans_itaiji is not None:
            # The table is already prepared.
            return

        itaiji_dic_json = os.path.join(
            os.path.dirname(__file__), 'itaiji_dic.json')

        with open(itaiji_dic_json, 'r', encoding='utf-8') as f:
            itaiji_dic = json.load(f)

        src_str, dst_str = '', ''
        for src, dst in itaiji_dic.items():
            src_str += src
            dst_str += dst

        cls.trans_itaiji = str.maketrans(src_str, dst_str)
        cls.trans_h2z = str.maketrans(
            {chr(0x0021 + i): chr(0xFF01 + i) for i in range(94)})
        cls.trans_z2h = str.maketrans(
            {chr(0xFF01 + i): chr(0x21 + i) for i in range(94)})

    def __init__(self, options: Optional[dict] = None):
        """
        Initialize the converter.

        Parameters
        ----------
        options: dict, optional
            Options to set optional characters, etc.
            See 'set_options()' for list of items.
        """
        self.__class__.read_itaiji_table()
        if options is not None:
            self.set_options(options)
        else:
            self.set_options({})

    def set_options(self, options: dict):
        numbers = rf'[0-9{strlib.kansuji}{strlib.arabic}十百千]+'
        # Optional postfixes for each address level
        # which can be ommitted or represented by hyphens.
        self.re_optional_postfixes = {
            AddressLevel.CITY: re.compile(r'(市|区|町|村)$'),
            AddressLevel.WARD: re.compile(r'(区)$'),
            AddressLevel.OAZA: re.compile(r'[0-9]+\.(町|条|線|丁|丁目|区|番|号|番丁|番町)$'),
            AddressLevel.AZA: re.compile(r'[0-9]+\.(町|条|線|丁|丁目|区|番|号)$'),
            AddressLevel.BLOCK: re.compile(r'[0-9A-Za-z甲乙丙丁]+\.?(番|番地|号|地)$'),
            AddressLevel.BLD: re.compile(r'[0-9]+\.(号|番地)$'),
        }

        # Prefixes that are sometimes added to words at will
        self.optional_prefixes = options.get(
            'prefixes', ['字', '大字', '小字'])

        # Letters that are sometimes insereted to words at will
        self.optional_letters_in_middle = options.get(
            'middle_letters', 'ケヶガツッノ')

        # Strings that are sometimes inserted to words at will
        self.optional_strings_in_middle = options.get(
            'middle_strings', ['大字', '小字', '字'])

        # Extra characters that may be added to the end of a word at will
        self.extra_characters = options.get(
            'suffixes', '-ノ')

        # Characters that may be the beginning of Chiban
        self.chiban_heads = options.get(
            'chiban_heads',
            ('甲乙丙丁戊己庚辛壬癸'
             '子丑寅卯辰巳午未申酉戌亥'
             '続新'
             'いろはにほへとちりぬるをわかよたれそつね'
             'イロハニホヘトチリヌルヲワカヨタレソツネ'))

        # Max length of Aza-name which can be ommitted
        self.max_skip_azaname = options.get(
            'max_aza_length', 5)

        # Generate regular expressions from option settings
        self.re_optional_prefixes = re.compile(r'^({})'.format(
            '|'.join(self.optional_prefixes)))
        self.re_optional_strings_in_middle = re.compile(
            r'^({})'.format(
                '|'.join(list(self.optional_letters_in_middle) +
                         self.optional_strings_in_middle)))
        self.first_letters_of_optional_strings_in_middle = ""
        for s in self.optional_strings_in_middle:
            if len(s) > 1:
                self.first_letters_of_optional_strings_in_middle += s[0]

        # Patterns that cannot be omitted as AZA names
        hyphens = re.escape(strlib.hyphen)
        self.re_not_ommisible_aza_patterns = re.compile(
            r'([^。、，．0-9a-zA-Z\t\n\r\f\v]{,15}?)(' +
            rf'{numbers}[条線丁区番号{hyphens}]|' +
            rf'[{self.chiban_heads}]{numbers}|' +
            rf'{numbers}$' +
            r')'
        )

        # Patterns that do not follow behind nodes at that level
        self.re_non_trailing_patterns = {
            AddressLevel.BLOCK: re.compile(r'[0-9A-Za-z甲乙丙丁]+\.?(番|番地|号|地)'),
            AddressLevel.BLD: re.compile(r'[0-9]+\.?(号|番地)'),
        }

    def check_optional_prefixes(self, notation: str) -> int:
        """
        Check optional prefixes in the notation and
        return the length of the prefix string.

        Parameters
        ----------
        notation: str
            The address notation to be checked.

        Return
        ------
        int
            The length of optional prefixes string.

        Examples
        --------
        >>> from jageocoder.itaiji import converter
        >>> converter.check_optional_prefixes('大字道仏')
        2
        >>> converter.check_optional_prefixes('字貝取')
        1
        """
        m = self.re_optional_prefixes.match(notation)
        if m:
            return len(m.group(1))

        return 0

    def check_optional_postfixes(self, notation: str, level: int) -> int:
        """
        Check optional postfixes in the notation and
        return the length of the postfix string.

        Parameters
        ----------
        notation : str
            The address notation to be checked.
        level: int
            Address level of the target element.

        Return
        ------
        int
            The length of optional postfixes string.

        Examples
        --------
        >>> from jageocoder.itaiji import converter
        >>> converter.check_optional_postfixes('1番地', 7)
        2
        >>> converter.check_optional_postfixes('四日市市', 3)
        1
        """
        if level not in self.re_optional_postfixes:
            return 0

        m = self.re_optional_postfixes[level].search(notation)
        if m:
            return len(m.group(1))

        return 0

    def check_trailing_string(self, index: str, level: int) -> bool:
        """
        Check for a pattern that should not be followed after
        the specified node.

        Parameters
        ----------
        index: str
            The trailing string.
        level: int
            The level of the specified node.

        Returns
        -------
        bool
            True if a pattern following the node.
            Otherwise false.
        """
        if level not in self.re_non_trailing_patterns:
            return False

        return self.re_non_trailing_patterns[level].match(index) is not None

    def standardize(self, notation: Optional[str],
                    keep_numbers: bool = False) -> str:
        """
        Standardize an address notation.

        Parameters
        ----------
        notation : str
            The address notation to be standardized.
        keep_numbers: bool, optional
            If set to True, do not process numerical characters.

        Return
        ------
        str
            The standardized address notation string.

        Examples
        --------

        """
        if notation is None or len(notation) == 0:
            return ""

        l_optional_prefix = self.check_optional_prefixes(notation)
        notation = notation[l_optional_prefix:]

        # Convert the notation according to the following rules.
        # 1. Variant characters with representative characters
        # 2. ZENKAKU characters with HANKAKU characters
        # 3. Lower case characters with capitalized characters
        # 4. HIRAGANA with KATAKANA
        # 5. Other exceptions
        notation = notation.translate(
            self.trans_itaiji).translate(self.trans_z2h).upper()  # type: ignore
        notation = str(jaconv.hira2kata(notation))
        notation = notation.replace('通リ', '通')

        new_notation = ""
        i = 0

        while i < len(notation):
            c = notation[i]

            # Replace hyphen-like characters with '-'
            if strlib.is_hyphen(c):
                new_notation += '-'
                i += 1
                continue

            # Replace numbers including Chinese characters
            # with number + '.' in the notation.
            if not keep_numbers and \
                    strlib.get_numeric_char(c) is not False:
                ninfo = strlib.get_number(notation[i:])
                new_notation += str(ninfo['n']) + '.'
                i += ninfo['i']
                if i < len(notation) and notation[i] == '.':
                    i += 1
                continue

            new_notation += c
            i += 1

        return new_notation

    def match_len(self, string: str, pattern: str,
                  removed_postfix: Optional[str] = None) -> int:
        """
        Returns the length of the substring that matches the patern
        from the beginning. The pattern must have been standardized.

        Parameters
        ----------
        string: str
            A long string starting with the pattern.
        pattern: str
            The search pattern.
        removed_postfix: str, optional
            The postfix that were included in the original pattern,
            but were removed for matching.

        Returns
        -------
        int
            The length of the substring that matches the pattern.
            If it does not match exactly, it returns 0.

        Notes
        -----
        - If a leading part of the pattern matches the string,
          this method returns 0.
        """
        logger.debug((
            "Counts the number of characters matching '{}' "
            "from the beginning of '{}'."
        ).format(pattern, string))
        nloops = 0
        pattern_pos = string_pos = 0
        while pattern_pos < len(pattern):
            nloops += 1
            if nloops > 256:
                msg = ('There is a possibility of an infinite loop.'
                       'pattern={}, string={}')
                raise RuntimeError(msg.format(pattern, string))

            if string_pos >= len(string):
                return 0

            is_equal, slen1, slen2 = self._check_equal(
                string, string_pos,
                pattern, pattern_pos)

            if not is_equal:
                return 0

            string_pos += slen1
            pattern_pos += slen2
            continue

        if removed_postfix is not None:
            # If the next character of the query string is
            # an optional character, Judge as mismatch
            alen = self.is_abbreviated_postfix(string, string_pos)
            if alen < 0:
                logger.debug((
                    "Removed postfix '{}' without corresponding abbreviation,"
                    "(the query following '{}')").format(
                        removed_postfix, string[string_pos:]))
                return 0

        logger.debug(
            "{} characters matched. ('{}')".format(
                string_pos, string[0:string_pos]
            ))
        return string_pos

    def _check_equal(
        self,
        string: str,
        string_pos: int,
        pattern: str,
        pattern_pos: int
    ) -> Tuple[bool, int, int]:
        """
        Determines if the leading parts of two strings,
        string and pattern, are equivalent.

        Parameters
        ----------
        string: str
            A long string starting with the pattern.
        string_pos: int
            Character position at which to start the comparison.
        pattern: str
            The search pattern.
        pattern_pos: int
            Character position at which to start the comparison.

        Returns
        -------
        (bool, int, int)
            - The first value is a boolean value indicating whether
              the two strings are equivalent.
            - The second value is the number of characters in the string
              that are matched.
            - The third value is the number of characters in the patter
              that are matched.

        """
        c = pattern[pattern_pos]
        s = string[string_pos]
        if c < '0' or c > '9':
            # Compare not numeric character
            # logger.debug("Comparing '{}'({}) with '{}'({})".format(
            #     c, pattern_pos, s, string_pos))
            if c == s and \
                    c not in self.first_letters_of_optional_strings_in_middle:
                return (True, 1, 1)

            slen = self.optional_str_len(string, string_pos)
            plen = self.optional_str_len(pattern, pattern_pos)
            if slen > 0 and plen > 0 and \
                    string[string_pos + slen:string_pos + slen + 1] == pattern[
                        pattern_pos + plen:pattern_pos + plen + 1]:
                return (True, slen + 1, plen + 1)

            if slen > 0 and string[string_pos + slen:string_pos + slen + 1] == c:
                return (True, slen + 1, 1)

            if plen > 0 and pattern[pattern_pos + plen:pattern_pos + plen + 1] == s:
                return (True, 1, plen + 1)

            if c == s:
                # For the case that c, s are in self.first_letters_of_optional_strings_in_middle
                return (True, 1, 1)

            # Search optional Aza-name
            aza_len = self.optional_aza_len(string, string_pos)
            s = string[string_pos + aza_len:string_pos + aza_len + 1]
            if s == c:
                return (True, aza_len + 1, 1)

            if plen > 0 and pattern[pattern_pos + plen:pattern_pos + plen + 1] == s:
                return (True, aza_len + 1, plen + 1)

            return (False, 0, 0)

        # Compare numbers:
        # Check if the numeric sequence of the search string
        # matches the number expected by the pattern.
        period_pos = pattern.find('.', pattern_pos)
        if period_pos < 0:
            raise RuntimeError(
                "No period after a number in the pattern string.")

        slen = self.optional_str_len(string, string_pos)
        expected = int(pattern[pattern_pos:period_pos])
        logger.debug("Comparing string {} with expected value {}".format(
            string[string_pos + slen:], expected))
        candidate = strlib.get_number(string[string_pos + slen:], expected)
        if candidate['n'] == expected and candidate['i'] > 0:
            logger.debug("Substring {} matches".format(
                string[string_pos + slen: string_pos + slen + candidate['i']]))
            return (True, slen + candidate['i'], period_pos + 1 - pattern_pos)

        return (False, 0, 0)

    def optional_str_len(self, string: str, pos: int) -> int:
        m = self.re_optional_strings_in_middle.match(
            string[pos:])

        if m:
            return len(m.group(1))

        return 0

    def optional_aza_len(self, string: str, pos: int = 0) -> int:
        """
        Returns the length of Aza-name candidates that can be omitted.

        Parameters
        ----------
        string: str
            The query string which may contain Aza-name (standardized)
        pos: int
            Position to start analysis

        Returns
        -------
        int
            Number of characters that can be omitted.
        """
        m = self.re_not_ommisible_aza_patterns.match(string[pos:])
        if m is None:
            return 0

        n = len(m.group(1))
        # n = string[pos:].find(m.group(0))
        return n

        candidates = []
        i = 0
        while i <= self.max_skip_azaname:
            if pos + i >= len(string):
                break

            number = strlib.get_number(string[pos + i])
            if number["i"] > 0:
                if self.re_optional_postfixes[AddressLevel.AZA].match(
                    string[pos + i + number["i"]:]
                ):
                    # 漢数字を含む数値の後ろに接尾辞が続く場合、
                    # その数字部分以降は省略不可
                    candidates.append(pos + i)
                    break
                elif string[pos + i] in '0123456789０１２３４５６７８９':
                    # 数字以降は省略不可
                    candidates.append(pos + i)
                    break
                else:
                    # 数値の途中では省略しない
                    i += number["i"]
                    continue

            i += 1

        return candidates

    def is_abbreviated_postfix(self, string: str, pos: int) -> int:
        """
        Checks whether an abbreviation exists at the specified position.

        Parameters
        ----------
        string: str
            The standardized query string.
        pos: int
            The specified position.

        Return
        ------
        int
            If an abbreviation exists, return 1.
            If ths position exceeds the string length, return 0.
            Otherwise -1.
        """
        if pos >= len(string):
            return 0

        c = string[pos]
        if strlib.is_hyphen(c):
            return 1

        if c != 'ノ' or pos >= len(string) - 1:
            return 0

        nc = string[pos + 1]  # The character next to 'ノ'
        if nc in self.chiban_heads or strlib.get_numeric_char(nc):
            return 1

        return -1

    def standardized_candidates(
            self, string: str, from_pos: int = 0) -> List[str]:
        """
        Enumerate possible candidates for the notation
        after standardization.

        This method is called recursively.

        Parameters
        ----------
        string: str
            The original address notation.
        from_pos: int, optional
            The character indent from where the processing starts.

        Results
        -------
        A list of str
            A list of candidate strings.
        """
        candidates = [string]
        for pos in range(from_pos,
                         len(self.optional_letters_in_middle) +
                         len(self.optional_strings_in_middle)):
            if pos < len(self.optional_strings_in_middle):
                substr = self.optional_strings_in_middle[pos]
            else:
                substr = self.optional_letters_in_middle[
                    pos - len(self.optional_strings_in_middle)]

            if string.find(substr) >= 0:
                # logger.debug('"{}" is in "{}"'.format(substr, string))
                candidates += self.standardized_candidates(
                    string.replace(substr, ''), pos + 1)

        return candidates


# Create the singleton object of a converter that normalizes
# address strings for backword compatibility.
if 'converter' not in vars():
    converter = Converter()
