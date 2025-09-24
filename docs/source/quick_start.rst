クイックスタート
================

ここでは Python 3.9.2 以上がインストール済みの
Linux, Windows, MacOS 上に、 jageocoder をインストールして
基本的なジオコーディング処理を行なうまでの一連の作業を示します。

以下の手順では省略していますが、 ``venv``  などを使って
仮想環境を作成することをお勧めします。
また、 ``python`` コマンドは環境によって ``python3`` に
読み替えてください。


インストール
------------

``pip`` (または ``pip3`` ) コマンドで jageocoder パッケージをインストールします。

.. code-block:: console

   $ pip install jageocoder

より詳細なインストール手順やアンインストールの方法については
:doc:`install` を参照してください。

.. note::

   住居表示や地番の位置参照情報の整備が進んだことにより、
   辞書データベースのサイズが大きくなってしまったため、
   Ver. 2.1.6 より辞書データベースをインストールしなくても
   Jageocoder サーバに接続して処理を行えるようになりました。
   :ref:`server-or-dictionary` を参照してください。

コマンドラインで実行
--------------------

Jageocoder は主に Python プログラム内から呼びだすライブラリとして
利用することを想定していますが、シェルスクリプトや他の言語から
コマンドを実行して利用することもできます。

.. code-block:: console

   $ jageocoder search --url=https://jageocoder.info-proto.com/jsonrpc '新宿区西新宿２－８－１'
   {"matched": "新宿区西新宿２－８－", "candidates": [{"id": 12977785, "name": "8番", "x": 139.691778, "y": 35.689627, "level": 7, "priority": 3, "note": null, "fullname": ["東京都", "新宿区", "西新宿", "二丁目", "8番"]}]}

   $ jageocoder reverse --url=https://jageocoder.info-proto.com/jsonrpc 139.691778 35.689627
   [{"candidate": {"fullname": ["東京都", "新宿区", "西新宿", "二丁目"], "id": 80217626, "level": 6, "name": "二丁目", "note": "aza_id:0023002/postcode:1600023", "priority": 2, "x": 139.6917724609375, "y": 35.689449310302734}, "dist": 19.721624552843714}, {"candidate": {"fullname": ["東京都", "新宿区", "西新宿", "六丁目"], "id": 80222945, "level": 6, "name": "六丁目", "note": "aza_id:0023006/postcode:1600023", "priority": 2, "x": 139.6909637451172, "y": 35.693424224853516}, "dist": 427.71233368734613}, {"candidate": {"fullname": ["東京都", "新宿区", "西新宿", "一丁目"], "id": 80216569, "level": 6, "name": "一丁目", "note": "aza_id:0023001/postcode:1600023", "priority": 2, "x": 139.69749450683594, "y": 35.69038391113281}, "dist": 524.2019773820475}]

上記以外のコマンドについては :doc:`command_line` を参照してください。

Python コードで実行
-------------------

Python プログラム内でジオコーディングを行ないます。

.. code-block:: python

   >>> import json
   >>> import jageocoder
   >>> jageocoder.init(url='https://jageocoder.info-proto.com/jsonrpc')
   >>> results = jageocoder.search('新宿区西新宿２－８－１')
   >>> print(json.dumps(results, indent=2, ensure_ascii=False))
   {
     "matched": "新宿区西新宿２－８－",
     "candidates": [
       {
         "id": 80223284,
         "name": "8番",
         "x": 139.6917724609375,
         "y": 35.68962860107422,
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
     ]
   }

Python プログラム内でリバースジオコーディングを行ないます。

.. code-block:: python

   >>> import json
   >>> import jageocoder
   >>> jageocoder.init(url='https://jageocoder.info-proto.com/jsonrpc')
   >>> results = jageocoder.reverse(139.691772, 35.689628, level=7)
   >>> print(json.dumps(results, indent=2, ensure_ascii=False))
   [
     {
       "candidate": {
         "fullname": [
           "東京都",
           "新宿区",
           "西新宿",
           "二丁目",
           "8番"
         ],
         "id": 80223284,
         "level": 7,
         "name": "8番",
         "note": "",
         "priority": 3,
         "x": 139.6917724609375,
         "y": 35.68962860107422
       },
       "dist": 0.07866663127258333
     },
     {
       "candidate": {
         "fullname": [
           "東京都",
           "新宿区",
           "西新宿",
           "二丁目",
           "9番"
         ],
         "id": 80223286,
         "level": 7,
         "name": "9番",
         "note": "",
         "priority": 3,
         "x": 139.692138671875,
         "y": 35.688079833984375
       },
       "dist": 174.95110253904488
     },
     {
       "candidate": {
         "fullname": [
           "東京都",
           "新宿区",
           "西新宿",
           "二丁目",
           "10番"
         ],
         "id": 80223182,
         "level": 7,
         "name": "10番",
         "note": "",
         "priority": 3,
         "x": 139.689697265625,
         "y": 35.687679290771484
       },
       "dist": 286.38673495897797
     }
   ]

Python コードから Jageocoder の API を利用するより詳しい例は
:doc:`code_samples` を参照してください。
