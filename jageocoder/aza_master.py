from __future__ import annotations
import datetime
import json
from logging import getLogger
import re

from PortableTab import BaseTable

from jageocoder.address import AddressLevel
from jageocoder.itaiji import converter as itaiji_converter

logger = getLogger(__name__)


class AzaMaster(BaseTable):
    """
    The mater table of Cho-Aza data from the address-base registry.

    Attributes
    ----------
    code: str
        全国地方公共団体コードの前方5桁 + 町字id
    names: str
        A JSON encoded list of pairs of [住所要素レベル, 表記]
    names_index: str
        Standardized names for retrieval
    aza_class: int
        町字区分コード
        1:大字・町, 2:丁目, 3:小字, 4:なし, 5:道路方式の道路名
    is_jukyo: bool
        住居表示フラグ
        1:住居表示実施, 0:住居表示非実施, 2:実施・非実施区域が併存
    start_count_type: int
        起番フラグ
        1:起番, 2:非起番, 0:登記情報に存在しない
    postcode: str
        郵便番号（セミコロン区切り）
    """

    __tablename__ = "aza_master"
    __schema__ = """
        struct AzaMaster {
            code @0 :Text;
            names @1 :Text;
            namesIndex @2 :Text;
            azaClass @3 :UInt8;
            isJukyo @4 :Bool;
            startCountType @5 :UInt8;
            postcode @6 :Text;
        }
        """
    __record_type__ = "AzaMaster"

    re_optional = re.compile(
        r'({})'.format(
            '|'.join(list('ケヶガツッノ') + ['字', '大字', '小字'])))

    def from_csvrow(self, row: dict) -> dict:
        names = self.get_names_from_csvrow(row)
        aza_master_row = {
            "code": row["lg_code"][0:5] + row["machiaza_id"],
            "names": json.dumps(names, ensure_ascii=False),
            "namesIndex": self.__class__.standardize_aza_name(names),
            "azaClass": row.get("machiaza_type"),
            "isJukyo": row.get("rsdt_addr_flg", "") == "1",
            "startCountType": row.get("wake_num_flg"),
            "postcode": row.get("post_code"),
        }
        for key in ("azaClass", "jukyoCode", "status",
                    "startCountType", "referenceCode",):
            if aza_master_row.get(key) is not None:
                aza_master_row[key] = int(aza_master_row[key])

        for key in ("validFrom", "validTo",):
            if aza_master_row.get(key) is not None:
                if aza_master_row[key] != "":
                    aza_master_row[key] = datetime.date.fromisoformat(
                        aza_master_row[key])
                else:
                    aza_master_row[key] = None

        if aza_master_row.get("postcode") is not None:
            if aza_master_row["postcode"] != "":
                aza_master_row["postcode"] = json.dumps(
                    aza_master_row["postcode"].split(";"),
                    ensure_ascii=False)

        else:
            aza_master_row["postcode"] = ""

        return aza_master_row

    def get_names_from_csvrow(self, row: dict) -> list:
        code = row["lg_code"][0:5] + row["machiaza_id"]
        names = []
        pref = row["pref"]
        if pref:
            names.append([
                AddressLevel.PREF,
                pref,
                row["pref_kana"],
                row["pref_roma"],
                code[0:2]])

        county = row["county"]
        if county:
            names.append([
                AddressLevel.COUNTY,
                county,
                row["county_kana"],
                row["county_roma"],
                code[0:3]])

        city = row["city"]
        ward = row["ward"]
        if ward:
            names.append([
                AddressLevel.CITY,
                city,
                row["city_kana"],
                row["city_roma"],
                code[0:3]])

            names.append([
                AddressLevel.WARD,
                ward,
                row["ward_kana"],
                row["ward_roma"],
                code[0:5]])
        else:
            names.append([
                AddressLevel.CITY,
                city,
                row["city_kana"],
                row["city_roma"],
                code[0:5]])

        oaza = row["oaza_cho"]
        if oaza:
            names.append([
                AddressLevel.OAZA,
                oaza,
                row["oaza_cho_kana"],
                row["oaza_cho_roma"],
                code[0:9]])

        chome = row["chome"]
        if chome:
            names.append([
                AddressLevel.AZA,
                chome,
                row["chome_kana"],
                row["chome_number"] + 'chome',
                code])

        aza = row["koaza"]
        if aza:
            names.append([
                AddressLevel.AZA,
                aza,
                row["koaza_kana"],
                row["koaza_roma"],
                code])

        return names

    @classmethod
    def standardize_aza_name(cls, names: list) -> str:
        """
        Convert list of address element in [level, name] format
        into a string with typographical deviations removed.
        """
        converted = ''
        for element in names:
            name = itaiji_converter.standardize(element[1])
            prefix_len = itaiji_converter.check_optional_prefixes(name)
            name = name[prefix_len:]
            if len(name) > 1:
                head, body, tail = name[0:1], name[1:-1], name[-1:]
            else:
                head, body, tail = name[0:1], '', ''

            body = cls.re_optional.sub('', body)
            name = head + body + tail
            converted += name

        return converted

    def search_by_names(
        self,
        elements: list,
    ):
        """
        Search AzaMaster record by a list of address elements.

        Parameters
        ----------
        elements: list
            List of address elements ([level, name])

        Return
        ------
        Record, None
            Aza_master record or None.

        Notes
        -----
        - This method uses sequential search so it is very slow.
        """
        st_name = self.__class__.standardize_aza_name(elements)
        for i in range(self.count_records()):
            record = self.get_record(pos=i)
            if record.names_index == st_name:
                return record

        logger.debug("'{}' is not in the aza_master table.".format(
            ''.join([x[1] for x in elements])))
        return None

    def search_by_code(
        self,
        code: str,
        as_dict: bool = False,
    ):
        """
        Search AzaMaster record by azacode.

        Parameters
        ----------
        code: str
            Azacode.

        Return
        ------
        Record, None
            Aza_master record or None.
        """
        if len(code) == 13:
            # lasdec(6digits) + aza_id(7digits)
            code = code[0:5] + code[6:]

        for record in self.search_records_on(attr="code", value=code):
            if record.code == code:
                if as_dict is True:
                    return {
                        "code": str(record.code),
                        "names": str(record.names),
                        "namesIndex": str(record.namesIndex),
                        "azaClass": int(record.azaClass),
                        "isJukyo": bool(record.isJukyo),
                        "startCountType": int(record.startCountType),
                        "postcode": str(record.postcode),
                    }

                return record

        raise KeyError(f"'{code}' is not in the aza_master table.")

    def binary_search(self, code: str) -> int:
        """
        Searches for the record with a code equal to or smaller than
        the specified string using the binary search method,
        and returns its location.

        Parameters
        ----------
        code: str
            The target code.

        Returns
        -------
        int
            The position.

        Notes
        -----
        - Returns -1 if the specified code is less than the code of
          the first record in the table.
        """
        search_range = (0, self.count_records())
        while search_range[0] < search_range[1]:
            pos = int((search_range[0] + search_range[1]) / 2)
            record = self.get_record(pos=pos)
            if record.code == code:
                return pos
            elif record.code > code:
                new_range = (search_range[0], pos)
            elif record.code < code:
                new_range = (pos, search_range[1])

            if new_range == search_range:
                return search_range[0]

            search_range = new_range

        return -1
