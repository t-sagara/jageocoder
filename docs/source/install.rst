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

   (.venv) $ pip install jageocoder==1.3.0


.. _install-dictionary:

住所辞書のインストール
----------------------

住所辞書は zip 形式でダウンロード可能です。
住所辞書は jageocoder のバージョンによって少しずつ内容が異なるため、
以下のコマンドで互換性のある辞書ファイルをダウンロードしてください。

.. code-block:: console

   (.venv) $ python -m jageocoder download-dictionary
   INFO:jageocoder.module:157:Downloading zipped dictionary file from https://www.info-proto.com/static/jusho-20220519.zip to ...


**注意** 住所辞書ファイルは圧縮した状態で 836MB 程度と大きいため、
ダウンロード・インストールには時間がかかります。

次にダウンロードした zip ファイルをインストールします。

.. code-block:: console

   (.venv) $ python -m jageocoder install-dictionary jusho-20220519.zip

``jusho-20220519.zip`` はダウンロードしたファイル名に変更してください。



.. _uninstallation:

アンインストール手順
--------------------

jageocoder をアンインストールする場合、先に辞書データベースを削除してください。
辞書データベースの場所が分かっている場合はそのディレクトリごと
削除しても構いませんが、 ``uninstall-dictionary`` コマンドを
利用すると簡単に削除できます。

.. code-block:: console

   (.venv) $ python -m jageocoder uninstall-dictionary

その後、 jageocoder パッケージを pip でアンインストールしてください。

.. code-block:: console

   (.venv) $ pip uninstall jageocoder


住所辞書データベースディレクトリを指定する
------------------------------------------

住所辞書データベースは、特に指定しない場合 Python 環境内に作成されます
（参考： :ref:`commandline-get-db-dir`）。

このデータベースは数GBのサイズがあるため、複数の Python 環境で jageocoder
を利用する際などには共用したいことがあります。そのような場合には、環境変数
``JAGEOCODER_DB_DIR`` をセットすると、
住所辞書データベースのディレクトリを指定することができます。

.. code-block:: console

   (.venv) $ export JAGEOCODER_DB_DIR=$HOME/jageocoder/db
   (.venv) $ python -m jageocoder get-db-dir
   /home/sagara/jageocoder/db

ただし jageocoder のバージョンは住所辞書に合わせてください。