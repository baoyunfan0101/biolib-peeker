from __future__ import annotations

from pathlib import Path

from rubberneck import EngineAction, EngineEvent, Item
from rubberneck.pipeline.base import PipelineResult
from rubberneck.pipeline.sqlite import SQLitePipeline

DB_NAME = 'taxa.db'

CATEGORY = {
    'included': 10,
    'unplaced': 20,
    'hybrids': 30,
    'fossil_included': 40,
    'fossil_unplaced': 41,
    'nomina_dubia': 50,
    'nomina_nuda': 51,
    'synonyms': 100,
    'synonyms_included': 110,
    'synonyms_nomen_nudum': 111,
    'synonyms_partim.': 112,
    'synonyms_misspelling': 113,
    'unjustified_emendation': 120,
    'unjustified_replacement_name': 121,
}

RANK = {
    'root': 1,
    'system': 10,
    'domain': 30,
    'superregnum': 50,
    'regnum': 51,
    'subregnum': 52,
    'kingdom': 60,
    'divisio': 70,
    'subdivisio': 80,
    'superphylum': 100,
    'phylum': 101,
    'subphylum': 102,
    'infraphylum': 103,
    'superclassis': 200,
    'class': 201,
    'subclass': 202,
    'infraclass': 203,
    'cohor': 250,
    'superorder': 300,
    'order': 301,
    'suborder': 302,
    'infraorder': 303,
    'parvorder': 304,
    'falanga': 350,
    'superfamily': 400,
    'family': 401,
    'subfamily': 402,
    'supertribus': 450,
    'tribus': 451,
    'subtribus': 452,
    'intergeneric': 500,
    'genus': 501,
    'subgenus': 502,
    'section': 503,
    'species': 601,
    'subspecies': 610,
    'varietas': 620,
    'form': 621,
    'cultivar': 622,
    'agregate': 630,
    'chimera': 631,
    'group': 640,
    'hybrid': 650,
}


class BioLibSQLitePipeline(SQLitePipeline):
    def __init__(
        self,
        path: str = './data',
        filename: str = DB_NAME,
        reset: bool = False,
    ) -> None:
        self.reset = reset
        Path(path).mkdir(parents=True, exist_ok=True)
        super().__init__(
            table='items',
            path=path,
            filename=filename,
            on_conflict='IGNORE',
        )

    def open(self) -> None:
        super().open()
        assert self._conn is not None
        with self._lock:
            if self.reset:
                self._conn.execute('DROP TABLE IF EXISTS taxa')
                self._conn.execute('DROP TABLE IF EXISTS synonyms')
            self._conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS taxa (
                    id INTEGER PRIMARY KEY,
                    parent INTEGER,
                    category INTEGER,
                    rank INTEGER,
                    scientific_name TEXT,
                    authority_year TEXT,
                    geological_range TEXT,
                    english_name TEXT
                )
                '''
            )
            self._conn.execute(
                '''
                INSERT OR IGNORE INTO taxa VALUES
                (?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    14772,
                    -1,
                    CATEGORY['included'],
                    RANK['root'],
                    'Vitae',
                    '',
                    '',
                    'living organisms',
                ),
            )
            self._conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS synonyms (
                    parent INTEGER,
                    category INTEGER,
                    synonym TEXT,
                    authority_year TEXT,
                    PRIMARY KEY (parent, synonym, authority_year)
                )
                '''
            )

    def process_item(self, item: Item) -> PipelineResult:
        assert self._conn is not None
        item_type = item.get('type')

        if item_type == 'taxon':
            category = CATEGORY.get(str(item['category'])) if item['category'] not in ('', None) else None
            if category is None and item['category'] not in ('', None):
                raise ValueError(f'unknown category: {item["category"]!r}')
            rank = RANK.get(str(item['rank'])) if item['rank'] not in ('', None) else None
            if rank is None and item['rank'] not in ('', None):
                raise ValueError(f'unknown rank: {item["rank"]!r}')

            with self._lock:
                cursor = self._conn.execute(
                    '''
                    INSERT OR IGNORE INTO taxa (
                        id,
                        parent,
                        category,
                        rank,
                        scientific_name,
                        authority_year,
                        geological_range,
                        english_name
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        item['id'],
                        item['parent'],
                        category,
                        rank,
                        item['scientific_name'],
                        item['authority_year'],
                        item['geological_range'],
                        item['english_name'],
                    ),
                )
            if cursor.rowcount:
                return (EngineEvent(EngineAction.COLLECT, {'taxa': cursor.rowcount}),)
            return ()

        if item_type == 'synonym':
            category = CATEGORY.get(str(item['category'])) if item['category'] not in ('', None) else None
            if category is None and item['category'] not in ('', None):
                raise ValueError(f'unknown category: {item["category"]!r}')

            with self._lock:
                cursor = self._conn.execute(
                    '''
                    INSERT OR IGNORE INTO synonyms (
                        parent,
                        category,
                        synonym,
                        authority_year
                    )
                    VALUES (?, ?, ?, ?)
                    ''',
                    (
                        item['parent'],
                        category,
                        item['synonym'],
                        item['authority_year'],
                    ),
                )
            if cursor.rowcount:
                return (EngineEvent(EngineAction.COLLECT, {'synonyms': cursor.rowcount}),)
            return ()

        raise ValueError(f'unknown BioLib item type: {item_type!r}')
