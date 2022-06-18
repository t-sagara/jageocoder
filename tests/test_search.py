import logging
from typing import List, Optional
import unittest

import jageocoder
from jageocoder.node import AddressNode

logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO)


class TestSearchMethods(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        jageocoder.init(mode="r")

    def _check(self, query: str, aza_skip='auto',
               target_area: Optional[List[str]] = None,
               match: str = None, ncandidates: int = None,
               level: int = None, fullname: list = None):
        jageocoder.set_search_config(
            aza_skip=aza_skip, target_area=target_area)
        result = jageocoder.search(query=query)
        if match:
            self.assertEqual(result["matched"], match)

        candidates = result["candidates"]
        if ncandidates:
            self.assertEqual(len(candidates), ncandidates)
        else:
            self.assertTrue(len(candidates) > 0)

        top = candidates[0]
        if level:
            self.assertEqual(top["level"], level)

        if fullname:
            if isinstance(fullname[0], str):
                self.assertEqual(top["fullname"], fullname)
            else:
                self.assertIn(top["fullname"], fullname)

        return top

    def test_jukyo(self):
        """
        Test for addresses followed by other strings.
        """
        self._check(
            query="多摩市落合1-15多摩センタートーセイビル",
            match="多摩市落合1-15",
            ncandidates=1,
            level=7,
            fullname=["東京都", "多摩市", "落合", "一丁目", "15番地"]
        )

    def test_with_area(self):
        """
        Test to search by specifying the target region.
        """
        self._check(
            query="落合1-15-2",
            match="落合1-15-",
            target_area=["多摩市"],
            ncandidates=1,
            level=7,
            fullname=["東京都", "多摩市", "落合", "一丁目", "15番地"]
        )

    def test_sapporo(self):
        """
        Test a notation which is omitting "条" in Sapporo city.
        """
        self._check(
            query="札幌市中央区北3西1-7",
            match="札幌市中央区北3西1-7",
            fullname=[
                "北海道", "札幌市", "中央区", "北三条",
                "西一丁目", "7番地"])

    def test_mie(self):
        """
        Test for an address beginning with a number.
        """
        self._check(
            query="三重県津市広明町13番地",
            match="三重県津市広明町13番地",
            fullname=["三重県", "津市", "広明町", "13番地"])

    def test_akita(self):
        self._check(
            query="秋田市山王4-1-1",
            match="秋田市山王4-1-",
            level=7,
            fullname=["秋田県", "秋田市", "山王", "四丁目", "1番"])

    def test_kyoto(self):
        """
        Test a notation which is containing street name in Kyoto city.
        """
        self._check(
            query="京都市上京区下立売通新町西入薮ノ内町",
            match="京都市上京区下立売通新町西入薮ノ内町",
            level=5,
            fullname=["京都府", "京都市", "上京区", "藪之内町"])

    def test_kyoto_yamatooji(self):
        """
        Test a notation which is containing street name in Kyoto city,
        where the street name contains oaza-name.
        """
        self._check(
            query="東山区大和大路通正面下る大和大路1-535",
            match="東山区大和大路通正面下る大和大路1-535",
            level=7,
            fullname=["京都府", "京都市", "東山区",
                      "大和大路", "一丁目", "535番地"])

    def test_oaza(self):
        """
        Test notations with and without "大字"
        """
        self._check(
            query="東京都西多摩郡瑞穂町大字箱根ケ崎2335番地",
            match="東京都西多摩郡瑞穂町大字箱根ケ崎2335番地",
            fullname=[
                ["東京都", "西多摩郡", "瑞穂町", "箱根ケ崎", "2335番地"],
                ["東京都", "西多摩郡", "瑞穂町", "大字箱根ケ崎", "2335番地"]],
            level=7)

    def test_oaza_not_in_dictionary(self):
        """
        Test notation with "大字" which is not included in the dictionary.
        """
        self._check(
            query="大分県宇佐市安心院町大字古川字長坂",
            match="大分県宇佐市安心院町大字古川",
            fullname=["大分県", "宇佐市", "安心院町古川"])

    def test_oaza_not_in_dictionary_with_oo(self):
        """
        Test notation with "大字" which is not included in the dictionary,
        and the name begins with "大".
        """

        # In case non-numbers follow
        self._check(
            query="岡山県新見市哲多町大字大野",
            fullname=["岡山県", "新見市", "哲多町大野"])

        # In case numbers follow
        self._check(
            query="徳島県阿南市那賀川町大字三栗字堤下",
            fullname=["徳島県", "阿南市", "那賀川町三栗"])

    def test_oaza_not_in_query(self):
        """
        Test notation with "大字" which is not included in the query.
        """
        self._check(
            query="熊本県阿蘇市波野小地野",
            fullname=["熊本県", "阿蘇市", "波野", "大字小地野"])

    def test_split_consecutive_numbers_kansuji_arabic(self):
        """
        Split consecutive Kansuji-Arabic numbers in the middle.
        """
        self._check(
            query="愛知県清須市助七１",
            level=6,
            fullname=["愛知県", "清須市", "助七", "一丁目"])

    def test_split_consecutive_numbers_kansuji_kansuji(self):
        """
        Split consecutive Kansuji numbers in the middle.
        """
        self._check(
            query="静岡県静岡市葵区与一四－１",
            level=7,
            fullname=["静岡県", "静岡市", "葵区", "与一", "四丁目", "1番"])

    def test_not_split_consecutive_numbers(self):
        """
        Do not split consecutive numbers in the middle..
        """
        self._check(
            query="札幌市中央区北一一西一三－１",
            level=7,
            fullname=["北海道", "札幌市", "中央区",
                      "北十一条", "西十三丁目", "1番"])

    def test_empty_aza(self):
        """
        Test parsing an address with an empty AZA name.
        """
        self._check(
            query="山形市大字十文字１",
            level=7,
            fullname=["山形県", "山形市", "大字十文字", "1番地"])

    def test_sen_in_aza(self):
        """
        Tests address notation includes non-numeric "千".
        """
        self._check(
            query="鳥取県米子市古豊千6",
            level=7,
            fullname=["鳥取県", "米子市", "古豊千", "6番地"])

    def test_man_in_aza(self):
        """
        Tests address notation includes non-numeric "万".
        """
        self._check(
            query="鳥取県米子市福万619",
            match="鳥取県米子市福万",
            level=5,
            fullname=["鳥取県", "米子市", "福万"])

    def test_kana_no_in_kana_string(self):
        """
        The "ノ" in address notations must not be treated as a hyphen.
        """
        #
        self._check(
            query="徳島県阿南市富岡町トノ町６５－６",
            match="徳島県阿南市富岡町トノ町６５－",
            fullname=["徳島県", "阿南市", "富岡町", "トノ町", "65番地"])

    def test_kana_no_in_non_kana_string(self):
        """
        The "ノ" between Kanji can be omitted.
        """
        self._check(
            query="埼玉県大里郡寄居町大字鷹巣",
            match="埼玉県大里郡寄居町大字鷹巣",
            fullname=[
                ["埼玉県", "大里郡", "寄居町", "大字鷹ノ巣"],
                ["埼玉県", "大里郡", "寄居町", "大字鷹巣"]]
        )

    def test_kana_no_between_numbers(self):
        """
        If "ノ" exists after numbers, check the next character of 'ノ'.
        The next character is a number, it will be treated as a hyphen.
        """
        self._check(
            query="新宿区西新宿二ノ８",
            level=7,
            fullname=["東京都", "新宿区", "西新宿", "二丁目", "8番"])

    def test_kana_no_after_numbers(self):
        """
        In case that the next character is;
        - a head character of chiban ('甲', 'イ', etc.),
          treat as a hyphen too
        - an other character, 'ノ' will be treated as is
        """
        self._check(
            query="群馬県伊勢崎市国定町２の甲１９９４",
            match="群馬県伊勢崎市国定町２の甲１９９４",
            fullname=["群馬県", "伊勢崎市", "国定町", "二丁目",
                      "甲", "1994番地"])

        self._check(
            query="千葉県袖ケ浦市久保田字一ノ山１５２３",
            match="千葉県袖ケ浦市久保田字一ノ山１５２３",
            fullname=["千葉県", "袖ケ浦市", "久保田", "1523番地"])

    def test_kana_no_terminate(self):
        """
        Check that Aza names ending in "ノ" match up to "ノ".
        """
        self._check(
            query="兵庫県宍粟市山崎町上ノ１５０２",
            match="兵庫県宍粟市山崎町上ノ",
            level=5,
            fullname=["兵庫県", "宍粟市", "山崎町上ノ"])

    def test_kana_no_aza(self):
        """
        Check that Aza names is "ノ".
        """
        self._check(
            query="石川県小松市軽海町ノ１４－１",
            match="石川県小松市軽海町ノ１４－",
            level=7)

        self._check(
            query="石川県小松市軽海町ノ－１４－１",
            match="石川県小松市軽海町ノ－１４－",
            level=7)

    def test_aza_aza(self):
        """
        Check that Aza names is "字".
        """
        self._check(
            query="香川県高松市林町字１４８",
            match="香川県高松市林町",
            level=5,
            fullname=["香川県", "高松市", "林町"])

    def test_kana_ke_terminate(self):
        """
        Check that Aza names ending in "ケ" will not match up to "ケ".
        """
        self._check(
            query="石川県羽咋市一ノ宮町ケ２８",
            match="石川県羽咋市一ノ宮町ケ",
            fullname=["石川県", "羽咋市", "一ノ宮町", "ケ"],
            level=6)

    def test_complement_cho(self):
        """
        Complement Oaza names if it lacks a "町", "村" or similar characters.
        """
        self._check(
            query="龍ケ崎市薄倉２３６４",
            level=7,
            fullname=["茨城県", "龍ケ崎市", "薄倉町", "2364番地"])

        self._check(
            query="宮城県仙台市太白区秋保湯元字寺田",
            fullname=["宮城県", "仙台市", "太白区", "秋保町湯元", "寺田"])

    def test_delete_cho(self):
        """
        Delete extra "町" in oaza names.
        """
        self._check(
            query="鹿児島県伊佐市菱刈町川北字古川２２６３",
            match="鹿児島県伊佐市菱刈町川北",
            fullname=["鹿児島県", "伊佐市", "菱刈川北"])

    def test_not_complement_cho(self):
        """
        Do not complete optional postfixes if the string does not end
        or is not followed by numbers or some characters, even if
        there are Oaza names that matches when these characters are completed.
        """
        self._check(
            query="熊本県球磨郡湯前町字上長尾",
            match="熊本県球磨郡湯前町")

    def test_no_optional_charcters_in_result(self):
        """
        Check that optional characters are not included in the match string.
        """
        self._check(
            query="富山市水橋開発字文化",
            match="富山市水橋開発",  # Not include '字'
            fullname=["富山県", "富山市", "水橋開発"])

        self._check(
            query="富山市水橋開発町",
            match="富山市水橋開発町",  # Not include '字'
            fullname=["富山県", "富山市", "水橋開発町"])

    def test_alphabet_gaiku(self):
        """
        Some gaiku contains alphabet characters.
        """
        top = self._check(
            query="大阪府大阪市中央区上町a-6")
        self.assertIn(
            top["fullname"],
            [["大阪府", "大阪市", "中央区", "上町", "A番"],
             ["大阪府", "大阪市", "中央区", "上町", "A番", "6号"]])

    def test_toori(self):
        """
        "通" in address notation sometimes expresses as "通り".
        """
        self._check(
            query="滝上町字滝上市街地１条通り",
            match="滝上町字滝上市街地１条通り",
            fullname=["北海道", "紋別郡", "滝上町", "字滝ノ上市街地一条通"])

    def test_jou_in_middle(self):
        """
        "条" in the middle of element names cannot be omitted.
        """
        self._check(
            query="愛知県春日井市上条町１",
            fullname=["愛知県", "春日井市", "上条町", "一丁目"])

        self._check(
            query="愛知県春日井市上町１",
            fullname=["愛知県", "春日井市", "上ノ町", "一丁目"])

    def test_ban_at_aza(self):
        """
        Test that Oaza terminates with "番" and be omitted in the query.
        """
        self._check(
            query="宮城県仙台市宮城野区福室字久保野２",
            fullname=["宮城県", "仙台市", "宮城野区", "福室", "久保野二番"])

    def test_bancho_at_aza(self):
        """
        Test that Oaza terminates with "番丁" or "番町",
        and be omitted in the query.
        """
        self._check(
            query="香川県綾歌郡宇多津町浜２の１２",
            fullname=["香川県", "綾歌郡", "宇多津町", "浜二番丁", "12番"])

        self._check(
            query="青森県十和田市東１６－４８",
            fullname=["青森県", "十和田市", "東十六番町", "48番"])

    def test_gou_at_oaza(self):
        """
        Test that Oaza terminates with "号" and be omitted in the query.
        """
        self._check(
            query="石川県白山市鹿島町１",
            fullname=["石川県", "白山市", "鹿島町", "一号"])

    def test_gou_at_aza(self):
        """
        Test that Aza terminates with "号" and be omitted in the query.
        """
        self._check(
            query="京都府南丹市園部町河原町４",
            fullname=["京都府", "南丹市", "園部町河原町", "四号"])

    def test_ku_at_aza(self):
        """
        Test that Aza terminates with "区" and be omitted in the query.
        """
        self._check(
            query="北海道北見市留辺蘂町温根湯温泉１",
            fullname=["北海道", "北見市", "留辺蘂町温根湯温泉", "一区"])

    def test_unnecessary_hyphen(self):
        """
        Testing for unnecessary "の" in the query string.
        """
        self._check(
            query="涌谷町涌谷八方谷１の16",
            fullname=["宮城県", "遠田郡", "涌谷町", "涌谷",
                      "八方谷一", "16番地"])

    def test_unnecessary_ku(self):
        """
        Testing for unnecessary "区" in the query string.
        """
        self._check(
            query="岩手県奥州市胆沢区小山",
            fullname=["岩手県", "奥州市", "胆沢小山"])

        self._check(
            query="青森県八戸市南郷区大字島守字赤羽６",
            fullname=[
                ["青森県", "八戸市", "南郷", "大字島守"],
                ["青森県", "八戸市", "南郷大字島守"]])

    def test_unnecessary_aza_name(self):
        """
        Testing for omitting Aza-names before Chiban.

        Omission of Aza-names are controled by 'aza_skip' option.
        The default value is 'auto'.
        """

        self._check(
            query="静岡県駿東郡小山町竹之下字上ノ原５５４",
            aza_skip='off',
            match="静岡県駿東郡小山町竹之下",
            fullname=["静岡県", "駿東郡", "小山町", "竹之下"])

        self._check(
            query="静岡県駿東郡小山町竹之下字上ノ原５５４",
            aza_skip='on',
            match="静岡県駿東郡小山町竹之下字上ノ原５５４",
            fullname=["静岡県", "駿東郡", "小山町", "竹之下", "554番地"]
        )

        # Aza-names contained in a node will be omitted
        # regardless of the option.
        self._check(
            query="千葉県八街市八街字七本松ろ９７－１",
            aza_skip='off',
            match="千葉県八街市八街字七本松ろ９７－",
            fullname=["千葉県", "八街市", "八街ろ", "97番地"])

        self._check(
            query="長野県千曲市礒部字下河原１１３７",
            aza_skip='off',
            match="長野県千曲市礒部",
            fullname=[
                ["長野県", "千曲市", "大字磯部"],
                ["長野県", "千曲市", "磯部"]])

        self._check(
            query="長野県千曲市礒部字下河原１１３７",
            match="長野県千曲市礒部字下河原１１３７",
            fullname=["長野県", "千曲市", "大字磯部", "1137番地"])

        # Case where "ハ" is included in Aza name to be omitted
        self._check(
            query="佐賀県嬉野市嬉野町大字下野字長波須ハ丙１２２４",
            aza_skip='off',
            match="佐賀県嬉野市嬉野町大字下野",
            fullname=["佐賀県", "嬉野市", "嬉野町", "大字下野"])

        self._check(
            query="佐賀県嬉野市嬉野町大字下野字長波須ハ丙１２２４",
            match="佐賀県嬉野市嬉野町大字下野字長波須ハ丙",
            fullname=["佐賀県", "嬉野市", "嬉野町", "大字下野", "丙"])

        # Case where "ロ" is included in Aza-name to be omitted
        # which is contained in a node.
        self._check(
            query="高知県安芸市赤野字シロケ谷尻甲２９９４",
            match="高知県安芸市赤野字シロケ谷尻甲",
            fullname=["高知県", "安芸市", "赤野甲"])

        # But do not omit Aza name which is match to the query.
        # If "鮫町骨沢" will be skipped, "青森県八戸市１"
        # can be resolved to "八戸市一番町"
        self._check(
            query="青森県八戸市鮫町骨沢１",
            fullname=["青森県", "八戸市", "大字鮫町", "骨沢", "1番地"])

        self._check(
            query="岩手県盛岡市東中野字立石８－１０",
            fullname=["岩手県", "盛岡市", "東中野", "立石", "8番地"])

        self._check(
            query="宮城県石巻市渡波字転石山１－６",
            fullname=["宮城県", "石巻市", "渡波", "転石山"])

        # If "字新得基線" will be skipped, "新得町１"
        # can be resolved to "字新得1番地"
        self._check(
            query="北海道上川郡新得町字新得基線１",
            match="北海道上川郡新得町字新得基線",
            fullname=[
                ["北海道", "上川郡", "新得町", "字新得", "基線"],
                ["北海道", "上川郡", "新得町", "字新得基線"]
            ])

        # Cases where the oaza-name directly under the city
        # needs to be skipped.
        self._check(
            query="高知県高岡郡佐川町字若枝甲４８５",
            match="高知県高岡郡佐川町字若枝甲４８５",
            fullname=["高知県", "高岡郡", "佐川町", "甲", "485番地"])

        # When enable_aza_skip option is set to True,
        # '十輪谷' will be omitted even it doesn't start with '字'
        self._check(
            query="広島県府中市鵜飼町十輪谷甲１２４－１",
            match="広島県府中市鵜飼町十輪谷甲１２４－",
            fullname=["広島県", "府中市", "鵜飼町", "甲", "124番地"])

    def test_not_omit_oaza(self):
        self._check(
            query="愛媛県松山市平林乙２－３",
            match="愛媛県松山市平林",
            fullname=["愛媛県", "松山市", "平林"])

        self._check(
            query="長野県長野市小島田町５２４",
            match="長野県長野市小島田町",
            fullname=["長野県", "長野市", "小島田町"])

        self._check(
            query="山形県酒田市京田２－１－１１",
            match="山形県酒田市京田２－１－",
            fullname=["山形県", "酒田市", "京田", "二丁目", "1番地"])

        self._check(
            query="宮城県仙台市青葉区芋沢字田尻６６",
            match="宮城県仙台市青葉区芋沢",
            fullname=["宮城県", "仙台市", "青葉区", "芋沢"])

        self._check(
            query="宮城県仙台市青葉区芋沢６６",
            match="宮城県仙台市青葉区芋沢６６",
            fullname=["宮城県", "仙台市", "青葉区", "芋沢", "66番地"])

    def test_mura_ooaza_koaza(self):
        """
        Test for an addresse containing Mura and Oaza in
        the Oaza field, and Aza in Koaza field.
        """
        self._check(
            query="脇町猪尻西上野61-1",
            fullname=["徳島県", "美馬市", "脇町", "大字猪尻",
                      "西上野", "61番地"])

    def test_not_repeat_omission(self):
        """
        Checks that omissions are not repeated.

        If optional characters in '中ノ町', which exists in '佐倉河',
        are omitted repeateadly, it would match '字中' in the query.
        """
        self._check(
            query="奥州市水沢区佐倉河字中半入川原１",
            match="奥州市水沢区佐倉河字中半入",
            fullname=["岩手県", "奥州市", "水沢佐倉河", "中半入"]
        )

        # '大字', '字', '小字' can be omitted if other optional
        # characters were omitted such as '町'
        self._check(
            query="鹿児島県霧島市霧島町大字永水４９６２",
            match="鹿児島県霧島市霧島町大字永水",
            fullname=["鹿児島県", "霧島市", "霧島永水"])

    def test_ommit_county(self):
        """
        Check that the search is possible even if the county name is omitted.
        """
        self._check(
            query="長野県小谷村大字中小谷丙１３１",
            match="長野県小谷村大字中小谷",
            fullname=["長野県", "北安曇郡", "小谷村", "大字中小谷"])

        self._check(
            query="長野県小谷村",
            match="長野県小谷村",
            fullname=["長野県", "北安曇郡", "小谷村"])

    def test_select_best(self):
        """
        Check that the best answer is returned for ambiguous queries.
        """
        # "佐賀県鹿島市納富分字藤津甲２" can be parsed as
        # - ["佐賀県", "鹿島市", "大字納富分", "藤津甲"] or
        # - ["佐賀県", "鹿島市", "大字納富分", "甲", "2番地"]
        self._check(
            query="佐賀県鹿島市納富分字藤津甲２",
            match="佐賀県鹿島市納富分字藤津甲",
            fullname=["佐賀県", "鹿島市", "大字納富分", "藤津甲"])

    def test_datsurakuchi(self):
        """
        """
        self._check(
            query="福島県いわき市平上高久塚田97乙",
            fullname=["福島県", "いわき市", "平上高久",
                      "塚田", "97番", "乙地"])


class TestSearchNodeMethods(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        jageocoder.init(mode="r")

    def _get_first_node(self, query: str) -> AddressNode:
        results = jageocoder.searchNode(query)
        return results[0].node

    def test_node_normal(self):
        node = self._get_first_node('多摩市落合１－１５－２')
        self.assertEqual(node.get_city_name(), '多摩市')
        self.assertEqual(node.get_city_jiscode(), '13224')
        self.assertEqual(node.get_city_local_authority_code(), '132241')
        self.assertEqual(node.get_pref_name(), '東京都')
        self.assertEqual(node.get_pref_jiscode(), '13')
        self.assertEqual(node.get_pref_local_authority_code(), '130001')
        self.assertEqual(node.get_postcode(), '2060033')

    def test_node_range(self):
        """
        Check the postcodes registered as a range.
        `札幌市中央区大通西（２０～２８丁目）`
        """
        node = self._get_first_node('札幌市中央区大通西２１－３−１８')
        self.assertEqual(node.get_city_name(), '中央区')
        self.assertEqual(node.get_city_jiscode(), '01101')
        self.assertEqual(node.get_city_local_authority_code(), '011011')
        self.assertEqual(node.get_pref_name(), '北海道')
        self.assertEqual(node.get_pref_jiscode(), '01')
        self.assertEqual(node.get_pref_local_authority_code(), '010006')
        self.assertEqual(node.get_postcode(), '0640820')

    def test_node_other(self):
        """
        Check the postcodes registered as others.
        `長野市 以下に掲載がない場合`
        """
        node = self._get_first_node('長野市大字長野箱清水1661−1')
        self.assertEqual(node.get_city_name(), '長野市')
        self.assertEqual(node.get_city_jiscode(), '20201')
        self.assertEqual(node.get_city_local_authority_code(), '202011')
        self.assertEqual(node.get_pref_name(), '長野県')
        self.assertEqual(node.get_pref_jiscode(), '20')
        self.assertEqual(node.get_pref_local_authority_code(), '200000')
        self.assertEqual(node.get_postcode(), '3810000')


if __name__ == "__main__":
    unittest.main()
