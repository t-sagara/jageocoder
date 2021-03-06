import csv
import copy
import glob
import io
import json
import logging
import os
import re
import sys
import zipfile

import jaconv

from jageocoder.itaiji import converter as itaiji_converter
from jageocoder.address import AddressLevel


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

    def __init__(self, jiscode_path, fp=None):
        with open(jiscode_path, 'r') as f:
            self.jiscodes = json.load(f)

        # 逆引きテーブルを作成 住所表記 -> jiscode
        self.jiscode_from_name = {}
        for jiscode, names in self.jiscodes.items():
            name = itaiji_converter.standardize(''.join(names))
            self.jiscode_from_name[name] = jiscode
            if len(names) == 3:
                altname = itaiji_converter.standardize(names[0] + names[2])
                self.jiscode_from_name[altname] = jiscode
                
        # jiscode : [住所要素名] -> jiscode : [(住所要素名,レベル)]
        for code, names in self.jiscodes.items():
            if len(names) == 1:
                # 都道府県のみ
                self.jiscodes[code] = [(names[0], AddressLevel.PREF,),]
                continue

            if len(names) == 2:
                # 都道府県＋市・特別区
                self.jiscodes[code] = [
                    (names[0], AddressLevel.PREF,),
                    (names[1], AddressLevel.CITY,),
                ]
                continue

            # 都道府県＋郡・支庁＋町村
            if names[2][-1] in '町村':
                self.jiscodes[code] = [
                    (names[0], AddressLevel.PREF,),
                    (names[1], AddressLevel.COUNTY,),
                    (names[2], AddressLevel.CITY,),
                ]
                continue

            # 都道府県＋市＋区
            if names[2][-1] == '区':
                self.jiscodes[code] = [
                    (names[0], AddressLevel.PREF,),
                    (names[1], AddressLevel.CITY,),
                    (names[2], AddressLevel.WORD,),
                ]
                continue

            raise RuntimeError("識別できないパターン: {}".format(names))
        
        # 出力先設定
        if fp is None:
            self.fp = sys.stdout
        else:
            self.fp = fp

    def _get_jiscode(self, name):
        st_name = itaiji_converter.standardize(name)
        if st_name in self.jiscode_from_name:
            return self.jiscode_from_name[st_name]

        return None

    def print_line(self, path, x, y, note=None):
        """
        JSONL 形式データファイルの１行分を出力する（v2形式）
        {"path":[["東京都",1],["新宿区",3],["西新宿",5],["二丁目",6],["8番",7]],"x":139.691778,"y":35.689627,"note":null}

        Parameters
        ----------
        path : list of (name, level)
            [['東京都',1],['新宿区',3],['西新宿',5],['二丁目',6],['8番',7]]
        x : float
            X 座標の値（経度）
        y : float
            Y 座標の値（緯度）
        note : str
            メモ
        """
        if note:
            record = {"path":path, "x":x, "y":y, "note":note}
        else:
            record = {"path":path, "x":x, "y":y}
            
        print(json.dumps(record, ensure_ascii=False), file=self.fp)

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
        """
        大字・町丁目レベル位置参照情報の１行を解析して住所ノードを追加する

        Parameters
        ----------
        args : list of str
        0: "都道府県コード"
        1: "都道府県名"
        2: "市区町村コード"
        3: "市区町村名"
        4: "大字町丁目コード"
        5: "大字町丁目名"
        6: "緯度"
        7: "経度"
        8: "原典資料コード"
        9: "大字・字・丁目区分コード"
        """
        if args[0] == '都道府県コード':
            return

        if args[2] == "07023":  # 07000-12.0b のバグ
            args[2] = "07203"

        pcode, pname, ccode, cname, isj_code, oaza, y, x = args[0:8]

        path = copy.copy(self.jiscodes[ccode])

        for place in self.guessAza(ccode, oaza):
            path.append((place[1], place[0],))

        self.print_line(path, float(x), float(y))

    def procGaikuLine(self, args, mode='latlon'):
        """
        街区レベル位置参照情報の１行を解析して住所ノードを追加する
        
        Parameters
        ----------
        args : list of str
        0: "都道府県名"
        1: "市区町村名"
        2: "大字・丁目名"
        3: "小字・通称名"
        4: "街区符号・地番"
        5: "座標系番号"
        6: "Ｘ座標"
        7: "Ｙ座標"
        8: "緯度"
        9: "経度"
        10: "住居表示フラグ"
        11: "代表フラグ"
        12: "更新前履歴フラグ"
        13: "更新後履歴フラグ"
        """
        if args[0] == '都道府県名' or args[2] == '' or args[11] == '0':
            # 字名が空欄のデータ, 非代表点 は登録しない
            return

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
            raise RuntimeError("{} の JISCODE が取得できません。({})".format(
                pref + city, args))

        if mode == 'latlon':
            y = args[8]  # latitude
            x = args[9]  # longitude
        elif mode == 'xy':
            x = args[6]
            y = args[7]

        x = float(x)
        y = float(y)
        path = copy.copy(self.jiscodes[jcode])

        # 以下の住所は枝番と思われる
        # 17206 石川県/加賀市/永井町五十六/12 => 石川県/加賀市/永井町/56番地/12
        if jcode == '17206':
            m = re.match(r'^永井町([一二三四五六七八九十１２３４５６７８９].*)$', args[2])
            if m:
                path.append(('永井町', AddressLevel.OAZA,))
                chiban = m.group(1).translate(self.trans_kansuji_zerabic)
                chiban = chiban.replace('十', '')
                path.append((chiban + '番地', AddressLevel.BLOCK,))
                hugou = jaconv.h2z(args[3], ascii=False, digit=False)
                path.append((hugou, AddressLevel.BLD,))
                self.print_line(path, x, y)
                return

        if args[3] == '':
            for place in self.guessAza(jcode, args[2]):
                path.append((place[1], place[0],))

        else:
            path.append((args[2], AddressLevel.OAZA,))
            path.append((args[3], AddressLevel.AZA,))

        hugou = jaconv.h2z(args[4], ascii=False, digit=False)
        if args[10] == '1':
            # 住居表示地域
            path.append((hugou + '番', AddressLevel.BLOCK,))
        else:
            path.append((hugou + '番地', AddressLevel.BLOCK,))

        self.print_line(path, x, y)

    def procJukyohyoujiLine(self, args):
        """
        住居表示住所の１行を解析して住所ノードを追加する
        """
        if len(args) > 9:
            raise RuntimeError("Invalid line: {}".format(args))

        jcode, aza, gaiku, kiso, code, dummy, lon, lat, scale = args
        lon = float(lon)
        lat = float(lat)
        path = copy.copy(self.jiscodes[jcode])

        # 大字，字レベル
        for place in self.guessAza(jcode, aza):
            path.append((place[1], place[0],))

        # 街区レベル
        hugou = jaconv.h2z(gaiku, ascii=False, digit=False)
        path.append((hugou + '番', AddressLevel.BLOCK,))

        # 住居表示レベル
        number = jaconv.h2z(kiso, ascii=False, digit=False)
        path.append((number + '号', AddressLevel.BLD))
        self.print_line(path, lon, lat)

    def _guessAza_sub(self, name, ignore_aza=False):
        """
        一般的なパターンの大字＋字名を分割する
        """
        if not ignore_aza:
            m = re.match(r'^([^字]+?[^文])字(.*)$', name)
            if m:
                return [
                    [AddressLevel.OAZA, m.group(1)],
                    [AddressLevel.AZA, m.group(2)]]

        m = re.match(
            r'^(.*[^０-９一二三四五六七八九〇十])([０-９一二三四五六七八九〇十]+線)(東|西|南|北)$', name)
        if m:
            return [
                [AddressLevel.OAZA, m.group(1)],
                [AddressLevel.AZA, m.group(2)],
                [AddressLevel.BLOCK, m.group(3)]]

        m = re.match(
            r'^(.*[^０-９一二三四五六七八九〇十])([０-９一二三四五六七八九〇十]+線(東|西)?)$', name)
        if m:
            return [
                [AddressLevel.OAZA, m.group(1)],
                [AddressLevel.AZA, m.group(2)]]

        m = re.match(
            r'^(.*[^０-９一二三四五六七八九〇十])([東西南北]?[０-９一二三四五六七八九〇十]+(丁目|線))$', name)
        if m:
            return [
                [AddressLevel.OAZA, m.group(1)],
                [AddressLevel.AZA, m.group(2)]]

        m = re.match(r'^(.*[^０-９一二三四五六七八九〇十])([０-９一二三四五六七八九〇十]+番地)$', name)
        if m:
            return [
                [AddressLevel.OAZA, m.group(1)],
                [AddressLevel.BLOCK, m.group(2)]]

        # 分割できなかった場合はそのまま
        return [[AddressLevel.OAZA, name]]

    def guessAza(self, jcode, name):
        """
        字名を推測する
        """
        places = []
        name = re.sub(r'[　\s+]', '', name)

        if name[0] == '字':
            # 先頭の '字' は無視して解析する
            result = self._guessAza_sub(name[1:], ignore_aza=True)

            # 先頭に '字' を戻す
            result[0][1] = '字' + result[0][1]
            return result

        if name.startswith('大字'):
            name = name[2:]

            if jcode == '06201' and name.startswith('十文字'):
                # 例外 山形県/山形市/十文字/大原
                return [
                    [AddressLevel.OAZA, '大字十文字'],
                    [AddressLevel.AZA, name[3:]]]

            m = re.match(r'^([^字]+?[^文])字(.+)', name)
            if m:
                return [
                    [AddressLevel.OAZA, '大字' + m.group(1)],
                    [AddressLevel.AZA, m.group(2)]]

            result = self._guessAza_sub(name)
            result[0][1] = '大字' + result[0][1]
            return result

        # 「位置参照情報」の「大字・町丁目名」が「（大字なし）」の場合がある
        if '（大字なし）' == name:
            return []

        # 以下の住所は「ｘ丁目」だが、丁目以下に字名がつく
        #   福島県/郡山市/日和田町八丁目 (堰町)
        #   長野県/飯田市/知久町三丁目 (大横)
        #   長野県/飯田市/通り町三丁目 (大横)
        #   長野県/飯田市/本町三丁目（大横）
        #   岐阜県/岐阜市/西野町６丁目（北町)
        m = None
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
            return [
                [AddressLevel.OAZA, m.group(1)],
                [AddressLevel.AZA, m.group(2)],
            ]

        # 以下の住所は整備ミスなので修正する
        #   長野県/長野市/若里6丁目 => 長野県/長野市/若里６丁目
        #   長野県/長野市/若里7丁目 => 長野県/長野市/若里７丁目
        #   広島県/福山市/駅家町大字弥生ケ => 広島県/福山市/駅家町大字弥生ヶ丘
        if jcode == '20201' and name == '若里6丁目':
            return [
                [AddressLevel.OAZA, '若里'],
                [AddressLevel.AZA, '６丁目']]

        if jcode == '20201' and name == '若里7丁目':
            return [
                [AddressLevel.OAZA, '若里'],
                [AddressLevel.AZA, '７丁目']]

        if jcode == '34207' and name == '駅家町大字弥生ケ':
            return [
                [AddressLevel.OAZA, '駅家町大字弥生ヶ丘']]

        return self._guessAza_sub(name)

    def add_from_gaiku_zipfile(self, zipfilepath):
        """
        街区レベル位置参照情報から住所表記を登録
        """
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
                        raise RuntimeError((
                            "変換できない文字が見つかりました。"
                            "処理中のファイルは {}, 直前の行は次の通りです。\n{}")
                            .format(pre_args))

    def add_from_oaza_zipfile(self, zipfilepath):
        """
        大字・町丁目レベル位置参照情報から住所表記を登録
        """
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
                        raise RuntimeError((
                            "変換できない文字が見つかりました。"
                            "処理中のファイルは {}, 直前の行は次の通りです。\n{}")
                            .format(filename, pre_args))

    def add_from_jukyohyouji_zipfile(self, zipfilepath):
        """
        住居表示住所から住所表記を登録
        """
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
                            self.procJukyohyoujiLine(args)
                            pre_args = args
                    except UnicodeDecodeError:
                        raise RuntimeError((
                            "変換できない文字が見つかりました。"
                            "処理中のファイルは {}, 直前の行は次の通りです。\n{}")
                            .format(filename, pre_args))


