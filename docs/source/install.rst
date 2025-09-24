.. _installation:

インストール手順
================

.. _install-package:

パッケージのインストール手順
----------------------------

``pip`` コマンドでインストールできます。

.. code-block:: console

   $ pip install jageocoder

バージョンを指定したい場合は ``==`` に続けてバージョン番号を指定してください。

.. code-block:: console

   $ pip install jageocoder==2.1.10

.. _server-or-dictionary:


Jageocoder サーバと住所データベース
-----------------------------------

``pip`` コマンドでインストールされる jageocoder パッケージには住所データベースは含まれていません。
住所データベースを利用するには次の2通りの方法があります。

- Jageocoder サーバを利用する
- 「住所データベースファイル」をインストールする

:doc:`quick_start` では Jageocoder をすぐに試すために、 ``url`` パラメータを指定して検索処理を
`デモンストレーション用 Jageocoder サーバ <https://jageocoder.info-proto.com/>`_
上で実行しています。これが1番目の方法です。

この方法はローカルマシンに住所データベースをインストールする必要がないので手軽ですが、
通信にかかる時間の分だけ遅くなったり、
サーバがメンテナンス等の事情により応答できないことがあるという欠点があります。
大量の住所を処理する必要がある場合や、個人情報などを外部に送信したくない場合は、
2番目の方法を選択してください。

.. note::

   デモンストレーション用サーバは1秒あたりのリクエスト数に制限をかけています。
   デモンストレーション用サーバの代わりに専用の Jageocoder サーバを
   独自に設置したい場合は
   https://github.com/t-sagara/jageocoder-server
   を参照してください。

.. _install-dictionary:

住所データベースファイルのインストール手順
------------------------------------------

住所データベースファイルは zip 形式でダウンロード可能です。
`住所データベースファイル一覧 <https://www.info-proto.com/static/jageocoder/latest/>`_
から、最新のものを選択してダウンロードしてください。

住所データベースは jageocoder のバージョンによってフォーマットが異なるため、
v1 用, v2.1 用のファイルは利用できません。v2.2 に対応する住所データベースファイルは
末尾が ``_v22.zip`` です。

.. code-block:: console

    $ jageocoder download-dictionary https://www.info-proto.com/static/jageocoder/20250423/v2/jukyo_all_20250423_v22.zip

次にダウンロードした zip ファイルをインストールします。

.. code-block:: console

    $ jageocoder install-dictionary jukyo_all_20250423_v22.zip

.. note::

   2025年9月の時点で、全国の住居表示と地番の住所を含む住所データベースファイルは
   4.5GB 以上、展開すると 20GB 以上になり、ストレージにその分の空きが必要です。

.. _uninstallation:

アンインストール手順
--------------------

Jageocoder をアンインストールする場合、先に住所データベースを削除してください。

住所データベースの場所が分かっている場合はそのディレクトリごと
削除しても構いませんが、 ``uninstall-dictionary`` コマンドを
利用すると簡単に削除できます。

.. code-block:: console

    $ jageocoder uninstall-dictionary

その後、 jageocoder パッケージを pip でアンインストールしてください。

.. code-block:: console

    $ pip uninstall jageocoder

.. note::

   Jageocoder の「住所データベース」の実体はランダムアクセス可能な
   バイナリデータファイルの集合です。 RDBMS は利用していません。


.. _db_priority:

接続先の優先順位
----------------

Jageocoder が利用する住所データベース、 Jageocoder サーバは次の順番に決定されます。

- ``--db-dir=`` (コマンドの場合)・ ``db_dir=`` (Python APIの場合) オプションで指定された住所データベースディレクトリ
- ``--url=`` (コマンドの場合)・ ``url=`` (Python APIの場合) オプションで指定された Jageocoder サーバの URL
- 環境変数 ``JAGEOCODER_DB2_DIR`` で指定された住所データベースディレクトリ
- 環境変数 ``JAGEOCODER_SERVER_URL`` で指定された Jageocoder サーバの URL
- Python 環境内の所定のディレクトリ (参考： :ref:`commandline-get-db-dir`)

.. code-block:: console

   $ export JAGEOCODER_SERVER_URL=https://jageocoder.info-proto.com/jsonrpc
   $ jageocoder search '新宿区西新宿２－８－１'  # デモンストレーション用サーバを利用します
   $ export JAGEOCODER_DB2_DIR=~/jageocoder/db2/
   $ jageocoder search '新宿区西新宿２－８－１'  # 指定した住所データベースを利用します
   $ jageocoder search --url=http://localhost:5000/jsonrpc '新宿区西新宿２－８－１'  # ローカルマシン上のサーバを利用します

.. note::

   もし ``JAGEOCODER_DB2_DIR`` と ``JAGEOCODER_SERVER_URL`` が両方ともセットされている場合、 ``JAGEOCODER_DB2_DIR`` が優先されます。
   ``JAGEOCODER_DB2_DIR`` が指すディレクトリに住所データベースが見つからないとエラーになります。
