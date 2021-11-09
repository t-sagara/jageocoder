import logging
from typing import Optional

import jageocoder
import jageocoder.version
from docopt import docopt

HELP = """
'jageocoder' is a Python package of Japanese-address geocoder.

Usage:
  {p} -h
  {p} get-db-dir
  {p} download-dictionary [--gaiku] [<url>]
  {p} install-dictionary [--gaiku] [--db-dir=<dir>] [<url_or_path>]
  {p} uninstall-dictionary [--db-dir=<dir>]
  {p} upgrade-dictionary [--db-dir=<dir>]

Options:
  -h --help       Show this help.
  --gaiku         Use block-level (default: building-level)
  --db-dir=<dir>  Specify dictionary directory.

Examples:

- Show dictionary directory

  python -m {p} get-db-dir

- Install dictionary

  (From web)
  python -m {p} install-dictionary

  (From local zipfile)
  python -m {p} install-dictionary ~/jusho.zip

- Uninstall dictionary in '/home/foo/jageocoder_db/'

  python -m {p} uninstall-dictionary --db-dir=/home/foo/jagteocoder_db

- Upgrade dictionary (after upgrading the package)

  python -m {p} upgrade-dictionary
""".format(p='jageocoder')


def get_download_url(level: Optional[str] = None):
    """
    Generate dictionary file download url.

    Parameters
    ----------
    level: str, optional
        The basename of the dictionary file.
        The default value is 'jusho'.

    Returns
    -------
    str
        The download URL.
    """
    base = level or 'jusho'
    url = 'https://www.info-proto.com/static/{base}-{dict_ver}.zip'
    url = url.format(base=base,
                     dict_ver=jageocoder.version.dictionary_version())

    return url


if __name__ == '__main__':
    args = docopt(HELP)

    if args['get-db-dir']:
        print(jageocoder.get_db_dir(mode='r'))
        exit(0)

    logging.basicConfig(format='%(levelname)s:%(message)s',
                        level=logging.INFO)
    if args['download-dictionary']:
        level = 'gaiku' if args['--gaiku'] else 'jusho'
        url = args['<url>'] or get_download_url(level)
        jageocoder.download_dictionary(url=url)
    elif args['install-dictionary']:
        level = 'gaiku' if args['--gaiku'] else 'jusho'
        path_or_url = args['<url_or_path>'] or get_download_url(level)
        jageocoder.install_dictionary(
            path_or_url=path_or_url,
            db_dir=args['--db-dir'])
    elif args['uninstall-dictionary']:
        jageocoder.uninstall_dictionary(
            db_dir=args['--db-dir'])
    elif args['upgrade-dictionary']:
        jageocoder.upgrade_dictionary(
            db_dir=args['--db-dir'])
