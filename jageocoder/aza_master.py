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
        1:大字・町, 2:丁目, 3:小字
    pref: str
        都道府県名
    pref_kana: str
        都道府県名_カナ
    pref_eng: str
        都道府県名_英字
    county: str
        郡名
    county_kana: str
        郡名_カナ
    county_eng: str
        郡名_英字
    city: str
        市区町村名
    city_kana: str
        市区町村名_カナ
    city_eng: str
        市区町村名_英字
    ward: str
        政令市区名
    ward_kana: str
        政令市区名_カナ
    ward_eng: str
        政令市区名_英字
    oaza: str
        大字・町名
    oaza_kana: str
        大字・町名_カナ
    oaza_eng: str
        大字・町名_英字
    chome: str
        丁目名
    chome_kana: str
        丁目名_カナ
    chome_num: str
        丁目名_数字
    koaza: str
        小字名
    koaza_kana: str
        小字名_カナ
    koaza_eng: str
        小字名_英字
    is_jukyo: bool
        住居表示フラグ
    jukyo_code: int
        住居表示方式コード
        1:街区方式, 2:道路方式, 0:住居表示でない
    is_oaza_alias: bool
        大字・町_通称フラグ
    is_koaza_alias: bool
        小字_通称フラグ
    is_oaza_gaiji: bool
        大字・町_外字フラグ
    is_koaza_gaiji: bool
        小字_外字フラグ
    status: int
        状態フラグ
        0:自治体確認待ち, 1:地方自治法の町字に該当, 2:地方自治法の町字に非該当, 3:不明
    start_count_type: int
        起番フラグ
        1:起番, 2:非起番, 0:登記情報に存在しない
    valid_from: date
        効力発生日
    valid_to: date
        廃止日
    reference_code: int
        原典資料コード
        1:自治体資料, 11:位置参照情報・自治体資料, 12:位置参照情報・街区レベル,
        13:位置参照情報・1/2500地形図, 10:位置参照情報・その他資料, 0:その他資料
    postcode: str
        郵便番号（セミコロン区切り）
    note: str
        備考
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
            "code": row["全国地方公共団体コード"][0:5] + row["町字id"],
            "names": json.dumps(names, ensure_ascii=False),
            "namesIndex": self.__class__.standardize_aza_name(names),
            "azaClass": row.get("町字区分コード"),
            # "pref": row["都道府県名"],
            # "pref_kana": row.get("都道府県名_カナ", ""),
            # "pref_eng": row.get("都道府県名_英字", ""),
            # "county": row.get("郡名", ""),
            # "county_kana": row.get("郡名_カナ", ""),
            # "county_eng": row.get("郡名_英字", ""),
            # "city": row.get("市区町村名", ""),
            # "city_kana": row.get("市区町村名_カナ", ""),
            # "city_eng": row.get("市区町村名_英字", ""),
            # "ward": row.get("政令市区名", ""),
            # "ward_kana": row.get("政令市区名_カナ", ""),
            # "ward_eng": row.get("政令市区名_英字", ""),
            # "oaza": row.get("大字・町名", ""),
            # "oaza_kana": row.get("大字・町名_カナ", ""),
            # "oaza_eng": row.get("大字・町名_英字", ""),
            # "chome": row.get("丁目名", ""),
            # "chome_kana": row.get("丁目名_カナ", ""),
            # "chome_num": row.get("丁目名_数字", ""),
            # "koaza": row.get("小字名", ""),
            # "koaza_kana": row.get("小字名_カナ", ""),
            # "koaza_eng": row.get("小字名_英字", ""),
            "isJukyo": row.get("住居表示フラグ", "") == "1",
            # "jukyo_code": row.get("住居表示方式コード"),
            # "is_oaza_alias": row.get("大字・町_通称フラグ", "") == "1",
            # "is_koaza_alias": row.get("小字_通称フラグ", "") == "1",
            # "is_oaza_gaiji": row.get("大字・町_外字フラグ", "") == "1",
            # "is_koaza_gaiji": row.get("小字_外字フラグ", "") == "1",
            # "status": row.get("状態フラグ"),
            "startCountType": row.get("起番フラグ"),
            # "valid_from": row.get("効力発生日"),
            # "valid_to": row.get("廃止日"),
            # "reference_code": row.get("原典資料コード"),
            "postcode": row.get("郵便番号"),
            # "note": row.get("備考"),
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
        code = row["全国地方公共団体コード"][0:5] + row["町字id"]
        names = []
        pref = row['都道府県名']
        if pref:
            names.append([
                AddressLevel.PREF,
                pref,
                row['都道府県名_カナ'],
                row['都道府県名_英字'],
                code[0:2]])

        county = row['郡名']
        if county:
            names.append([
                AddressLevel.COUNTY,
                county,
                row['郡名_カナ'],
                row['郡名_英字'],
                code[0:3]])

        city = row['市区町村名']
        ward = row['政令市区名']
        if ward:
            names.append([
                AddressLevel.CITY,
                city,
                row['市区町村名_カナ'],
                row['市区町村名_英字'],
                code[0:3]])

            names.append([
                AddressLevel.WARD,
                ward,
                row['政令市区名_カナ'],
                row['政令市区名_英字'],
                code[0:5]])
        else:
            names.append([
                AddressLevel.CITY,
                city,
                row['市区町村名_カナ'],
                row['市区町村名_英字'],
                code[0:5]])

        oaza = row['大字・町名']
        if oaza:
            names.append([
                AddressLevel.OAZA,
                oaza,
                row['大字・町名_カナ'],
                row['大字・町名_英字'],
                code[0:9]])

        chome = row['丁目名']
        if chome:
            names.append([
                AddressLevel.AZA,
                chome,
                row['丁目名_カナ'],
                row['丁目名_数字'] + 'chome',
                code])

        aza = row['小字名']
        if aza:
            names.append([
                AddressLevel.AZA,
                aza,
                row['小字名_カナ'],
                row['小字名_英字'],
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
        for i in range(self.count_records):
            record = self.get_record(pos=i)
            if record.names_index == st_name:
                return record

        logger.debug("'{}' is not in the aza_master table.".format(
            ''.join([x[1] for x in elements])))
        return None

    def search_by_code(
        self,
        code: str,
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
                return record

        logger.debug("'{}' is not in the aza_master table.".format(code))
        return None

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
