import json
import logging
import sys

import jageocoder
from jageocoder.exceptions import JageocoderError
from docopt import docopt

HELP = """
'jageocoder' は日本の住所ジオコーダを実装した Python パッケージです。

Usage:
  {p} -h
  {p} -v
  {p} search [-d] [--area=<area>] [--db-dir=<dir>|--url=<url>] <address>
  {p} reverse [-d] [--level=<level>] [--db-dir=<dir>|--url=<url>] <longitude> <latitude>
  {p} get-db-dir [-d]
  {p} download-dictionary [-d] <url>
  {p} install-dictionary [-d] [-y] [--db-dir=<dir>] <path>
  {p} uninstall-dictionary [-d] [--db-dir=<dir>]
  {p} list-datasets [-d] [--db-dir=<dir>|--url=<url>]

Options:
  -h --help           このヘルプメッセージを表示します.
  -v --version        バージョン番号を表示します.
  -d --debug          実行時にデバッグメッセージを表示します.
  -y --yes            確認メッセージに対して自動的に y と答えます。
  --area=<area>       検索対象地域の都道府県・市区町村名を指定します。
  --level=<level>     検索する住所レベルを指定します。
  --db-dir=<dir>      住所データベースのディレクトリを指定します。
  --url=<url>         Jageocoderサーバのエンドポイント URL を指定します。

Examples:

- 住所を検索します。

  {p} search 多摩市落合1-15
  {p} search --area=14152 中央1-1
  {p} search --area=東京都 落合1-15
  {p} search --area=町田市,八王子市 中町１－１

  環境変数で検索オプションを指定できます（[]内がデフォルト）。
  - JAGEOCODER_OPT_AZA_SKIP (on,off,[auto])
    「字」の省略判定処理を指定します。
  - JAGEOCODER_OPT_BEST_ONLY ([true],false)
    最適解のみ表示するかどうかを指定します。
  - JAGEOCODER_OPT_REQUIRE_COORDINATES ([true],false)
    座標が登録されている住所のみ検索対象とするかどうかを指定します。
    座標が登録されていない場合、経緯度 ≒ 999.9 と表示されます。
  - JAGEOCODER_OPT_AUTO_REDIRECT ([true],false)
    検索した住所が合併等により変わっている場合、
    変更先の住所を自動的に検索するかどうかを指定します。

- 住所データベースのディレクトリを表示します。

  {p} get-db-dir

- 住所データベースをインストールします。

  (ウェブから最新の全国住居表示レベルデータファイルをダウンロードします)
  {p} download-dictionary https://www.info-proto.com/static/jageocoder/latest/jukyo_all_v21.zip

  (ダウンロードしたファイルをインストールします)
  {p} install-dictionary jukyo_all_v21.zip

- 住所データベースをアンインストールします。

  {p} uninstall-dictionary

- 住所データベースに含まれるデータセット一覧を表示します。

  {p} list-datasets
""".format(p='jageocoder')  # noqa: E501


def main():
    args = docopt(HELP)

    if args['--version']:
        print(jageocoder.__version__)
        exit(0)

    if args['--debug']:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    if args['get-db-dir']:
        print(jageocoder.get_db_dir(mode='r'))
        exit(0)

    logger = logging.getLogger('jageocoder')
    logger.setLevel(log_level)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(
        logging.Formatter(
            '%(levelname)s:%(name)s:%(lineno)s:%(funcName)s:%(message)s')
    )
    logger.addHandler(console_handler)

    if args['search']:
        jageocoder.init(db_dir=args['--db-dir'], mode='r', url=args['--url'])
        target_area = None
        if args.get('--area'):
            target_area = args['--area'].split(',')

        try:
            jageocoder.set_search_config(target_area=target_area)
        except RuntimeError:
            print((
                "'{}' is incorrect as a parameter for "
                "the --area option.").format(args['--area']),
                file=sys.stderr)
            exit(1)

        try:
            print(json.dumps(
                jageocoder.search(query=args['<address>']),
                ensure_ascii=False))
        except RuntimeError as e:
            print(
                "An error occurred during the search: {}".format(e),
                file=sys.stderr)
            exit(1)

    elif args['reverse']:
        from jageocoder.address import AddressLevel
        jageocoder.init(db_dir=args['--db-dir'], mode='r', url=args['--url'])
        print(json.dumps(
            jageocoder.reverse(
                x=float(args['<longitude>']),
                y=float(args['<latitude>']),
                level=int(args['--level'] or AddressLevel.AZA)),
            ensure_ascii=False))

    elif args['download-dictionary']:
        url = args['<url>']
        try:
            jageocoder.download_dictionary(url=url)
        except JageocoderError:
            logging.warning((
                'Could not find the dictionary at the URL.'
                'Make sure the URL is correct.'))
            exit(1)

    elif args['install-dictionary']:
        path = args['<path>']
        try:
            jageocoder.install_dictionary(
                path=path,
                db_dir=args['--db-dir'],
                skip_confirmation=(args['--yes'] is True),
            )
        except JageocoderError:
            logging.warning((
                "辞書データファイルが '{}' にありません。".format(path)
            ))
            exit(1)

    elif args['uninstall-dictionary']:
        jageocoder.uninstall_dictionary(
            db_dir=args['--db-dir'])
        exit(0)

    elif args['list-datasets']:
        jageocoder.init(db_dir=args['--db-dir'], mode='r', url=args['--url'])
        datasets = list(jageocoder.get_datasets().values())
        datasets.sort(key=lambda x: x["id"])
        print(json.dumps(datasets, indent=2, ensure_ascii=False))
        exit(0)


if __name__ == '__main__':
    main()
