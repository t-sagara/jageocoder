from abc import ABC
from logging import getLogger
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from geographiclib.geodesic import Geodesic
from rtree import index
from rtree.exceptions import RTreeError
from tqdm import tqdm

from jageocoder.local_tree import LocalTree
from jageocoder.address import AddressLevel
from jageocoder.node import AddressNode, AddressNodeTable

logger = getLogger(__name__)


class NodeDist(object):

    def __init__(self, dist: float, node: AddressNode) -> None:
        self.dist = dist
        self.node = node

    def __repr__(self) -> str:
        return f"NodeDist({self.dist}, {self.node})"


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
        nodes: List[NodeDist]
    ) -> List[NodeDist]:
        """
        Select the 3 nodes that make the smallest triangle
        surrounding the target point.

        Parameters
        ----------
        x: float
            The longitude of the target point.
        y: float
            The latitude of the target point.
        nodes: List[NodeDist]
            The candidate list of (distance, node).

        Returns
        -------
        List[NodeDist]
            Up to 3 nodes surrounding the target point
            and their distance.
        """
        def kval(t0: int, t1: int, t2: int) -> int:
            """
            Generate hash key for the triangle
            """
            sval = sorted((t0, t1, t2))
            return sval[0] * 10000 + sval[1] * 100 + sval[2]

        def side(
                ab: Tuple[float, float], ap: Tuple[float, float]) -> float:
            """
            Get the outer product of vector ab and vector ap.
            """
            return ab[0] * ap[1] - ab[1] * ap[0]

        triangle_candidate: Optional[Tuple[int, int, int]] = None
        p0, p1 = 0, 1
        a = nodes[p0].node
        ap = (x - a.x, y - a.y)

        # Find point b that does not fall on the line between p(x, y) and a.
        for p1 in range(1, len(nodes) - 2):
            b = nodes[p1].node
            ab = (b.x - a.x, b.y - a.y)
            side_p = side(ab, ap)

            if abs(side_p) > 1.0e-10:
                break

        else:
            b = None

        # Find q where triangle abq surrounds point p.
        if b is not None:
            for p2 in range(p1 + 1, len(nodes)):
                q = nodes[p2].node
                aq = (q.x - a.x, q.y - a.y)
                side_q = side(ab, aq)
                if side_p * side_q < 0.0 or \
                        (side_p < 0 and side_q > side_p) or \
                        (side_p > 0 and side_q < side_p):
                    continue

                if cls.p_contained_triangle(
                    (x, y),
                    (a.x, a.y),
                    (b.x, b.y),
                    (q.x, q.y)
                ):
                    triangle_candidate = (p0, p1, p2)
                    break

            else:
                triangle_candidate = None

        if triangle_candidate is None:
            # If the triangle containing the target cannot
            # be constructed, the two nearest points are returned.
            return nodes[:2]

        triangle: Tuple[int, int, int] = triangle_candidate

        i = 0
        processed_triangles = set({kval(*triangle), })
        while i < len(nodes):
            if i in triangle:
                i += 1
                continue

            if cls.p_contained_circumcircle(
                (nodes[i].node.x, nodes[i].node.y),
                (nodes[triangle[0]].node.x, nodes[triangle[0]].node.y),
                (nodes[triangle[1]].node.x, nodes[triangle[1]].node.y),
                (nodes[triangle[2]].node.x, nodes[triangle[2]].node.y)
            ):
                new_triangle = None
                for j in range(3):
                    tt = [x for x in triangle]
                    tt[j] = i
                    k = kval(*tt)
                    if k in processed_triangles:
                        continue

                    if cls.p_contained_triangle(
                        (x, y),
                        (nodes[tt[0]].node.x, nodes[tt[0]].node.y),
                        (nodes[tt[1]].node.x, nodes[tt[1]].node.y),
                        (nodes[tt[2]].node.x, nodes[tt[2]].node.y)
                    ):
                        new_triangle = (tt[0], tt[1], tt[2])
                        break

                if new_triangle:
                    triangle = new_triangle
                    processed_triangles.add(kval(*triangle))
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

    geod = Geodesic.WGS84  # type: ignore

    def __init__(self, tree: LocalTree):
        self._tree = tree
        self.idx = None

        treepath = Path(tree.db_dir) / "rtree"
        dat_path = Path(tree.db_dir) / "rtree.dat"
        idx_path = Path(tree.db_dir) / "rtree.idx"
        if dat_path.exists() and idx_path.exists():
            try:
                self.idx = self.load_rtree(treepath)
                if self.test_rtree() is False:
                    logger.warning((
                        "RTree datafile exists but it does not match "
                        "the registered address data."
                    ))
                    dat_path.unlink()
                    idx_path.unlink()
                    self.idx = None

            except RTreeError as e:
                logger.warning("Can't load the RTree datafile.({})".format(e))
                dat_path.unlink()
                idx_path.unlink()
                self.idx = None

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

    def create_rtree(self, treepath: Path) -> index.Rtree:
        """
        Create RTree from the nodes in the address tree.

        Parameters
        ----------
        treepath: Path
            The base filename of the rtree data files.
            RTree data files consist of ".dat" and ".idx".

        Returns
        -------
        index.Rtree
            Created rtree index.
        """
        file_idx = index.Rtree(str(treepath))  # Filename must be passed as str
        node_table: AddressNodeTable = self._tree.address_nodes

        max_id = node_table.count_records()
        registered_coordinates = set()

        logger.info("Building RTree for reverse geocoding...")
        id = AddressNode.ROOT_NODE_ID
        with tqdm(total=max_id, mininterval=0.5, ascii=True) as pbar:
            prev_id = 0
            while id < max_id:
                pbar.update(id - prev_id)
                prev_id = id

                node = node_table.get_record(pos=id)
                if node.level <= AddressLevel.WARD:
                    registered_coordinates.clear()
                    id += 1
                    continue

                if node.sibling_id == node.id + 1:
                    # The node has no child nodes

                    if not node.has_valid_coordinate_values():
                        id += 1
                        continue

                    key = (node.x, node.y)
                    if key in registered_coordinates:
                        id += 1
                        continue

                    file_idx.insert(
                        id=id,
                        coordinates=(node.x, node.y, node.x, node.y),
                    )
                    registered_coordinates.add(key)
                    id += 1
                    continue

                # The node has 1 or more child nodes
                if node.level == AddressLevel.BLOCK:
                    # Get BDR of child nodes
                    bdr = None
                    for child_id in range(node.id + 1, node.sibling_id):
                        child_node = node_table.get_record(child_id)
                        if not child_node.has_valid_coordinate_values():
                            continue

                        if bdr is None:
                            bdr = (child_node.x, child_node.y,
                                   child_node.x, child_node.y)
                        else:
                            bdr = (
                                min(child_node.x, bdr[0]),
                                min(child_node.y, bdr[1]),
                                max(child_node.x, bdr[2]),
                                max(child_node.y, bdr[3]),
                            )

                    if bdr:
                        file_idx.insert(
                            id=id,
                            coordinates=bdr,
                        )
                    else:
                        # All child nodes have invalid coordinate values
                        key = (node.x, node.y)
                        if node.has_valid_coordinate_values() and \
                                key not in registered_coordinates:
                            file_idx.insert(
                                id=id,
                                coordinates=(node.x, node.y, node.x, node.y),
                            )
                            registered_coordinates.add(key)

                    id = node.sibling_id
                    continue

                id += 1

        return file_idx

    def load_rtree(self, treepath: Path) -> index.Rtree:
        """
        Load RTree from the data files.

        Parameters
        ----------
        treepath: Path
            The base path to the rtree data files.

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
        if self.idx is None:
            return False

        center_id: int = self._tree.address_nodes.count_records() // 2
        node = self._tree.get_node_by_id(node_id=center_id)
        while True:
            while node.level < AddressLevel.BLOCK:
                node = self._tree.get_node_by_id(node_id=node.id + 1)

            while node.level > AddressLevel.BLOCK:
                node = node.parent
                if node is None:
                    return False

            if node.has_valid_coordinate_values():
                break

            node = self._tree.get_node_by_id(node_id=node.sibling_id)

        results = tuple(self.idx.nearest(
            (node.x, node.y, node.x, node.y), 1, objects=True))
        if len(results) == 0:
            return False

        item = results[0]
        target_node = self._tree.get_node_by_id(node_id=item.id)
        target_bbox = item.bbox
        res = target_node.x >= target_bbox[0] \
            and target_node.y >= target_bbox[1] \
            and target_node.x <= target_bbox[2] \
            and target_node.y <= target_bbox[3]

        return res

    def _sort_by_dist(
        self,
        lon: float,
        lat: float,
        nodes: Iterable[AddressNode],
    ) -> List[NodeDist]:
        """
        Sort nodes by real(projected) distance from the target point.

        Paramters
        ---------
        lon: float
            The longitude of the target point.
        lat: float
            The latitude of the target point.
        nodes: Iterable[AddressNode]
            The list of candidate node.

        Returns
        -------
        List[NodeDist]
            The sorted list of (distance, address node).
        """
        results = []
        for node in nodes:
            if not node.has_valid_coordinate_values():
                continue

            dist = self.distance(node.x, node.y, lon, lat)
            results.append(NodeDist(dist, node))

        results.sort(key=lambda x: x.dist)
        return results

    def nearest(
        self,
        x: float,
        y: float,
        level: Optional[int] = None,
        as_dict: Optional[bool] = True,
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
        as_dict: bool, default=True
            If False is specified, the addressNode object is stored
            in the "candidate" field.

        Returns
        -------
        [{"candidate":AddressNode or dict, "dist":float}]
            Returns the results of retrieval up to 3 nodes.
        """
        if self.idx is None:
            raise RTreeError("R-Tree is not created.")

        level = level or AddressLevel.AZA

        # Retrieve top k-nearest nodes using the R-tree index.
        # If the node registered in the index is an intermediate node,
        # expand its leaf nodes.
        candidates = []
        nearests = self.idx.nearest((x, y, x, y), 20, objects=True)
        for item in nearests:
            node = self._tree.get_node_by_id(item.id)
            if item.bbox[0] == item.bbox[2] and item.bbox[1] == item.bbox[3]:
                candidates.append(node)
            else:
                for child_id in range(node.id + 1, node.sibling_id):
                    child_node = self._tree.get_node_by_id(child_id)
                    if child_node.sibling_id == child_id + 1 and \
                            child_node.has_valid_coordinate_values():
                        candidates.append(child_node)

        node_dists = self._sort_by_dist(x, y, candidates)

        # Select the 3 nodes that make the smallest triangle
        # surrounding the target point
        if len(node_dists) == 0:
            return []

        if len(node_dists) <= 3 or node_dists[0].dist < 1.0e-02:
            # If the distance between the nearest point and the search point is
            # less than 1 cm, it returns three points in order of distance.
            # This is because the nearest point may not be included in
            # the search results due to a calculation error.
            node_dists = node_dists[0:3]
        else:
            node_dists = DelaunayTriangle.select(x, y, node_dists)

        # Convert nodes to the dict format.
        results = []
        registered = set()
        for v in node_dists:
            dist, node = v.dist, v.node
            while node.level > level:
                node = node.parent
                if node is None:
                    raise RTreeError("R-Tree index is broken.")

            if node.id in registered:
                continue

            results.append({
                "candidate": node.as_dict() if as_dict else node,
                "dist": dist
            })
            registered.add(node.id)

        return results
