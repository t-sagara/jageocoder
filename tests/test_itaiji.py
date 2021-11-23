import unittest

from jageocoder.itaiji import converter


class TestItaijiMethods(unittest.TestCase):

    def _test_qa(self, q, a):
        r = converter.standardize(q)
        self.assertEqual(r, a)

    def test_number(self):
        # Numeric representations
        self._test_qa("１０１番地", "101.番地")
        self._test_qa("二十四号", "24.号")
        self._test_qa("あ二五四線", "あ254.線")

    def test_replace_no(self):
        # Replace 'の' between numeric characters
        self._test_qa("２の１", "2.-1.")

        # Omit 'の' between non-numeric characters
        self._test_qa("井の頭公園駅", "井頭公園駅")

    def test_ommit_ga(self):
        # Ommit 'ケヶガがツッつ' between Kanji characters
        self._test_qa("竜ヶ崎市", "竜崎市")

        # Not delete those characters between Kana characters
        self._test_qa("つつじが丘", "つつじが丘")

    def test_replace_old_new(self):
        # Replace old-complex Kanji characters to new-simple alternatives
        self._test_qa("龍崎市", "竜崎市")
        self._test_qa("籠原駅", "篭原駅")

    def test_match_len(self):
        # Compare strings without numeric characters
        r = converter.match_len(
            string='東京都多摩市落合',
            pattern='東京都多摩市落合')
        self.assertEqual(r, 8)

        # Compare strings containing numeric characters
        string = converter.standardize(
            '千代田区一ツ橋２-１', keep_numbers=True)
        r = converter.match_len(
            string=string,
            pattern='1000.代田区1.っ橋2.-1.')
        self.assertEqual(r, 10)

        # Compare strings containing numeric characters,
        # a complex case
        string = converter.standardize(
            '福島県浪江町高瀬丈六十に', keep_numbers=True)
        r = converter.match_len(
            string=string,
            pattern='福島県浪江町高瀬丈6.10.')
        self.assertEqual(r, 11)


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
