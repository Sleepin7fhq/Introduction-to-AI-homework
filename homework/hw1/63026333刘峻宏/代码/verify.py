#!/usr/bin/env python3
"""Backtracking verification for the 4-term index-partition problem.

Only the Python standard library is used.  All printed text is ASCII.
"""

import sys
from functools import lru_cache

sys.setrecursionlimit(10000)


def make_solver(m):
    """Return solve(i, j) -> tuple of groups, or None if impossible.

    A group is a tuple of four 1-based indices in increasing order.
    The search uses these facts:
      1. The smallest still-uncovered index x must be the first term of
         its group, because every smaller index is already deleted/covered.
      2. A 4-term AP starting at x has the form x, x+d, x+2d, x+3d.
      3. Failed bitmasks are memoized.
    """
    n = 4 * m + 2
    full = (1 << n) - 1  # bits 0..n-1 represent indices 1..n

    @lru_cache(maxsize=None)
    def search(mask):
        if mask == 0:
            return ()

        low = mask & -mask
        x = low.bit_length() - 1  # 0-based smallest available index
        max_d = (n - 1 - x) // 3

        # Larger steps first: for m=3, (2,13), this finds the proof's
        # three step-3 groups.
        for d in range(max_d, 0, -1):
            bits = low
            ok = True
            for t in (1, 2, 3):
                y = x + t * d
                bit = 1 << y
                if not (mask & bit):
                    ok = False
                    break
                bits |= bit
            if not ok:
                continue

            rest = search(mask ^ bits)
            if rest is not None:
                group = (x + 1, x + d + 1, x + 2 * d + 1, x + 3 * d + 1)
                return (group,) + rest

        return None

    def solve(i, j):
        removed = (1 << (i - 1)) | (1 << (j - 1))
        return search(full & ~removed)

    return solve


def is_valid_partition(m, i, j, groups):
    """Independent check of a returned partition."""
    n = 4 * m + 2
    if groups is None or len(groups) != m:
        return False

    seen = set()
    for group in groups:
        if len(group) != 4:
            return False
        if not all(1 <= x <= n for x in group):
            return False
        if not (group[0] < group[1] < group[2] < group[3]):
            return False
        if not (group[1] - group[0] == group[2] - group[1]
                == group[3] - group[2]):
            return False
        for x in group:
            if x in seen:
                return False
            seen.add(x)

    expected = set(range(1, n + 1)) - {i, j}
    return seen == expected


def valid_pairs(m):
    n = 4 * m + 2
    solve = make_solver(m)
    result = []
    for i in range(1, n):
        for j in range(i + 1, n + 1):
            groups = solve(i, j)
            if groups is not None:
                assert is_valid_partition(m, i, j, groups)
                result.append((i, j))
    return result


def main():
    print("Backtracking verification: 4-term AP index partitions")
    print("")

    print("Part (a): enumeration for m = 1..5")
    print("The family-A lower bound is (m+1)(m+2)/2.")
    print("The two-family bound is m^2+m+1 (used in solution.md).")
    print("")

    all_pairs = {}
    for m in range(1, 6):
        n = 4 * m + 2
        pairs = valid_pairs(m)
        all_pairs[m] = pairs

        total = n * (n - 1) // 2
        family_a_bound = (m + 1) * (m + 2) // 2
        two_family_bound = m * m + m + 1
        ratio = len(pairs) / total

        assert len(pairs) >= family_a_bound
        assert len(pairs) >= two_family_bound

        print(
            "m={m:1d} n={n:2d} valid={v:3d} total={t:3d} "
            "ratio={r:.6f} familyA_bound={a:2d} "
            "familyA_ok={ao} two_family_bound={b:2d} "
            "two_family_ok={bo}".format(
                m=m,
                n=n,
                v=len(pairs),
                t=total,
                r=ratio,
                a=family_a_bound,
                ao="YES" if len(pairs) >= family_a_bound else "NO",
                b=two_family_bound,
                bo="YES" if len(pairs) >= two_family_bound else "NO",
            )
        )

    print("")

    print("Part (b): all valid pairs for m = 1")
    print("valid_pairs =", all_pairs[1])
    expected_m1 = [(1, 2), (1, 6), (5, 6)]
    print("expected_from_part_1 =", expected_m1)
    print("match =", all_pairs[1] == expected_m1)
    assert all_pairs[1] == expected_m1

    print("")

    print("Part (c): m = 3 and (i, j) = (2, 13)")
    solve3 = make_solver(3)
    groups = solve3(2, 13)
    print("partitionable =", groups is not None)
    if groups is not None:
        for k, group in enumerate(groups, 1):
            print("  group {k}: {g}".format(k=k, g=group))
        print("independent_check =", is_valid_partition(3, 2, 13, groups))

        expected_groups = [
            (1, 4, 7, 10),
            (3, 6, 9, 12),
            (5, 8, 11, 14),
        ]
        same = sorted(groups) == sorted(expected_groups)
        print("matches_part_2_construction =", same)

    print("")
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
