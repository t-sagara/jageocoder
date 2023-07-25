from abc import ABC
from logging import getLogger
import os
from typing import Iterable, List, Optional, Tuple

from geographiclib.geodesic import Geodesic
from rtree import index
from rtree.exceptions import RTreeError
from tqdm import tqdm

from jageocoder.tree import AddressTree
from jageocoder.address import AddressLevel
from jageocoder.node import AddressNode, AddressNodeTable

logger = getLogger(__name__)


class DelaunayTriangle(ABC):

    @classmethod
    def p_contained_triangle(
        cls,
        p: Tuple[float, float],
        p0: Tuple[float, float],
        p1: Tuple[float, float],
        p2: Tuple[float, float]
    ) -> bool:
        """
        Determine if the point p is inside the triangle (p0, p1, p2).

        Parameters
        ----------
        p: (float, float)
            x and y coordinates of point p.
        p0, p1, p2: (float, float)
            x and y coordinates of vertices p0, p1, p2 of the triangle.

        Return
        ------
        bool
            If the point p is inside the triangle, return True.
        """
        area = (-p1[1] * p2[0] + p0[1] * (-p1[0] + p2[0]) +
                p0[0] * (p1[1] - p2[1]) + p1[0] * p2[1])
        s = (p0[1] * p2[0] - p0[0] * p2[1] + (p2[1] - p0[1])
             * p[0] + (p0[0] - p2[0]) * p[1])
        t = (p0[0] * p1[1] - p0[1] * p1[0] + (p0[1] - p1[1])
             * p[0] + (p1[0] - p0[0]) * p[1])

        if area < 0.0:
            area = -area
            s = -s
            t = -t

        if 0 < s < area and 0 < t < area and 0 < area - s - t < area:
            return True

        return False

    @classmethod
    def get_circumcircle(
        cls,
        p0: Tuple[float, float],
        p1: Tuple[float, float],
        p2: Tuple[float, float]
    ) -> Tuple[float, float, float]:
        """
        Calculate the coordinates and radius of the circumcircle
        of the triangle (p0, p1, p2).

        Parameters
        ----------
        p0, p1, p2: (float, float)
            x and y coordinates of vertices p0, p1, p2 of the triangle.

        Return
        ------
        (float, float, float)
            x,y coordinates of the circumcenter, and
            the square of the radius.
        """
        xt = (p2[1] - p0[1]) * (p1[0] * p1[0] - p0[0] * p0[0] +
                                p1[1] * p1[1] - p0[1] * p0[1]) + \
            (p0[1] - p1[1]) * (p2[0] * p2[0] - p0[0] * p0[0] +
                               p2[1] * p2[1] - p0[1] * p0[1])
        yt = (p0[0] - p2[0]) * (p1[0] * p1[0] - p0[0] * p0[0] +
                                p1[1] * p1[1] - p0[1] * p0[1]) + \
            (p1[0] - p0[0]) * (p2[0] * p2[0] - p0[0] * p0[0] +
                               p2[1] * p2[1] - p0[1] * p0[1])
        c = 2 * ((p1[0] - p0[0]) * (p2[1] - p0[1]) -
                 (p1[1] - p0[1]) * (p2[0] - p0[0]))

        x = xt / c
        y = yt / c
        r2 = (x - p0[0]) * (x - p0[0]) + (y - p0[1]) * (y - p0[1])
        return (x, y, r2)

    @classmethod
    def p_contained_circumcircle(
        cls,
        p: Tuple[float, float],
        p0: Tuple[float, float],
        p1: Tuple[float, float],
        p2: Tuple[float, float]
    ) -> bool:
        """
        Determine if the point p is inside the circumcircle of
        triangle (p0, p1, p2).

        Parameters
        ----------
        p: (float, float)
            x and y coordinates of point p.
        p0, p1, p2: (float, float)
            x and y coordinates of vertices p0, p1, p2 of the triangle.

        Return
        ------
        bool
            If the point p is inside the circumcircle, return True.
        """
        cx, cy, r2 = cls.get_circumcircle(p0, p1, p2)
        pr2 = (p[0] - cx) * (p[0] - cx) + (p[1] - cy) * (p[1] - cy)
        if pr2 < r2:
            return True

        return False

    @classmethod
    def select(
        cls,
        x: float,
        y: float,
        nodes: List[AddressNode]
    ) -> List[AddressNode]:
        """
        Select the 3 nodes that make the smallest triangle
        surrounding the target point.

        Parameters
        ----------
        x: float
            The longitude of the target point.
        y: float
            The latitude of the target point.
        nodes: List[AddressNode]
            The candidate nodes.

        Returns
        -------
        List[AddressNode]
            Up to 3 nodes surrounding the target point.
        """
        def kval(t: Tuple[int, int, int]) -> int:
            sval = sorted(t)
            return sval[0] * 10000 + sval[1] * 100 + sval[2]

        triangle = None
        for p0 in range(len(nodes) - 2):
            for p1 in range(p0 + 1, len(nodes) - 1):
                for p2 in range(p1 + 1, len(nodes)):
                    if cls.p_contained_triangle(
                        (x, y),
                        (nodes[p0].x, nodes[p0].y),
                        (nodes[p1].x, nodes[p1].y),
                        (nodes[p2].x, nodes[p2].y)
                    ):
                        triangle = [p0, p1, p2]
                        break

                if triangle is not None:
                    break

            if triangle is not None:
                break

        if triangle is None:
            # If the triangle containing the target cannot
            # be constructed, the two nearest points are returned.
            return nodes[:2]

        i = 0
        processed_triangles = set({kval(triangle), })
        while i < len(nodes):
            if i in triangle:
                i += 1
                continue

            if cls.p_contained_circumcircle(
                (nodes[i].x, nodes[i].y),
                (nodes[triangle[0]].x, nodes[triangle[0]].y),
                (nodes[triangle[1]].x, nodes[triangle[1]].y),
                (nodes[triangle[2]].x, nodes[triangle[2]].y)
            ):
                new_triangle = None
                for j in range(3):
                    tt = triangle[:]
                    tt[j] = i
                    k = kval(tt)
                    if k in processed_triangles:
                        continue

                    if cls.p_contained_triangle(
                        (x, y),
                        (nodes[tt[0]].x, nodes[tt[0]].y),
                        (nodes[tt[1]].x, nodes[tt[1]].y),
                        (nodes[tt[2]].x, nodes[tt[2]].y)
                    ):
                        new_triangle = tt
                        break

                if new_triangle:
                    triangle = new_triangle
                    processed_triangles.add(kval(triangle))
                    i = 0
                    continue

            i += 1

        return [nodes[i] for i in triangle]


