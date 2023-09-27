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
   139.6917724609375 35.68962860107422

:py:meth:`jageocoder.searchNode` は、
指定した住所文字列に最長一致すると解釈された
:py:class:`Result <jageocoder.result.Result>` クラスの
オブジェクトリストを返します。

.. code-block:: python

   >>> type(results[0])
   <class 'jageocoder.result.Result'>

このクラスのオブジェクトは、一致した文字列を
:py:attr:`matched <jageocoder.result.Result.matched>` 属性に、住所ノードを
:py:attr:`node <jageocoder.result.Result.node>` 属性に持っています。

.. code-block:: python

   >>> results[0].matched
   '新宿区西新宿2-8-'
   >>> results[0].node
   {'id': 50357162, 'name': '8番', 'x': 139.6917724609375, 'y': 35.68962860107422, 'level': 7, 'priority': 3, 'note': '', 'fullname': ['東京都', '新宿区', '西新宿', '二丁目', '8番']}

住所ノードは :py:class:`AddressNode <jageocoder.node.AddressNode>`
クラスのオブジェクトなので、:py:attr:`x <jageocoder.node.AddressNode.x>`
属性に経度、 :py:attr:`y <jageocoder.node.AddressNode.y>` 属性に緯度、
:py:attr:`level <jageocoder.node.AddressNode.level>` 属性に住所レベルを持ちます。

.. code-block:: python

   >>> results[0].node.x
   139.6917724609375
   >>> results[0].node.y
   35.68962860107422
   >>> results[0].node.level
   7

住所レベルの数値の意味は :py:class:`jageocoder.address.AddressLevel`
の定義を参照してください。


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
   >>> [x.node.get_fullname(" ") for x in results]
   ['千葉県 千葉市 中央区 中央 一丁目', '神奈川県 相模原市 中央区 中央 一丁目']

もし対象の住所が神奈川県にあることがあらかじめ分かっている場合には、
``target_area`` で検索範囲を神奈川県に指定しておくことで
千葉市の候補を除外できます。

.. code-block:: python

   >>> jageocoder.set_search_config(target_area=['神奈川県'])
   >>> results = jageocoder.searchNode('中央区中央1')
   >>> [x.node.get_fullname(" ") for x in results]
   ['神奈川県 相模原市 中央区 中央 一丁目']

設定した ``target_area`` を初期値に戻したい場合は ``[]`` または
``None`` をセットしてください。また、設定条件を確認するには
:py:meth:`jageocoder.get_search_config` を呼んでください。

.. code-block:: python

   >>> jageocoder.set_search_config(target_area=[])
   >>> jageocoder.get_search_config()
   {
      'debug': False,
      'aza_skip': None,
      'best_only': True,
      'target_area': [],
      'require_coordinates': True,
      'auto_redirect': True
   }


.. _sample-reverse-geocoding:

経緯度から住所を調べる
----------------------

地点の経緯度を指定し、その地点の住所を調べることができます
（いわゆるリバースジオコーディング）。

:py:meth:`jageocoder.reverse` に調べたい地点の経度と緯度を渡すと、
指定した地点を囲むドロネー三角形を構成する住所ノードを検索し、
住所ノードを ``candidate``、指定した地点からの距離を ``dist`` に持つ
dict の list を返します。

.. code-block:: python

   >>> import jageocoder
   >>> jageocoder.init()
   >>> triangle = jageocoder.reverse(139.6917, 35.6896)
   >>> if len(triangle) > 0:
   ...     print(triangle[0]['candidate']['fullname'])
   ...
   ['東京都', '新宿区', '西新宿', '二丁目']

:py:meth:`jageocoder.reverse` に ``level`` オプションパラメータを
指定すると、検索する住所のレベルを指定できます。デフォルトでは
字レベル (6) なので、街区・地番レベルで検索したい場合は 7 を、
号・枝番レベルまで検索したい場合は 8 を指定してください。

.. code-block:: python

   >>> triangle = jageocoder.reverse(139.6917, 35.6896, level=7)
   >>> if len(triangle) > 0:
   ...     print(triangle[0]['candidate']['fullname'])
   ...
   ['東京都', '新宿区', '西新宿', '二丁目', '8番']

