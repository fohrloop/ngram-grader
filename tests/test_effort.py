from pathlib import Path

from app.config import Config
from app.effort import (
    DirectionType,
    FingerType,
    Hand,
    Hands,
    Index,
    Middle,
    Pinky,
    RepeatType,
    Ring,
    RowDiffType,
    create_permutations,
    get_direction_for_bigram,
    get_direction_for_trigram,
    get_hands_data,
    get_rowdiff_for_bigram,
    get_union_of_keys,
    permutation_is_typable,
)
from rich.text import Text

test_folder = Path(__file__).parent.parent
examples_folder = test_folder.parent / "examples"


class TestHand:

    def test_normal_config(self, config: Config):
        hands = get_hands_data(config)
        left, right = hands.left, hands.right
        # fmt: off
        left_expected = Hand(hand='Left', symbols={0: '1', 1: '2', 2: '3', 3: '4', 4: '5', 5: '6', 6: '7', 7: '8', 8: '9', 9: '0'})
        right_expected = Hand(hand='Right', symbols={0: 'A', 1: 'B', 2: 'C', 3: 'D', 4: 'E', 5: 'F', 6: 'G', 7: 'H', 8: 'I', 9: 'J'})
        # fmt: on
        assert left.hand == left_expected.hand
        assert right.hand == right_expected.hand
        assert left.symbols == left_expected.symbols
        assert right.symbols == right_expected.symbols

    def test_fingers_and_colors(self, config_minimal: Config):
        hands = get_hands_data(config_minimal)
        left, right = hands.left, hands.right
        assert left.key_categories == right.key_categories == {0: "M", 1: "m", 2: "i"}
        assert left.fingers == right.fingers == {0: "m", 1: "m", 2: "i"}
        assert (
            left.colors
            == right.colors
            == {0: "orange3", 1: "chartreuse3", 2: "chartreuse3"}
        )

    def test_get_finger(self, config_minimal: Config):
        hands = get_hands_data(config_minimal)

        key_seq = (0, 2, 1)

        expected_out = Text.assemble(
            ("M", "orange3"), ("i", "chartreuse3"), ("m", "chartreuse3")
        )
        assert hands.left.get_fingers_str(key_seq) == expected_out
        assert hands.right.get_fingers_str(key_seq) == expected_out
        assert hands.get_fingers_str(key_seq) == expected_out

    def test_repeat_type_ordering(self):
        assert RepeatType.SFT > RepeatType.SFB
        assert RepeatType.SFB > RepeatType.SFS

        assert FingerType.P > FingerType.R
        assert FingerType.R > FingerType.M
        assert FingerType.M > FingerType.I
        assert FingerType.I > FingerType.T

        left = RepeatType.SFS, FingerType.P
        right = RepeatType.SFT, FingerType.I
        assert max(left, right) == right

    def test_get_repeats(self, config_minimal: Config):
        hands = get_hands_data(config_minimal)
        # Nothing
        assert hands.get_repeats_tuple((1, 2)) is None
        assert hands.get_repeats_tuple((1,)) is None

        # REP: index
        assert hands.get_repeats_tuple((2, 2)) == (RepeatType.REP, FingerType.I)
        # SFB: middle
        assert hands.get_repeats_tuple((0, 1)) == (RepeatType.SFB, FingerType.M)

        # SFS: index
        assert hands.get_repeats_tuple((2, 0, 2)) == (RepeatType.SFS, FingerType.I)
        # SFS: middle
        assert hands.get_repeats_tuple((0, 2, 1)) == (RepeatType.SFS, FingerType.M)
        # SFT middle
        assert hands.get_repeats_tuple((0, 1, 0)) == (RepeatType.SFT, FingerType.M)

    def test_get_repeats_text(self, config_minimal: Config):
        hands = get_hands_data(config_minimal)

        assert hands.get_repeats_text((0, 1)) == Text.assemble(
            ("SFB", Hands.repeat_colors[RepeatType.SFB]),
            "(",
            ("m", Hands.finger_colors[Middle]),
            ")",
        )

    def test_get_rowdiff_bigrams(self, config_full: Config):
        hands = get_hands_data(config_full)
        assert hands.get_rowdiff((9, 4)) == (RowDiffType.MiddleBelowIndex2u,)
        assert hands.get_rowdiff((9, 1)) == (RowDiffType.MiddleBelowIndex2u,)

        assert hands.get_rowdiff((9, 14)) == (RowDiffType.MiddleBelowPinky1u,)
        assert hands.get_rowdiff((8, 13)) == (RowDiffType.MiddleBelowPinky1u,)
        assert hands.get_rowdiff((9, 16)) == (RowDiffType.MiddleBelowPinky1u,)

        assert hands.get_rowdiff((6, 13)) == (RowDiffType.IndexBelowPinky2u,)
        assert hands.get_rowdiff((3, 13)) == (RowDiffType.IndexBelowPinky2u,)

        assert hands.get_rowdiff((9, 10)) == (RowDiffType.MiddleBelowRing2u,)

        assert hands.get_rowdiff((15, 10)) == (RowDiffType.PinkyBelowRing2u,)

        assert hands.get_rowdiff((9, 13)) == (RowDiffType.MiddleBelowPinky2u,)

        assert hands.get_rowdiff((12, 14)) == (RowDiffType.RingBelowPinky1u,)
        assert hands.get_rowdiff((12, 16)) == (RowDiffType.RingBelowPinky1u,)
        assert hands.get_rowdiff((11, 13)) == (RowDiffType.RingBelowPinky1u,)

        assert hands.get_rowdiff((12, 13)) == (RowDiffType.RingBelowPinky2u,)

    def test_get_rowdiff_trigrams(self, config_full: Config):
        hands = get_hands_data(config_full)

        # This has both, MiddleBelowIndex2u (9,4) and MiddleBelowRing2u (10,9)
        assert hands.get_rowdiff((10, 9, 4)) == (
            RowDiffType.MiddleBelowRing2u,
            RowDiffType.MiddleBelowIndex2u,
        )
        # This has just MiddleBelowIndex2u (9,4)!
        assert hands.get_rowdiff((10, 4, 9)) == (RowDiffType.MiddleBelowIndex2u,)

    def test_get_rowdiff_text(self, config_full: Config):
        hands = get_hands_data(config_full)

        assert hands.get_rowdiff_text((9, 4)) == Text.assemble(
            ("mi2u", Hands.rowdiff_colors[RowDiffType.MiddleBelowIndex2u])
        )

        assert hands.get_rowdiff_text((10, 9, 4)) == Text.assemble(
            ("mr2u", Hands.rowdiff_colors[RowDiffType.MiddleBelowRing2u]),
            " ",
            ("mi2u", Hands.rowdiff_colors[RowDiffType.MiddleBelowIndex2u]),
        )

    def test_max_rowdiff_tuples(self):

        # middle effort: MiddleBelowPinky2u
        # high effort: RingBelowPinky2u
        # low effort: MiddleBelowIndex2u
        tuple1 = (RowDiffType.MiddleBelowPinky2u,)
        tuple2 = (RowDiffType.MiddleBelowIndex2u, RowDiffType.RingBelowPinky2u)
        assert max(tuple1, tuple2, key=max) == tuple2


