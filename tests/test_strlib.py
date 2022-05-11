import unittest

from jageocoder.strlib import strlib


class TestStrlibMethods(unittest.TestCase):

    def test_get_number(self):
        qa_list = [
            ['２-', 2],
            ['1234a', 1234],
            ['0015', 15],
            ['２４', 24],
            ['一三五', 135],
            ['二千四十五万円', 20450000],
            ['０線', 0],
        ]
        for qa in qa_list:
            r = strlib.get_number(qa[0])
            n = r['n']
            self.assertEqual(n, qa[1])


if __name__ == '__main__':
    unittest.main()
