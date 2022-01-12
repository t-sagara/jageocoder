# jageocoder - A Python Japanese geocoder

`jageocoder` は日本の住所用ジオコーダです。
東京大学空間情報科学研究所の [「CSV アドレスマッチングサービス」](https://geocode.csis.u-tokyo.ac.jp/home/csv-admatch/) および
国土地理院の [「地理院地図」](https://maps.gsi.go.jp/) で利用している
C++ ジオコーダを Python に移植しました。

# はじめに

このパッケージは Python プログラムに住所ジオコーディング機能を提供します。
`init()` で初期化し、 `search()` に住所文字列を渡すと、
ジオコーディング結果が得られます。

```python
python
>>> import jageocoder
>>> jageocoder.init()
>>> jageocoder.search('新宿区西新宿2-8-1')
{'matched': '新宿区西新宿2-8-', 'candidates': [{'id': 5961406, 'name': '8番', 'x': 139.691778, 'y': 35.689627, 'level': 7, 'note': None, 'fullname': ['東京都', '新宿区', '西新宿', '二丁目', '8番']}]}
```

# インストール方法

## 事前準備

Python 3.6 以降が必要です。

jageocoder をインストールすると、以下のパッケージなども
自動的にインストールされます。

- [marisa-trie](https://pypi.org/project/marisa-trie/)
    TRIE インデックスの作成と検索に利用します
- [SQLAlchemy](https://pypi.org/project/SQLAlchemy/)
    RDBMS (Sqlite3) のアクセスに利用します

## インストール手順

- `pip install jageocoder` でパッケージをインストールします
- `install-dictionary` コマンドで住所辞書をインストールします

```sh
pip install jageocoder
python -m jageocoder install-dictionary
```

辞書データベースは `{sys.prefix}/jageocoder/db/` の下に
作成されますが、ユーザが書き込み権限を持っていない場合には
`{site.USER_DATA}/jageocoder/db/` に作成します。

辞書データベースが作成されたディレクトリを知る必要がある場合、
以下のように `get-db-dir` コマンドを実行するか、スクリプト内で
`jageocoder.get_db_dir()` メソッドを呼びだしてください。

```sh
python -m jageocoder get-db-dir
```

上記以外の任意の場所に作成したい場合、住所辞書をインストールする前に
環境変数 `JAGEOCODER_DB_DIR` でディレクトリを指定してください。

```sh
export JAGEOCODER_DB_DIR='/usr/local/share/jageocoder/db'
python -m jageocoder install-dictionary
```

## 辞書の更新

`install-dictionary` コマンドを実行すると、その時点でインストール
されている jageocoder パッケージと互換性のあるバージョンの
住所辞書ファイルをダウンロードしてインストールします。

住所辞書ファイルをインストールした後で jageocoder パッケージを
バージョンアップした場合、住所辞書ファイルと互換性が無くなる場合があり、
その場合は辞書を再インストールするか更新する必要があります。

辞書を更新するには `upgrade-dictionary` コマンドを実行します。
この処理には長時間かかることがあります。

```sh
python -m jageocoder upgrade-dictionary
```

## アンインストール手順

アンインストールする場合、まず辞書データベースを含むディレクトリを
削除してください。ディレクトリごと削除しても構いませんが、
`uninstall-dictionary` コマンドも利用できます。

```sh
python -m jageocoder uninstall-dictionary
```

その後、 jageocoder パッケージを pip でアンインストールしてください。

```sh
pip uninstall jageocoder
```

# 使い方

まず jageocoder をインポートし、 `init()` で初期化します。

```
>>> import jageocoder
>>> jageocoder.init()
```

## 住所から経緯度を調べる

経緯度を調べたい住所を `search()` で検索します。

`search()` は一致した文字列を `matched` に、検索結果のリストを
`candidates` に持つ dict を返します。 `candidates` の各要素には
住所ノード (AddressNode) の情報が入っています。

```
>>> jageocoder.search('新宿区西新宿２－８－１')
{'matched': '新宿区西新宿２－８－', 'candidates': [{'id': 12299846, 'name': '8番', 'x': 139.691778, 'y': 35.689627, 'level': 7, 'note': None, 'fullname': ['東京都', '新宿区', '西新宿', '二丁目', '8番']}]}
```

項目の意味は次の通りです。

- id: データベース内での ID
- name: 住所表記
- x: 経度
- y: 緯度
- level: 住所レベル（1:都道府県, 2:郡／振興局, 3:市町村・23特別区,
    4:政令市の区, 5:大字, 6:字・丁目, 7:街区・地番, 8:住居番号・枝番）
- note: メモ（自治体コードなど）
- fullname: 都道府県レベルからこのノードまでの住所表記のリスト

## 経緯度から住所を調べる

住所を調べたい経度緯度を `reverse()` で検索します（リバースジオコーディング）。
指定した経緯度を持つ点を囲む3つの住所を返します。

`candidate` に住所ノード (AddressNode) の情報、 `dist` に指定した地点から
住所の代表点までの距離（測地線距離、単位はメートル）が入っています。

```
>>> jageocoder.reverse(139.6917, 35.6896)
[{'candidate': {'id': 12299330, 'name': '二丁目', 'x': 139.691774, 'y': 35.68945, 'level': 6, 'note': 'postcode:1600023', 'fullname': ['東京都', '新宿区', '西新宿', '二丁目']}, 'dist': 17.940303970792183}, {'candidate': {'id': 12300198, 'name': '六丁目', 'x': 139.690969, 'y': 35.693426, 'level': 6, 'note': 'postcode:1600023', 'fullname': ['東京都', '新宿区', '西新宿', '六丁目']}, 'dist': 429.6327545403412}, {'candidate': {'id': 12300498, 'name': '四丁目', 'x': 139.68762, 'y': 35.68754, 'level': 6, 'note': 'postcode:1600023', 'fullname': ['東京都', '新宿区', '西新宿', '四丁目']}, 'dist': 434.31591285255234}]
```

`level` オプションパラメータを指定すると、より詳細な住所を返します。
ただし計算に時間がかかります。

```
>>> jageocoder.reverse(139.6917, 35.6896, level=7)
[{'candidate': {'id': 12299340, 'name': '8番', 'x': 139.691778, 'y': 35.689627, 'level': 7, 'note': None, 'fullname': ['東京都', '新宿区', '西新宿', '二丁目', '8番']}, 'dist': 7.669497303543382}, {'candidate': {'id': 12299330, 'name': '二丁目', 'x': 139.691774, 'y': 35.68945, 'level': 6, 'note': 'postcode:1600023', 'fullname': ['東京都', '新宿区', '西新宿', '二丁目']}, 'dist': 17.940303970792183}, {'candidate': {'id': 12300588, 'name': '15番', 'x': 139.688172, 'y': 35.689264, 'level': 7, 'note': None, 'fullname': ['東京都', '新宿区', '西新宿', '四丁目', '15番']}, 'dist': 321.50874020809823}]
```

## 住所の属性情報を調べる

住所に関する情報を取得するには `searchNode()` を使います。
この関数は `jageocoder.result.Result` 型のリストを返します。
ここから住所ノードに直接アクセスできます。

```
>>> results = jageocoder.searchNode('新宿区西新宿２－８－１')
>>> len(results)
1
>>> results[0].matched
'新宿区西新宿２－８－'
>>> type(results[0].node)
<class 'jageocoder.node.AddressNode'>
>>> node = results[0].node
>>> node.get_fullname()
['東京都', '新宿区', '西新宿', '二丁目', '8番']
```

### 自治体コードを取得する

自治体コードには JISX0402（5桁）と地方公共団体コード（6桁）があります。
都道府県コード JISX0401（2桁）も取得できます。

```
>>> node.get_city_jiscode()  # 5桁コード
'13104'
>>> node.get_city_local_authority_code() # 6桁コード
'131041'
>>> node.get_pref_jiscode()  # 都道府県コード
'13'
```

### 地図へのリンクを取得する

地理院地図と Google 地図へのリンク URL を生成します。

```
>>> node.get_gsimap_link()
'https://maps.gsi.go.jp/#16/35.689627/139.691778/'
>>> node.get_googlemap_link()
'https://maps.google.com/maps?q=35.689627,139.691778&z=16'
```

### 親ノードを辿る

「親ノード」とは、住所の一つ上の階層を表すノードのことです。
ノードの属性 `parent` で取得します。

今 `node` は '8番' を指しているので、親ノードは '二丁目' になります。

```
>>> parent = node.parent
>>> parent.get_fullname()
['東京都', '新宿区', '西新宿', '二丁目']
>>> parent.x, parent.y
(139.691774, 35.68945)
```

### 子ノードを辿る

「子ノード」とは、住所の一つ下の階層を表すノードのことです。
ノードの属性 `children` で取得します。

親ノードは一つですが、子ノードは複数あります。
実際に返すのは SQL クエリオブジェクトですが、
イテレータでループしたり list にキャストできます。

今 `parent` は '二丁目' を指しているので、子ノードは
そこに含まれる街区符号（○番）になります。

```
>>> parent.children
<sqlalchemy.orm.dynamic.AppenderQuery object at 0x7fbc08404b38>
>>> [child.name for child in parent.children]
['10番', '11番', '1番', '2番', '3番', '4番', '5番', '6番', '7番', '8番', '9番']
```

# 開発者向け情報

## ユニットテスト

ユニットテストは unittest で行ないます。

```python
python -m unittest
```

`tests.test_search` テストには特殊な住所表記の例が含まれています。

- 札幌市内の省略表記（例：「北三条西一丁目」を「北3西1」と表記）
- 京都市内の通り名表記（例：「薮ノ内町」を「下立売通新町西入薮ノ内町」と表記）

## 独自の辞書を作成したい場合

辞書コンバータ `jageocoder-converter` を利用してください。

[jageocoder-converter](https://github.com/t-sagara/jageocoder-converter)

## 異体字を追加したい場合

特定の文字を別の文字に読み替えたい場合、異体字辞書に登録します。
詳細は `itaiji_dic/README.md` を参照してください。

## サンプルウェブアプリ

Flask を利用したシンプルなウェブアプリのサンプルが
`flask-demo` の下にあります。

次の手順を実行し、ポート 5000 にアクセスしてください。

```
cd flask-demo
pip install flask flask-cors
bash run.sh
```

## ToDo

- 住所変更への対応

    自治体統合などによる住所変更があった場合に、旧住所を新住所に
    自動的に変換する機能は jageocoder では将来実装予定です。

## ご協力頂ける場合

日本の住所表記は非常に多様なので、うまく変換できない場合には
お知らせ頂けるとありがたいです。ロジックの改良提案も歓迎します。
どのような住所がどう解析されるべきかをご連絡頂ければ幸いです。

## 作成者

* **相良 毅** - [株式会社情報試作室](https://www.info-proto.com/)

## 利用許諾条件

MIT ライセンスでご利用頂けます。

This project is licensed under [the MIT License](https://opensource.org/licenses/mit-license.php).

ただしこの利用許諾条件は住所辞書データに対しては適用されません。
各辞書データのライセンスを参照してください。

## 謝辞

20年以上にわたり、アドレスマッチングサービスを継続するために
所内ウェブサーバを利用させて頂いている
東京大学空間情報科学研究センターに感謝いたします。

また、NIIの北本朝展教授には、比較的古い住所体系を利用している地域の
大規模なサンプルのご提供と、解析結果の確認に多くのご協力を頂きましたことを
感謝いたします。