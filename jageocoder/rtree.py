import os
from typing import Iterable, Optional

from geographiclib.geodesic import Geodesic
from rtree import index
from tqdm import tqdm

from jageocoder.tree import AddressTree
from jageocoder.address import AddressLevel
from jageocoder.node import AddressNode, AddressNodeTable


class Index(object):

    geod = Geodesic.WGS84

    def __init__(self, tree: AddressTree):
        self._tree = tree

        treepath = os.path.join(tree.db_dir, "rtree")
        if os.path.exists(treepath + ".dat") and os.path.exists(treepath + ".idx"):
            self.idx = self.load_rtree(treepath)
        else:
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

    def create_rtree(self, treepath: os.PathLike):
        node_table: AddressNodeTable = self._tree.address_nodes
        file_idx = index.Rtree(str(treepath))
        max_id = node_table.count_records()
        id = AddressNode.ROOT_NODE_ID

        nrecords = node_table.count_records()
        with tqdm(total=nrecords, mininterval=0.5) as pbar:
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

    def load_rtree(self, treepath: os.PathLike):
        file_idx = index.Rtree(str(treepath))
        return file_idx

    def _sort_by_dist(
                self,
                lon: float,
                lat: float,
                id_list: Iterable[int]
            ) -> list:
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
                level: Optional[int] = AddressLevel.AZA
            ):
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
