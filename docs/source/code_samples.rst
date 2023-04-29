コードサンプル
==============

ここでは jageocoder モジュールを Python コード内から
呼びだして利用する方法を、サンプルを用いて説明します。

.. _sample-geocoding:

住所から経緯度を調べる
----------------------

住所文字列を指定し、その住所の経緯度を調べる処理を実装します。

より厳密には、指定された住所文字列にもっとも長く一致するレコードを
住所辞書データベースから検索し、そのレコードに格納されている
経緯度の値を返します。

.. code-block:: python

   >>> import jageocoder
   >>> jageocoder.init()
   >>> results = jageocoder.searchNode('新宿区西新宿2-8-1')
   >>> if len(results) > 0:
   ...     print(results[0].node.x, results[0].node.y)
   ...
   139.691778 35.689627

:py:meth:`jageocoder.searchNode` は、
指定した住所文字列に最長一致すると解釈された
:py:class:`Result <jageocoder.result.Result>` クラスの
オブジェクトリストを返します。

.. code-block:: python

   >>> type(results[0])
   <class 'jageocoder.result.Result'>

このクラスのオブジェクトは、一致した文字列を
:py:attr:`matched <jageocoder.result.Result.matched>` 属性に、住所要素を
:py:attr:`node <jageocoder.result.Result.node>` 属性に持っています。

.. code-block:: python

   >>> results[0].matched
   '新宿区西新宿2-8-'
   >>> results[0].node
   [12111340:東京都(139.69178,35.68963)1(lasdec:130001/jisx0401:13)]>[12951429:新宿区(139.703463,35.69389)3(jisx0402:13104/postcode:1600000)]>[12976444:西新宿(139.697501,35.690383)5()]>[12977775:二丁目(139.691774,35.68945)6(aza_id:0023002/postcode:1600023)]>[12977785:8番(139.691778,35.689627)7(None)]

住所要素は :py:class:`AddressNode <jageocoder.node.AddressNode>`
クラスのオブジェクトなので、:py:attr:`x <jageocoder.node.AddressNode.x>`
属性に経度、 :py:attr:`y <jageocoder.node.AddressNode.y>` 属性に緯度、
:py:attr:`level <jageocoder.node.AddressNode.level>` 属性に住所レベルを持ちます。

.. code-block:: python

   >>> results[0].node.x
   139.691778
   >>> results[0].node.y
   35.689627
   >>> results[0].node.level
   7

住所レベルの数値の意味は :py:class:`jageocoder.address.AddressLevel`
の定義を参照してください。
この x, y を返すことで、住所に対応する経緯度を取得できます。

.. _sample-set-search-config:

住所検索条件を変更する
----------------------

:py:meth:`jageocoder.set_search_config` を利用すると、
住所検索の条件を変更することができます。

たとえば「中央区中央1」を検索すると、次のように
「千葉県千葉市」と「神奈川県相模原市」にある「中央区中央一丁目」の
住所が見つかります。

.. code-block:: python

   >>> import jageocoder
   >>> jageocoder.init()
   >>> results = jageocoder.searchNode('中央区中央1')
   >>> [''.join(x.node.get_fullname()) for x in results]
   ['千葉県千葉市中央区中央一丁目', '神奈川県相模原市中央区中央一丁目']

もし対象の住所が神奈川県にあることがあらかじめ分かっている場合には、
``target_area`` で検索範囲を神奈川県に指定しておくことで
千葉市の候補を除外できます。

.. code-block:: python

   >>> jageocoder.set_search_config(target_area=['神奈川県'])
   >>> results = jageocoder.searchNode('中央区中央1')
   >>> [''.join(x.node.get_fullname()) for x in results]
   ['神奈川県相模原市中央区中央一丁目']

設定した ``target_area`` を初期値に戻したい場合は ``[]`` を
セットしてください。また、設定条件を確認するには
:py:meth:`jageocoder.get_search_config` を呼んでください。

.. code-block:: python

   >>> jageocoder.set_search_config(target_area=[])
   >>> jageocoder.get_search_config()
   {
      'debug': False,
      'aza_skip': False,
      'best_only': True,
      'target_area': []
   }

.. _sample-reverse-geocoding:

経緯度から住所を調べる
----------------------

地点の経緯度を指定し、その地点の住所を調べます（リバースジオコーディング）。

より厳密には、指定した地点を囲む３点（ドロネー三角形の頂点）を
構成する住所の情報を取得し、一番目の点（最も指定した座標に近い点）の
住所表記を返します。

.. code-block:: python

   >>> import jageocoder
   >>> jageocoder.init()
   >>> triangle = jageocoder.reverse(139.6917, 35.6896)
   >>> if len(triangle) > 0:
   ...     print(triangle[0]['candidate']['fullname'])
   ...
   ['東京都', '新宿区', '西新宿', '二丁目']

:py:meth:`jageocoder.reverse` に ``level`` オプションパラメータを
指定すると、検索する住所のレベルを変更できます。

.. code-block:: python

   >>> triangle = jageocoder.reverse(139.6917, 35.6896, level=7)
   >>> if len(triangle) > 0:
   ...     print(triangle[0]['candidate']['fullname'])
   ...
   ['東京都', '新宿区', '西新宿', '二丁目', '8番']

.. note::

   リバースジオコーディング用のインデックスは、初めてリバース
   ジオコーディングを実行した時に自動的に作成されます。
   インデックスを削除したい場合は、辞書ディレクトリにある
   ``rtree.dat`` ``rtree.idx`` という 2 つのファイルを削除してください。

.. _sample-node-methods:

住所の属性情報を調べる
----------------------

:py:class:`AddressNode <jageocoder.node.AddressNode>`
クラスのオブジェクトには、
経緯度以外にもさまざまな属性やクラスメソッドがあります。