if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)

    basedir = os.path.dirname(__file__)
    jiscode_path = os.path.join(basedir, 'jiscode.json')
    output_filepath = os.path.join(basedir, 'output/00.txt')

    with open(output_filepath, 'w', encoding='utf-8') as fout:
        # 都道府県名および県庁所在地座標
        input_filepath = os.path.join(basedir, 'geonlp/japan_pref.csv')
        with open(input_filepath, 'r', encoding='cp932', newline='') as f:
            reader = csv.reader(f)
            converter = IsjConverter(jiscode_path, fp=fout)
            for rows in reader:
                if rows[0] == 'geonlp_id':
                    continue

                name, lon, lat = rows[6], float(rows[11]), float(rows[12])
                converter.print_line([(name, AddressLevel.PREF,),], lon, lat)
                name = rows[2]
                if name == '北海':
                    continue
                
                converter.print_line([(name, AddressLevel.PREF,),], lon, lat)

        # 市区町村名および役場所在地座標
        input_filepath = os.path.join(basedir, 'geonlp/japan_city.csv')
        with open(input_filepath, 'r', encoding='cp932', newline='') as f:
            reader = csv.reader(f)
            converter = IsjConverter(jiscode_path, fp=fout)
            for rows in reader:
                if rows[0] == 'geonlp_id':
                    continue

                jiscode = rows[1]
                path = converter.jiscodes[jiscode]
                lon, lat = rows[11], rows[12]
                if lon and lat:
                    converter.print_line(path, float(lon), float(lat))

    # 大字町丁目レベル位置参照情報
    for pref_code in range(1, 48):
        output_filepath = os.path.join(
            basedir, 'output/{:02}_oaza.txt'.format(pref_code))
        with open(output_filepath, 'w', encoding='utf-8') as f:

            basename = "{:02d}000.zip".format(pref_code)
            converter = IsjConverter(jiscode_path, fp=f)

            oaza_filepath = os.path.join(basedir, 'oaza', basename)
            if os.path.exists(oaza_filepath):
                logging.debug("Reading from {}".format(oaza_filepath))
                converter.add_from_oaza_zipfile(oaza_filepath)
                added = True

    # 街区レベル位置参照情報
    for pref_code in range(1, 48):
        output_filepath = os.path.join(
            basedir, 'output/{:02}_gaiku.txt'.format(pref_code))
        with open(output_filepath, 'w', encoding='utf-8') as f:

            basename = "{:02d}000.zip".format(pref_code)
            converter = IsjConverter(jiscode_path, fp=f)

            gaiku_filepath = os.path.join(basedir, 'gaiku', basename)
            if os.path.exists(gaiku_filepath):
                logging.debug("Reading from {}".format(gaiku_filepath))
                converter.add_from_gaiku_zipfile(gaiku_filepath)
                added = True

    # 住居表示住所レベル
    for pref_code in range(1, 48):
        output_filepath = os.path.join(
            basedir, 'output/{:02}_jusho.txt'.format(pref_code))
        with open(output_filepath, 'w', encoding='utf-8') as f:

            basename = "{:02d}000.zip".format(pref_code)
            converter = IsjConverter(jiscode_path, fp=f)

            for jusho_filepath in sorted(glob.glob(
                os.path.join(basedir,
                             'saigai.gsi.go.jp/jusho/download/data/',
                             '{:02d}*.zip'.format(pref_code)))):
                logging.debug("Reading from {}".format(jusho_filepath))
                converter.add_from_jukyohyouji_zipfile(jusho_filepath)
                added = True
