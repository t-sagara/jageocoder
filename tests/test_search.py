import logging
import unittest

import jageocoder

logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO)


class TestSearchMethods(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        jageocoder.init(mode='r')

    def test_jukyo(self):
        """
        Test for addresses followed by other strings.
        """
        query = "多摩市落合1-15多摩センタートーセイビル"
        result = jageocoder.search(query)
        self.assertEqual(result['matched'], '多摩市落合1-15')
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        top = candidates[0]
        self.assertEqual(top['level'], 7)
        self.assertEqual(
            top['fullname'],
            ['東京都', '多摩市', '落合', '一丁目', '15番地'])

    def test_sapporo(self):
        """
        Test a notation which is omitting '条' in Sapporo city.
        """
        query = '札幌市中央区北3西1-7'
        result = jageocoder.search(query)
        self.assertEqual(result['matched'], '札幌市中央区北3西1-7')
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        top = candidates[0]
        self.assertEqual(top['level'], 7)
        self.assertEqual(
            top['fullname'],
            ['北海道', '札幌市', '中央区', '北三条', '西一丁目', '7番地'])

    def test_mie(self):
        """
        Test for an address beginning with a number.
        """
        query = '三重県津市広明町13番地'
        result = jageocoder.search(query)
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        top = candidates[0]
        self.assertEqual(
            top['fullname'],
            ['三重県', '津市', '広明町', '13番地'])

    def test_akita(self):
        query = '秋田市山王4-1-1'
        result = jageocoder.search(query)
        self.assertEqual(result['matched'], '秋田市山王4-1-')
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        top = candidates[0]
        self.assertEqual(top['level'], 7)
        self.assertEqual(top['fullname'],
                         ['秋田県', '秋田市', '山王', '四丁目', '1番'])

    def test_kyoto(self):
        """
        Test a notation which is containing street name in Kyoto city.
        """
        query = '京都市上京区下立売通新町西入薮ノ内町'
        result = jageocoder.search(query)
        self.assertEqual(result['matched'], '京都市上京区下立売通新町西入薮ノ内町')
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        top = candidates[0]
        self.assertEqual(top['level'], 5)
        self.assertEqual(top['fullname'],
                         ['京都府', '京都市', '上京区', '藪之内町'])

    def test_oaza(self):
        """
        Test notations with and without "大字"
        """
        query = '東京都西多摩郡瑞穂町大字箱根ケ崎2335番地'
        result = jageocoder.search(query)
        self.assertEqual(result['matched'], '東京都西多摩郡瑞穂町大字箱根ケ崎2335番地')
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        top = candidates[0]
        self.assertEqual(top['level'], 7)
        self.assertIn(top['fullname'],
                      [['東京都', '西多摩郡', '瑞穂町', '箱根ケ崎', '2335番地'],
                       ['東京都', '西多摩郡', '瑞穂町', '大字箱根ケ崎', '2335番地']])

        query = '東京都西多摩郡瑞穂町箱根ケ崎2335番地'
        result = jageocoder.search(query)
        self.assertEqual(result['matched'], '東京都西多摩郡瑞穂町箱根ケ崎2335番地')
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        top = candidates[0]
        self.assertEqual(top['level'], 7)
        self.assertIn(top['fullname'],
                      [['東京都', '西多摩郡', '瑞穂町', '箱根ケ崎', '2335番地'],
                       ['東京都', '西多摩郡', '瑞穂町', '大字箱根ケ崎', '2335番地']])

    def test_oaza_not_in_dictionary(self):
        """
        Test notation with "大字" which is not included in the dictionary.
        """
        query = '大分県宇佐市安心院町大字古川字長坂'
        result = jageocoder.search(query)
        self.assertEqual(result['matched'], '大分県宇佐市安心院町大字古川')
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        top = candidates[0]
        self.assertEqual(top['fullname'],
                         ['大分県', '宇佐市', '安心院町古川'])

    def test_split_consecutive_numbers_kansuji_arabic(self):
        """
        Split consecutive Kansuji-Arabic numbers in the middle.
        """
        query = '愛知県清須市助七１'
        result = jageocoder.search(query)
        self.assertEqual(result['matched'], '愛知県清須市助七１')
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        top = candidates[0]
        self.assertEqual(top['level'], 6)
        self.assertEqual(top['fullname'],
                         ['愛知県', '清須市', '助七', '一丁目'])

    def test_split_consecutive_numbers_kansuji_kansuji(self):
        """
        Split consecutive Kansuji numbers in the middle.
        """
        query = '静岡県静岡市葵区与一四－１'
        result = jageocoder.search(query)
        self.assertEqual(result['matched'], '静岡県静岡市葵区与一四－１')
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        top = candidates[0]
        self.assertEqual(top['level'], 7)
        self.assertEqual(top['fullname'],
                         ['静岡県', '静岡市', '葵区', '与一', '四丁目', '1番'])

    def test_not_split_consecutive_numbers(self):
        """
        Do not split consecutive numbers in the middle..
        """
        query = '札幌市中央区北一一西一三－１'
        result = jageocoder.search(query)
        self.assertEqual(result['matched'], '札幌市中央区北一一西一三－１')
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        top = candidates[0]
        self.assertEqual(top['level'], 7)
        self.assertEqual(
            top['fullname'],
            ['北海道', '札幌市', '中央区', '北十一条', '西十三丁目', '1番'])

    def test_empty_aza(self):
        """
        Test parsing an address with an empty AZA name.
        """
        query = '山形市大字十文字１'
        result = jageocoder.search(query)
        self.assertEqual(result['matched'], '山形市大字十文字１')
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        top = candidates[0]
        self.assertEqual(top['level'], 7)
        self.assertEqual(
            top['fullname'],
            ['山形県', '山形市', '大字十文字', '1番地'])

    def test_sen_in_aza(self):
        query = '鳥取県米子市古豊千6'
        result = jageocoder.search(query)
        self.assertEqual(result['matched'], '鳥取県米子市古豊千6')
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        top = candidates[0]
        self.assertEqual(top['level'], 7)
        self.assertEqual(
            top['fullname'],
            ['鳥取県', '米子市', '古豊千', '6番地'])

    def test_man_in_aza(self):
        query = '鳥取県米子市福万619'
        result = jageocoder.search(query)
        self.assertEqual(result['matched'], '鳥取県米子市福万')
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        top = candidates[0]
        self.assertEqual(top['level'], 5)
        self.assertEqual(
            top['fullname'],
            ['鳥取県', '米子市', '福万'])

    def test_kana_no_in_kana_string(self):
        """
        The "ノ" in address notations must not be treated as a hyphen.
        """
        query = '徳島県阿南市富岡町トノ町６５－６'
        result = jageocoder.search(query)
        self.assertEqual(result['matched'], '徳島県阿南市富岡町トノ町６５－')
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        top = candidates[0]
        self.assertEqual(top['level'], 7)
        self.assertIn(top['fullname'],
                      [['徳島県', '阿南市', '富岡町', 'トノ町', '65番地']])

    def test_kana_no_in_non_kana_string(self):
        """
        The "ノ" between Kanji can be omitted.
        """
        query = '埼玉県大里郡寄居町大字鷹巣'
        result = jageocoder.search(query)
        self.assertEqual(result['matched'], '埼玉県大里郡寄居町大字鷹巣')
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        top = candidates[0]
        self.assertEqual(top['level'], 5)
        self.assertEqual(top['fullname'],
                         ['埼玉県', '大里郡', '寄居町', '鷹ノ巣'])

    def test_kana_no_between_numbers(self):
        """
        The "ノ" between numbers will be treated as a hyphen.
        """
        query = '新宿区西新宿二ノ８'
        result = jageocoder.search(query)
        self.assertEqual(result['matched'], '新宿区西新宿二ノ８')
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        top = candidates[0]
        self.assertEqual(top['level'], 7)
        self.assertEqual(top['fullname'],
                         ['東京都', '新宿区', '西新宿', '二丁目', '8番'])

    def test_kana_no_terminate(self):
        """
        Check that Aza names ending in "ノ" match up to "ノ".
        """
        query = '兵庫県宍粟市山崎町上ノ１５０２'
        result = jageocoder.search(query)
        self.assertEqual(result['matched'], '兵庫県宍粟市山崎町上ノ')
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        top = candidates[0]
        self.assertEqual(top['level'], 5)

    def test_kana_no_aza(self):
        """
        Check that Aza names is "ノ".
        """
        query = '石川県小松市軽海町ノ１４－１'
        result = jageocoder.search(query)
        self.assertEqual(result['matched'], '石川県小松市軽海町ノ１４－')
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        top = candidates[0]
        self.assertEqual(top['level'], 7)

        query = '石川県小松市軽海町ノ－１４－１'
        result = jageocoder.search(query)
        self.assertEqual(result['matched'], '石川県小松市軽海町ノ－１４－')
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        top = candidates[0]
        self.assertEqual(top['level'], 7)

    def test_kana_ke_terminate(self):
        """
        Check that Aza names ending in "ケ" will not match up to "ケ".
        """
        query = '石川県羽咋市一ノ宮町ケ２８'
        result = jageocoder.search(query)
        self.assertEqual(result['matched'], '石川県羽咋市一ノ宮町')
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        top = candidates[0]
        self.assertEqual(top['level'], 5)

    def test_complement_cho(self):
        """
        Complement Oaza names if it lacks a '町', '村' or similar characters.
        """
        query = '龍ケ崎市薄倉２３６４'
        result = jageocoder.search(query)
        self.assertEqual(result['matched'], '龍ケ崎市薄倉２３６４')
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        top = candidates[0]
        self.assertEqual(top['level'], 7)
        self.assertEqual(top['fullname'],
                         ['茨城県', '龍ケ崎市', '薄倉町', '2364番地'])

    def test_not_complement_cho(self):
        """
        Do not complete optional postfixes if the string does not end
        or is not followed by numbers or some characters, even if
        there are Oaza names that matches when these characters are completed.
        """
        query = '熊本県球磨郡湯前町字上長尾'
        result = jageocoder.search(query)
        self.assertEqual(result['matched'], '熊本県球磨郡湯前町')
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        top = candidates[0]
        self.assertEqual(top['level'], 3)
        self.assertEqual(top['fullname'],
                         ['熊本県', '球磨郡', '湯前町'])

    def test_alphabet_gaiku(self):
        """
        Some gaiku contains alphabet characters.
        """
        query = '大阪府大阪市中央区上町a-6'
        result = jageocoder.search(query)
        self.assertIn(result['matched'],
                      ['大阪府大阪市中央区上町a-', '大阪府大阪市中央区上町a-6'])
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        top = candidates[0]
        self.assertIn(top['level'], [7, 8])
        self.assertIn(
            top['fullname'],
            [['大阪府', '大阪市', '中央区', '上町', 'A番'],
             ['大阪府', '大阪市', '中央区', '上町', 'A番', '6号']])

    def test_toori(self):
        """
        '通' in address notation sometimes expresses as '通り'.
        """
        query = '滝上町字滝上市街地１条通り'
        result = jageocoder.search(query)
        self.assertEqual(result['matched'], '滝上町字滝上市街地１条通り')
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        top = candidates[0]
        self.assertEqual(top['level'], 5)
        self.assertEqual(top['fullname'],
                         ['北海道', '紋別郡', '滝上町', '字滝ノ上市街地一条通'])

    def test_jou_in_middle(self):
        """
        '条' in the middle of element names cannot be omitted.
        """
        query = '愛知県春日井市上条町１'
        result = jageocoder.search(query)
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        self.assertEqual(
            candidates[0]['fullname'],
            ['愛知県', '春日井市', '上条町', '一丁目'])

        query = '愛知県春日井市上町１'
        result = jageocoder.search(query)
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        self.assertEqual(
            candidates[0]['fullname'],
            ['愛知県', '春日井市', '上ノ町', '一丁目'])

    def test_ban_at_aza(self):
        query = '宮城県仙台市宮城野区福室字久保野２'
        result = jageocoder.search(query)
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        self.assertEqual(
            candidates[0]['fullname'],
            ['宮城県', '仙台市', '宮城野区', '福室', '久保野二番'])

    def test_gou_at_oaza(self):
        query = '石川県白山市鹿島町１'
        result = jageocoder.search(query)
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        self.assertEqual(
            candidates[0]['fullname'],
            ['石川県', '白山市', '鹿島町', '一号'])

    def test_gou_at_aza(self):
        query = '京都府南丹市園部町河原町４'
        result = jageocoder.search(query)
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        self.assertEqual(
            candidates[0]['fullname'],
            ['京都府', '南丹市', '園部町河原町', '四号'])

    def test_ku_at_aza(self):
        query = '北海道北見市留辺蘂町温根湯温泉１'
        result = jageocoder.search(query)
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        self.assertEqual(
            candidates[0]['fullname'],
            ['北海道', '北見市', '留辺蘂町温根湯温泉', '一区'])

    def test_unnecessary_hyphen(self):
        query = '涌谷町涌谷八方谷１の16'
        result = jageocoder.search(query)
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        self.assertEqual(
            candidates[0]['fullname'],
            ['宮城県', '遠田郡', '涌谷町', '涌谷', '八方谷一', '16番地'])


if __name__ == '__main__':
    unittest.main()
