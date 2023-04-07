import json
import logging
import os
import sys
from typing import Optional

import jageocoder
from jageocoder.exceptions import JageocoderError
from docopt import docopt

HELP = r"""
'jageocoder' is a Python package of Japanese-address geocoder.

Usage:
  {p} -h
  {p} -v
  {p} search [-d] [--area=<area>] [--db-dir=<dir>] [--force-aza-skip|--disable-aza-skip] <address>
  {p} reverse [-d] [--level=<level>] [--db-dir=<dir>] <longitude> <latitude>
  {p} get-db-dir [-d]
  {p} download-dictionary [-d] [--gaiku] [<url>]
  {p} install-dictionary [-d] [--gaiku] [--db-dir=<dir>] [<url_or_path>]
  {p} uninstall-dictionary [-d] [--db-dir=<dir>]
  {p} migrate-dictionary [-d] [--db-dir=<dir>]

Options:
  -h --help           Show this help.
  -v --version        Show package version.
  -d --debug          Show debug messages.
  --area=<area>       Specify the target area by jiscode or names.
  --force-aza-skip    Skip aza-names whenever possible.
  --disable-aza-skip  Do not skip aza-names.
  --level=<level>     Max address level to search.
  --gaiku             Use block-level (default: building-level)
  --db-dir=<dir>      Specify dictionary directory.

Examples:

- Search address

  {p} search 多摩市落合1-15
  {p} search --area=14152 中央1-1
  {p} search --area=東京都 落合1-15

- Show dictionary directory

  {p} get-db-dir

- Install dictionary

  (From web)
  {p} install-dictionary

  (From local zipfile)
  {p} install-dictionary ~/jusho.zip

- Uninstall dictionary in '/home/foo/jageocoder_db/'

  {p} uninstall-dictionary --db-dir=/home/foo/jagteocoder_db

- Migrate dictionary (after upgrading the package)

  {p} migrate-dictionary
""".format(p='jageocoder')  # noqa: E501


def get_download_url(level: Optional[str] = None,
                     version: Optional[str] = None):
    """
    Generate dictionary file download url.

    Parameters
    ----------
    level: str, optional
        The basename of the dictionary file.
        The default value is 'jusho'.

    version: str, optional
        Version string.
        If ommitted, use compatible version with the package.

    Returns
    -------
    str
        The download URL.
    """
    base = level or 'jusho'
    version = version or jageocoder.dictionary_version()
    url = 'https://www.info-proto.com/static/{base}-{version}.zip'
    url = url.format(base=base, version=version)

    return url


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

    logging.basicConfig(format='%(levelname)s:%(name)s:%(lineno)s:%(message)s',
                        level=log_level)

    if args['search']:
        jageocoder.init(db_dir=args['--db-dir'], mode='r')
        skip_aza = 'auto'
        if args.get('--area'):
            target_area = args['--area'].split(',')
        else:
            target_area = None

        if args['--disable-aza-skip']:
            skip_aza = 'off'
        elif args['--force-aza-skip']:
            skip_aza = 'on'

        try:
            jageocoder.set_search_config(
                aza_skip=skip_aza, target_area=target_area)
            print(json.dumps(
                jageocoder.search(query=args['<address>']),
                ensure_ascii=False))
        except RuntimeError:
            if args['--area'] is None:
                db_dir = os.environ.get("JAGEOCODER_DB_DIR")
                if db_dir is not None:
                    print((
                        "In the directory {} specified by the JAGEOCODER_DB_DIR "
                        "environment variable, ").format(db_dir),
                        end="")

                print("The dictionary is not installed correctly")
                exit(0)
            print(
                "'{}' is incorrect as a parameter for the --area option.".format(
                    args['--area']),
                file=sys.stderr)

    elif args['reverse']:
        from jageocoder.address import AddressLevel
        jageocoder.init(db_dir=args['--db-dir'], mode='r')
        print(json.dumps(
            jageocoder.reverse(
                x=float(args['<longitude>']),
                y=float(args['<latitude>']),
                level=int(args['--level'] or AddressLevel.AZA)),
            ensure_ascii=False))

    elif args['download-dictionary']:
        level = 'gaiku' if args['--gaiku'] else 'jusho'
        url = args['<url>'] or get_download_url(level)
        try:
            jageocoder.download_dictionary(url=url)
        except JageocoderError:
            logging.warning((
                'Could not find a compatible version of the dictionary.'
                ' Download the latest version instead.'))
            jageocoder.download_dictionary(
                url=get_download_url(level, 'latest'))

    elif args['install-dictionary']:
        level = 'gaiku' if args['--gaiku'] else 'jusho'
        path_or_url = args['<url_or_path>'] or get_download_url(level)
        try:
            jageocoder.install_dictionary(
                path_or_url=path_or_url,
                db_dir=args['--db-dir'])
        except JageocoderError:
            logging.warning((
                'Could not find a compatible version of the dictionary. '
                'Run "download-dictionary" to download '
                'the latest version instead.'))

    elif args['uninstall-dictionary']:
        jageocoder.uninstall_dictionary(
            db_dir=args['--db-dir'])
    elif args['migrate-dictionary']:
        jageocoder.migrate_dictionary(
            db_dir=args['--db-dir'])


if __name__ == '__main__':
    main()
