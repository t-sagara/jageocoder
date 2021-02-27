# jageocoder - A Python Japanese geocoder

This is a Python port of the Japanese-address geocoder used in CSIS at the University of Tokyo's ["Address Matching Service"](https://newspat.csis.u-tokyo.ac.jp/geocode/modules/addmatch/index.php?content_id=1) and [GSI Maps](https://maps.gsi.go.jp/).

## Getting Started

This package provides address-geocoding functionality for Python programs. The basic usage is to specify a dictionary with `init()` then call `search()` to get geocoding results.

```python
python
>>> import jageocoder
>>> jageocoder.init(dsn='sqlite:///db/isj.db', trie='db/isj.trie')
>>> print(jageocoder.search('新宿区西新宿2-8-1'))
{'matched': '新宿区西新宿2-8-', 'candidates': [{'id': 5962895, 'name': '8番', 'x': 139.691778, 'y': 35.689627, 'level': 7, 'note': None, 'fullname': ['東京都', '新宿区', '西新宿', '二丁目', '8番']}]}
```

### Prerequisites

Requires Python 3.7.x or later and the following packages.

- [marisa-trie-m](https://pypi.org/project/marisa-trie-m/)
    for building and retrieving TRIE index
- [SQLAlchemy](https://pypi.org/project/SQLAlchemy/)
    for abstracting access to the RDBMS

### Installing

- Install the package using `pip install jageocoder`
- Download the dictionary file for SQLite3 from [here](https://www.info-proto.com/resource/isj-20210227.db.bz2)
- Create a TRIE index.

Note: This dictionary is created from the names and coordinates of address elements in the "GAIKU level" and "OAZA/CHOUME level", downloaded from the [MLIT's "Location Reference Information Download Service"](https://nlftp.mlit.go.jp/isj/index.html).

```sh
pip install jageocoder
mkdir db
curl https://www.info-proto.com/resource/isj-20210227.db.bz2 | bzip2 -dc > db/isj.db
python
>>> import jageocoder
>>> jageocoder.init(
	dsn="sqlite:///db/isj.db",
	trie="db/isj.trie")
>>> jageocoder.tree.create_trie_index()
    (it may takes several minutes)
```

## Running the tests

```python
python -m unittest
``` 

`tests.test_search` tests for some special address notations.

- Street address in Sapporo city such as '北3西1' for '北三条西一丁目'
- Toorina in Kyoto city such as '下立売通新町西入薮ノ内町' for '薮ノ内町'


## Deployment

At this time, this package has been developed more to illustrate the logic of Japanese-address geocoding than for actual use. Because of the emphasis on readability and ease of installation, it is about 50 times slower than the version developed in C++ in 2000.

If you are assuming practical use, consider putting SQLite3 files on fast storages like tmpfs, using cache mechanisms, or using other RDBMS such as PostgreSQL.

## ToDos

### Supporting address changes

The functionality to handle address changes due to municipal consolidation, etc. has already been implemented in the C++ version, but will be implemented in this package in the future.

### Documents for creating own dictionaries

The detailed procedure for creating a dictionary will be documented in due course.

To create your own dictionary, create a dictionary file in text format from location reference information, and read it into the database using `AddressTree.read_stream()`. There is an unorganized script in `utils/create_database.py` for your reference.

A script to create a dictionary file in text format from location reference information of MLIT is available in `converter/mlit-isj/`. We will organize these scripts in order.

## Contributing

Address notation varies. So suggestions for logic improvements are welcome. Please submit an issue with examples of address notations in use and how they should be parsed.

## Authors

* **Takeshi SAGARA** - [Info-proto Co.,Ltd.](https://www.info-proto.com/)

## License

This project is licensed under the [CC-BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).

This is not the scope of the dictionary data license. Please follow the license of the respective dictionary data.

## Acknowledgements

We would like to thank CSIS for allowing us to provide address matching services on their institutional website for over 20 years.
