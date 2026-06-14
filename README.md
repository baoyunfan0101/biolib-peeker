# BioLib Peeker

A lightweight personal project for crawling and organizing BioLib taxonomy data.

## What it does

Starting from a root taxon page, the crawler recursively traverses BioLib taxonomy pages and extracts records into two
datasets.

- Source:  
  https://www.biolib.cz/

- Default root page:  
  https://www.biolib.cz/en/taxon/id14772/

### taxa

| Field Name         | Description                                                                                                     | Example                                                                                     |
|--------------------|-----------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------|
| `id`               | BioLib identifier extracted from the page URL.                                                                  | `14772`                                                                                     |
| `parent`           | BioLib ID of the page where the record was found.                                                               | `14778`, `14783`                                                                            |
| `category`         | Category stored as an integer mapping. See `CATEGORY` in `db/abstract_store.py` for the complete mapping.       | `10`=`included`, `51`=`nomina_nuda`, `100`=`synonyms`, `121`=`unjustified_replacement_name` |
| `rank`             | Taxonomic rank stored as an integer hierarchy. See `RANK` in `db/abstract_store.py` for the complete hierarchy. | `1`=`root`, `30`=`domain`, `401`=`family`, `501`=`genus`, `601`=`species`                   |
| `scientific_name`  | Scientific name extracted from the record.                                                                      | `Bacteria`, `Eukaryota`                                                                     |
| `authority_year`   | Authority and publication year extracted from the record.                                                       | `(Haeckel, 1894) Woese, Kandler Wheelis, 1990`, `Whittaker & Margulis, 1978`                |
| `geological_range` | Geological age range extracted from the record, when available.                                                 | `Archean – recent`, `Proterozoic – recent`                                                  |
| `english_name`     | English common name extracted from the record, when available.                                                  | `bacterians`, `lifeforms with nucletic cells`                                               |

### synonyms

| Field Name       | Description                                                                                               | Example                                                                                                         |
|------------------|-----------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------|
| `parent`         | BioLib ID of the page where the synonym was found.                                                        | `14772`                                                                                                         |
| `category`       | Category stored as an integer mapping. See `CATEGORY` in `db/abstract_store.py` for the complete mapping. | `100`=`synonyms`, `110`=`synonyms_included`, `113`=`synonyms_misspelling`, `121`=`unjustified_replacement_name` |
| `synonym`        | Synonym name extracted from the record.                                                                   | `Panbiota`                                                                                                      |
| `authority_year` | Authority and publication year extracted from the record.                                                 | `Wagner, 2004`                                                                                                  |

## Project Structure

```text
biolib-peeker/
├── README.md
├── LICENSE
├── requirements.txt
├── .gitignore
│
├── biolib_parser.py       # parse BioLib taxonomy pages
├── main_loop.py           # crawler entry point and worker loop
│
└── db/
    ├── __init__.py
    ├── abstract_store.py  # storage interface and shared mappings
    ├── memory_store.py    # in-memory queue with CSV export
    └── sqlite_store.py    # SQLite-backed persistent queue
```

## Storage

- **MemoryStore**: in-memory BFS queue, exports to CSVs.
- **SqliteStore**: persistent BFS queue, supports multithreaded crawling, resumes after interruption.

## Run

First run:

```bash
python -m main_loop --init-page 14772 --store sqlite --reset --workers 8 --log summary
```

Resume unfinished pages (only with **SqliteStore**):

```bash
python -m main_loop --store sqlite --workers 8 --log summary
```

| Argument        | Description                                                                     | Default   |
|-----------------|---------------------------------------------------------------------------------|-----------|
| `--init-page`   | Starting BioLib page ID. Only used when `--reset` is set.                       | `14772`   |
| `--store`       | Storage backend: `memory` or `sqlite`.                                          | `sqlite`  |
| `--reset`       | Reset existing data before crawling.                                            | `False`   |
| `--log`         | Log level: `none`, `summary`, or `detail`.                                      | `summary` |
| `--workers`     | Number of worker threads. Multi-threading is only supported with `SqliteStore`. | `8`       |
| `--idle-rounds` | Consecutive empty polls before a worker exits.                                  | `30`      |
| `--idle-sleep`  | Sleep time between empty polls in seconds.                                      | `1.0`     |

## Disclaimer

This project is strictly for personal use and learning.
It is not affiliated with or endorsed by BioLib.
Do not use it for commercial purposes, redistribution, or public services.