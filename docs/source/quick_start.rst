クイックスタート
================

ここでは Python 3.6 以上がインストール済みの
Linux, Windows, MacOS 上に、 jageocoder をインストールして
基本的なジオコーディング処理を行なうまでの一連の作業を示します。

以下の手順では省略しますが、 venv による仮想環境をお勧めします。
また、 `python` インタープリタは環境によっては `python3` と
入力する必要がある場合があります。


インストール
------------

`pip` (または pip3) で jageocoder パッケージをインストールします。
次に、住所辞書をダウンロードしてインストールします。

.. code-block:: console

   $ pip install jageocoder
   $ python -m jageocoder install-dictionary

より詳細なインストール手順やアンインストールの方法については
:doc:`install` を参照してください。


コマンドラインでジオコーディング
--------------------------------

Jageocoder は Python プログラムから呼びだして利用することを
想定していますが、コマンドライン用のインタフェースから
利用することもできます。

.. code-block:: console

   $ python -m jageocoder search '新宿区西新宿２－８－１'
   {"matched": "新宿区西新宿２－８－", "candidates": [{"id": 12977785, "name": "8番", "x": 139.691778, "y": 35.689627, "level": 7, "priority": 3, "note": null, "fullname": ["東京都", "新宿区", "西新宿", "二丁目", "8番"]}]}


コマンドラインで逆ジオコーディング
----------------------------------

同様に逆ジオコーディング（経緯度から住所を取得）もできます。

.. code-block:: console

   $ python -m jageocoder reverse 139.6917 35.6896
   [{"candidate": {"id": 12977775, "name": "二丁目", "x": 139.691774, "y": 35.68945, "level": 6, "priority": 2, "note": "aza_id:0023002/postcode:1600023", "fullname": ["東京都", "新宿区", "西新宿", "二丁目"]}, "dist": 17.940303970792183}, {"candidate": {"id": 12978643, "name": "六丁目", "x": 139.690969, "y": 35.693426, "level": 6, "priority": 2, "note": "aza_id:0023006/postcode:1600023", "fullname": ["東京都", "新宿区", "西新宿", "六丁目"]}, "dist": 429.6327545403412}, {"candidate": {"id": 12978943, "name": "四丁目", "x": 139.68762, "y": 35.68754, "level": 6, "priority": 2, "note": "aza_id:0023004/postcode:1600023", "fullname": ["東京 都", "新宿区", "西新宿", "四丁目"]}, "dist": 434.31591285255234}]


ジオコーディングの簡単なコード
------------------------------

Python プログラムから呼びだしてジオコーディングを行ないます。

.. code-block:: python

   >>> import jageocoder
   >>> jageocoder.init()
   >>> import jageocoder
   >>> jageocoder.search('新宿区西新宿２－８－１')
   {'matched': '新宿区西新宿２－８－', 'candidates': [{'id': 12977785, 'name': '8番', 'x': 139.691778, 'y': 35.689627, 'level': 7, 'priority': 3, 'note': None, 'fullname': ['東京都', '新宿区', '西新宿', '二丁目', '8番']}]}


逆ジオコーディングの簡単なコード
--------------------------------

Python プログラムから呼びだして逆ジオコーディングを行ないます。

.. code-block:: python

   >>> import jageocoder
   >>> jageocoder.init()
   >>> import jageocoder
   >>> jageocoder.reverse('新宿区西新宿２－８－１')
   >>> jageocoder.reverse(139.6917, 35.6896)
   [{'candidate': {'id': 12977775, 'name': '二丁目', 'x': 139.691774, 'y': 35.68945, 'level': 6, 'priority': 2, 'note': 'aza_id:0023002/postcode:1600023', 'fullname': ['東京都', '新宿区', '西新宿', '二丁目']}, 'dist': 17.940303970792183}, {'candidate': {'id': 12978643, 'name': '六丁目', 'x': 139.690969, 'y': 35.693426, 'level': 6, 'priority': 2, 'note': 'aza_id:0023006/postcode:1600023', 'fullname': ['東京都', '新宿区', '西新宿', '六丁目']}, 'dist': 429.6327545403412}, {'candidate': {'id': 12978943, 'name': '四丁目', 'x': 139.68762, 'y': 35.68754, 'level': 6, 'priority': 2, 'note': 'aza_id:0023004/postcode:1600023', 'fullname': ['東京 都', '新宿区', '西新宿', '四丁目']}, 'dist': 434.31591285255234}]
