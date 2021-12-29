from logging import getLogger
import math
from typing import List, NoReturn, Optional, Union

from geographiclib.geodesic import Geodesic

from jageocoder.address import AddressLevel
from jageocoder.node import AddressNode
from jageocoder.tree import AddressTree

logger = getLogger(__name__)


def p_contained(
        p: [float, float], p0: [float, float],
        p1: [float, float], p2: [float, float]) -> bool:
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


def get_circumcircle(
        p0: [float, float], p1: [float, float],
        p2: [float, float]) -> [float, float, float]:
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
    return [x, y, r2]


def p_contained_circumcircle(
        p: [float, float], p0: [float, float],
        p1: [float, float], p2: [float, float]) -> bool:
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
    cx, cy, r2 = get_circumcircle(p0, p1, p2)
    pr2 = (p[0] - cx) * (p[0] - cx) + (p[1] - cy) * (p[1] - cy)
    if pr2 < r2:
        return True

    return False


class ReverseCandidate(object):

    def __init__(self, node: AddressNode, dist: Optional[float] = None):
        self.node = node
        self.dist = dist

    def get_node(self) -> AddressNode:
        return self.node

    def get_dist(self) -> Union[float, None]:
        return self.dist

    def set_dist(self, dist: float) -> NoReturn:
        self.dist = dist


