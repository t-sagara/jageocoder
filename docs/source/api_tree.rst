AddressTree クラス
==================

住所階層木構造を表すクラスです。

jageocoder では、住所は表形式ではなく、
id=0 を持つ根 (root) ノードの下に都道府県を表すノードがあり、
そのさらに下に市区町村を表すノードがあり、という
階層木構造を利用して管理しています。

それぞれのノードは :py:class:`jageocoder.node.AddressNode` クラスの
オブジェクトです。

また、このクラスはデータベース接続セッションも管理しています。
言い換えれば、複数の AddressTree オブジェクトを生成すれば、
複数のデータベースを利用するコードを書くこともできます。


.. autoclass:: jageocoder.tree.AddressTree
   :members:
   :special-members: __init__
   :undoc-members:
