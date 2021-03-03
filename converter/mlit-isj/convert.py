import csv
import io
import json
import os
import re
import sys
import zipfile

import jaconv

from jageocoder.itaiji import converter as itaiji_converter


class Node(object):

    def __init__(self, name, x, y, level, flag=False):
        self.name = name
        self.x = x
        self.y = y
        self.level = level
        self.children = None
        self.flag = flag

    def addChild(self, node):
        if self.children is None:
            self.children = {}

        if node.name not in self.children:
            self.children[node.name] = node
            curnode = node
        elif self.children[node.name].flag and not node.flag:
            self.children[node.name] = node
            curnode = self.children[node.name]
        else:
            curnode = self.children[node.name]

        return curnode

    def printTree(self, fp, upper=None):
        names = []
        if upper is not None and upper != '':
            names.append(upper)

        if self.name:
            names.append(self.name)

        if len(names) > 0:
            for name in names:
                if not isinstance(name, str):
                    print(names, file=sys.stderr)
                    import pdb
                    pdb.set_trace()

        new_upper = ','.join(names)
        if self.level is not None:
            line = "{},{},{},{}".format(
                new_upper, self.x, self.y, self.level)
            print(line, file=fp)

        if self.children:
            for name, child in self.children.items():
                child.printTree(fp, new_upper)


