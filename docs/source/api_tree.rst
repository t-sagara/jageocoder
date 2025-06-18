AddressTree クラス
==================

住所階層木構造を表す抽象基底クラスです。

Jageocoder では、住所は表形式ではなく、
id=0 を持つ根 (root) ノードの下に都道府県を表すノードがあり、
そのさらに下に市区町村を表すノードがあり、という
階層木構造を利用して管理しています。

それぞれのノードは :py:class:`jageocoder.node.AddressNode`
クラスのオブジェクトです。

また、このクラスは利用する住所データベースの情報も管理しています。
複数の AddressTree オブジェクトを生成し、それぞれ別の住所データベースを開けば、
同時に複数の異なる住所データベースを利用することもできます。

.. autoclass:: jageocoder.tree.AddressTree
   :members:
   :special-members: __init__
   :undoc-members:


LocalTree クラス
================

ローカルマシン上にデータベースを持つ住所開創器構造へのアクセスを実装した
AddressTree クラスのサブクラスです。

AddressTree クラスオブジェクトをインスタンス化する際に、
:py:attr:`db_dir <jageocoder.tree.AddressTree.db_dir>` 属性または環境変数
`JAGEOCODER_DB2_DIR` で住所データベースのディレクトリを指定すると
LocalTree クラスのオブジェクトが生成されます。

.. autoclass:: jageocoder.local.LocalTree
   :members:
   :special-members: __init__
   :undoc-members:


RemoteTree クラス
=================

Jageocoder サーバ上の住所階層木構造へのアクセスを実装した
AddressTree クラスのサブクラスです。

AddressTree クラスオブジェクトをインスタンス化する際に、
:py:attr:`url <jageocoder.tree.AddressTree.url>` 属性または環境変数
`JAGEOCODER_SERVER_URL` で Jageocoder サーバのエンドポイント URL を指定すると
RemoteTree クラスのオブジェクトが生成されます。

各メソッドの呼び出しは JSON-RPC を利用してサーバ上で実行されます。
通信中にエラーが発生した場合は
``jageocoder.exceptions.RemoteTreeException`` が発生します。
この例外は ``jageocoder.exceptions.AddressTreeException`` のサブクラスなので、
``AddressTreeException`` を catch すれば捕捉できます。

.. autoclass:: jageocoder.remote.RemoteTree
   :members:
   :special-members: __init__
   :undoc-members:
