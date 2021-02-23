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

        # Not replace 'の' between non-numeric characters
        self._test_qa("井の頭公園駅", "井の頭公園駅")

    def test_ommit_ga(self):
        # Ommit 'ケヶガがツッつ' between Kanji characters
        self._test_qa("竜ヶ崎市", "竜崎市")

        # Not delete those characters between Kana characters
        self._test_qa("つつじが丘", "つつじが丘")

    def test_replace_old_new(self):
        # Replace old-complex Kanji characters to new-simple alternatives
        self._test_qa("龍崎市", "竜崎市")
        self._test_qa("籠原駅", "篭原駅")
