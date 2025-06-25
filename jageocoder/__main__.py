import json
import logging
import sys

import click
import jageocoder
from jageocoder.exceptions import JageocoderError
from jageocoder.address import AddressLevel


@click.group(context_settings=dict(help_option_names=['-h', '--help']))
@click.option('-d', '--debug', is_flag=True, help='実行時にデバッグメッセージを表示します。')
@click.version_option(jageocoder.__version__, '-v', '--version')
@click.pass_context
def cli(ctx, debug):
    """'jageocoder' は日本の住所ジオコーダを実装した Python パッケージです。"""
    ctx.ensure_object(dict)
    ctx.obj['debug'] = debug

    log_level = logging.DEBUG if debug else logging.INFO

    logger = logging.getLogger('jageocoder')
    logger.setLevel(log_level)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(
        logging.Formatter('%(levelname)s:%(name)s:%(lineno)s:%(funcName)s:%(message)s')
    )
    logger.addHandler(console_handler)


@cli.command()
@click.option('--area', help='検索対象地域の都道府県・市区町村名を指定します。')
@click.option('--db-dir', help='住所データベースのディレクトリを指定します。')
@click.option('--url', help='Jageocoderサーバのエンドポイント URL を指定します。')
@click.argument('address')
@click.pass_context
def search(ctx, area, db_dir, url, address):
    """住所を検索します。"""
    jageocoder.init(db_dir=db_dir, mode='r', url=url)
    target_area = area.split(',') if area else None
    try:
        jageocoder.set_search_config(target_area=target_area)
    except RuntimeError:
        print(f"'{area}' is incorrect as a parameter for the --area option.", file=sys.stderr)
        ctx.exit(1)
    try:
        result = jageocoder.search(query=address)
        print(json.dumps(result, ensure_ascii=False))
    except RuntimeError as e:
        print(f"An error occurred during the search: {e}", file=sys.stderr)
        ctx.exit(1)


@cli.command()
@click.option('--level', type=int, help='検索する住所レベルを指定します。')
@click.option('--db-dir', help='住所データベースのディレクトリを指定します。')
@click.option('--url', help='Jageocoderサーバのエンドポイント URL を指定します。')
@click.argument('longitude', type=float)
@click.argument('latitude', type=float)
def reverse(level, db_dir, url, longitude, latitude):
    """リバースジオコーディングを実行します。"""
    jageocoder.init(db_dir=db_dir, mode='r', url=url)
    lvl = level if level is not None else AddressLevel.AZA
    result = jageocoder.reverse(x=longitude, y=latitude, level=int(lvl))
    print(json.dumps(result, ensure_ascii=False))


@cli.command('get-db-dir')
def get_db_dir_cmd():
    """住所データベースのディレクトリを表示します。"""
    print(jageocoder.get_db_dir(mode='r'))


@cli.command('download-dictionary')
@click.argument('url')
def download_dictionary(url):
    """住所辞書ファイルをダウンロードします。"""
    try:
        jageocoder.download_dictionary(url=url)
    except JageocoderError:
        logging.warning('Could not find the dictionary at the URL. Make sure the URL is correct.')
        sys.exit(1)


@cli.command('install-dictionary')
@click.option('--db-dir', help='住所データベースのディレクトリを指定します。')
@click.option('-y', '--yes', is_flag=True, help='確認メッセージに対して自動的に y と答えます。')
@click.argument('path')
def install_dictionary(db_dir, yes, path):
    """住所辞書ファイルをインストールします。"""
    try:
        jageocoder.install_dictionary(path=path, db_dir=db_dir, skip_confirmation=yes)
    except JageocoderError:
        logging.warning("辞書データファイルが '{}' にありません。".format(path))
        sys.exit(1)


@cli.command('uninstall-dictionary')
@click.option('--db-dir', help='住所データベースのディレクトリを指定します。')
def uninstall_dictionary(db_dir):
    """住所データベースをアンインストールします。"""
    jageocoder.uninstall_dictionary(db_dir=db_dir)


@cli.command('list-datasets')
@click.option('--db-dir', help='住所データベースのディレクトリを指定します。')
@click.option('--url', help='Jageocoderサーバのエンドポイント URL を指定します。')
def list_datasets(db_dir, url):
    """データセットの一覧を表示します。"""
    jageocoder.init(db_dir=db_dir, mode='r', url=url)
    datasets = list(jageocoder.get_datasets().values())
    datasets.sort(key=lambda x: x['id'])
    print(json.dumps(datasets, indent=2, ensure_ascii=False))


def main():
    cli(obj={})


if __name__ == '__main__':
    main()

