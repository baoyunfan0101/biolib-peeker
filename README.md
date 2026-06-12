# BioLib Peeker

A lightweight personal project for crawling and organizing BioLib taxonomy data.

## What it does

Starting from a root taxon page, the crawler recursively traverses BioLib taxonomy pages and extracts:

| Field Name | Description | Example |
|---|---|---|
| `id` | BioLib identifier. For taxa, extracted from the page URL; for synonyms, stored separately in SQLite without an `id`. | `14782` |
| `parent` | BioLib ID of the page where the record was found. | `14772`, `14782` |
| `category` | Normalized category ID derived from the source section and stored as an integer mapping. | `10`=`included`, `20`=`unplaced`, `30`=`hybrids`, `40`=`fossil_included`, `41`=`fossil_unplaced`, `50`=`nomina_dubia`, `51`=`nomina_nuda`, `100`=`synonyms`, `110`=`synonyms_included`, `111`=`synonyms_nomen_nudum`, `112`=`synonyms_partim.`, `113`=`synonyms_misspelling`, `120`=`unjustified_emendation`, `121`=`unjustified_replacement_name` |
| `rank` | Taxonomic rank mapped to a numeric hierarchy in SQLite. | `domain`, `family`, `species`, `subgenus`, `section`, `cultivar` |
| `scientific_name` | Scientific name extracted from the record. | `Bacteria`, `Panbiota` |
| `authority_year` | Authority and publication year extracted from the record. | `Linnaeus, 1758`, `Wagner, 2004` |
| `geological_range` | Geological age range extracted from the record, when available. | `Archean–recent` |
| `english_name` | English common name extracted from the record, when available. | `bacterians`, `lion` |

- Source:  
https://www.biolib.cz/

- Default root page:  
https://www.biolib.cz/en/taxon/id14772/

## Project Structure

```text
biolib-peeker/
├── biolib_parser.py       # parse BioLib pages
├── main_loop.py           # BFS crawling loop
└── db/
    ├── abstract_store.py  # storage interface definition
    ├── memory_store.py    # in-memory CSV backend
    └── sqlite_store.py    # persistent SQLite backend with separate taxa/synonym tables
```

## Storage

- **MemoryStore**: in-memory BFS queue, exports to CSV.
- **SqliteStore**: persistent BFS queue, resumes after interruption, stores taxa and synonyms in separate SQLite tables.

## Run

First run:
```bash
python -m main_loop --init-page 14772 --store sqlite --reset --log summary
```

Resume unfinished pages (only with **SqliteStore**):
```bash
python -m main_loop --store sqlite --log summary
```

| Argument | Description | Default |
|---|---|---|
| `--init-page` | Starting page ID. | `"14772"` |
| `--store` | Storage backend. | `"sqlite"` |
| `--reset` | Reset existing data before crawling. | `False` |
| `--log` | Log level. | `"summary"` |

## Disclaimer

This project is strictly for personal use and learning.
It is not affiliated with or endorsed by BioLib.
Do not use it for commercial purposes, redistribution, or public services.                          | `"summary"` |

## Disclaimer

This project is strictly for personal use and learning.
It is not affiliated with or endorsed by BioLib.
Do not use it for commercial purposes, redistribution, or public services.