まず以下のコードで「新宿区西新宿2-8-1」に対応する住所要素の
AddressNode オブジェクトを node 変数に代入しておきます。

.. code-block:: python

   >>> import jageocoder
   >>> jageocoder.init()
   >>> results = jageocoder.searchNode('新宿区西新宿2-8-1')
   >>> node = results[0].node

**GeoJSON 表現**

:py:meth:`as_geojson() <jageocoder.node.AddressNode.as_geojson>`
メソッドを利用すると GeoJSON 表現を取得できます。
このメソッドが返すのは dict 形式のオブジェクトです。
GeoJSON 文字列を取得するには、 ``json.dumps()`` でエンコードしてください。

.. code-block:: python

   >>> import json
   >>> print(json.dumps(node.as_geojson(), indent=2, ensure_ascii=False))
   {
     "type": "Feature",
     "geometry": {
       "type": "Point",
       "coordinates": [
         139.691778,
         35.689627
       ]
     },
     "properties": {
       "id": 12977785,
       "name": "8番",
       "level": 7,
       "priority": 3,
       "note": null,
       "fullname": [
         "東京都",
         "新宿区",
         "西新宿",
         "二丁目",
         "8番"
       ]
     }
   }

**都道府県コード**

:py:meth:`get_pref_jiscode() <jageocoder.node.AddressNode.get_pref_jiscode>`
メソッドを利用すると JISX0401 で規定されている都道府県コード（2桁）を取得できます。
同様に、 :py:meth:`get_pref_local_authority_code() <jageocoder.node.AddressNode.get_pref_local_authority_code>`
メソッドでこの都道府県の団体コード（6桁）を取得できます。

.. code-block:: python

   >>> node.get_pref_jiscode()
   '13'
   >>> node.get_pref_local_authority_code()
   '130001'

**市区町村コード**

:py:meth:`get_city_jiscode() <jageocoder.node.AddressNode.get_city_jiscode>`
メソッドを利用すると
JISX0402 で規定されている市区町村コード（5桁）を取得できます。
同様に、 :py:meth:`get_city_local_authority_code() <jageocoder.node.AddressNode.get_city_local_authority_code()>`
メソッドでこの市区町村の団体コード（6桁）を取得できます。

.. code-block:: python

   >>> node.get_city_jiscode()
   '13104'
   >>> node.get_city_local_authority_code()
   '131041'

**アドレス・ベース・レジストリ**

:py:meth:`get_aza_code() <jageocoder.node.AddressNode.get_aza_code>` メソッドで、
この住所に対応するアドレス・ベース・レジストリの町字コードを取得できます。
:py:meth:`get_aza_names() <jageocoder.node.AddressNode.get_aza_names()>` メソッドで
町字レベルの名称（漢字表記、カナ表記、英字表記）を取得できます。

.. code-block:: python

   >>> node.get_aza_code()
   '131040023002'
   >>> node.get_aza_names()
   [[1, '東京都', 'トウキョウト', 'Tokyo', '13'], [3, '新宿区', 'シンジュクク', 'Shinjuku-ku', '13104'], [5, '西新宿', 'ニシシンジュク', '', '131040023'], [6, '二 丁目', '２チョウメ', '2chome', '131040023002']]

:py:meth:`get_aza_names() <jageocoder.node.AddressNode.get_aza_names()>` は
v1.3 から list オブジェクトを返すように変更されました。

**郵便番号**

:py:meth:`get_postcode() <jageocoder.node.AddressNode.get_postcode>` メソッドで
郵便番号を取得できます。ただし事業者郵便番号は登録されていません。

.. code-block:: python

   >>> node.get_postcode()
   '1600023'

**地図URLのリンク**

:py:meth:`get_gsimap_link() <jageocoder.node.AddressNode.get_gsimap_link>`
メソッドで地理院地図へのリンクURLを、
:py:meth:`get_googlemap_link() <jageocoder.node.AddressNode.get_googlemap_link>`
メソッドでGoogle 地図へのリンクURLを生成します。

これらのリンクは座標から生成しています。

.. code-block:: python

   >>> node.get_gsimap_link()
   'https://maps.gsi.go.jp/#16/35.689627/139.691778/'
   >>> node.get_googlemap_link()
   'https://maps.google.com/maps?q=35.689627,139.691778&z=16'

**親ノードを辿る**

「親ノード」とは、住所の一つ上の階層を表すノードのことです。
AddressNode の属性 :py:attr:`parent <jageocoder.node.AddressNode.parent>`
で取得できます。

今 node は '8番' を指しているので、親ノードは '二丁目' になります。

.. code-block:: python

   >>> parent = node.parent
   >>> parent.get_fullname()
   ['東京都', '新宿区', '西新宿', '二丁目']
   >>> parent.x, parent.y
   (139.691774, 35.68945)

**子ノードを辿る**

「子ノード」とは、住所の一つ下の階層を表すノードのことです。
AddressNode の属性 :py:attr:`children <jageocoder.node.AddressNode.children>`
で取得します。

親ノードは一つですが、子ノードは複数あります。
実際に返すのは SQL クエリオブジェクトですが、
イテレータでループしたり list にキャストできます。

今 parent は '二丁目' を指しているので、子ノードは
そこに含まれる街区レベル（○番）を持つノードのリストになります。

.. code-block:: python

   >>> parent.children
   <sqlalchemy.orm.dynamic.AppenderQuery object at 0x7f7d2f241438>
   >>> [child.name for child in parent.children]
   ['10番', '11番', '1番', '2番', '3番', '4番', '5番', '6番', '7番', '8番', '9番']

AddressNode のメソッドのより詳しい説明は API リファレンスの
:doc:`api_node` を参照してください。
