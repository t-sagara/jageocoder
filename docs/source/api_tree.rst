AddressTree クラス
==================

住所階層木構造を表すクラスです。

Jageocoder では、住所は表形式ではなく、
id=0 を持つ根 (root) ノードの下に都道府県を表すノードがあり、
そのさらに下に市区町村を表すノードがあり、という
階層木構造を利用して管理しています。

それぞれのノードは :py:class:`jageocoder.node.AddressNode`
クラスのオブジェクトです。

また、このクラスは利用する住所データベースの情報も管理しています。
言い換えれば、複数の AddressTree オブジェクトを生成し、
それぞれ別の住所データベースを開けば、同時に複数の
異なる住所データベースを利用することもできます。

.. autoclass:: jageocoder.tree.AddressTree
   :members:
   :special-members: __init__
   :undoc-members:


RemoteTree クラス
=================

Jageocoder サーバ上の住所階層木構造へのアクセスを
AddressTree クラスと同様に可能にするためのラップクラスです。

各メソッドの呼び出しは JSON-RPC を利用してサーバ上で実行されます。
通信中にエラーが発生した場合は
``jageocoder.exceptions.RemoteTreeException`` が発生します。
この例外は ``jageocoder.exceptions.AddressTreeException`` のサブクラスなので、
``AddressTreeException`` を catch すれば捕捉できます。

.. autoclass:: jageocoder.remote.RemoteTree
   :members:
   :special-members: __init__
   :undoc-members:
