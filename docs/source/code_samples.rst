コードサンプル
==============

ここでは jageocoder モジュールを Python コード内から
呼びだして利用する方法を、サンプルを用いて説明します。

.. _sample-geocoding:

住所から経緯度を調べる
----------------------

住所文字列を指定し、その住所の経緯度を調べる処理を実装します。

より厳密には、指定された住所文字列にもっとも長く一致するレコードを
住所データベースから検索し、そのレコードに格納されている経緯度の値を返します。

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
「千葉県千葉市」、「神奈川県相模原市」、「静岡県浜松市」にある
「中央区中央一丁目」の住所が見つかります。

.. code-block:: python

   >>> import jageocoder
   >>> jageocoder.init()
   >>> results = jageocoder.searchNode('中央区中央1')
   >>> [x.node.get_fullname(" ") for x in results]
   ['千葉県 千葉市 中央区 中央 一丁目', '神奈川県 相模原市 中央区 中央 一丁目', '静岡県 浜松市 中央区 中央 一丁目']

もし対象の住所が神奈川県であることがあらかじめ分かっている場合には、
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
指定した地点を囲む最大３点の住所ノードを検索し、
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
指定すると検索する住所のレベルを指定できます。デフォルトでは
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
   この処理には辞書データーベースのサイズやマシン性能によって
   非常に長い時間がかかる (数十分) ので、辞書データベースのインストール後に
   ``jageocoder reverse 135 34`` のように実行して
   インデックスを構築しておくことをお勧めします。

   インデックスを削除したい場合は、辞書データベースのディレクトリにある
   ``rtree.dat`` ``rtree.idx`` という 2 つのファイルを削除してください。


.. _sample-node-methods:

住所の属性情報を調べる
----------------------

:py:class:`AddressNode <jageocoder.node.AddressNode>`
クラスのオブジェクトには、
経緯度以外にもさまざまな属性やクラスメソッドがあります。

まず以下のコードで「新宿区西新宿2-8-1」に対応する住所要素の
AddressNode オブジェクトを変数 ``node`` に代入しておきます。

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

:py:meth:`get_machiaza_id() <jageocoder.node.AddressNode.get_machiaza_id>` メソッドで、
この住所に対応するアドレス・ベース・レジストリの町字ID (7桁) を取得できます。
:py:meth:`get_aza_code() <jageocoder.node.AddressNode.get_aza_code>` メソッドで、
この住所に対応するアドレス・ベース・レジストリから計算した町字レベルのコード
(市区町村コード 5桁 + 町字ID 7桁) を取得できます。
:py:meth:`get_aza_names() <jageocoder.node.AddressNode.get_aza_names()>` メソッドで
町字レベルの名称（漢字表記、カナ表記、英字表記）を取得できます。

.. code-block:: python

   >>> node.get_machiaza_id()
   '0023002'
   >>> node.get_aza_code()
   '131040023002'
   >>> node.get_aza_names()
   [[1, '東京都', 'トウキョウト', 'Tokyo', '13'], [3, '新宿区', 'シンジュクク', 'Shinjuku-ku', '13104'], [5, '西新宿', 'ニシシンジュク', '', '131040023'], [6, '二 丁目', '２チョウメ', '2chome', '131040023002']]

.. note::

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

住所の属性から住所を検索する
----------------------------

郵便番号や自治体コードなどの属性から住所を検索することができます。

.. note::

   属性から住所を検索する機能は v2.1.7 で追加されました。

**郵便番号から住所を検索する**

:py:meth:`search_by_postcode() <jageocoder.search_by_postcode>`
メソッドで指定した郵便番号に対応する住所を検索し、
:py:class:`AddressNode <jageocoder.node.AddressNode>` のリストを返します。

.. code-block:: python

   >>> import jageocoder
   >>> jageocoder.init()
   >>> jageocoder.search_by_postcode('1600023')
   [{'id': 80225155, 'name': '八丁目', 'x': 139.6924591064453, 'y': 35.695777893066406, 'level': 6, 'priority': 2, 'note': 'aza_id:0023008/postcode:1600023', 'fullname': ['東京都', '新宿区', '西新宿', '八丁目']}, {'id': 80223785, 'name': '七丁目', 'x': 139.69723510742188, 'y': 35.695579528808594, 'level': 6, 'priority': 2, 'note': 'aza_id:0023007/postcode:1600023', 'fullname': ['東京都', '新宿区', ' 西新宿', '七丁目']}, {'id': 80222872, 'name': '六丁目', 'x': 139.6909637451172, 'y': 35.693424224853516, 'level': 6, 'priority': 2, 'note': 'aza_id:0023006/postcode:1600023', 'fullname': ['東京都', '新宿区', '西新宿', '六丁目']}, {'id': 80216496, 'name': '一丁目', 'x': 139.69749450683594, 'y': 35.69038391113281, 'level': 6, 'priority': 2, 'note': 'aza_id:0023001/postcode:1600023', 'fullname': ['東京都', '新宿区', '西新宿', '一丁目']}, {'id': 80217553, 'name': '二丁目', 'x': 139.6917724609375, 'y': 35.689449310302734, 'level': 6, 'priority': 2, 'note': 'aza_id:0023002/postcode:1600023', 'fullname': ['東京都', '新宿区', '西新宿', '二 丁目']}, {'id': 80221464, 'name': '五丁目', 'x': 139.68556213378906, 'y': 35.69288635253906, 'level': 6, 'priority': 2, 'note': 'aza_id:0023005/postcode:1600023', 'fullname': ['東京都', '新宿区', '西新宿', '五丁目']}, {'id': 80218874, 'name': '四丁目', 'x': 139.6876220703125, 'y': 35.687538146972656, 'level': 6, 'priority': 2, 'note': 'aza_id:0023004/postcode:1600023', 'fullname': ['東京都', '新宿区', '西新宿', '四丁目']}, {'id': 80217662, 'name': '三丁目', 'x': 139.68917846679688, 'y': 35.68452835083008, 'level': 6, 'priority': 2, 'note': 'aza_id:0023003/postcode:1600023', 'fullname': ['東京都', '新宿区', '西新宿', '三丁目']}]
   >>> jageocoder.search_by_postcode('1600023')[0].get_fullname()
   ['東京都', '新宿区', '西新宿', '八丁目']

**都道府県コードから住所を検索する**

:py:meth:`search_by_prefcode() <jageocoder.search_by_prefcode>`
メソッドで指定した都道府県コードに対応する住所を検索し、
:py:class:`AddressNode <jageocoder.node.AddressNode>`
のリストを返します。

都道府県コードは JISX0401 (2桁) または団体コード (6桁) で指定してください。

.. code-block:: python

   >>> jageocoder.search_by_prefcode('13')
   [{'id': 77147240, 'name': '東京都', 'x': 139.6917724609375, 'y': 35.68962860107422, 'level': 1, 'priority': 1, 'note': 'lasdec:130001/jisx0401:13', 'fullname': ['東京都']}]

**市区町村コードから住所を検索する**

:py:meth:`search_by_citycode() <jageocoder.search_by_citycode>`
メソッドで指定した市区町村コードに対応する住所を検索し、
:py:class:`AddressNode <jageocoder.node.AddressNode>`
のリストを返します。

市区町村コードは JISX0402 (5桁) または団体コード (6桁) で指定してください。

.. code-block:: python

   >>> jageocoder.search_by_citycode('13104')
   [{'id': 80117136, 'name': '新宿区', 'x': 139.70346069335938, 'y': 35.69388961791992, 'level': 3, 'priority': 1, 'note': 'geoshape_city_id:13104A1968/jisx0402:13104/postcode:1600000', 'fullname': ['東京都', '新宿区']}]

**町字IDから住所を検索する**

:py:meth:`search_by_machiaza_id() <jageocoder.search_by_machiaza_id>`
メソッドで指定した町字IDに対応する住所を検索し、
:py:class:`AddressNode <jageocoder.node.AddressNode>`
のリストを返します。

町字IDはアドレス・ベース・レジストリで定義されている 7桁の数字で指定できますが、
その場合は全国の自治体が対象になります。

対象市区町村を限定したい場合は先頭に市区町村コード (JISX0402 5桁または団体コード6桁)
を追加して 12桁 または 13桁 の数字を指定してください。

.. code-block:: python

   >>> [x.get_fullname('') for x in jageocoder.search_by_machiaza_id('0023002')]
   ['北海道北広島市白樺町二丁目', '山口県光市中島田二丁目', ... '東京都大田区西六郷二丁目', '福岡県福岡市博多区上牟田二丁目']
   >>> jageocoder.search_by_machiaza_id('131040023002')
   [{'id': 80217553, 'name': '二丁目', 'x': 139.6917724609375, 'y': 35.689449310302734, 'level': 6, 'priority': 2, 'note': 'aza_id:0023002/postcode:1600023', 'fullname': ['東京都', '新宿区', '西新宿', '二丁目']}]
