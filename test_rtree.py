import datetime
from pathlib import Path

from rtree import index
from tqdm import tqdm

import jageocoder
from jageocoder.address import AddressLevel
from jageocoder.node import AddressNodeTable

jageocoder.init()


def create_rtree(datafile: Path):
    node_table: AddressNodeTable = jageocoder.get_module_tree().address_nodes
    dd = 0.0001
    file_idx = index.Rtree(str(datafile))
    for node in tqdm(
            iterable=node_table.retrieve_records(),
            total=node_table.count_records(),
            mininterval=0.5):
        if node.level > AddressLevel.AZA:
            continue

        file_idx.insert(
            id=node.id,
            coordinates=[node.x - dd, node.y - dd, node.x + dd, node.y + dd]
        )

    return file_idx


def load_rtree(datafile: Path):
    file_idx = index.Rtree(str(datafile))
    return file_idx


if __name__ == "__main__":
    start_at = datetime.datetime.now()
    datafile = Path(__file__).parent / "rtree"
    if (datafile.parent / "rtree.dat").exists():
        idx = load_rtree(datafile)
    else:
        idx = create_rtree(datafile)

    x, y = 139.92953491210938, 37.49776077270508
    # dd = 0.001
    # print("Intersection:")
    # for node_id in idx.intersection((x - dd, y - dd, x + dd, y + dd)):
    #     node = jageocoder.get_module_tree().get_address_node(id=node_id)
    #     print(node.__repr__())

    # print("Nearest:")

    node_by_level = {}
    for node_id in idx.nearest((x, y, x, y), 10):
        node = jageocoder.get_module_tree().get_address_node(id=node_id)
        if node.level not in node_by_level:
            node_by_level[node.level] = [node]
        else:
            node_by_level[node.level].append(node)

    max_level = max(node_by_level.keys())
    nodes = node_by_level[max_level][0:3]

    local_idx = index.Rtree()
    for node in nodes:
        for child_id in range(node.id + 1, node.sibling_id):
            child_node = jageocoder.get_module_tree().get_address_node(id=child_id)
            local_idx.insert(
                id=child_node.id,
                coordinates=[child_node.x, child_node.y, child_node.x, child_node.y]
            )

    node_by_level = {}
    for node_id in local_idx.nearest((x, y, x, y), 10):
        node = jageocoder.get_module_tree().get_address_node(id=node_id)
        if node.level not in node_by_level:
            node_by_level[node.level] = [node]
        else:
            node_by_level[node.level].append(node)

    max_level = max(node_by_level.keys())
    nodes = node_by_level[max_level][0:3]
    for node in nodes:
        print(node.get_fullname())

    print(datetime.datetime.now() - start_at)