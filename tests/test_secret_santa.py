"""
Tests for Secret Santa pairing generation.

Focuses on:
- Self-match prevention
- Blocked pairings
- Family exclusions
- Edge cases where pairings are impossible
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pytest

from secret_santa.secret_santa import SecretSanta


@pytest.mark.unit
class TestPairGeneration:

    def test_no_self_matches(self):
        """
        Nobody should ever draw themselves.
        """

        cog = SecretSanta(None)

        participants = [1, 2, 3, 4]

        pairings = cog._generate_pairings(participants)

        assert pairings is not None

        for giver, receiver in pairings:
            assert giver != receiver

    def test_directional_block_is_respected(self):
        """
        A blocked giver->receiver pairing should never occur.
        """

        cog = SecretSanta(None)

        participants = [1, 2, 3, 4]

        blocked = [
            [1, 2]
        ]

        for _ in range(250):

            pairings = cog._generate_pairings(
                participants,
                blocked_pairings=blocked
            )

            assert pairings is not None

            assert (1, 2) not in pairings

    def test_directional_block_is_one_way(self):
        """
        Blocking 1->2 should not block 2->1.
        """

        cog = SecretSanta(None)

        participants = [1, 2, 3, 4]

        blocked = [
            [1, 2]
        ]

        found_reverse = False

        for _ in range(500):

            pairings = cog._generate_pairings(
                participants,
                blocked_pairings=blocked
            )

            assert (1, 2) not in pairings

            if (2, 1) in pairings:
                found_reverse = True
                break

        assert found_reverse

    def test_multiple_blocked_pairings(self):
        """
        Multiple blocked pairings should all be respected.
        """

        cog = SecretSanta(None)

        participants = [1, 2, 3, 4, 5]

        blocked = [
            [1, 2],
            [2, 3],
            [3, 4],
        ]

        for _ in range(200):

            pairings = cog._generate_pairings(
                participants,
                blocked_pairings=blocked
            )

            assert pairings is not None

            for restriction in blocked:
                assert tuple(restriction) not in pairings

    def test_family_group_prevents_pairing(self):
        """
        Members of the same family group should never
        draw each other.
        """

        cog = SecretSanta(None)

        participants = [1, 2, 3, 4]

        family_groups = [
            [1, 2]
        ]

        for _ in range(200):

            pairings = cog._generate_pairings(
                participants,
                family_groups=family_groups
            )

            assert pairings is not None

            assert (1, 2) not in pairings
            assert (2, 1) not in pairings

    def test_large_family_group_prevents_all_internal_matches(self):
        """
        No member should draw another member
        from the same family group.
        """

        cog = SecretSanta(None)

        participants = [1, 2, 3, 4, 5, 6]

        family_groups = [
            [1, 2, 3]
        ]

        family = {1, 2, 3}

        for _ in range(200):

            pairings = cog._generate_pairings(
                participants,
                family_groups=family_groups
            )

            assert pairings is not None

            for giver, receiver in pairings:

                if giver in family:
                    assert receiver not in family

    def test_family_and_blocked_pairings_together(self):
        """
        Family restrictions and directional blocks
        should both be enforced simultaneously.
        """

        cog = SecretSanta(None)

        participants = [1, 2, 3, 4, 5]

        blocked = [
            [4, 5]
        ]

        family_groups = [
            [1, 2]
        ]

        for _ in range(200):

            pairings = cog._generate_pairings(
                participants,
                blocked_pairings=blocked,
                family_groups=family_groups
            )

            assert pairings is not None

            assert (4, 5) not in pairings
            assert (1, 2) not in pairings
            assert (2, 1) not in pairings

    def test_impossible_two_person_family_group(self):
        """
        Two participants in one family group
        cannot be matched.
        """

        cog = SecretSanta(None)

        participants = [1, 2]

        family_groups = [
            [1, 2]
        ]

        pairings = cog._generate_pairings(
            participants,
            family_groups=family_groups
        )

        assert pairings is None

    def test_impossible_blocked_pairings(self):
        """
        If restrictions make all pairings impossible,
        None should be returned.
        """

        cog = SecretSanta(None)

        participants = [1, 2]

        blocked = [
            [1, 2],
            [2, 1]
        ]

        pairings = cog._generate_pairings(
            participants,
            blocked_pairings=blocked
        )

        assert pairings is None