class Reverse(object):
    """
    Class for reverse geocoding.

    Attributes
    ----------
    tablename: str
        The table name for reverse lookup of address-node IDs
        at Oaza and Aza levels from spatial area.
    geod: geographiclib.geodesic.Geodesic
        The geodesic class ( WGS84).

    Note
    ----
    This class is not extended sqlalchemy.ext.declarative.
    Therefore, database operations are performed by calling SQL directly.
    """

    tablename = 'node_aza'
    geod = Geodesic.WGS84

    def __init__(self, x: float, y: float,
                 tree: AddressTree, max_level: Optional[int] = None):
        """
        Initialize.

        Attributes
        ----------
        x, y: float
            The x(lon) and y(lat) coordinates of the target point.
        tree: AddressTree
            A tree containing address nodes.
        max_level: int
            Maximum level of the address node to be retrieved.
        candidates: [ReverseCandidate]
            A list of candidate address nodes and their distances
            from the target location.
        triangle: [AddressNode]
            List of address nodes that compose the Delaunay triangle.
        mbr: dict
            The minimum boundary rectangle that contains the circumcircle
            of the triangle.
        """
        self.x = x
        self.y = y
        self.tree = tree
        self.max_level = max_level or AddressLevel.AZA
        self.candidates = []
        self.triangle = None
        self.mbr = None

    def clear(self):
        """
        Clear the stack of Address Candidates.
        """
        self.candidates.clear()
        self.triangle = None
        self.mbr = None

    def is_in_circumcircle(self, node: AddressNode) -> bool:

        if self.mbr:
            if node.x < self.mbr['minx'] or node.x > self.mbr['maxx'] or\
                    node.y < self.mbr['miny'] or node.y > self.mbr['maxy']:
                return False

        if self.triangle:
            contained = p_contained_circumcircle(
                [node.x, node.y],
                [self.triangle[0].x, self.triangle[0].y],
                [self.triangle[1].x, self.triangle[1].y],
                [self.triangle[2].x, self.triangle[2].y])

            return contained

        return False

    def update_mbr(self) -> NoReturn:
        x, y, r2 = get_circumcircle(
            [self.triangle[0].x, self.triangle[0].y],
            [self.triangle[1].x, self.triangle[1].y],
            [self.triangle[2].x, self.triangle[2].y])

        r = math.sqrt(r2)

        self.mbr = {
            "minx": x - r,
            "miny": y - r,
            "maxx": x + r,
            "maxy": y + r,
        }

    def add_candidate(self, cand: ReverseCandidate) -> bool:
        """
        Add an address candidate and sequentially calculate
        the Delaunay triangle that encloses the target point (x, y).

        Parameters
        ----------
        node: AddressNode
            A candidate address node.

        Return
        ------
        bool
            Returns True if the added address node can be a correct answer
            at the time it is added.

        Note
        ----
        Candidate nodes are accumulated in the stack
        `self.candidates` until a triangle containing the target point is found.
        Once a triangle is found, update the triangle with each additional node.

        The vertices of the Delaunay triangle are stored in `self.triangle`
        """
        node = cand.get_node()
        if self.triangle is None:
            msg = "Calling add_candidate, node={}, triangle=None"
            logger.debug(msg.format(
                ''.join(node.get_fullname())))
        else:
            logger.debug("Calling add_candidate, node={}, triangle={}".format(
                ''.join(node.get_fullname()),
                [''.join(self.triangle[0].get_fullname()),
                 ''.join(self.triangle[1].get_fullname()),
                 ''.join(self.triangle[2].get_fullname())]))

        if self.triangle:
            if node in self.triangle:
                logger.debug("The node is a vertice of the triangle.")
                return False

            contained = self.is_in_circumcircle(node)
            if not contained:
                logger.debug("The node is outside the triangle.")
                return False

            if p_contained(
                [self.x, self.y],
                [node.x, node.y],
                [self.triangle[1].x, self.triangle[1].y],
                    [self.triangle[2].x, self.triangle[2].y]):
                self.triangle[0] = node
            elif p_contained(
                [self.x, self.y],
                [node.x, node.y],
                [self.triangle[0].x, self.triangle[0].y],
                    [self.triangle[2].x, self.triangle[2].y]):
                self.triangle[1] = node
            else:
                self.triangle[2] = node

            self.update_mbr()
            logger.debug(("This node is inside the triangle and "
                          "has updated the triangle."))
            return True

        if len(self.candidates) >= 2:
            for i0 in range(0, len(self.candidates) - 1):
                for i1 in range(i0 + 1, len(self.candidates)):
                    p0 = self.candidates[i0].get_node()
                    p1 = self.candidates[i1].get_node()
                    if p_contained([self.x, self.y], [node.x, node.y],
                                   [p0.x, p0.y], [p1.x, p1.y]):
                        self.triangle = [node, p0, p1]
                        logger.debug(
                            "The triangle has been composed by this node.")
                        for cand in self.candidates:
                            self.add_candidate(cand)

                        # Use the triangle after this.
                        del self.candidates
                        return True

        self.candidates.append(cand)
        logger.debug(("The triangle could not be composed, "
                      "so the node added to the list."))
        return True

    def add_candidate_by_distance(self, cand: ReverseCandidate) -> bool:
        """
        Add an address candidate and select top-k nearest neighbors.

        Parameters
        ----------
        node: AddressNode
            A candidate address node.

        Return
        ------
        bool
            Returns True if the added address node can be a correct answer
            at the time it is added.

        Note
        ----
        Candidate nodes are accumulated in the stack `self.candidates`.
        """
        dist = cand.get_dist()
        i = len(self.candidates)
        while i > 0:
            if dist > self.candidates[i - 1].get_dist():
                break

            i -= 1

        self.candidates.insert(i, cand)
        self.candidates = self.candidates[0:3]
        return True

    def add_candidate_recursively(
            self,
            seed_node: AddressNode,
            max_level: Optional[int] = None) -> bool:
        """
        Add one address node as a candidate, and add its child nodes recursively.
        This method call `add_candidate()` which calls `add_candidate()`
        to compose Delaunay triangle.

        Parameters
        ----------
        seed_node: AddressNode
            A candidate address node.
        max_level: int, optional
            Maximum address level for address nodes to be added recursively.

        Note
        ----
        This method call `add_candidate()` which calls `add_candidate()`
        to compose Delaunay triangle.
        """
        max_level = max_level or self.max_level
        if seed_node.level > max_level:
            return False

        children = seed_node.children
        added_children = 0
        for child in children:
            if self.add_candidate_recursively(child, max_level):
                added_children += 1

        if added_children == 0:
            if not self.add_candidate(
                    ReverseCandidate(seed_node)):
                return False

        return True

    def add_candidate_recursively_simple(
            self,
            seed_node: AddressNode,
            max_level: Optional[int] = None) -> bool:
        """
        Add one address node as a candidate, and add its child nodes recursively.

        Parameters
        ----------
        seed_node: AddressNode
            A candidate address node.
        max_level: int, optional
            Maximum address level for address nodes to be added recursively.

        Note
        ----
        This method simply add a node to the stack.
        """
        max_level = max_level or self.max_level
        if seed_node.level > max_level:
            return False

        children = seed_node.children
        added_children = 0
        for child in children:
            if self.add_candidate_recursively_simple(child, max_level):
                added_children += 1

        if added_children == 0:
            cand = ReverseCandidate(
                seed_node,
                self.distance(seed_node.x, seed_node.y, self.x, self.y))

            if not self.add_candidate_by_distance(cand):
                return False

        return True

    def search_rough(self) -> List[int]:
        """
        Roughly search for the IDs of address nodes above Aza-level
        in the coordinate range.

        Return
        ------
        [int]
            List of node IDs.
        """
        results = []
        dy = 0.01
        dx = 0.01 / math.cos(self.y * math.pi / 180.0)
        while len(results) < 10 and dy < 0.1:
            results = []
            sql = ("SELECT id FROM node_aza"
                   " WHERE x >= :minx AND x <= :maxx"
                   " AND y >= :miny AND y <= :maxy"
                   " ORDER BY level ASC")
            res = self.tree.session.execute(
                sql,
                {"minx": self.x-dx, "maxx": self.x+dx,
                 "miny": self.y-dy, "maxy": self.y+dy})

            for row in res:
                results.append(row[0])

            dy *= 1.5
            dy *= 1.5

        return results

    def searchNode(self) -> list:
        """
        Search address nodes near the target point.
        """
        seeds = self.search_rough()

        for seed in seeds:
            node = self.tree.get_node_by_id(seed)
            self.add_candidate_recursively(
                node, max_level=AddressLevel.AZA)

        if self.max_level > AddressLevel.AZA:
            if self.triangle:
                for seed in seeds:
                    node = self.tree.get_node_by_id(seed)
                    self.add_candidate_recursively(node)

            else:
                self.clear()
                for seed in seeds:
                    node = self.tree.get_node_by_id(seed)
                    self.add_candidate_recursively_simple(node)

        results = []
        if self.triangle:
            for node in self.triangle:
                cand = ReverseCandidate(
                    node, self.distance(
                        self.x, self.y, node.x, node.y))
                results.append(cand)
        else:
            for cand in self.candidates:
                if cand.get_dist() is None:
                    node = cand.get_node()
                    dist = self.distance(
                        self.x, self.y,
                        node.x, node.y)
                    cand.set_dist(dist)

                results.append(cand)

        results.sort(key=lambda cand: cand.get_dist())
        return results[0:3]

    def search(self) -> list:
        """
        Search address nodes near the target point,
        and return as dict representations.
        """
        candidates = self.searchNode()
        results = []
        for cand in candidates:
            results.append({
                "candidate": cand.get_node().as_dict(),
                "dist": cand.get_dist()
            })

        return results

    def distance(self, lon0: float, lat0: float,
                 lon1: float, lat1: float) -> float:
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


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG)
    p = [1.0, 1.0]
    p1 = [0.0, 0.0]
    p2 = [0.0, 2.0]
    p3 = [2.0, 1.0]
    print(p_contained(p, p1, p2, p3))  # True
    print(p_contained(p2, p, p1, p2))  # False
    print(p_contained(p1, p, p1, p3))  # False

    print(get_circumcircle([0, 0], [63, 0], [15, 20]))
