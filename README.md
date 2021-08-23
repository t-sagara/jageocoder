# jageocoder - A Python Japanese geocoder

This is a Python port of the Japanese-address geocoder used in CSIS at the University of Tokyo's ["Address Matching Service"](https://newspat.csis.u-tokyo.ac.jp/geocode/modules/addmatch/index.php?content_id=1) and [GSI Maps](https://maps.gsi.go.jp/).

## Getting Started

This package provides address-geocoding functionality for Python programs. The basic usage is to specify a dictionary with `init()` then call `search()` to get geocoding results.

```python
python
>>> import jageocoder
>>> jageocoder.init()
>>> jageocoder.search('新宿区西新宿2-8-1')
{'matched': '新宿区西新宿2-8-', 'candidates': [{'id': 5961406, 'name': '8番', 'x': 139.691778, 'y': 35.689627, 'level': 7, 'note': None, 'fullname': ['東京都', '新宿区', '西新宿', '二丁目', '8番']}]}
```

### Prerequisites

Requires Python 3.6.x or later and the following packages.

- [marisa-trie](https://pypi.org/project/marisa-trie/)
    for building and retrieving TRIE index
- [SQLAlchemy](https://pypi.org/project/SQLAlchemy/)
    for abstracting access to the RDBMS

### Installing

- Install the package using `pip install jageocoder`
- Download the latest zipped dictionary data from [here](https://www.info-proto.com/jageocoder/#data)
- Install the dictionary.

```sh
pip install jageocoder
curl https://www.info-proto.com/static/jusho.zip -o jusho.zip
python
>>> import jageocoder
>>> jageocoder.install_dictionary('jusho.zip')
```

The dictionary database will be created under
`{sys.prefix}/jageocoder/db/`, or if the user doesn't have 
write permission there `{site.USER_DATA}/jageocoder/db/`
by default.

If you need to know the location of the directory containing
the dictionary database, perform `get_db_dir()` as follows.

```sh
python
>>> import jageocoder
>>> jageocoder.get_db_dir()
```

If you prefer to create it in another location, set the environment
variable `JAGEOCODER_DB_DIR` before executing `install_dictionary()`.

```sh
export JAGEOCODER_DB_DIR='/usr/local/share/jageocoder/db'
python
>>> import jageocoder
>>> jageocoder.install_dictionary('jusho.zip')
```

## Uninstalling

Remove the directory containing the database.
Then, do `pip uninstall jageocoder`.

## Running the tests

```python
python -m unittest
``` 

`tests.test_search` tests for some special address notations.

- Street address in Sapporo city such as '北3西1' for '北三条西一丁目'
- Toorina in Kyoto city such as '下立売通新町西入薮ノ内町' for '薮ノ内町'

## Create your own dictionary

Please use the dictionary coverter
[jageocoder-converter](https://github.com/t-sagara/jageocoder-converter).

## Deployment

At this time, this package has been developed more to illustrate the logic of Japanese-address geocoding than for actual use. Because of the emphasis on readability and ease of installation, it is about 50 times slower than the version developed in C++ in 2000.

If you are assuming practical use, consider putting SQLite3 files on fast storages like tmpfs, using cache mechanisms, or using other RDBMS such as PostgreSQL.

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
