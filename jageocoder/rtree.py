from logging import getLogger
import os
from typing import Iterable, List, Optional

from geographiclib.geodesic import Geodesic
from rtree import index
from rtree.exceptions import RTreeError
from tqdm import tqdm

from jageocoder.tree import AddressTree
from jageocoder.address import AddressLevel
from jageocoder.node import AddressNode, AddressNodeTable

logger = getLogger(__name__)


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
        with tqdm(total=max_id, mininterval=0.5) as pbar:
            prev_id = 0
            while id < max_id:
                pbar.update(id - prev_id)
                prev_id = id

                node = node_table.get_record(pos=id)
                if node.level > AddressLevel.AZA:
                    id = node.sibling_id
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
        node_by_level = {}
        for node in self._sort_by_dist(x, y, self.idx.nearest((x, y, x, y), 10)):
            if node.level not in node_by_level:
                node_by_level[node.level] = [node]
            else:
                node_by_level[node.level].append(node)

        # Select 3-nearest points to the target from the highest level.
        max_level = max(node_by_level.keys())
        nodes = node_by_level[max_level][0:3]

        if level > max_level:
            # Search points in the higher levels
            local_idx = index.Rtree()  # Create local rtree on memory
            for node in nodes:
                for child_id in range(node.id + 1, node.sibling_id):
                    child_node = self._tree.get_address_node(id=child_id)
                    local_idx.insert(
                        id=child_node.id,
                        coordinates=(
                            child_node.x, child_node.y,
                            child_node.x, child_node.y))

            # Select 3-nearest points using the local rtree
            nodes = []
            ancestors = set()
            for node in self._sort_by_dist(
                    x, y, local_idx.nearest((x, y, x, y), 10)):
                if node.id in ancestors:
                    continue

                nodes.append(node)
                if len(nodes) == 3:
                    break

                # Ancestor nodes of registering node are excluded.
                cur = node.parent
                while cur is not None:
                    ancestors.add(cur.id)
                    cur = cur.parent

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

        return results
