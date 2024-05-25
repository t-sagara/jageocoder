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
        def kval(t: Tuple[int, int, int]) -> int:
            sval = sorted(t)
            return sval[0] * 10000 + sval[1] * 100 + sval[2]

        triangle = None
        for p0 in range(len(nodes) - 2):
            for p1 in range(p0 + 1, len(nodes) - 1):
                for p2 in range(p1 + 1, len(nodes)):
                    if cls.p_contained_triangle(
                        (x, y),
                        (nodes[p0].node.x, nodes[p0].node.y),
                        (nodes[p1].node.x, nodes[p1].node.y),
                        (nodes[p2].node.x, nodes[p2].node.y)
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
                (nodes[i].node.x, nodes[i].node.y),
                (nodes[triangle[0]].node.x, nodes[triangle[0]].node.y),
                (nodes[triangle[1]].node.x, nodes[triangle[1]].node.y),
                (nodes[triangle[2]].node.x, nodes[triangle[2]].node.y)
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
                        (nodes[tt[0]].node.x, nodes[tt[0]].node.y),
                        (nodes[tt[1]].node.x, nodes[tt[1]].node.y),
                        (nodes[tt[2]].node.x, nodes[tt[2]].node.y)
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

        logger.info("Building RTree for reverse geocoding...")
        id = AddressNode.ROOT_NODE_ID
        stack = []
        with tqdm(total=max_id, mininterval=0.5, ascii=True) as pbar:
            prev_id = 0
            next_sibling_id = max_id
            while id < max_id:
                pbar.update(id - prev_id)
                prev_id = id

                node = node_table.get_record(pos=id)
                if node.level <= AddressLevel.WARD:
                    id += 1
                    continue

                if node.level <= AddressLevel.AZA:
                    stack.append([
                        node.id, node.sibling_id,
                        set(), set(), set(), set()
                    ])
                    next_sibling_id = min(next_sibling_id, node.sibling_id)

                if not node.has_valid_coordinate_values():
                    node = node.add_dummy_coordinates()

                id += 1

                if node.has_valid_coordinate_values():
                    for i in range(len(stack) - 1, -1, -1):
                        r = stack[i]
                        r[2].add(node.x)
                        r[3].add(node.y)
                        r[4].add(node.x)
                        r[5].add(node.y)
                        if len(r[2]) > 100:
                            r[2] = {min(r[2]), }
                            r[3] = {min(r[3]), }
                            r[4] = {max(r[4]), }
                            r[5] = {max(r[5]), }

                if id >= next_sibling_id:
                    for i in range(len(stack) - 1, -1, -1):
                        r = stack[i]
                        if id >= r[1]:
                            if len(r[2]) > 0:
                                file_idx.insert(
                                    id=r[0],
                                    coordinates=(
                                        min(r[2]), min(r[3]),
                                        max(r[4]), max(r[5]),
                                    ),
                                )

                            del stack[i]

                    if len(stack) > 0:
                        next_sibling_id = min([r[1] for r in stack])
                    else:
                        next_sibling_id = max_id

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

        results = tuple(self.idx.intersection(
            (node.x, node.y, node.x, node.y)))
        return len(results) > 0 and node.id in results

    def _sort_by_dist(
        self,
        lon: float,
        lat: float,
        id_list: Iterable[int]
    ) -> List[NodeDist]:
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
        List[NodeDist]
            The sorted list of (distance, address node).
        """
        results = []
        for node_id in set(id_list):
            node = self._tree.get_node_by_id(node_id=node_id)
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

        def _remove_parent_nodes(
            candidates: Iterable[NodeDist]
        ) -> List[NodeDist]:
            ancestors = set()
            max_level = 0
            if len(candidates) == 0:
                return []

            nodes = []
            for v in candidates:
                dist, node = v.dist, v.node
                if node.id in ancestors:
                    continue

                if not node.has_valid_coordinate_values():
                    node = node.add_dummy_coordinates()

                nodes.append(NodeDist(dist, node))
                max_level = max(max_level, node.level)

                # List ancestor nodes of registering node.
                cur = node.parent
                while cur is not None:
                    # nodes = [node for node in nodes if node.id != cur.id]
                    ancestors.add(cur.id)
                    cur = cur.parent

            # Exclude ancestor nodes
            nodes = [node for node in nodes if node.node.id not in ancestors]
            return nodes

        def _get_k_nearest_child_nodes(
            aza_node_dists: List[NodeDist],
            *,
            candidates: Optional[List[NodeDist]] = None,
            node_map: Optional[dict] = None,
            k: Optional[int] = 20,
            min_k: Optional[int] = 0,
            max_dist: Optional[float] = 500.0,
        ) -> Tuple[List[NodeDist], dict]:
            candidates = candidates or []
            node_map = node_map or {}
            for v in aza_node_dists:
                dist, node = v.dist, v.node
                child_id = node.id + 1
                for child_id in range(node.id + 1, node.sibling_id):
                    child_node = self._tree.get_node_by_id(
                        node_id=child_id)
                    if child_node.level > level:
                        continue

                    if not child_node.has_valid_coordinate_values():
                        if child_node.level == level:
                            continue

                        child_node = child_node.add_dummy_coordinates()
                        if not child_node.has_valid_coordinate_values():
                            continue

                    key = (child_node.x, child_node.y)
                    if key in node_map:
                        # A node with the same coordinates are already registered
                        node_map[key].append(child_node)
                        continue

                    dist = self.distance(x, y, child_node.x, child_node.y)
                    i = len(candidates)
                    while i > 0:
                        if dist >= candidates[i - 1].dist:
                            break

                        i -= 1

                    if i < min_k or (i < k and dist <= max_dist):
                        candidates.insert(i, NodeDist(dist, child_node))
                        node_map[key] = [child_node]
                        n = len(candidates)
                        if n > k:
                            delnode = candidates[k].node
                            del node_map[(delnode.x, delnode.y)]
                            del candidates[k]
                        elif n > min_k and candidates[min_k].dist > max_dist:
                            delnode = candidates[min_k].node
                            del node_map[(delnode.x, delnode.y)]
                            del candidates[min_k]

            return (candidates, node_map)

        level = level or AddressLevel.AZA
        node_map = None
        if level <= AddressLevel.AZA:
            # Retrieve top k-nearest nodes using the R-tree index.
            nearests = self.idx.nearest((x, y, x, y), 20)
            node_dists = _remove_parent_nodes(
                self._sort_by_dist(x, y, nearests))

        else:
            # Retrieve all OAZA and AZA nodes containing the specified point.
            intersections = set(self.idx.intersection((x, y, x, y)))
            aza_node_dists = _remove_parent_nodes(
                self._sort_by_dist(x, y, intersections))
            if len(aza_node_dists) == 0:
                nearests = self.idx.nearest((x, y, x, y), 20)
                aza_node_dists = _remove_parent_nodes(
                    self._sort_by_dist(x, y, nearests))

            candidates, node_map = _get_k_nearest_child_nodes(
                aza_node_dists, min_k=1)

            # Retrieve OAZA and AZA nodes that do not contain the specified point
            # but are adjacent to it.
            edge_node = candidates[-1].node
            delta = ((x - edge_node.x) * (x - edge_node.x) +
                     (y - edge_node.y) * (y - edge_node.y)) ** 0.5
            borders = set(self.idx.intersection(
                (x - delta, y - delta, x + delta, y + delta))).difference(intersections)
            aza_node_dists = _remove_parent_nodes(
                self._sort_by_dist(x, y, borders))
            candidates, node_map = _get_k_nearest_child_nodes(
                aza_node_dists,
                candidates=candidates,
                node_map=node_map)

            node_dists = _remove_parent_nodes(candidates)

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

        # Restore nodes with the same coordinates
        if node_map is not None:
            _node_dists = []
            for v in node_dists:
                dist, node = v.dist, v.node
                key = (node.x, node.y)
                for n in node_map[key]:
                    _node_dists.append(NodeDist(dist, n))

            node_dists = _node_dists

        # Convert nodes to the dict format.
        results = []
        registered = set()
        for v in node_dists:
            dist, node = v.dist, v.node
            while node.level > level:
                node = node.parent
                dist = None

            if node.id in registered:
                continue

            if dist is None:
                dist = self.distance(x, y, node.x, node.y)

            results.append({
                "candidate": node.as_dict() if as_dict else node,
                "dist": dist
            })
            registered.add(node.id)

        # Sort by distance
        results = sorted(results, key=lambda r: r['dist'])

        return results
