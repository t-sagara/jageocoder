クイックスタート
================

ここでは Python 3.7 以上がインストール済みの
Linux, Windows, MacOS 上に、 jageocoder をインストールして
基本的なジオコーディング処理を行なうまでの一連の作業を示します。

以下の手順では省略していますが、 ``venv``  などを使って
仮想環境を作成することをお勧めします。
また、 ``python`` コマンドは環境によって ``python3`` に
読み替えてください。


インストール
------------

``pip`` (または ``pip3`` ) コマンドで jageocoder パッケージをインストールします。
次に、住所辞書をダウンロードしてインストールします。

.. code-block:: console

   $ pip install jageocoder
   $ jageocoder download-dictionary https://www.info-proto.com/static/jageocoder/latest/v2/jukyo_all_v21.zip
   $ jageocoder install-dictionary jukyo_all_v21.zip

より詳細なインストール手順やアンインストールの方法については
:doc:`install` を参照してください。


コマンドラインでジオコーディング
--------------------------------

Jageocoder は Python プログラム内から呼びだすパッケージとして
利用することを想定していますが、コマンドライン・インタフェースから
利用することもできます。

.. code-block:: console

   $ jageocoder search '新宿区西新宿２－８－１'
   {"matched": "新宿区西新宿２－８－", "candidates": [{"id": 12977785, "name": "8番", "x": 139.691778, "y": 35.689627, "level": 7, "priority": 3, "note": null, "fullname": ["東京都", "新宿区", "西新宿", "二丁目", "8番"]}]}

ジオコーディングの簡単なコード
------------------------------

Python プログラムから呼びだしてジオコーディングを行ないます。

.. code-block:: python

   >>> import json
   >>> import jageocoder
   >>> jageocoder.init()
   >>> results = jageocoder.search('新宿区西新宿２－８－１')
   >>> print(json.dumps(results, indent=2, ensure_ascii=False))
   {
     "matched": "新宿区西新宿２－８－",
     "candidates": [
       {
         "id": 12977785,
         "name": "8番",
         "x": 139.691778,
         "y": 35.689627,
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
     ]
   }

Python コードから jageocoder を利用するより詳しい方法は
:doc:`code_samples` を参照してください。
