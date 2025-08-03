from collections import OrderedDict
import re
from typing import Optional, Set

from jageocoder.node import AddressNode
from jageocoder.tree import AddressTree

from tqdm import tqdm


class ItaijiChecker(object):

    def __init__(self):
        self.tree = AddressTree()
        self.root = self.tree.get_root()
        self.counts = self.tree.count_records()

    def find_first_node(
        self,
        cands: Set[str]
    ) -> OrderedDict[str, Optional[AddressNode]]:
        """
        Find the first node that contains `cand` char in the name.
        """
        results: OrderedDict[str, AddressNode | None] = OrderedDict({})
        processed: Set[str] = set()
        for id in tqdm(range(self.root.id, self.counts)):
            node = self.tree.get_node_by_id(id)
            for cand in cands:
                if cand in node.name:
                    results[cand] = node
                    processed.add(cand)

            cands = cands - processed

        print(results)
        return results


def check_candidates(cands: str):
    checker = ItaijiChecker()
    cand_set = set()
    for cand in cands:
        if not re.match(r'\s', cand):
            cand_set.add(cand)

    nodes = checker.find_first_node(cand_set)
    for cand, node in nodes.items():
        if node is not None:
            print(f"Character '{cand}' is used in {node}")
        else:
            print(f"Character '{cand}' is not used in the database.")


if __name__ == "__main__":
    candidates = """
椙 杉
荆 荊
鑢 鑪
冝 宜
禱 祷
背 脊
簗 梁
誥 詰
薦 菰
狸 狢
茅 萱
閏 潤
炮 砲
椄 接
穏 隠
鑓 鎗
榑 槫
銫 鉋
㧡 核
"""
    check_candidates(candidates)


"""
Character '杉' is used in [168327:三杉町(140.2818603515625,42.24656295776367)5(aza_id:0047000/postcode:0493114)]
Character '萱' is used in [255914:萱野(141.8538055419922,43.20878219604492)5(aza_id:0015000/postcode:0682166)]
Character '背' is used in [893732:背負(143.51889038085938,42.74537658691406)5(aza_id:0011000/postcode:0895305)]
Character '梁' is used in [1448961:梁川町(140.74716186523438,41.7906494140625)5(aza_id:0164000/postcode:0400015)]
Character '狸' is used in [2219611:字狸沢(140.52984619140625,43.03388214111328)6()]
Character '茅' is used in [2225026:大字茅沼村(140.54339599609375,43.0836067199707)5(aza_id:0002000/postcode:0450202)]
Character '詰' is used in [2654348:字木詰(141.63467407226562,43.01667785644531)5(aza_id:0003000/postcode:0691329)]
Character '隠' is used in [8260156:恋隠(143.97300720214844,43.01420211791992)6(aza_id:0000140/postcode:0880353)]
Character '荊' is used in [10751975:字荊窪(999.9000244140625,999.9000244140625)6(aza_id:0014106/postcode:0340051)]
Character '簗' is used in [11016846:字簗田川原(999.9000244140625,999.9000244140625)6(aza_id:0002142/postcode:0390112)]
Character '鎗' is used in [11083395:字鎗水(999.9000244140625,999.9000244140625)6(aza_id:0135167/postcode:0391703)]
Character '砲' is used in [11897802:鉄砲平(141.56275939941406,40.52422332763672)6(aza_id:0000379)]
Character '菰' is used in [12002091:木造菰槌(140.31980895996094,40.855377197265625)5(aza_id:0034000/postcode:0383286)]
Character '宜' is used in [13419030:大字祢宜町(140.47621154785156,40.61209487915039)5(aza_id:0203000/postcode:0368056)]
Character '祷' is used in [14571634:祈祷沢(141.1217041015625,38.88593673706055)6(postcode:0210901)]
Character '潤' is used in [18286097:潤沢(141.0050048828125,39.19796371459961)6(aza_id:0003217/postcode:0294503)]
Character '鑓' is used in [18294767:鑓水(141.10964965820312,39.19343185424805)6(aza_id:0003417/postcode:0294503)]
Character '狢' is used in [20411808:字狢討(999.9000244140625,999.9000244140625)6(aza_id:0259146/postcode:9812402)]
Character '冝' is used in [20983243:字袮冝沢(999.9000244140625,999.9000244140625)6(aza_id:0137147/postcode:9896303)]
Character '炮' is used in [20983327:字鉄炮町(999.9000244140625,999.9000244140625)6(aza_id:0137146/postcode:9896303)]
Character '椙' is used in [21974859:北沢椙の沢(999.9000244140625,999.9000244140625)6(aza_id:1065420/postcode:9872304)]
Character '鉋' is used in [25153684:字鉋殻谷地(999.9000244140625,999.9000244140625)6(aza_id:0094324)]
Character '鑪' is used in [25853191:字鑪鞴ノ袋(999.9000244140625,999.9000244140625)6(aza_id:0006152/postcode:0182101)]
Character '接' is used in [31798874:接待(140.15081787109375,38.25236892700195)6(aza_id:0000128)]
Character '閏' is used in [33891546:字閏井谷地(999.9000244140625,999.9000244140625)6(aza_id:0063111/postcode:9691403)]
Character '薦' is used in [35239103:字薦槌越(999.9000244140625,999.9000244140625)6(aza_id:0015244/postcode:9691641)]
Character '榑' is used in [36437261:字榑木(999.9000244140625,999.9000244140625)6(aza_id:0009164/postcode:9791506)]
Character '核' is used in [39909333:字中核工業団地(999.9000244140625,999.9000244140625)6(aza_id:0002207/postcode:9690101)]
Character '穏' is used in [46083898:安穏台(140.30337524414062,35.92060470581055)6(aza_id:0000101)]
Character '誥' is used in [103647392:字非ノ誥(999.9000244140625,999.9000244140625)6(aza_id:0027274/postcode:9390715)]
Character '脊' is used in [104139003:字小脊(999.9000244140625,999.9000244140625)6(aza_id:0163104/postcode:9392508)]
Character '鑢' is used in [190056088:吉鑢(133.29513549804688,35.235862731933594)6(aza_id:0000116)]
"""
