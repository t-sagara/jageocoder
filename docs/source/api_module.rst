モジュールメソッド
==================

jageocoder モジュールのメソッドは、以下の3つのグループに分類できます。

住所辞書データベースのインストールや削除などの管理を行なう
   :py:meth:`jageocoder.download_dictionary`,
   :py:meth:`jageocoder.install_dictionary`,
   :py:meth:`jageocoder.uninstall_dictionary`,
   :py:meth:`jageocoder.migrate_dictionary`,
   :py:meth:`jageocoder.create_trie_index`,
   :py:meth:`jageocoder.dictionary_version`

モジュールの初期化や状態確認などの管理を行なう
   :py:meth:`jageocoder.init`,
   :py:meth:`jageocoder.free`,
   :py:meth:`jageocoder.is_initialized`,
   :py:meth:`jageocoder.get_db_dir`,
   :py:meth:`jageocoder.get_module_tree`,
   :py:meth:`jageocoder.version`

検索機能を提供する
   :py:meth:`jageocoder.set_search_config`,
   :py:meth:`jageocoder.get_search_config`,
   :py:meth:`jageocoder.search`,
   :py:meth:`jageocoder.searchNode`,
   :py:meth:`jageocoder.reverse`


.. automodule:: jageocoder
   :members:
   :private-members:
