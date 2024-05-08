.. _installation:

インストール手順
================

.. _install-package:

パッケージのインストール
------------------------

``pip`` コマンドでインストールできます。

.. code-block:: console

   $ pip install jageocoder

バージョンを指定したい場合は ``==`` に続けてバージョン番号を指定してください。

.. code-block:: console

   $ pip install jageocoder==2.1.6.post1

.. _server-or-dictionary:

Jageocoder サーバと住所データベース
-----------------------------------

:doc:`quick_start` では Jageocoder をすぐに試すために、
``url`` パラメータを指定して検索処理を
`デモンストレーション用 Jageocoder サーバ <https://jageocoder.info-proto.com/>`_
上で実行しています。

この方法はローカルマシンに住所データをインストールする必要がないので手軽ですが、
通信にかかる時間の分だけ遅くなったり、サーバがメンテナンス等の事情により
応答できないことがあるという欠点があります。
大量の住所を処理する必要がある場合や、個人情報など外部に送信したくない場合は、
:ref:`install-dictionary` 以降の手順に従って住所データベースをインストールしてください。

なお、コマンドラインや API で Jageocoder サーバを利用する場合は
:doc:`quick_start` のように明示的に ``url`` パラメータを指定してもよいですが、
環境変数 ``JAGEOCODER_SERVER_URL`` にエンドポイント URL をセットしておくと
``url`` パラメータを省略可能です。

.. code-block:: console

   $ export JAGEOCODER_SERVER_URL=https://jageocoder.info-proto.com/jsonrpc
   $ jageocoder search '新宿区西新宿２－８－１'  # 指定したサーバを利用します

.. note::

   デモンストレーション用サーバはリクエストに制限をかけています。
   デモンストレーション用サーバの代わりに専用の Jageocoder サーバを
   独自に設置したい場合は
   https://github.com/t-sagara/jageocoder-server
   を参照してください。

.. _install-dictionary:

住所データベースファイルのインストール
--------------------------------------

住所データベースファイルは zip 形式でダウンロード可能です。
`住所データベースファイル一覧 <https://www.info-proto.com/static/jageocoder/latest/>`_
から、最新のものを選択してダウンロードしてください。

住所データベースは jageocoder のバージョンによってフォーマットが異なるため、
v1 用のファイルは利用できません。v2.1 に対応する住所データベースファイルは
末尾が ``_v21.zip`` です。

.. code-block:: console

    $ jageocoder download-dictionary https://www.info-proto.com/static/jageocoder/latest/v2/jukyo_all_v21.zip

次にダウンロードした zip ファイルをインストールします。

.. code-block:: console

    $ jageocoder install-dictionary jukyo_all_v21.zip

.. note::

   2024年4月の時点で、全国の住居表示と地番の住所を含む住所データベースファイルは
   4GB 以上、展開すると 25GB 以上になり、ストレージにその分の空きが必要です。

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


住所データベースディレクトリを指定する
--------------------------------------

住所データベースは特に指定しない場合 Python 環境内に作成されます
（参考： :ref:`commandline-get-db-dir`）。

このデータベースはサイズが大きいため、1台のマシン上の
複数の Python 環境で Jageocoder を利用する際、
各環境にインストールせずに共用したいことがあります。
そのような場合には、環境変数
``JAGEOCODER_DB2_DIR`` をセットして住所データベースのディレクトリを
指定してください。

.. code-block:: console

    $ export JAGEOCODER_DB2_DIR=$HOME/jageocoder/db2
    $ jageocoder get-db-dir
   /home/sagara/jageocoder/db2

ただし jageocoder のバージョンは住所データベースのバージョンと
互換性がある必要があります。

.. note::

   もし ``JAGEOCODER_DB2_DIR`` と ``JAGEOCODER_SERVER_URL`` が両方とも
   セットされている場合、 ``JAGEOCODER_DB2_DIR`` が優先されます。
   ``JAGEOCODER_DB2_DIR`` が指すディレクトリに住所データベースが
   見つからない場合は、 ``JAGEOCODER_SERVER_URL`` で指定された
   Jageocoder サーバに接続します。
