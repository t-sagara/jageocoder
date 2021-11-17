# jageocoder - A Python Japanese geocoder

日本語版は README_ja.md をお読みください。

This is a Python port of the Japanese-address geocoder used in CSIS at the University of Tokyo's ["Address Matching Service"](https://newspat.csis.u-tokyo.ac.jp/geocode/modules/addmatch/index.php?content_id=1) and [GSI Maps](https://maps.gsi.go.jp/).

# Getting Started

This package provides address-geocoding functionality for Python programs. The basic usage is to specify a dictionary with `init()` then call `search()` to get geocoding results.

```python
python
>>> import jageocoder
>>> jageocoder.init()
>>> jageocoder.search('新宿区西新宿2-8-1')
{'matched': '新宿区西新宿2-8-', 'candidates': [{'id': 5961406, 'name': '8番', 'x': 139.691778, 'y': 35.689627, 'level': 7, 'note': None, 'fullname': ['東京都', '新宿区', '西新宿', '二丁目', '8番']}]}
```

# How to install

## Prerequisites

Requires Python 3.6.x or later.

The following packages will be installed automatically.

- [marisa-trie](https://pypi.org/project/marisa-trie/)
    for building and retrieving TRIE index
- [SQLAlchemy](https://pypi.org/project/SQLAlchemy/)
    for abstracting access to the RDBMS

## Install instructions

- Install the package with `pip install jageocoder`
- Install the dictionary with `install-dictionary` command

```sh
pip install jageocoder
python -m jageocoder install-dictionary
```

The dictionary database will be created under
`{sys.prefix}/jageocoder/db/`, or if the user doesn't have 
write permission there `{site.USER_DATA}/jageocoder/db/`
by default.

If you need to know the location of the directory containing
the dictionary database, perform `get-db-dir` command as follows,
or call `jageocoder.get_db_dir()` in your script.

```sh
python -m jageocoder get-db-dir
```

If you prefer to create it in another location, set the environment
variable `JAGEOCODER_DB_DIR` before executing `install_dictionary()`
to specify the directory.

```sh
export JAGEOCODER_DB_DIR='/usr/local/share/jageocoder/db'
python -m install-dictionary
```

## Update dictinary

The `install-dictionary` command will download and install
a version of the address dictionary file that is compatible with
the currently installed jageocoder package.

If you upgrade the jageocoder package after installing
the address dictionary file, it may no longer be compatible with
the installed address dictionary file.
In which case you will need to reinstall or update the dictionary.

To update the dictionary, run the `upgrade-dictionary` command.
This process may take a long time.

```sh
python -m upgrade-dictionary
```

## Uninstall instructions

Remove the directory containing the database, or perform 
`uninstall-dictionary` command as follows.

```sh
python -m jageocoder uninstall-dictionary
```

Then, uninstall the package with `pip` command.

```sh
pip uninstall jageocoder
```


# For developers

## Running the unittests

```python
python -m unittest
``` 

`tests.test_search` tests for some special address notations.

- Street address in Sapporo city such as '北3西1' for '北三条西一丁目'
- Toorina in Kyoto city such as '下立売通新町西入薮ノ内町' for '薮ノ内町'

## Create your own dictionary

Please use the dictionary coverter
[jageocoder-converter](https://github.com/t-sagara/jageocoder-converter).

## ToDos

- Supporting address changes

    The functionality to handle address changes due to municipal consolidation, etc.
    has already been implemented in the C++ version, but will be implemented
    in this package in the future.

## Contributing

Address notation varies. So suggestions for logic improvements are welcome.
Please submit an issue with examples of address notations in use and how they should be parsed.

## Authors

* **Takeshi SAGARA** - [Info-proto Co.,Ltd.](https://www.info-proto.com/)

## License

This project is licensed under [the MIT License](https://opensource.org/licenses/mit-license.php).

This is not the scope of the dictionary data license. Please follow the license of the respective dictionary data.

## Acknowledgements

We would like to thank CSIS for allowing us to provide address matching services on their institutional website for over 20 years.
