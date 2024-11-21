"""The Key Sequence Sorter App.

Development
------------
Run in one terminal: (this shows logs and prints)
    uv run textual console
Run in another terminal: (this runs the app)
    uv run textual run --dev app/sort_app/sort_app.py foo examples/keyseq_effort_numbers_mini.yml
"""

from __future__ import annotations

import datetime as dt
import typing
from collections import Counter
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import TypedDict

from rich.align import Align
from rich.panel import Panel
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Footer, Label, Log

from app.config import Config, read_config
from app.effort import create_permutations, get_hands_data
from app.exit_modal import ExitModal
from app.progress import Progress
from app.sort_app.placement_manager import NgramPlacementManager
from app.sort_app.positionbar import PositionBar

if typing.TYPE_CHECKING:

    from app.effort import Hands

    KeySeq = tuple[int, ...]

STARTING_INSTRUCTIONS = """
Instructions:
The three shown cards are: the new ngram (highlighted, in the middle) and the two
surrounding ngrams. The rest of the ngrams are not shown.

This program uses binary search for placement. In other words, all new ngrams are
placed to the middle of the ordered ngrams. Each you move left, you jump to the middle
of the all the remaining ordered ngrams which have lower effort; each movement divides
the search space by two. This way placing an ngram to a set of 4000 ngrams takes maximum
of just 12 steps.

LEFT = "more of these" / low effort
RIGHT = "less of these" / high effort.
"""


@dataclass
class NgramShowParams:
    lower: KeySeq | None
    upper: KeySeq | None
    new: KeySeq | None
    hands: Hands


class DuplicateValuesError(RuntimeError): ...


class GetSymbolTextKwargs(TypedDict):
    key_seq: KeySeq | None
    fallback: str
    center: int


class NgramCard(Vertical):

    def __init__(self, identifier: str, hands: Hands, keyseq: KeySeq | None) -> None:
        super().__init__()
        self.identifier = identifier
        self.hands = hands
        self.keyseq = keyseq
        self.text = Label(self.to_content(self.keyseq), classes="ngram-card")

    def compose(self) -> ComposeResult:
        yield self.text

    def update(self, keyseq: KeySeq | None, is_finished: bool = False) -> None:
        self.keyseq = keyseq
        self.text.update(self.to_content(self.keyseq, is_finished=is_finished))
        self.text.classes = "ngram-card hidden" if keyseq is None else "ngram-card"

    def get_style(self, is_finished: bool = False) -> str:
        if is_finished or self.identifier != "new":
            return "#0d4247"
        return "#2beaff"

    def to_content(self, key_seq: KeySeq | None, is_finished: bool = False) -> Align:
        style = self.get_style(is_finished)

        kwargs = GetSymbolTextKwargs(key_seq=key_seq, fallback="   ", center=3)
        symbols_left = self.hands.get_symbols_text("Left", **kwargs)
        symbols_right = self.hands.get_symbols_text("Right", **kwargs)
        text = symbols_left + "\n" + symbols_right
        panel = Panel(text, padding=(1, 5), border_style=style)
        return Align(
            panel,
            align="center",  # Align the panel to the center
            vertical="middle",
            pad=True,
        )


class NgramSortColumn(Horizontal):
    def __init__(self, params: NgramShowParams) -> None:
        super().__init__()
        self.params = params
        self.card_left = NgramCard("left", self.params.hands, self.params.lower)
        self.card_middle = NgramCard("new", self.params.hands, self.params.new)
        self.card_right = NgramCard("right", self.params.hands, self.params.upper)

    def compose(self) -> ComposeResult:
        yield self.card_left
        yield self.card_middle
        yield self.card_right

    def update(
        self,
        left: KeySeq | None,
        right: KeySeq | None,
        new: KeySeq | None,
        is_finished: bool = False,
    ):
        self.card_left.update(left)
        self.card_middle.update(new, is_finished=is_finished)
        self.card_right.update(right)


class MainArea(Vertical):

    default_text = Text(
        "Move the ngram to the LEFT or RIGHT (or press ENTER to place it)",
    )

    def __init__(
        self,
        ngram_params: NgramShowParams,
        total_sequences: int = 0,
    ) -> None:
        self.total_sequences = total_sequences
        self.ngram_params = ngram_params
        self.sort_col = NgramSortColumn(self.ngram_params)
        self.text = Label(self.default_text, id="keyseq_instructions", classes="box")
        self.text_additional = Label("", id="additional_text")
        self.log_component = Log()
        self.log_component.can_focus = False
        self.log_component.auto_scroll = True
        # self.log_component.styles.height = 18
        self.position_bar = PositionBar(0, 1, 1, 0)
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Progress(total_sequences=self.total_sequences)
        with Container(
            classes="centered-full-width-container", id="instructions-text-container"
        ):
            yield self.text
        with Container(
            classes="centered-full-width-container", id="ngram-cards-container"
        ):
            yield self.sort_col
        with Container(
            classes="centered-full-width-container", id="position-bar-container"
        ):
            yield self.position_bar
        with Container(id="additional-text-container"):
            yield self.text_additional
        with Container(classes="centered-full-width-container", id="log-container"):
            yield self.log_component

    def set_progress(self, progress: int) -> None:
        self.progress.update(total=self.total_sequences, progress=progress)

    @cached_property
    def text(self) -> Label:
        return typing.cast(Label, self.query_one("#keyseq_instructions"))

    @cached_property
    def progress(self) -> Progress:
        return self.query_one(Progress)

    def update(
        self,
        left: KeySeq | None,
        right: KeySeq | None,
        new: KeySeq | None,
        positions: tuple[float, float, float, float],
        additional_text: Text | str = "",
        is_finished: bool = False,
    ):
        if is_finished:
            self.text.update(
                "🎉 All ngrams placed! Save the results (Ctrl-S) and quit (Ctrl-C)."
            )
            self.text_additional.update("")
        else:
            self.text.update(self.default_text)
            self.text_additional.update(additional_text)
        self.sort_col.update(left, right, new, is_finished=is_finished)
        self.position_bar.update(*positions)

    def write_log(self, message: str):
        self.log_component.write_line(message)


