コマンドライン・インタフェース
==============================

ここでは jageocoder モジュールをコマンドラインから呼びだして
利用する方法を説明します。

同じ内容はオンラインヘルプでも確認できます。

.. code-block:: console

   (.venv) $ jageocoder -h

.. _commandline-geocoding:

ジオコーディング
----------------

住所文字列をキーとして住所辞書データベースを検索し、
先頭から最長一致すると解釈できるレコードを取得し、
そのレコードの経緯度を含む情報を返します。

最長一致する長さが同じ候補が複数存在する場合、全ての候補を返します。

コマンド
   ``search``

パラメータ
   住所文字列

オプション
   ``-d`` デバッグ情報を表示します。

   ``--area=<area>`` 検索する都道府県や市区町村を指定します。
   省略した場合は全国を対象とします。複数の都道府県・市区町村を
   指定する場合は ``,`` で区切ります。

   ``--db-dir=<dir>`` 住所辞書データベースを配置したディレクトリを
   指定します。

**実行例**

.. code-block:: console

   # 「落合１－１５－２」を検索します。
   # 「栃木県下都賀郡壬生町落合一丁目15番2号」と
   # 「広島県広島市安佐北区落合一丁目15番2号」が返ります。
   (.venv) $ jageocoder search '落合１－１５－２'
   {"matched": "落合１－１５－２", "candidates": [{"id": 6894076, "name": "2号", "x": 139.820208258, "y": 36.450565089, "level": 8, "priority": 4, "note": null, "fullname": ["栃木県", "下都賀郡", "壬生町", "落合", "一丁目", "15番", "2号"]}, {"id": 34195069, "name": "2号", "x": 132.510432116, "y": 34.473211622, "level": 8, "priority": 4, "note": null, "fullname": ["広島県", "広島市", "安佐北区", "落合", "一丁目", "15番", "2号"]}]}

   # 「落合１－１５－２」を東京都から検索します。
   # 「東京都多摩市落合一丁目15番地」が返ります。
   (.venv) $ jageocoder search --area=東京都 '落合１－１５－２'
   {"matched": "落合１－１５－", "candidates": [{"id": 12724450, "name": "15番地", "x": 139.428969, "y": 35.625779, "level": 7, "priority": 3, "note": null, "fullname": ["東京都", "多摩市", "落合", "一丁目", "15番地"]}]}

.. _commandline-reverse-geocoding:

逆ジオコーディング
------------------

この機能は v2 では利用できません。

.. _commandline-get-db-dir:

住所辞書ディレクトリの取得
--------------------------

実行中の Python 環境で、住所辞書データベースがインストールされている
ディレクトリを取得します。

辞書データベースは ``{sys.prefix}/jageocoder/db2/`` の下に
作成されますが、ユーザが書き込み権限を持っていない場合には
``{site.USER_DATA}/jageocoder/db2/`` に作成されます。

上記以外の任意の場所を指定したい場合、環境変数 ``JAGEOCODER_DB2_DIR``
でディレクトリを指定することができます。

コマンド
   ``get-db-dir``

パラメータ
   （なし）

オプション
   ``-d`` デバッグ情報を表示します。

**実行例**

.. code-block:: console

   (.venv) $ jageocoder get-db-dir
   /home/sagara/.local/share/virtualenvs/jageocoder-kWBL7Ve6/jageocoder/db2/

.. _commandline-download-dictionary:

住所辞書ファイルのダウンロード
------------------------------

住所データベースファイルをウェブからダウンロードします。
v2 より URL は省略不可になりました。

`住所データベースファイル <https://www.info-proto.com/static/jageocoder/latest/v2/>`_
のリストからダウンロードするファイルを選択し、その URL を指定してください。

このコマンドは ``curl`` や ``wget`` コマンドなどが利用できない場合を
想定して用意しているので、任意の方法でダウンロードして構いません。


コマンド
   ``download-dictionary``

パラメータ
   ``<url>`` ダウンロードする URL を指定します（省略不可）。

オプション
   ``-d`` デバッグ情報を表示します。

**実行例**

.. code-block:: console

   # 街区レベルまでの全国住所辞書ファイルをダウンロードします
   (.venv) $ jageocoder download-dictionary https://www.info-proto.com/static/jageocoder/latest/v2/gaiku_all_v20.zip

.. _commandline-install-dictionary:

住所辞書ファイルのインストール
------------------------------

住所辞書ファイルを展開し、住所辞書データベースを作ります。

コマンド
   ``install-dictionary``

パラメータ
   ``<path>`` インストールする住所辞書ファイルのパスを指定します（省略不可）。

オプション
   ``-d`` デバッグ情報を表示します。

   ``--db-dir`` 住所辞書データベースを作るディレクトリを
   指定します。

**実行例**

.. code-block:: console

   # ダウンロード済みの住所辞書ファイルをインストールします
   (.venv) $ jageocoder install-dictionary gaiku_all_v20.zip

.. _commandline-uninstall-dictionary:

住所辞書ファイルのアンインストール
----------------------------------

住所辞書データベースをアンインストールします。

コマンド
   ``uninstall-dictionary``

パラメータ
   （なし）

オプション
   ``-d`` デバッグ情報を表示します。

   ``--db-dir=<dir>`` 住所辞書データベースのディレクトリを指定します。

**実行例**

.. code-block:: console

   # 住所辞書データベースをアンインストールします
   (.venv) $ jageocoder uninstall-dictionary
   INFO:jageocoder.module:248:Removing directory ...
   INFO:jageocoder.module:251:Dictionary has been uninstalled.

.. _commandline-migrate-dictionary:

住所辞書ファイルのマイグレーション
----------------------------------

この機能は v2 で廃止になりました。
