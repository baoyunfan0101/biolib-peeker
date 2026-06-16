from crawler.model import BatchShipment
from db.abstract_store import AbstractStore


class WarehouseKeeper:
    def __init__(
            self,
            store: AbstractStore,
    ) -> None:
        self.store = store

    def dispatch(
            self,
            limit: int,
    ) -> list[int]:
        return self.store.pop(limit)

    def receive(
            self,
            shipment: BatchShipment,
    ) -> None:
        self.store.write_taxa(shipment.taxa_items)
        self.store.write_synonym(shipment.synonym_items)
        self.store.push(shipment.child_page_ids)
        self.store.mark_done(shipment.done_page_ids)
        self.store.mark_failed(shipment.failed_page_ids)

    def close(self) -> None:
        self.store.close()

    def __len__(self) -> int:
        return len(self.store)
