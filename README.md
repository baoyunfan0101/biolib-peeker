# BioLib Peeker

[![Rubberneck](https://img.shields.io/badge/framework-Rubberneck-181717?logo=github)](https://github.com/baoyunfan0101/rubberneck)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

A lightweight personal project for crawling and organizing BioLib taxonomy data.

> **Current version:** v2.0.0  
> **Legacy standalone version:** [v1.0.0](https://github.com/baoyunfan0101/biolib-peeker/tree/v1.0.0)

## What it does

Starting from a root taxon page, the rubberneck-based crawler traverses BioLib taxonomy pages and extracts records into two datasets.

- **Source:** [BioLib](https://www.biolib.cz/)

- **Default root page:** [BioLib taxon 14772](https://www.biolib.cz/en/taxon/id14772/)

### taxa

| Field Name         | Description                                                                                                     | Example                                                                                     |
|--------------------|-----------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------|
| `id`               | BioLib identifier extracted from the page URL.                                                                  | `14772`                                                                                     |
| `parent`           | BioLib ID of the page where the record was found.                                                               | `14778`, `14783`                                                                            |
| `category`         | Category stored as an integer mapping. See `CATEGORY` in `biolib_pipeline.py` for the complete mapping.         | `10`=`included`, `51`=`nomina_nuda`, `100`=`synonyms`, `121`=`unjustified_replacement_name` |
| `rank`             | Taxonomic rank stored as an integer hierarchy. See `RANK` in `biolib_pipeline.py` for the complete hierarchy.   | `1`=`root`, `30`=`domain`, `401`=`family`, `501`=`genus`, `601`=`species`                   |
| `scientific_name`  | Scientific name extracted from the record.                                                                      | `Bacteria`, `Eukaryota`                                                                     |
| `authority_year`   | Authority and publication year extracted from the record.                                                       | `(Haeckel, 1894) Woese, Kandler Wheelis, 1990`, `Whittaker & Margulis, 1978`                |
| `geological_range` | Geological age range extracted from the record, when available.                                                 | `Archean – recent`, `Proterozoic – recent`                                                  |
| `english_name`     | English common name extracted from the record, when available.                                                  | `bacterians`, `lifeforms with nucletic cells`                                               |

### synonyms

| Field Name       | Description                                                                                               | Example                                                                                                         |
|------------------|-----------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------|
| `parent`         | BioLib ID of the page where the synonym was found.                                                        | `14772`                                                                                                         |
| `category`       | Category stored as an integer mapping. See `CATEGORY` in `biolib_pipeline.py` for the complete mapping.   | `100`=`synonyms`, `110`=`synonyms_included`, `113`=`synonyms_misspelling`, `121`=`unjustified_replacement_name` |
| `synonym`        | Synonym name extracted from the record.                                                                   | `Panbiota`                                                                                                      |
| `authority_year` | Authority and publication year extracted from the record.                                                 | `Wagner, 2004`                                                                                                  |

## Project Structure

```text
biolib-peeker/
├── README.md
├── LICENSE
├── requirements.txt
├── .gitignore
├── main.py                 # rubberneck engine entry point
├── biolib_parser.py        # pure BioLib HTML parser
├── biolib_spider.py        # rubberneck spider and BioLib challenge middleware
└── biolib_pipeline.py      # BioLib SQLite pipeline
```

## Run

Install dependencies:

```bash
pip install -r requirements.txt
```

Start or resume crawling:

```bash
python main.py
```

## Disclaimer

This project is strictly for personal use and learning.
It is not affiliated with or endorsed by BioLib.
Do not use it for commercial purposes, redistribution, or public services.
