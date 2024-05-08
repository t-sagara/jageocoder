# Jageocoder - A Python Japanese geocoder

`Jageocoder` は日本の住所用ジオコーダです。
東京大学空間情報科学研究センターの
[「CSV アドレスマッチングサービス」](https://geocode.csis.u-tokyo.ac.jp/home/csv-admatch/) および国土地理院の [「地理院地図」](https://maps.gsi.go.jp/) で利用している C++ ジオコーダ `DAMS` を Python に移植しました。

# はじめに

このパッケージは Python プログラムに住所ジオコーディング機能を提供します。
`init()` で初期化し、 `search()` に住所文字列を渡すと、
ジオコーディング結果が得られます。

```python
>>> import jageocoder
>>> jageocoder.init(url='https://jageocoder.info-proto.com/jsonrpc')
>>> jageocoder.search('新宿区西新宿2-8-1')
{'matched': '新宿区西新宿2-8-', 'candidates': [{'id': 5961406, 'name': '8番', 'x': 139.691778, 'y': 35.689627, 'level': 7, 'note': None, 'fullname': ['東京都', '新宿区', '西新宿', '二丁目', '8番']}]}
```

# インストール方法

## 事前準備

Python 3.7 以降が動作する環境が必要です。

その他の依存パッケージは自動的にインストールされます。

## インストール手順

`pip install jageocoder` でパッケージをインストールします

```
pip install jageocoder
```

Jageocoder を利用するには、同一マシン上に「辞書データベース」をインストールするか、 [jageocoder-server](https://t-sagara.github.io/jageocoder/server/) が提供する RPC サービスに接続する必要があります。

### 辞書データベースをインストールする場合

辞書データベースをインストールすると大量のデータも高速に処理できます。全国の住所を網羅するデータベースは 30GB 以上のストレージが必要です。

- 利用する辞書データベースファイルを [ここから](https://www.info-proto.com/static/jageocoder/latest/v2/) ダウンロードします

      wget https://www.info-proto.com/static/jageocoder/latest/v2/jukyo_all_v21.zip

- 辞書データベースをインストールします
    
      jageocoder install-dictionary jukyo_all_v21.zip

辞書データベースが作成されたディレクトリを知る必要がある場合、
以下のように `get-db-dir` コマンドを実行するか、スクリプト内で
`jageocoder.get_db_dir()` メソッドを呼びだしてください。

```bash
jageocoder get-db-dir
```

上記以外の任意の場所に作成したい場合、住所辞書をインストールする前に
環境変数 `JAGEOCODER_DB2_DIR` でディレクトリを指定してください。

```bash
export JAGEOCODER_DB2_DIR='/usr/local/share/jageocoder/db2'
jageocoder install-dictionary jukyo_all_v21.zip
```

### Jageocoder サーバに接続する場合

辞書データベースはサイズが大きいので、複数のマシンにインストールするとストレージを消費しますし、更新の手間もかかります。
そこで各マシンに辞書データベースをインストールする代わりに、Jageocoder サーバに接続して検索処理を代行させることもできます。

サーバを利用したい場合、環境変数 `JAGEOCODER_SERVER_URL` にサーバの
エンドポイントを指定してください。
公開デモンストレーション用サーバの場合は次の通りです。

```bash
export JAGEOCODER_SERVER_URL=https://jageocoder.info-proto.com/jsonrpc
```

ただし公開デモンストレーション用サーバはアクセスが集中すると負荷に耐えられないため、1秒1リクエストまでに制限しています。
大量の処理を行いたい場合は [こちら](https://t-sagara.github.io/jageocoder/server/) を参照して独自 Jageocoder サーバを設置してください。エンドポイントはサーバの `/jsonrpc` になります。

## アンインストール手順

アンインストールする場合、まず辞書データベースを含むディレクトリを
削除してください。ディレクトリごと削除しても構いませんが、
`uninstall-dictionary` コマンドも利用できます。

```bash
jageocoder uninstall-dictionary
```

その後、 jageocoder パッケージを pip でアンインストールしてください。

```bash
pip uninstall jageocoder
```

# 使い方

## コマンドラインから利用する

Jageocoder はライブラリとしてアプリケーションに組み込み、API を呼びだして利用することを想定していますが、簡単なコマンドラインインタフェースも用意しています。

たとえば住所をジオコーディングしたい場合は次のコマンドを実行します。

```bash
jageocoder search 新宿区西新宿２－８－１
```

利用可能なコマンド一覧は `--help` で確認してください。

```bash
jageocoder --help
```

## APIを利用する

まず jageocoder をインポートし、 `init()` で初期化します。

```python
>>> import jageocoder
>>> jageocoder.init()
```

`init()` のパラメータ `db_dir` で住所データベースがインストールされているディレクトリを指定できます。あるいは `url` で Jageocoder サーバのエンドポイント URL を指定できます。省略された場合は環境変数の値を利用します。

```python
>>> jageocoder.init(db_dir='/path/to/the/database')
>>> jageocoder.init(url='https://your.jageocoder.server/jsonrpc')
```

### 住所から経緯度を調べる

経緯度を調べたい住所を `search()` で検索します。

`search()` は一致した文字列を `matched` に、検索結果のリストを
`candidates` に持つ dict を返します。 `candidates` の各要素には
住所ノード (AddressNode) の情報が入っています
（見やすくするために表示結果を整形しています）。

```python
>>> jageocoder.search('新宿区西新宿２－８－１')
{
  'matched': '新宿区西新宿２－８－',
  'candidates': [{
    'id': 12299846, 'name': '8番',
    'x': 139.691778, 'y': 35.689627, 'level': 7, 'note': None,
    'fullname': ['東京都', '新宿区', '西新宿', '二丁目', '8番']
  }]
}
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

### 経緯度から住所を調べる

地点の経緯度を指定し、その地点の住所を調べることができます
（いわゆるリバースジオコーディング）。

`reverse()` に調べたい地点の経度と緯度を渡すと、指定した地点を囲む最大3点の住所ノードを検索できます。

```python
>>> import jageocoder
>>> jageocoder.init()
>>> triangle = jageocoder.reverse(139.6917, 35.6896, level=7)
>>> if len(triangle) > 0:
...     print(triangle[0]['candidate']['fullname'])
...
['東京都', '新宿区', '西新宿', '二丁目', '8番']
```

上の例では ``level`` オプションパラメータに 7 を指定して、街区・地番レベルまで検索しています。

> [!Note]
>
> リバースジオコーディング用のインデックスは、初めてリバースジオコーディングを実行した時に自動的に作成されます。
この処理には長い時間がかかりますので、注意してください。

### 住所の属性情報を調べる

住所に関する情報を取得するには `searchNode()` を使います。
この関数は `jageocoder.result.Result` 型のリストを返します。
Result オブジェクトの node 要素から住所ノードにアクセスできます。

```python
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

#### GeoJSON 表現を取得する

Result および AddressNode オブジェクトの `as_geojson()` メソッドを
利用すると GeoJSON 表現を取得できます。

```python
>>> results[0].as_geojson()
{'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [139.691778, 35.689627]}, 'properties': {'id': 12299851, 'name': '8番', 'level': 7, 'note': None, 'fullname': ['東京都', '新宿区', '西新宿', '二丁目', '8番'], 'matched': '新宿区西新宿２－８－'}}
>>> results[0].node.as_geojson()
{'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [139.691778, 35.689627]}, 'properties': {'id': 12299851, 'name': '8番', 'level': 7, 'note': None, 'fullname': ['東京都', '新宿区', '西新宿', '二丁目', '8番']}}
```

#### 自治体コードを取得する

自治体コードには JISX0402（5桁）と地方公共団体コード（6桁）があります。
都道府県コード JISX0401（2桁）も取得できます。

```python
>>> node.get_city_jiscode()  # 5桁コード
'13104'
>>> node.get_city_local_authority_code() # 6桁コード
'131041'
>>> node.get_pref_jiscode()  # 都道府県コード
'13'
```

#### 地図へのリンクを取得する

地理院地図と Google 地図へのリンク URL を生成します。

```python
>>> node.get_gsimap_link()
'https://maps.gsi.go.jp/#16/35.689627/139.691778/'
>>> node.get_googlemap_link()
'https://maps.google.com/maps?q=35.689627,139.691778&z=16'
```

#### 親ノードを辿る

「親ノード」とは、住所の一つ上の階層を表すノードのことです。
ノードの属性 `parent` で取得します。

今 `node` は '8番' を指しているので、親ノードは '二丁目' になります。

```python
>>> parent = node.parent
>>> parent.get_fullname()
['東京都', '新宿区', '西新宿', '二丁目']
>>> parent.x, parent.y
(139.691774, 35.68945)
```

#### 子ノードを辿る

「子ノード」とは、住所の一つ下の階層を表すノードのことです。
ノードの属性 `children` で取得します。

親ノードは一つですが、子ノードは複数あります。
実際に返すのは SQL クエリオブジェクトですが、
イテレータでループしたり list にキャストできます。

今 `parent` は '二丁目' を指しているので、子ノードは
そこに含まれる街区符号（○番）になります。

```python
>>> parent.children
<sqlalchemy.orm.dynamic.AppenderQuery object at 0x7fbc08404b38>
>>> [child.name for child in parent.children]
['10番', '11番', '1番', '2番', '3番', '4番', '5番', '6番', '7番', '8番', '9番']
```

# 開発者向け情報

## ユニットテスト

ユニットテストは pytest で行ないます。

```sh
pytest
```

`tests.test_search` テストには特殊な住所表記の例が含まれています。

- 札幌市内の省略表記（例：「北三条西一丁目」を「北3西1」と表記）
- 京都市内の通り名表記（例：「薮ノ内町」を「下立売通新町西入薮ノ内町」と表記）

## 独自の辞書を作成したい場合

辞書コンバータ [jageocoder-converter](https://github.com/t-sagara/jageocoder-converter) を利用してください。Version 2.0 系列の辞書を作成するには、 jageocoder-converter も 2.0 以降を利用する必要があります。

## 異体字を追加したい場合

特定の文字を別の文字に読み替えたい場合、異体字辞書に登録します。
詳細は `itaiji_dic/README.md` を参照してください。

## サンプルウェブアプリ

Flask を利用したシンプルなウェブアプリのサンプルが
`flask-demo` の下にあります。

次の手順を実行し、ポート 5000 にアクセスしてください。

```bash
cd flask-demo
pip install flask flask-cors
bash run.sh
```

## ご協力頂ける場合

日本の住所表記は非常に多様なので、うまく変換できない場合にはお知らせ頂けるとありがたいです。ロジックの改良提案も歓迎します。どのような住所がどう解析されるべきかをご連絡頂ければ幸いです。

## 作成者

* **相良 毅** - [株式会社情報試作室](https://www.info-proto.com/)

## 利用許諾条件

MIT ライセンスでご利用頂けます。

This project is licensed under [the MIT License](https://opensource.org/licenses/mit-license.php).

ただしこの利用許諾条件は住所辞書データに対しては適用されません。
各辞書データのライセンスを参照してください。

## 謝辞

20年以上にわたり、アドレスマッチングサービスを継続するために所内ウェブサーバを利用させて頂いている東京大学空間情報科学研究センターに感謝いたします。

また、NIIの北本朝展教授には、比較的古い住所体系を利用している地域の
大規模なサンプルのご提供と、解析結果の確認に多くのご協力を頂きましたことを感謝いたします。