class TestRowDiff:

    def test_rowdiff_same_finger_2u(self):
        assert (
            get_rowdiff_for_bigram(FingerType.P, 0, FingerType.P, 2)
            == RowDiffType.RowDiff2u
        )

    def test_rowdiff_same_row(self):
        assert get_rowdiff_for_bigram(FingerType.P, 1, FingerType.I, 1) is None

    def test_rowdiff_index_below_pinky_2u(self):
        assert (
            get_rowdiff_for_bigram(FingerType.I, 2, FingerType.P, 0)
            == RowDiffType.IndexBelowPinky2u
        )

    def test_rowdiff_middle_below_index_2u(self):
        assert (
            get_rowdiff_for_bigram(FingerType.M, 2, FingerType.I, 0)
            == RowDiffType.MiddleBelowIndex2u
        )

    def test_rowdiff_middle_below_index_1u(self):
        assert get_rowdiff_for_bigram(FingerType.M, 1, FingerType.I, 0) is None

    def test_rowdiff_middle_below_pinky_1u(self):
        assert (
            get_rowdiff_for_bigram(FingerType.M, 2, FingerType.P, 1)
            == RowDiffType.MiddleBelowPinky1u
        )

    def test_rowdiff_middle_below_pinky_2u(self):
        assert (
            get_rowdiff_for_bigram(FingerType.M, 3, FingerType.P, 1)
            == RowDiffType.MiddleBelowPinky2u
        )


