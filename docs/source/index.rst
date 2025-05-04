Jageocoder ドキュメント
=======================

**Jageocoder** は日本の住所のジオコーディング・リバースジオコーディングを行う Python パッケージです。
住所を解析して経緯度を求めたり（ジオコーディング）、
逆に経緯度から対応する住所を検索（リバースジオコーディング）することができます。

.. code-block:: python

   >>> import jageocoder
   >>> jageocoder.init()
   >>> jageocoder.search('新宿区西新宿2-8-1')
   {'matched': '新宿区西新宿2-8-', 'candidates': [{'id': 80217731, 'name': '8番', 'x': 139.6917724609375, 'y': 35.68962860107422, 'level': 7, 'priority': 3, 'note': '', 'fullname': ['東京都', '新宿区', '西新宿', '二丁目', '8番']}]}
   >>> jageocoder.reverse(139.691772, 35.689628, level=7)[0]
   {'candidate': {'id': 80217731, 'name': '8番', 'x': 139.6917724609375, 'y': 35.68962860107422, 'level': 7, 'priority': 3, 'note': '', 'fullname': ['東京都', '新 宿区', '西新宿', '二丁目', '8番']}, 'dist': 0.07866663127258333}


動作環境
--------

Python 3.8 以上がインストールされた Linux, Windows, MacOS で動作します。


ライセンス表示
--------------

Copyright (c) 2021-2024 Takeshi SAGARA 相良 毅

`MIT ライセンス <https://opensource.org/licenses/mit-license.php>`_
で利用できます。

ただしこのライセンスは住所データベースで利用している
辞書データに対しては適用されません。
辞書データの利用条件・ライセンスは、それぞれの辞書データの
提供元が設定した条件に従いますので、住所データベースを
インストールしたディレクトリの ``README.md`` を確認してください。


目次
----

.. toctree::

   quick_start
   install
   command_line
   code_samples
   api
