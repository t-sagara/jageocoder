import json
import logging
import sys

import jageocoder
from jageocoder.exceptions import JageocoderError
from docopt import docopt

HELP = """
'jageocoder' is a Python package of Japanese-address geocoder.

Usage:
  {p} -h
  {p} -v
  {p} search [-d] [--area=<area>] [--db-dir=<dir>] [--force-aza-skip|--disable-aza-skip] <address>
  {p} get-db-dir [-d]
  {p} download-dictionary [-d] <url>
  {p} install-dictionary [-d] [--db-dir=<dir>] <path>
  {p} uninstall-dictionary [-d] [--db-dir=<dir>]

Options:
  -h --help           Show this help.
  -v --version        Show version number.
  -d --debug          Show debug messages.
  --area=<area>       Specify the target area by jiscode or names.
  --force-aza-skip    Skip aza-names whenever possible.
  --disable-aza-skip  Do not skip aza-names.
  --db-dir=<dir>      Specify dictionary directory.

Examples:

- Search address

  {p} search 多摩市落合1-15
  {p} search --area=14152 中央1-1
  {p} search --area=東京都 落合1-15

- Show dictionary directory

  {p} get-db-dir

- Install dictionary

  (Download from web)
  {p} download-dictionary https://www.info-proto.com/static/jageocoder/latest/jukyo_all_v20.zip

  (Install from the file)
  {p} install-dictionary jukyo_all_v20.zip

- Uninstall dictionary in '/home/foo/jageocoder_db/'

  {p} uninstall-dictionary --db-dir=/home/foo/jageocoder_db
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
        logging.Formatter('%(levelname)s:%(name)s:%(lineno)s:%(message)s')
    )
    logger.addHandler(console_handler)

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
                db_dir=args['--db-dir']
            )
        except JageocoderError:
            logging.warning((
                "Could not find the dictionary at '{}'.".format(path)
            ))
            exit(1)

    elif args['uninstall-dictionary']:
        jageocoder.uninstall_dictionary(
            db_dir=args['--db-dir'])
    elif args['migrate-dictionary']:
        jageocoder.migrate_dictionary(
            db_dir=args['--db-dir'])


if __name__ == '__main__':
    main()
