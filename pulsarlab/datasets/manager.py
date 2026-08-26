"""UI-free dataset manager with atomic visibility/state operations."""

from __future__ import annotations


from pulsarlab.datasets.dataset import Dataset


class DatasetManager:
    """Manage datasets without importing Qt or plotting code."""

    def __init__(self) -> None:
        self._datasets: dict[str, Dataset] = {}
        self._active_id: str | None = None

    def add(self, dataset: Dataset) -> None:
        self._datasets[dataset.dataset_id] = dataset
        if self._active_id is None or not self._datasets.get(self._active_id, dataset).visible:
            self._active_id = dataset.dataset_id

    def remove(self, dataset_id: str) -> None:
        self._datasets.pop(dataset_id, None)
        if self._active_id == dataset_id:
            self._active_id = self.first_visible_id()

    def clear(self) -> None:
        self._datasets.clear()
        self._active_id = None

    def get(self, dataset_id: str) -> Dataset | None:
        return self._datasets.get(dataset_id)

    def all(self) -> list[Dataset]:
        return list(self._datasets.values())

    def visible(self) -> list[Dataset]:
        return [d for d in self._datasets.values() if d.visible]

    def first_visible_id(self) -> str | None:
        for d in self._datasets.values():
            if d.visible:
                return d.dataset_id
        return None

    @property
    def active_id(self) -> str | None:
        if self._active_id is not None:
            d = self._datasets.get(self._active_id)
            if d is not None and d.visible:
                return self._active_id
        return self.first_visible_id()

    @active_id.setter
    def active_id(self, dataset_id: str | None) -> None:
        if dataset_id is None or (dataset_id in self._datasets and self._datasets[dataset_id].visible):
            self._active_id = dataset_id

    def active(self) -> Dataset | None:
        aid = self.active_id
        return None if aid is None else self._datasets.get(aid)

    def set_visible(self, dataset_id: str, visible: bool) -> None:
        dataset = self._datasets.get(dataset_id)
        if dataset is None:
            return
        self._datasets[dataset_id] = dataset.with_visibility(visible)
        if not visible and self._active_id == dataset_id:
            self._active_id = self.first_visible_id()
        elif visible and self._active_id is None:
            self._active_id = dataset_id

    def set_active_components(self, dataset_id: str, components: set[int] | None) -> None:
        dataset = self._datasets.get(dataset_id)
        if dataset is None:
            return
        self._datasets[dataset_id] = dataset.with_active_components(components)

    def replace_dataset(self, dataset: Dataset) -> None:
        if dataset.dataset_id not in self._datasets:
            return
        self._datasets[dataset.dataset_id] = dataset