class Index(object):
    """
    The RTree index class for reverse geocoding.

    Parameters
    ----------
    tree: AddressTree
        The address tree to build rtree.

    Attributes
    ----------
    idx: rtree.index
        The rtree index class.
    geod: geographiclib.geodesic.Geodesic
        The WGS84 geodecis instance for calculating distances between
        2 points represented by (lon, lat).
    """

    geod = Geodesic.WGS84

    def __init__(self, tree: AddressTree):
        self._tree = tree
        self.idx = None

        treepath = os.path.join(tree.db_dir, "rtree")
        if os.path.exists(treepath + ".dat") and \
                os.path.exists(treepath + ".idx"):
            try:
                self.idx = self.load_rtree(treepath)
                if self.test_rtree() is False:
                    logger.warning((
                        "RTree datafile exists but it does not match "
                        "the registered address data."
                    ))
                    os.unlink(treepath + ".dat")
                    os.unlink(treepath + ".idx")
                    self.idx = None

            except RTreeError as e:
                logger.warning("Can't load the RTree datafile.({})".format(e))
                os.unlink(treepath + ".dat")
                os.unlink(treepath + ".idx")

        if self.idx is None:
            self.idx = self.create_rtree(treepath)

    def distance(
        self,
        lon0: float, lat0: float,
        lon1: float, lat1: float
    ) -> float:
        """
        Calculates the geodesic distance between two points (p0, p1)
        given in longitude and latitude.

        Parameters
        ----------
        lon0, lat0: float
            Longitude and latitude of the point p0.
        lon1, lat1: float
            Longitude and latitude of the point p1.

        Return
        ------
        float
            The geodesic distance, in meter.
        """
        g = self.geod.Inverse(lat0, lon0, lat1, lon1)
        return g['s12']

    def create_rtree(self, treepath: os.PathLike) -> index.Rtree:
        """
        Create RTree from the nodes in the address tree.

        Parameters
        ----------
        treepath: os.PathLike
            The base filename of the rtree data files.
            RTree data files consist of ".dat" and ".idx".

        Returns
        -------
        index.Rtree
            Created rtree index.
        """
        file_idx = index.Rtree(str(treepath))
        node_table: AddressNodeTable = self._tree.address_nodes

        max_id = node_table.count_records()
        id = AddressNode.ROOT_NODE_ID
        with tqdm(total=max_id, mininterval=0.5, ascii=True) as pbar:
            prev_id = 0
            while id < max_id:
                pbar.update(id - prev_id)
                prev_id = id

                node = node_table.get_record(pos=id)
                if node.level > AddressLevel.AZA:
                    id = node.sibling_id
                    continue
                elif node.level < AddressLevel.OAZA:
                    id += 1
                    continue

                file_idx.insert(
                    id=id,
                    coordinates=(node.x, node.y, node.x, node.y)
                )
                id += 1

        return file_idx

    def load_rtree(self, treepath: os.PathLike) -> index.Rtree:
        """
        Load RTree from the data files.

        Parameters
        ----------
        treepath: os.PathLike
            The base filename of the rtree data files.

        Returns
        -------
        index.Rtree
            Loaded rtree index.
        """
        file_idx = index.Rtree(str(treepath))
        return file_idx

    def test_rtree(self) -> bool:
        """
        Test the created/loaded Rtree index.

        Returns
        -------
        bool
            If the index passes the test, return True.
            Otherwise return False.
        """
        node_table = self._tree.address_nodes
        node = node_table.get_record(pos=node_table.count_records() // 2)
        while node.level < AddressLevel.OAZA:
            node = node_table.get_record(pos=node.id + 1)

        while node.level > AddressLevel.AZA:
            node = node.parent

        return node.id in self.idx.nearest((node.x, node.y, node.x, node.y), 2)

    def _sort_by_dist(
        self,
        lon: float,
        lat: float,
        id_list: Iterable[int]
    ) -> List[AddressNode]:
        """
        Sort nodes by real(projected) distance from the target point.

        Paramters
        ---------
        lon: float
            The longitude of the target point.
        lat: float
            The latitude of the target point.
        id_list: Iterable[int]
            The list of node-id.

        Returns
        -------
        List[AddressNode]
            The sorted list of address nodes.
        """
        results = []
        for node_id in id_list:
            node = self._tree.get_address_node(id=node_id)
            dist = self.distance(node.x, node.y, lon, lat)
            results.append((node, dist))

        results.sort(key=lambda x: x[1])
        return [x[0] for x in results]

    def nearest(
        self,
        x: float,
        y: float,
        level: Optional[int] = None
    ):
        """
        Search nearest nodes of the target point.

        Parameters
        ----------
        x: float
            The longitude of the target point.
        y: float
            The latitude of the target point.
        level: int, optional
            The level of the address ndoes to be retrieved as a result.
            If omitted, search down to the AZA level.

        Returns
        -------
        [{"candidate":AddressNode, "dist":float}]
            Returns the results of retrieval up to 3 nodes.
        """
        level = level or AddressLevel.AZA

        # Search nodes by Rtree Index
        nodes = []
        ancestors = set()
        max_level = 0
        for node in self._sort_by_dist(
                x, y, self.idx.nearest((x, y, x, y), 10)):
            if node.id in ancestors:
                continue

            nodes.append(node)
            max_level = max(max_level, node.level)
            # Ancestor nodes of registering node are excluded.
            cur = node.parent
            while cur is not None:
                nodes = [node for node in nodes if node.id != cur.id]
                ancestors.add(cur.id)
                cur = cur.parent

        if level > max_level:
            # Search points in the higher levels
            local_idx = index.Rtree()  # Create local rtree on memory
            for node in nodes:
                child_id = node.id
                while child_id < node.sibling_id:
                    child_node = self._tree.get_address_node(id=child_id)
                    if child_node.level > level:
                        child_id = child_node.parent.sibling_id
                        continue

                    local_idx.insert(
                        id=child_id,
                        coordinates=(
                            child_node.x, child_node.y,
                            child_node.x, child_node.y))
                    child_id += 1

            nodes = []
            ancestors = set()
            for node in self._sort_by_dist(
                    x, y, local_idx.nearest((x, y, x, y), 20)):
                if node.id in ancestors:
                    continue

                nodes.append(node)
                # Ancestor nodes of registering node are excluded.
                cur = node.parent
                while cur is not None:
                    nodes = [node for node in nodes if node.id != cur.id]
                    ancestors.add(cur.id)
                    cur = cur.parent

        # Select the 3 nodes that make the smallest triangle
        # surrounding the target point
        nodes = DelaunayTriangle.select(x, y, nodes)

        # Convert nodes to the dict format.
        results = []
        registered = set()
        for node in nodes:
            while node.level > level:
                node = node.parent

            if node.id in registered:
                continue

            results.append({
                "candidate": node.as_dict(),
                "dist": self.distance(x, y, node.x, node.y)
            })
            registered.add(node.id)

        # Sort by distance
        results = sorted(results, key=lambda r: r['dist'])

        return results