class TestDirection:

    def test_bigrams(self):
        assert (
            get_direction_for_bigram(FingerType.P, FingerType.M)
            == DirectionType.InwardsPinkyMiddle
        )
        assert (
            get_direction_for_bigram(FingerType.M, FingerType.P)
            == DirectionType.OutwardsMiddlePinky
        )
        assert (
            get_direction_for_bigram(FingerType.P, FingerType.R)
            == DirectionType.InwardsPinkyRing
        )
        assert (
            get_direction_for_bigram(FingerType.R, FingerType.P)
            == DirectionType.OutwardsRingPinky
        )
        assert get_direction_for_bigram(FingerType.P, FingerType.I) is None
        assert get_direction_for_bigram(FingerType.M, FingerType.I) is None
        assert get_direction_for_bigram(FingerType.I, FingerType.I) is None

    def test_trigrams(self):
        # No pinky -> Redirect lvl 1
        assert get_direction_for_trigram(Middle, Index, Ring) is DirectionType.Redirect1
        # Index in the middle (pinky included)-> Redirect lvl 2
        assert (
            get_direction_for_trigram(Middle, Index, Pinky) is DirectionType.Redirect2
        )
        # Index not in the middle (pinky included) -> Redirect lvl 3
        assert (
            get_direction_for_trigram(Middle, Pinky, Index) is DirectionType.Redirect3
        )
        # No index -> Redirect lvl 4
        assert get_direction_for_trigram(Middle, Pinky, Ring) is DirectionType.Redirect4

        # Not a redirect
        assert get_direction_for_trigram(Index, Middle, Ring) is None

        # Not a redirect, but pinky included
        assert (
            get_direction_for_trigram(Index, Ring, Pinky)
            == DirectionType.OutwardsRingPinky
        )
        assert (
            get_direction_for_trigram(Pinky, Ring, Index)
            == DirectionType.InwardsPinkyRing
        )
        assert (
            get_direction_for_trigram(Pinky, Middle, Index)
            == DirectionType.InwardsPinkyMiddle
        )
        # In this case, there are two matches: InwardsPinkyRing and InwardsPinkyMiddle
        # Since the InwardsPinkyRing is one with larger effort, it should be returned
        assert (
            get_direction_for_trigram(Pinky, Ring, Middle)
            == DirectionType.InwardsPinkyRing
        )


class TestCreateUnionOfKeys:

    def test_simple(self):
        left = Hand(hand="Left", symbols={0: "1", 1: "2", 2: "3"})
        right = Hand(hand="Right", symbols={0: "A", 1: "B"})

        assert get_union_of_keys(left, right) == [0, 1, 2]

    def test_simple_another(self):
        left = Hand(hand="Left", symbols={0: "1", 6: "6"})
        right = Hand(hand="Right", symbols={1: "B"})

        assert get_union_of_keys(left, right) == [0, 1, 6]


class TestCreatePermutations:
    left = Hand(hand="Left", symbols={0: "x", 1: "y", 2: "z"})
    right = Hand(hand="Right", symbols={0: "a", 1: "b", 2: "c", 3: "d"})

    def test_simple(self):

        permutations = create_permutations(self.left, self.right, sequence_lengths=(1,))
        assert permutations == [(0,), (1,), (2,), (3,)]

    def test_2key(self):
        permutations = create_permutations(self.left, self.right, sequence_lengths=(2,))
        assert permutations == [
            (0, 0),
            (0, 1),
            (0, 2),
            (0, 3),
            (1, 0),
            (1, 1),
            (1, 2),
            (1, 3),
            (2, 0),
            (2, 1),
            (2, 2),
            (2, 3),
            (3, 0),
            (3, 1),
            (3, 2),
            (3, 3),
        ]

    def test_3key(self):
        permutations = create_permutations(
            left=Hand(hand="Left", symbols={0: "x", 1: "y"}),
            right=Hand(hand="Right", symbols={3: "d"}),
            sequence_lengths=(3,),
        )
        # In this case, the left hand can type all permutations with  0 and 1,
        # and right hand can only type (3,3,3)
        assert permutations == [
            (0, 0, 0),
            (0, 0, 1),
            (0, 1, 0),
            (0, 1, 1),
            (1, 0, 0),
            (1, 0, 1),
            (1, 1, 0),
            (1, 1, 1),
            (3, 3, 3),
        ]


class TestPermutationIsTypable:
    def test_is_typable(self):

        left = Hand(hand="Left", symbols={0: "x", 1: "y", 2: "z"})
        right = Hand(hand="Right", symbols={0: "x", 1: "y", 6: "z"})

        # Can be typed only with left
        assert permutation_is_typable(left, right, (2,)) == True
        # Can be typed only with right
        assert permutation_is_typable(left, right, (6,)) == True
        # Can be typed with both
        assert permutation_is_typable(left, right, (0, 1)) == True
        # Can be typed with left
        assert permutation_is_typable(left, right, (0, 1, 2)) == True
        # Can be typed with right
        assert permutation_is_typable(left, right, (0, 1, 6)) == True
        # Can't be typed with any hands (2 and 6 do exist, but in different hands)
        assert permutation_is_typable(left, right, (2, 6)) == False
        assert permutation_is_typable(left, right, (1, 2, 6)) == False