class IsjConverter(object):
    """
    街区レベル位置参照情報のコンバータ
    """

    seirei = [
        "札幌市", "仙台市", "さいたま市", "千葉市", "横浜市",
        "川崎市", "相模原市", "新潟市", "静岡市", "浜松市",
        "名古屋市", "京都市", "大阪市", "堺市", "神戸市",
        "岡山市", "広島市", "北九州市", "福岡市", "熊本市"]

    kansuji = ['〇', '一', '二', '三', '四', '五', '六', '七', '八', '九']
    trans_kansuji_zarabic = str.maketrans('一二三四五六七八九', '１２３４５６７８９')

    def __init__(self):
        with open("../jiscode.json", 'r') as f:
            self.jiscodes = json.load(f)

        self.jiscode_from_name = {}
        for jiscode, names in self.jiscodes.items():
            name = itaiji_converter.standardize(''.join(names))
            self.jiscode_from_name[name] = jiscode
            if len(names) == 3:
                altname = itaiji_converter.standardize(names[0] + names[2])
                self.jiscode_from_name[altname] = jiscode

        self.root = Node(None, None, None, None)

    def _get_jiscode(self, name):
        st_name = itaiji_converter.standardize(name)
        if st_name in self.jiscode_from_name:
            return self.jiscode_from_name[st_name]

        return None

    def print_tree(self, fp):
        self.root.printTree(fp)

    @staticmethod
    def _arabicToNumber(arabic):
        """
        アラビア数字を数値に変換する
        """
        total = 0
        for char in string:
            i = "０１２３４５６７８９0123456789".index(char)
            if i is None:
                break
            elif i < 10:
                total = total * 10 + i
            else:
                total = total * 10 + i - 10

        return total

    @staticmethod
    def _numberToKansuji(num):
        """
        数値を漢数字に変換する
        """
        kanji = ''
        if num >= 1000:
            i = num / 1000
            if i > 1:
                kanji += self.kansuji[i]

            kanji += '千'
            num = num % 1000

        if num >= 100:
            i = num / 100
            if i > 1:
                kanji += self.kansuji[i]

            kanji += '百'
            num = num % 100

        if num >= 10:
            i = num / 10
            if i > 1:
                kanji += self.kansuji[i]

            kanji += '十'
            num = num % 10

        if num > 0:
            kanji += self.kansuji[num]

        return kanji

    def procOazaLine(self, args):
        if args[0] == '都道府県コード':
            return self.root

        if args[2] == "07023":  # 07000-12.0b のバグ
            args[2] = "07203"

        pcode, pname, ccode, cname, isj_code, oaza, y, x = args[0:8]

        curnode = self.addCityByJiscode(ccode, x, y)

        for place in self.guessAza(ccode, oaza):
            level, name = place
            newnode = Node(name, x, y, level)
            curnode = curnode.addChild(newnode)

        return self.root

    def procGaikuLine(self, args, mode='latlon'):
        if args[0] == '都道府県名' or args[2] == '' or args[11] == '0':
            # 字名が空欄のデータ, 非代表点 は登録しない
            return self.root

        flag = False
        if args[12] == '3' or args[13] == '3':
            # 削除データはフラグ付きで登録する
            flag = True

        pref = args[0]
        city = args[1]

        # 不正なデータ
        if pref == '大阪市':
            pref = "大阪府"
        elif pref == '岩手県' and city == '上開伊郡大槌町':
            city = '上閉伊郡大槌町'

        jcode = self._get_jiscode(pref + city)
        if jcode is None and city.find('ケ') >= 0:
            jcode = self._get_jiscode(pref + city.replace('ケ', 'ヶ'))

        if jcode is None and city.find('ヶ') >= 0:
            jcode = self._get_jiscode(pref + city.replace('ヶ', 'ケ'))

        if jcode is None:
            import pdb
            pdb.set_trace()
            raise RuntimeError("{} の JISCODE が取得できません。({})".format(
                pref + city, args))

        if mode == 'latlon':
            y = args[8]  # latitude
            x = args[9]  # longitude
        elif mode == 'xy':
            x = args[6]
            y = args[7]

        curnode = self.addCityByJiscode(jcode, x, y)

        # 以下の住所は枝番と思われる
        # 17206 石川県/加賀市/永井町五十六/12 => 石川県/加賀市/永井町/56番地/12
        if jcode == '17206':
            m = re.match(r'^永井町([一二三四五六七八九十１２３４５６７８９].*)$', args[2])
            if m:
                curnode = curnode.addChild(Node('永井町', x, y, 5, true))
                chiban = m.group(1).translate(self.trans_kansuji_zerabic)
                chiban = chiban.replace('十', '')
                curnode = curnode.addChild(Node(chiban + '番地', x, y, 7, true))
                hugou = jaconv.h2z(args[3], ascii=False, digit=False)
                curnode = curnode.addChild(Node(hugou, x, y, 8, true))
                return self.root

        if args[3] == '':
            for place in self.guessAza(jcode, args[2]):
                level, name = place
                newnode = Node(name, x, y, level, flag)
                curnode = curnode.addChild(newnode)

        else:
            newnode = Node(args[2], x, y, 5, flag)
            curnode = curnode.addChild(newnode)
            newnode = Node(args[3], x, y, 6, flag)
            curnode = curnode.addChild(newnode)

        #self.registerOaza(args[2], jcode, x, y)

        hugou = jaconv.h2z(args[4], ascii=False, digit=False)
        if args[10] == '1':
            # 住居表示地域
            newnode = Node(hugou + '番', x, y, 7, flag)
        else:
            newnode = Node(hugou + '番地', x, y, 7, flag)

        curnode = curnode.addChild(newnode)
        return self.root

    def _guessAza_sub(self, name, ignore_aza=False):
        """
        一般的なパターンの大字＋字名を分割する
        """
        if not ignore_aza:
            m = re.match(r'^([^字]+?[^文])字(.*)$', name)
            if m:
                return [[5, m.group(1)], [6, m.group(2)]]

        m = re.match(
            r'^(.*[^０-９一二三四五六七八九〇十])([０-９一二三四五六七八九〇十]+線)(東|西|南|北)$', name)
        if m:
            return [[5, m.group(1)], [6, m.group(2)], [7, m.group(3)]]

        m = re.match(
            r'^(.*[^０-９一二三四五六七八九〇十])([０-９一二三四五六七八九〇十]+線(東|西)?)$', name)
        if m:
            return [[5, m.group(1)], [6, m.group(2)]]

        m = re.match(r'^(.*[^０-９一二三四五六七八九〇十])([０-９一二三四五六七八九〇十]+丁目)$', name)
        if m:
            return [[5, m.group(1)], [6, m.group(2)]]

        m = re.match(r'^(.*[^０-９一二三四五六七八九〇十])([０-９一二三四五六七八九〇十]+番地)$', name)
        if m:
            return [[5, m.group(1)], [7, m.group(2)]]

        # 分割できなかった場合はそのまま
        return [[5, name]]

    def guessAza(self, jcode, name):
        """
        字名を推測する
        """
        places = []
        name = re.sub(r'[　\s+]', '', name)

        if name[0] == '字':
            # 先頭の '字' は除去する
            name = name[1:]

            return self._guessAza_sub(name, ignore_aza=True)

        if name.startswith('大字'):
            name = name[2:]

            if jcode == '06201' and name.startswith('十文字'):
                # 例外 山形県/山形市/十文字/大原
                return [[5, '十文字'], [6, name[3:]]]

            m = re.match(r'^([^字]+?[^文])字(.+)', name)
            if m:
                return [[5, m.group(1)], [6, m.group(2)]]

            return self._guessAza_sub(name)

        # 「位置参照情報」の「大字・町丁目名」が「（大字なし）」の場合がある
        if '（大字なし）' == name:
            return []

        # 以下の住所は「ｘ丁目」だが、丁目以下に字名がつく
        #   福島県/郡山市/日和田町八丁目 (堰町)
        #   長野県/飯田市/知久町三丁目 (大横)
        #   長野県/飯田市/通り町三丁目 (大横)
        #   長野県/飯田市/本町三丁目（大横）
        #   岐阜県/岐阜市/西野町６丁目（北町)
        if jcode == '07203':
            m = re.match(r'^(日和田町)(八丁目.*)$', name)
        elif jcode == '20205':
            m = re.match(r'^(知久町)(三丁目.*)$', name)
            if not m:
                m = re.match(r'^(通り町)(三丁目.*)$', name)
            if not m:
                m = re.match(r'^(本町)([三四]丁目.*)$', name)
        elif jcode == '21201':
            m = re.match(r'^(西野町)([６７六七]丁目.*)$', name)
            if m:
                return [[5, m.group(1)], [6, m.group(2)]]

        # 以下の住所は整備ミスなので修正する
        #   長野県/長野市/若里6丁目 => 長野県/長野市/若里６丁目
        #   長野県/長野市/若里7丁目 => 長野県/長野市/若里７丁目
        #   広島県/福山市/駅家町大字弥生ケ => 広島県/福山市/駅家町大字弥生ヶ丘
        if jcode == '20201' and name == '若里6丁目':
            return [[5, '若里'], [6, '６丁目']]

        if jcode == '20201' and name == '若里7丁目':
            return [[5, '若里'], [6, '７丁目']]

        if jcode == '34207' and name == '駅家町大字弥生ケ':
            return [[5, '駅家町大字弥生ヶ丘']]

        return self._guessAza_sub(name)

    def addCityByJiscode(self, jiscode, x=99999.9, y=99999.9):
        curnode = self.root
        if jiscode not in self.jiscodes:
            raise RuntimeError("jiscode:{} は見つかりません".format(jiscode))

        names = self.jiscodes[jiscode]

        # 都道府県
        # 末尾の「都府県」を省略した都府県名も登録する -> 国土地理院要望
        if names[0].endswith(("都", "府", "県",)):
            curnode.addChild(Node(names[0][0:-1], x, y, 1))

        newnode = Node(names[0], x, y, 1)
        curnode = curnode.addChild(newnode)

        if len(names) == 1:
            return curnode

        m = re.match(r'(.*)(郡|支庁|総合振興局|振興局|島)$', names[1])
        if m:
            curnode.addChild(Node(m.group(1), x, y, 2))
            newnode = Node(names[1], x, y, 2)
            curnode = curnode.addChild(newnode)
        else:
            m = re.match(r'(.*)(市|町|村)$', names[1])
            if m:
                curnode.addChild(Node(m.group(1), x, y, 3))
                newnode = Node(names[1], x, y, 3)
                curnode = curnode.addChild(newnode)
            else:
                if names[0] == '東京都':
                    m = re.match(r'(.*)区', names[1])
                    if m:
                        curnode.addChild(Node(m.group(1), x, y, 3))
                        newnode = Node(names[1], x, y, 3)
                        curnode = curnode.addChild(newnode)

        if len(names) == 2:
            return curnode

        m = re.match(r'(.*)(町|村)$', names[2])
        if m:
            curnode.addChild(Node(m.group(1), x, y, 3))
            newnode = Node(names[2], x, y, 3)
            curnode = curnode.addChild(newnode)
        else:
            m = re.match(r'(.*)区$', names[2])
            if m:
                curnode.addChild(Node(m.group(1), x, y, 4))
                newnode = Node(names[2], x, y, 4)
                curnode = curnode.addChild(newnode)

        return curnode

    def add_from_gaiku_zipfile(self, zipfilepath):
        with zipfile.ZipFile(zipfilepath) as z:
            for filename in z.namelist():
                if not filename.lower().endswith('.csv'):
                    continue

                with z.open(filename, mode='r') as f:
                    ft = io.TextIOWrapper(
                        f, encoding='CP932', newline='',
                        errors='backslashreplace')
                    reader = csv.reader(ft)
                    pre_args = None
                    try:
                        for args in reader:
                            self.procGaikuLine(args)
                            pre_args = args
                    except UnicodeDecodeError:
                        print("変換できない文字が見つかりました。処理中のファイルは {}, 直前の行は次の通りです。\n{}".format(
                            filename, pre_args), file=sys.stderr)
                        exit(-1)

    def add_from_oaza_zipfile(self, zipfilepath):
        with zipfile.ZipFile(zipfilepath) as z:
            for filename in z.namelist():
                if not filename.lower().endswith('.csv'):
                    continue

                pre_args = None
                with z.open(filename, mode='r') as f:
                    ft = io.TextIOWrapper(
                        f, encoding='CP932', newline='',
                        errors='backslashreplace')
                    reader = csv.reader(ft)
                    try:
                        for args in reader:
                            self.procOazaLine(args)
                            pre_args = args
                    except UnicodeDecodeError:
                        print("変換できない文字が見つかりました。処理中のファイルは {}, 直前の行は次の通りです。\n{}".format(
                            filename, pre_args), file=sys.stderr)
                        exit(-1)


if __name__ == '__main__':
    basedir = os.path.dirname(__file__)

    for pref_code in range(1, 48):
        basename = "{:02d}000.zip".format(pref_code)
        converter = IsjConverter()
        added = False

        oaza_filepath = os.path.join(basedir, 'oaza', basename)
        if os.path.exists(oaza_filepath):
            converter.add_from_oaza_zipfile(oaza_filepath)
            added = True

        gaiku_filepath = os.path.join(basedir, 'gaiku', basename)
        if os.path.exists(gaiku_filepath):
            converter.add_from_gaiku_zipfile(gaiku_filepath)
            added = True

        if not added:
            continue

        output_filepath = os.path.join(basedir, '{:02}.txt'.format(pref_code))
        with open(output_filepath, 'w', encoding='utf-8') as f:
            converter.print_tree(f)
