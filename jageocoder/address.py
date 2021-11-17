from logging import getLogger

from jageocoder.exceptions import AddressLevelError

logger = getLogger(__name__)


class AddressLevel(object):
    """
    Address Levels

    1 = 都道府県
    2 = 郡・支庁・振興局
    3 = 市町村および特別区
    4 = 政令市の区
    5 = 大字
    6 = 字
    7 = 地番または住居表示実施地域の街区
    8 = 枝番または住居表示実施地域の住居番号
    """

    # Constants
    UNDEFINED = -1
    PREF = 1
    COUNTY = 2
    CITY = 3
    WARD = 4
    OAZA = 5
    AZA = 6
    BLOCK = 7
    BLD = 8

    @classmethod
    def guess(cls, name, parent, trigger):
        """
        Guess the level of the address element.

        Parameters
        ----------
        name : str
            The name of the address element
        parent : AddressNode
            The parent node of the target.
        trigger : dict
            properties of the new address node who triggered
            adding the address element.

            name : str. name. ("２丁目")
            x : float. X coordinate or longitude. (139.69175)
            y : float. Y coordinate or latitude. (35.689472)
            level : int. Address level (1: pref, 3: city, 5: oaza, ...)
            note : str. Note.
        """
        lastchar = name[-1]
        if parent.id == -1:
            return cls.PREF

        if parent.level == cls.PREF and \
                (lastchar == '郡' or name.endswith(('支庁', '振興局',))):
            return cls.COUNTY

        if lastchar in '市町村':
            if parent.level < cls.CITY:
                return cls.CITY

            if parent.level in (cls.CITY, cls.OAZA,):
                return parent.level + 1

        if lastchar == '区':
            if parent.level == cls.CITY:
                return cls.WARD

            if parent.name == '東京都':
                return cls.CITY

        if parent.level < cls.OAZA:
            return cls.OAZA

        if parent.level == cls.OAZA:
            return cls.AZA

        if parent.level == cls.AZA:
            if trigger['level'] <= cls.BLOCK:
                # If the Aza-name is over-segmented, Aza-level address elements
                # may appear in series.
                # ex: 北海道,帯広市,稲田町南,九線,西,19番地
                return cls.AZA

            return cls.BLOCK

        raise AddressLevelError(
            ('Cannot estimate the level of the address element. '
                'name={}, parent={}, trigger={}'.format(
                    name, parent, trigger)))
