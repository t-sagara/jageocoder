# jageocoder - A Python Japanese geocoder

`jageocoder` は日本の住所用ジオコーダです。
東京大学空間情報科学研究所の [「CSV アドレスマッチングサービス」](https://geocode.csis.u-tokyo.ac.jp/home/csv-admatch/) および
国土地理院の [「地理院地図」](https://maps.gsi.go.jp/) で利用している
C++ ジオコーダを Python に移植しました。

# はじめに

このパッケージは Python プログラムに住所ジオコーディング機能を提供します。
`init()` で初期化し、 `search()` に住所文字列を渡すと、
ジオコーディング結果が得られます。

```python
python
>>> import jageocoder
>>> jageocoder.init()
>>> jageocoder.search('新宿区西新宿2-8-1')
{'matched': '新宿区西新宿2-8-', 'candidates': [{'id': 5961406, 'name': '8番', 'x': 139.691778, 'y': 35.689627, 'level': 7, 'note': None, 'fullname': ['東京都', '新宿区', '西新宿', '二丁目', '8番']}]}
```

# インストール方法

## 事前準備

Python 3.6 以降が必要です。

jageocoder をインストールすると、以下のパッケージなども
自動的にインストールされます。

- [marisa-trie](https://pypi.org/project/marisa-trie/)
    TRIE インデックスの作成と検索に利用します
- [SQLAlchemy](https://pypi.org/project/SQLAlchemy/)
    RDBMS (Sqlite3) のアクセスに利用します

## インストール手順

- `pip install jageocoder` でパッケージをインストールします
- `install-dictionary` コマンドで住所辞書をインストールします

```sh
pip install jageocoder
python -m jageocoder install-dictionary
```

辞書データベースは `{sys.prefix}/jageocoder/db/` の下に
作成されますが、ユーザが書き込み権限を持っていない場合には
`{site.USER_DATA}/jageocoder/db/` に作成します。

辞書データベースが作成されたディレクトリを知る必要がある場合、
以下のように `get-db-dir` コマンドを実行するか、スクリプト内で
`jageocoder.get_db_dir()` メソッドを呼びだしてください。

```sh
python -m jageocoder get-db-dir
```

上記以外の任意の場所に作成したい場合、住所辞書をインストールする前に
環境変数 `JAGEOCODER_DB_DIR` でディレクトリを指定してください。

```sh
export JAGEOCODER_DB_DIR='/usr/local/share/jageocoder/db'
python -m install-dictionary
```

## 辞書の更新

`install-dictionary` コマンドを実行すると、その時点でインストール
されている jageocoder パッケージと互換性のあるバージョンの
住所辞書ファイルをダウンロードしてインストールします。

住所辞書ファイルをインストールした後で jageocoder パッケージを
バージョンアップした場合、住所辞書ファイルと互換性が無くなる場合があり、
その場合は辞書を再インストールするか更新する必要があります。

辞書を更新するには `upgrade-dictionary` コマンドを実行します。
この処理には長時間かかることがあります。

```sh
python -m upgrade-dictionary
```

## アンインストール手順

アンインストールする場合、まず辞書データベースを含むディレクトリを
削除してください。ディレクトリごと削除しても構いませんが、
`uninstall-dictionary` コマンドも利用できます。

```sh
python -m jageocoder uninstall-dictionary
```

その後、 jageocoder パッケージを pip でアンインストールしてください。

```sh
pip uninstall jageocoder
```


# 開発者向け情報

## ユニットテスト

ユニットテストは unittest で行ないます。

```python
python -m unittest
```

`tests.test_search` テストには特殊な住所表記の例が含まれています。

- 札幌市内の省略表記（例：「北三条西一丁目」を「北3西1」と表記）
- 京都市内の通り名表記（例：「薮ノ内町」を「下立売通新町西入薮ノ内町」と表記）

## 独自の辞書を作成したい場合

辞書コンバータ `jageocoder-converter` を利用してください。

[jageocoder-converter](https://github.com/t-sagara/jageocoder-converter).

## サンプルウェブアプリ

Flask を利用したシンプルなウェブアプリのサンプルが
`flask-demo` の下にあります。

次の手順を実行し、ポート 5000 にアクセスしてください。

```
cd flask-demo
pip install flask
bash run.sh
```

## ToDo

- 住所変更への対応

    自治体統合などによる住所変更があった場合に、旧住所を新住所に
    自動的に変換する機能は jageocoder では将来実装予定です。

## ご協力頂ける場合

日本の住所表記は非常に多様なので、うまく変換できない場合には
お知らせ頂けるとありがたいです。ロジックの改良提案も歓迎します。
どのような住所がどう解析されるべきかをご連絡頂ければ幸いです。

## 作成者

* **相良 毅** - [株式会社情報誌作成津](https://www.info-proto.com/)

## 利用許諾条件

MIT ライセンスでご利用頂けます。

This project is licensed under [the MIT License](https://opensource.org/licenses/mit-license.php).

ただしこの利用許諾条件は住所辞書データに対しては適用されません。
各辞書データのライセンスを参照してください。

## 謝辞

20年以上にわたり、アドレスマッチングサービスを継続するために
所内ウェブサーバを利用させて頂いている
東京大学空間情報科学研究センターに感謝いたします。
