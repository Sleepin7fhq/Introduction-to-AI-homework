# -*- coding: utf-8 -*-
"""Compute all metrics for the 2nd assignment (confusion matrix, 4-class speech wakeup task)."""
import numpy as np

CLASSES = ["silence", "unknown", "wakeup", "sleep"]
CM = np.array([
    [39,   0,   0,   0],
    [ 1, 276,   3,   7],
    [ 0,  17, 221,   0],
    [ 0,  29,   7, 195],
], dtype=float)

total = CM.sum()
diag = np.diag(CM)
print("=" * 78)
print("CONFUSION MATRIX  (rows = true label, cols = predicted label)")
print("=" * 78)
hdr = "true\\pred".ljust(10) + "".join(c.rjust(8) for c in CLASSES) + "row(sum)".rjust(10)
print(hdr)
for i, c in enumerate(CLASSES):
    print(c.ljust(10) + "".join(f"{int(v):8d}" for v in CM[i]) + f"{int(CM[i].sum()):10d}")
print("col(sum)".ljust(10) + "".join(f"{int(CM[:, j].sum()):8d}" for j in range(4)) + f"{int(total):10d}")

print("\n" + "=" * 78)
print("PER-CLASS METRICS")
print("=" * 78)
TP = diag
FN = CM.sum(axis=1) - diag          # row sum - TP
FP = CM.sum(axis=0) - diag          # col sum - TP
TN = total - TP - FN - FP
support = CM.sum(axis=1)

P = TP / (TP + FP)
R = TP / (TP + FN)
F1 = 2 * P * R / (P + R)
ACC_i = (TP + TN) / total           # one-vs-rest accuracy
FPR = FP / (FP + TN)
TPR = R

print(f"{'class':<10}{'TP':>5}{'FN':>5}{'FP':>5}{'TN':>6}{'support':>9}"
      f"{'P':>9}{'R':>9}{'F1':>9}{'Acc':>9}{'FPR':>9}{'TPR':>9}")
for i, c in enumerate(CLASSES):
    print(f"{c:<10}{int(TP[i]):5d}{int(FN[i]):5d}{int(FP[i]):5d}{int(TN[i]):6d}{int(support[i]):9d}"
          f"{P[i]:9.4f}{R[i]:9.4f}{F1[i]:9.4f}{ACC_i[i]:9.4f}{FPR[i]:9.4f}{TPR[i]:9.4f}")

accuracy = diag.sum() / total
macro = (P.mean(), R.mean(), F1.mean())
weighted = ((P * support).sum() / total, (R * support).sum() / total, (F1 * support).sum() / total)
micro_P = diag.sum() / CM.sum()
micro_R = diag.sum() / CM.sum()
micro_F1 = 2 * micro_P * micro_R / (micro_P + micro_R)

print("\n" + "=" * 78)
print("OVERALL / AGGREGATE")
print("=" * 78)
print(f"correct (trace)          = {int(diag.sum())}")
print(f"total samples            = {int(total)}")
print(f"Accuracy (overall)       = {diag.sum()}/{total} = {accuracy:.6f}  ({accuracy*100:.2f}%)")
print(f"Error rate               = 1 - Acc = {1-accuracy:.4f}")
print(f"Macro    P/R/F1          = {macro[0]:.4f} / {macro[1]:.4f} / {macro[2]:.4f}")
print(f"Weighted P/R/F1 (support)= {weighted[0]:.4f} / {weighted[1]:.4f} / {weighted[2]:.4f}")
print(f"Micro    P/R/F1          = {micro_P:.4f} / {micro_R:.4f} / {micro_F1:.4f}")

print("\n" + "=" * 78)
print("BINARY / GROUPED VIEW (wake word vs. non-wake word)")
print("=" * 78)
# wakeup vs rest
for pos in ["wakeup", "sleep"]:
    k = CLASSES.index(pos)
    neg = [i for i in range(4) if i != k]
    TP2 = CM[k, k]
    FN2 = CM[k, neg].sum()
    FP2 = CM[neg, k].sum()
    TN2 = CM[np.ix_(neg, neg)].sum()
    P2 = TP2 / (TP2 + FP2)
    R2 = TP2 / (TP2 + FN2)
    F1_2 = 2 * P2 * R2 / (P2 + R2)
    FPR2 = FP2 / (FP2 + TN2)
    TPR2 = R2
    print(f"\n[{pos.upper()} vs REST]  TP={int(TP2)} FN={int(FN2)} FP={int(FP2)} TN={int(TN2)}")
    print(f"  Precision(查准率)= {TP2:.0f}/({TP2:.0f}+{FP2:.0f}) = {P2:.4f}")
    print(f"  Recall(查全率)   = {TP2:.0f}/({TP2:.0f}+{FN2:.0f}) = {R2:.4f}")
    print(f"  F1               = {F1_2:.4f}")
    print(f"  FPR(FPA)         = {FP2:.0f}/({FP2:.0f}+{TN2:.0f}) = {FPR2:.4f}")
    print(f"  TPR              = {TPR2:.4f}")
    print(f"  Accuracy(ovr)    = ({TP2:.0f}+{TN2:.0f})/{total:.0f} = {(TP2+TN2)/total:.4f}")

# silence+unknown merged as "noise/non-wake" vs wakeup+sleep
print("\n--- Merged 2-class: {silence,unknown} vs {wakeup,sleep} ---")
A = CM[0:2, 0:2].sum()      # true noise, pred noise
B = CM[0:2, 2:4].sum()      # true noise, pred wake
C = CM[2:4, 0:2].sum()      # true wake, pred noise
D = CM[2:4, 2:4].sum()      # true wake, pred wake
print(f"  [[{A:.0f}, {B:.0f}], [{C:.0f}, {D:.0f}]]  (rows=true)")
print(f"  Accuracy = {A+D:.0f}/{total:.0f} = {(A+D)/total:.4f}")

# verification checks
print("\n" + "=" * 78)
print("SANITY CHECKS")
print("=" * 78)
assert CM.sum() == 795, CM.sum()
assert diag.sum() == 731, diag.sum()
assert CM.sum(axis=1).sum() == CM.sum(axis=0).sum() == total
for i in range(4):
    assert TP[i] + FN[i] == support[i]
    assert TP[i] + FP[i] == CM[:, i].sum()
for i in range(4):
    assert TN[i] == total - support[i] - FP[i]
print("per-class consistency OK; F1 recomputed from P,R OK")
print("row sums:", CM.sum(axis=1), "-> total", CM.sum(axis=1).sum())
print("col sums:", CM.sum(axis=0), "-> total", CM.sum(axis=0).sum())
print("all assertions passed")
