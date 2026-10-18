#!/usr/bin/env python3
"""Numerical diagnostics for a_{n+1} = a_n + 1/a_n, a_1 > 0.

The mathematical proof is analytic:

1. a_{n+1} > a_n > 0, so the sequence is positive and strictly increasing.
2. If it were bounded above, the monotone bounded principle would give
   a_n -> L >= a_1 > 0. Passing to the limit in the recurrence gives
   L = L + 1/L, a contradiction. Hence a_n -> +infinity.
3. Set b_n = a_n^2 / 2. Then
       b_{n+1} - b_n = 1 + 1/(2 a_n^2) -> 1.
   Since b_n is strictly increasing and unbounded, Stolz's theorem gives
       b_n / n -> 1.
4. Therefore
       a_n / sqrt(2n) = sqrt(b_n / n) -> 1.

This script does not replace that proof. It checks the numerical behaviour
of the three objects that appear in the proof:

    a_n,  b_n / n,  a_n / sqrt(2n),

and verifies positivity, monotonicity, and the limiting normalized ratios.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from typing import Iterable


@dataclass(frozen=True)
class Sample:
    n: int
    a_n: float
    b_n_over_n: float
    normalized: float
    normalized_error: float


def build_sequence(a1: float, count: int) -> list[float]:
    """Return a_1, ..., a_count."""
    if not math.isfinite(a1) or a1 <= 0:
        raise ValueError("a1 must be finite and strictly positive")
    if count < 1:
        raise ValueError("count must be at least 1")

    values = [a1]
    for _ in range(1, count):
        a_n = values[-1]
        a_next = a_n + 1.0 / a_n
        if not math.isfinite(a_next):
            raise ArithmeticError("the sequence exceeded floating-point range")
        values.append(a_next)
    return values


def check_proof_invariants(values: Iterable[float]) -> dict[str, object]:
    """Check the algebraic and limiting quantities used in the proof."""
    sequence = list(values)
    if len(sequence) < 2:
        raise ValueError("at least two terms are required")

    positive = all(value > 0 for value in sequence)
    increasing = all(
        sequence[index + 1] > sequence[index]
        for index in range(len(sequence) - 1)
    )

    # b_n = a_n^2 / 2.  Stolz is applied to b_n / n.
    normalized_differences = [
        (sequence[index + 1] ** 2 - sequence[index] ** 2) / 2.0
        for index in range(len(sequence) - 1)
    ]

    samples: list[Sample] = []
    for index, a_n in enumerate(sequence, start=1):
        b_n_over_n = (a_n**2 / 2.0) / index
        normalized = a_n / math.sqrt(2.0 * index)
        samples.append(
            Sample(
                n=index,
                a_n=a_n,
                b_n_over_n=b_n_over_n,
                normalized=normalized,
                normalized_error=abs(normalized - 1.0),
            )
        )

    return {
        "positive": positive,
        "strictly_increasing": increasing,
        "last_normalized_difference": normalized_differences[-1],
        "last_b_n_over_n": samples[-1].b_n_over_n,
        "last_normalized_value": samples[-1].normalized,
        "last_absolute_error": samples[-1].normalized_error,
        "samples": samples,
    }


def print_table(samples: list[Sample], tail: int) -> None:
    tail = max(1, min(tail, len(samples)))
    print(
        f"{'n':>6}  {'a_n':>18}  {'b_n/n':>14}  "
        f"{'a_n/sqrt(2n)':>16}  {'error':>10}"
    )
    print("-" * 76)
    for sample in samples[-tail:]:
        print(
            f"{sample.n:6d}  {sample.a_n:18.10f}  "
            f"{sample.b_n_over_n:14.10f}  "
            f"{sample.normalized:16.10f}  "
            f"{sample.normalized_error:10.3e}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Numerically verify the normalized asymptotics of a nonlinear recurrence."
    )
    parser.add_argument(
        "--a1",
        type=float,
        default=1.0,
        help="positive initial term (default: 1.0)",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=30,
        help="number of terms to compute (default: 30)",
    )
    parser.add_argument(
        "--tail",
        type=int,
        default=8,
        help="number of final rows to print (default: 8)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit a machine-readable summary instead of the table",
    )
    args = parser.parse_args()

    values = build_sequence(args.a1, args.n)
    report = check_proof_invariants(values)
    samples: list[Sample] = report.pop("samples")  # type: ignore[assignment]

    if args.json:
        payload = {
            **report,
            "a1": args.a1,
            "terms": args.n,
            "samples": [asdict(sample) for sample in samples[-args.tail :]],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    print(f"a_1 = {args.a1:g}, computed terms = {len(values)}")
    print(f"all terms positive: {report['positive']}")
    print(f"strictly increasing: {report['strictly_increasing']}")
    print(
        "last normalized difference "
        f"b_(n+1)-b_n = {report['last_normalized_difference']:.12f}"
    )
    print()
    print_table(samples, args.tail)
    print()
    print(f"estimated limit of a_n/sqrt(2n): {report['last_normalized_value']:.12f}")
    print(f"absolute error: {report['last_absolute_error']:.3e}")


if __name__ == "__main__":
    main()
