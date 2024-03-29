Jageocoder ドキュメント
=======================

**Jageocoder** は日本の住所ジオコーダーの一つです。
辞書と Python 解析用モジュールをローカルマシンにインストールすると、
オフラインでの住所ジオコーディングを行なうことができます。

.. code-block:: python

   >>> import jageocoder
   >>> jageocoder.init()
   >>> jageocoder.search('新宿区西新宿2-8-1')
   {'matched': '新宿区西新宿2-8-', 'candidates': [{'id': 5961406, 'name': '8番', 'x': 139.691778, 'y': 35.689627, 'level': 7, 'note': None, 'fullname': ['東京都', '新宿区', '西新宿', '二丁目', '8番']}]}


動作環境
--------

Python 3.7 以上がインストールされた、 Linux, Windows, MacOS
で動作します。


ライセンス表示
--------------

Copyright (c) 2021-2023 Takeshi SAGARA 相良 毅

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
