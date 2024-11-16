from __future__ import annotations

import typing
from functools import cached_property

from textual.containers import Vertical
from textual.widgets import Label, ProgressBar

if typing.TYPE_CHECKING:

    KeySeq = tuple[int, ...]


class Progress(Vertical):

    def __init__(self, total_sequences: int = 0) -> None:
        self.total_sequences = total_sequences
        super().__init__(id="progress-container")

    def compose(self):
        yield Label(
            f"Placed 0 out of of {self.total_sequences} ngrams", id="progress-title"
        )
        yield ProgressBar(total=self.total_sequences, show_eta=False, id="progress-bar")

    def update(self, total: int, progress: int) -> None:
        self.progress.update(total=total, progress=progress)
        self.text.update(f"Placed {progress} out of {total} ngrams.")

    @cached_property
    def progress(self) -> ProgressBar:
        return typing.cast(ProgressBar, self.query_one("#progress-bar"))

    @cached_property
    def text(self) -> Label:
        return typing.cast(Label, self.query_one("#progress-title"))