class KeySequenceSortApp(App):
    TITLE = "Ngram Sorter"
    CSS_PATH = "sort_app.tcss"
    BINDINGS = [
        Binding("ctrl+c", "exit", "Exit"),
        Binding("ctrl+s", "save", "Save"),
        Binding("left", "left", "Left"),
        Binding("right", "right", "Right"),
        Binding("enter", "place_ngram", "Place ngram"),
        Binding("backspace", "move_back", "Move back"),
        Binding("escape", "reset_current_ngram", "Reset current ngram"),
        Binding("p", "previous_ngram", "Previous ngram"),
    ]

    def __init__(self, file_out: Path | str, config: Config) -> None:
        self.file_out = Path(file_out)
        self.config = config
        self.hands = get_hands_data(self.config)
        permutations = create_permutations(
            self.hands.left, self.hands.right, sequence_lengths=(1, 2, 3)
        )
        self.n_ngrams = len(permutations)
        self.main_area = MainArea(
            ngram_params=NgramShowParams(None, None, None, hands=self.hands),
            total_sequences=self.n_ngrams,
        )
        self.manager = NgramPlacementManager(
            permutations=permutations,
            callback=self.refresh_ngram_view,
        )
        super().__init__()

    def compose(self) -> ComposeResult:
        """Create child widgets for the app. This happens before on_mount."""
        with Horizontal():
            yield self.main_area
        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        self.load_from_file()
        self.write_log("Session started.")
        self.write_log(STARTING_INSTRUCTIONS)

    def action_exit(self):
        self.push_screen(ExitModal(), self.conditional_exit)

    def action_left(self):
        self.manager.move_left()

    def action_right(self):
        self.manager.move_right()

    def action_place_ngram(self):
        if self.manager.is_finished():
            return

        idx = self.manager.current_placement_index()
        ngram_keyseq = self.manager.place_current_ngram()
        if ngram_keyseq is None or idx is None:
            return

        ngram_left = self.hands.left.get_symbols(ngram_keyseq)
        ngram_right = self.hands.right.get_symbols(ngram_keyseq)

        self.write_log(f"Placed ngram {ngram_left} {ngram_right} to {idx+1}")

    def action_move_back(self):
        self.manager.move_back()

    def action_reset_current_ngram(self):
        self.manager.reset_current_ngram()

    def action_previous_ngram(self):
        self.manager.previous_ngram()

    def action_save(self):
        with open(self.file_out, "w") as f:
            for key_seq in self.ordered_ngrams:
                f.write(",".join(map(str, key_seq)) + "\n")
        self.write_log(f"Saved ngrams to {self.file_out}")

    def conditional_exit(self, condition: bool):
        if condition:
            self.exit()

    def write_log(self, message: str):
        ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {message}"
        self.main_area.write_log(line)

    def load_from_file(self) -> None:
        if self.file_out.exists():
            self.write_log(f"Loading ngrams from {self.file_out}")
            with open(self.file_out, "r") as f:
                lines = f.readlines()
            key_seqs = [tuple(map(int, line.strip().split(","))) for line in lines]
            if not key_seqs:
                return
            most_common_ngram, repeats = Counter(key_seqs).most_common(1)[0]
            if repeats > 1:
                raise DuplicateValuesError(
                    f'Duplicate values for "{most_common_ngram}" in "{self.file_out}".'
                )
            self.manager.load_state(key_seqs)
        else:
            # This inserts the first key sequence.
            self.action_place_ngram()

    def refresh_ngram_view(
        self,
    ) -> None:
        if not hasattr(self, "manager"):
            return  # skip during init

        n_left = len(self.manager.ngrams_left_side_of_current)
        n_right = len(self.manager.ngrams_right_side_of_current)
        cur_idx = self.manager.current_placement_index()

        curpos = (
            (f"pos: ", (str(cur_idx + 1), "plum3"), ", ")
            if cur_idx is not None
            else ("",)
        )

        leftstyle = "pale_green1"
        rightstyle = "sky_blue2"
        totalstyle = "bold wheat1"
        text = Text.assemble(
            *curpos,
            "L: ",
            (str(n_left), leftstyle),
            ", R: ",
            (str(n_right), rightstyle),
            " (total: ",
            (f"{n_left  + n_right}", totalstyle),
            ")",
        )
        self.main_area.update(
            left=self.manager.left_of_current,
            right=self.manager.right_of_current,
            new=self.manager.current_ngram,
            additional_text=text,
            is_finished=self.manager.is_finished(),
            positions=self.manager.ordered_ngrams_area_widths(),
        )
        self.main_area.set_progress(len(self.ordered_ngrams))

    @property
    def ordered_ngrams(self) -> list[KeySeq]:
        return self.manager.ordered_ngrams


if __name__ == "__main__":
    import sys

    app = KeySequenceSortApp(sys.argv[1], config=read_config(sys.argv[2]))
    app.run()
