"""IMO 1988 P6: exact integer experiments. Python 3, standard library only.
Run: python3 verify.py --limit 2000
Finite experiments support illustration; the mathematical proof is in solution.md.
"""
import argparse
import json
from math import isqrt
from pathlib import Path


def descend(a, b):
    if a <= 0 or b <= 0:
        raise ValueError("Inputs must be positive integers")
    a, b = max(a, b), min(a, b)
    numerator, denominator = a*a+b*b, a*b+1
    k, remainder = divmod(numerator, denominator)
    if remainder:
        raise ValueError("Divisibility hypothesis fails")
    trace = [[a, b]]
    if k == 1:
        assert (a, b) == (1, 1)
        return k, trace
    while b:
        c = k*b-a
        assert 0 <= c < b
        assert b*b+c*c == k*(b*c+1)
        assert b+c < a+b
        a, b = b, c
        trace.append([a, b])
    assert a*a == k
    return k, trace


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=2000)
    args = parser.parse_args()
    if args.limit < 1:
        parser.error('--limit must be positive')
    n = args.limit
    hits = 0
    values = set()
    max_steps = 0
    for b in range(1, n+1):
        for a in range(b, n+1):
            k, r = divmod(a*a+b*b, a*b+1)
            if r:
                continue
            hits += 1
            assert isqrt(k)**2 == k
            actual_k, trace = descend(a, b)
            assert actual_k == k
            values.add(k)
            max_steps = max(max_steps, len(trace)-1)
    examples = []
    for a, b in [(1, 1), (8, 2), (30, 8), (112, 30), (27, 3), (240, 27)]:
        k, trace = descend(a, b)
        examples.append(dict(a=a, b=b, k=k, trace=trace))
    report = dict(limit=n, candidate_pairs=n*(n+1)//2,
                  valid_unordered_pairs=hits, quotient_values=sorted(values),
                  max_descent_steps=max_steps, examples=examples,
                  conclusion='All finite checks passed; this is not a proof for all integers.')
    target = Path(__file__).with_name('verification_results.json')
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
