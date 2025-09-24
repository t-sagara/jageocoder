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
マルチスレッドアプリケーションではスレッドごとに AddressTree を生成する必要があります。

AddressTree はオブジェクトファクトリー機能を持ちます。
:ref:`db_priority` に従って接続先を決定した際に、サーバ上の住所データベースに接続する場合は
:py:class:`jageocoder.local.LocalTree` クラスのインスタンスを、 Jageocoder サーバに接続する場合は
:py:class:`jageocoder.remote.RemoteTree` クラスのインスタンスを生成します。

.. code-block:: python

   >>> from jageocoder.tree import AddressTree
   >>> local_tree = AddressTree(db_dir="db")
   >>> type(local_tree)
   <class 'jageocoder.local.LocalTree'>
   >>> local_tree.searchNode("新宿区西新宿2-8-1")[0]
   {"node": {"id": 80223284, "name": "8番", "name_index": "8.番", "x": 139.6917724609375, "y": 35.68962860107422, "level": 7, "priority": 3, "note": "", "parent_id": 80223179, "sibling_id": 80223285}, "matched": "新宿区西新宿2-8-"}
   >>> remote_tree = AddressTree(url="https://jageocoder.info-proto.com/jsonrpc")
   >>> type(remote_tree)
   <class 'jageocoder.remote.RemoteTree'>
   >>> remote_tree.searchNode("新宿区西新宿2-8-1")[0]
   {"node": {"id": 80223284, "name": "8番", "name_index": "8.番", "x": 139.6917724609375, "y": 35.68962860107422, "level": 7, "priority": 3, "note": "", "parent_id": 80223179, "sibling_id": 80223285}, "matched": "新宿区西新宿2-8-"}


.. autoclass:: jageocoder.tree.AddressTree
   :members:
   :special-members: __init__
   :undoc-members:


LocalTree クラス
================

ローカルマシン上にデータベースを持つ住所階層木構造へのアクセスを実装した
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
