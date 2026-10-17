"""核对 IMO 2001 Problem 3 证明中的关键计数关系。

程序展示数值结构；一般性结论仍由题目中的计数论证保证。
"""


def proof_counts(girls: int = 21, boys: int = 21, max_solved: int = 6,
                 sparse_limit: int = 2) -> dict[str, int]:
    """返回总男女搭档数与两类稀少题搭档数上界。"""
    # 若某女生解出的题都至多有 sparse_limit 名男生，
    # max_solved 道题最多覆盖 max_solved*sparse_limit 名男生。
    # 由于每位女生要与所有 boys 名男生都共享题目，至少有一道题
    # 不是“男生稀少题”，所以稀少题至多 max_solved - 1 道。
    sparse_problems_per_person = max_solved - 1
    partners_per_person = sparse_problems_per_person * sparse_limit

    total_pairs = girls * boys
    boy_sparse_pairs_upper = girls * partners_per_person
    girl_sparse_pairs_upper = boys * partners_per_person
    bad_pairs_upper = boy_sparse_pairs_upper + girl_sparse_pairs_upper

    return {
        "total_pairs": total_pairs,
        "boy_sparse_pairs_upper": boy_sparse_pairs_upper,
        "girl_sparse_pairs_upper": girl_sparse_pairs_upper,
        "bad_pairs_upper": bad_pairs_upper,
    }


if __name__ == "__main__":
    counts = proof_counts()
    for label, value in counts.items():
        print(f"{label}: {value}")

    assert counts["total_pairs"] == 441
    assert counts["bad_pairs_upper"] == 420
    assert counts["total_pairs"] > counts["bad_pairs_upper"]
    print("至少存在一对男女搭档避开两类稀少题。")
