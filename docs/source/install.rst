.. _installation:

インストール手順
================

.. _install-package:

パッケージのインストール
------------------------

``pip`` コマンドでインストールできます。

.. code-block:: console

   (.venv) $ pip install jageocoder

バージョンを指定したい場合は ``==`` に続けてバージョン番号を指定してください。

.. code-block:: console

   (.venv) $ pip install jageocoder==2.1.0


.. _install-dictionary:

住所データベースファイルのインストール
--------------------------------------

住所データベースファイルは ` zip 形式でダウンロード可能です。最新の
`住所データベースファイル一覧 <https://www.info-proto.com/static/jageocoder/latest/v2/>`_
から、必要な地域を含むものを選択してダウンロードしてください。

住所データベースは jageocoder のバージョンによってフォーマットが異なるため、
v1 用のファイルは利用できません。v2.1 に対応する住所データベースファイルは
末尾が `_v21.zip` です。

.. code-block:: console

   (.venv) $ jageocoder download-dictionary https://www.info-proto.com/static/jageocoder/latest/v2/jukyo_all_v21.zip

**注意** 住所データベースファイルは圧縮した状態でもファイルサイズが大きいため、
ダウンロード・インストールには時間がかかります。

次にダウンロードした zip ファイルをインストールします。

.. code-block:: console

   (.venv) $ jageocoder install-dictionary jukyo_all_v21.zip


.. _uninstallation:

アンインストール手順
--------------------

jageocoder をアンインストールする場合、先に住所データベースを削除してください。
住所データベースの場所が分かっている場合はそのディレクトリごと
削除しても構いませんが、 ``uninstall-dictionary`` コマンドを
利用すると簡単に削除できます。

.. code-block:: console

   (.venv) $ jageocoder uninstall-dictionary

その後、 jageocoder パッケージを pip でアンインストールしてください。

.. code-block:: console

   (.venv) $ pip uninstall jageocoder


住所データベースディレクトリを指定する
--------------------------------------

住所データベースは、特に指定しない場合 Python 環境内に作成されます
（参考： :ref:`commandline-get-db-dir`）。

このデータベースは数GBのサイズがあるため、複数の Python 環境で jageocoder
を利用する際には共用したいことがあります。そのような場合には、環境変数
``JAGEOCODER_DB2_DIR`` をセットすると、
住所データベースのディレクトリを指定することができます。

.. code-block:: console

   (.venv) $ export JAGEOCODER_DB2_DIR=$HOME/jageocoder/db2
   (.venv) $ jageocoder get-db-dir
   /home/sagara/jageocoder/db2

ただし jageocoder のバージョンは住所データベースのバージョンと
互換性がある必要があります。


