import logging
import unittest

import jageocoder
from jageocoder.address import AddressLevel
from jageocoder.node import AddressNode

logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO)


class TestReverseMethods(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        jageocoder.init(mode="r")

    def test_aza_level(self):
        """
        Test reverse lookup of an address from coordinates in general conditions.
        """
        results = jageocoder.reverse(x=139.428969, y=35.625779)
        candidate_names = [x['candidate']['fullname'] for x in results]

        self.assertTrue(len(candidate_names) > 0)
        self.assertEqual(candidate_names[0], ["東京都", "多摩市", "落合", "一丁目"])
        # self.assertEqual(candidate_names[1], ["東京都", "多摩市", "愛宕", "四丁目"])
        # self.assertEqual(candidate_names[2], ["東京都", "多摩市", "豊ケ丘", "一丁目"])

    def test_endless_pattern(self):
        results = jageocoder.reverse(
            y=35.689472, x=139.69175, level=7, as_dict=False
        )
        nearest_node = results[0]["candidate"]
        self.assertTrue(isinstance(nearest_node, jageocoder.node.AddressNode))
        self.assertEqual(nearest_node.dataset["title"], "街区レベル位置参照情報")

    def test_block_level(self):
        """
        Test reverse lookup of an address from coordinates in general conditions
        at Block level.
        """
        results = jageocoder.reverse(
            x=139.428969, y=35.625779, level=AddressLevel.BLOCK)
        candidate_names = [x['candidate']['fullname'] for x in results]

        self.assertEqual(len(candidate_names), 3)
        self.assertTrue(
            ["東京都", "多摩市", "落合", "一丁目", "15番地"] in candidate_names
        )

    def test_edge_case(self):
        """
        Test for the case where the specified coordinates are at the edge of
        the land and cannot form a Delaunay triangle.
        """
        results = jageocoder.reverse(
            y=35.720882, x=140.869360, level=AddressLevel.AZA)
        candidate_names = [x['candidate']['fullname'] for x in results]
        self.assertTrue(len(candidate_names) > 0)
        self.assertEqual(
            ["千葉県", "銚子市", "海鹿島町"], candidate_names[0]
        )
        # self.assertEqual(
        #     ["千葉県", "銚子市", "君ケ浜"], candidate_names[1]
        # )

    def test_edge_block_level(self):
        """
        Test for the case where the specified coordinates are at the edge of
        the land and cannot form a Delaunay triangle and lookup at Block level.
        """
        results = jageocoder.reverse(
            y=35.720882, x=140.869360, level=AddressLevel.BLOCK)
        candidate_names = [x['candidate']['fullname'] for x in results]
        self.assertTrue(len(candidate_names) >= 2)
        self.assertTrue(
            ["千葉県", "銚子市", "海鹿島町", "5244番地"] in candidate_names
        )
        self.assertTrue(
            ["千葉県", "銚子市", "海鹿島町", "5254番地"] in candidate_names
        )

    def test_island(self):
        """
        Test for the case where there are not a sufficient number of
        address nodes around, such as on an island.
        """
        results = jageocoder.reverse(x=142.155764, y=26.660128)
        candidate_names = [x['candidate']['fullname'] for x in results]
        self.assertTrue(len(candidate_names) >= 1)
        self.assertTrue(
            candidate_names[0][-1] in ("母島", "字西浦", "西浦")
        )

    def test_hachijo(self):
        """
        Test for the case where there are not a sufficient number of
        address nodes around, such as on an island.
        """
        results = jageocoder.reverse(
            x=139.79204562036716, y=33.113018869587904)  # 町立八丈病院
        candidate_names = [x['candidate']['fullname'] for x in results]
        self.assertTrue(len(candidate_names) > 0)
        self.assertIn(
            candidate_names[0], (
                ["東京都", "八丈町", "三根"],
                ["東京都", "八丈町", "中道"]),
        )

    def test_skip_index_no_lat_lon(self):
        """

        Test for the case where not include rtree index data
        without latitude and longitude.
        """
        results = jageocoder.reverse(
            x=136.901476, y=36.98889, level=6, as_dict=False)
        for result in results:
            candidate: AddressNode = result["candidate"]
            if not candidate.has_valid_coordinate_values():
                candidate = candidate.add_dummy_coordinates()

            self.assertTrue(candidate.has_valid_coordinate_values())

    def test_noname_oaza(self):
        results = jageocoder.reverse(
            x=140.182312, y=35.9114227, level=8, as_dict=False)
        candidate: AddressNode = results[0]["candidate"]
        self.assertEqual(candidate.name, "3710番地")

        results = jageocoder.reverse(
            x=140.188034, y=35.9068260, level=8, as_dict=False)
        candidate: AddressNode = results[0]["candidate"]
        self.assertEqual(candidate.name, "4235番地")

    def test_kyoto_cityhall(self) -> None:
        results = jageocoder.reverse(
            x=135.768188, y=35.0115738, level=8)
        candidate = results[0]["candidate"]
        self.assertEqual(candidate["name"], "488番地")

    def test_kyoto_edgecase(self) -> None:
        results = jageocoder.reverse(
            x=135.7586754, y=35.0203540, level=8, as_dict=False)
        candidate = results[0]["candidate"]
        self.assertEqual(candidate.get_city_name(), "上京区")

    def test_remove_edaban(self) -> None:
        results = jageocoder.reverse(
            x=139.4287109375, y=35.6257438659668, level=8
        )