.. note::

   リバースジオコーディング用のインデックスは、初めてリバース
   ジオコーディングを実行した時に自動的に作成されます。
   この処理には辞書データーベースのサイズによっては非常に長い
   時間がかかる（1時間以上）ので、辞書データベースのインストール後に
   ``jageocoder reverse 135 34`` のように実行して構築しておくことを
   お勧めします。

   インデックスを削除したい場合は、辞書データベースのディレクトリにある
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
   >>> print(json.dumps(node.as_geojson(), indent=4, ensure_ascii=False))
   {
      "type": "Feature",
      "geometry": {
         "type": "Point",
         "coordinates": [
               139.6917724609375,
               35.68962860107422
         ]
      },
      "properties": {
         "id": 50357162,
         "name": "8番",
         "level": 7,
         "priority": 3,
         "note": "",
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
郵便番号を取得できます。ただしビルや事業者の郵便番号は登録されていません。

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
   'https://maps.gsi.go.jp/#16/35.689629/139.691772/'
   >>> node.get_googlemap_link()
   'https://maps.google.com/maps?q=35.689629,139.691772&z=16'

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
   (139.6917724609375, 35.689449310302734)

**子ノードを辿る**

「子ノード」とは、住所の一つ下の階層を表すノードのことです。
AddressNode の属性 :py:attr:`children <jageocoder.node.AddressNode.children>`
で取得します。

親ノードは一つですが、子ノードは複数あります。
今 parent は '二丁目' を指しているので、子ノードは
そこに含まれる街区レベル（○番）を持つノードのリストになります。

.. code-block:: python

   >>> parent.children
   [{'id': 50357153, 'name': '1番', 'x': 139.6939239501953, 'y': 35.6916618347168, 'level': 7, 'priority': 3, 'note': '', 'fullname': ['東京都', '新宿区', '西新宿', '二丁目', '1番']}, {'id': 50357154, 'name': '10番', 'x': 139.689697265625, 'y': 35.687679290771484, 'level': 7, 'priority': 3, 'note': '', 'fullname': ['東京都', '新宿区', '西新宿', '二丁目', '10番']}, {'id': 50357155, 'name': '11番', 'x': 139.6876983642578, 'y': 35.691104888916016, 'level': 7, 'priority': 3, 'note': '', 'fullname': ['東京都', '新宿区', '西新宿', '二丁目', '11番']}, {'id': 50357156, 'name': '2番', 'x': 139.6943359375, 'y': 35.68998718261719, 'level': 7, 'priority': 3, 'note': '', 'fullname': ['東京都', '新宿区', '西新宿', '二丁目', '2番']}, {'id': 50357157, 'name': '3番', 'x': 139.6947784423828, 'y': 35.68826675415039, 'level': 7, 'priority': 3, 'note': '', 'fullname': ['東京都', '新宿区', '西新宿', '二丁目', '3番']}, {'id': 50357158, 'name': '4番', 'x': 139.69332885742188, 'y': 35.688148498535156, 'level': 7, 'priority': 3, 'note': '', 'fullname': ['東京都', '新宿区', '西新宿', '二丁目', '4番']}, {'id': 50357159, 'name': '5番', 'x': 139.69297790527344, 'y': 35.68976593017578, 'level': 7, 'priority': 3, 'note': '', 'fullname': ['東京都', '新宿区', '西新宿', '二丁目', '5番']}, {'id': 50357160, 'name': '6番', 'x': 139.6924591064453, 'y': 35.6920166015625, 'level': 7, 'priority': 3, 'note': '', 'fullname': ['東京都', '新宿区', '西新宿', '二丁目', '6番']}, {'id': 50357161, 'name': '7番', 'x': 139.69137573242188, 'y': 35.691253662109375, 'level': 7, 'priority': 3, 'note': '', 'fullname': ['東京都', '新宿区', '西新宿', '二丁目', '7番']}, {'id': 50357162, 'name': '8番', 'x': 139.6917724609375, 'y': 35.68962860107422, 'level': 7, 'priority': 3, 'note': '', 'fullname': ['東京都', '新宿区', '西新宿', '二丁目', '8番']}, {'id': 50357163, 'name': '9番', 'x': 139.692138671875, 'y': 35.688079833984375, 'level': 7, 'priority': 3, 'note': '', 'fullname': ['東京都', '新宿区', '西新宿', '二丁目', '9番']}]
   >>> [child.name for child in parent.children]
   ['1番', '10番', '11番', '2番', '3番', '4番', '5番', '6番', '7番', '8番', '9番']

AddressNode のメソッドのより詳しい説明は API リファレンスの
:doc:`api_node` を参照してください。
