"""從 UMWP「缺關鍵資訊」配對中篩出 pilot 候選題。

條件：來源為 SVAMP / MultiArith / ASDiv；原題與缺題只差一個數字；
答案能由兩到三個數字的加減或乘除組合得出（用來標記題目需要哪一類運算）。
"""
import itertools, json, re, sys

NUM = re.compile(r"\d+(?:\.\d+)?")


def nums(text):
    return [float(x) for x in NUM.findall(text.replace(",", ""))]


def find_ops(values, answer):
    """回傳能算出答案的運算類型集合：'addsub'、'muldiv' 或 'mixed'。"""
    kinds = set()
    for n in (2, 3):
        for combo in itertools.permutations(values, n):
            for ops in itertools.product("+-*/", repeat=n - 1):
                expr = str(combo[0])
                for op, v in zip(ops, combo[1:]):
                    expr = f"({expr}{op}{v})"
                try:
                    if abs(eval(expr) - answer) < 1e-6:
                        s = set(ops)
                        if s <= {"+", "-"}:
                            kinds.add("addsub")
                        elif s <= {"*", "/"}:
                            kinds.add("muldiv")
                        else:
                            kinds.add("mixed")
                except ZeroDivisionError:
                    pass
    return kinds


def main(path, out):
    rows = [json.loads(l) for l in open(path)]
    by_id = {r["id"]: r for r in rows}
    cands = []
    for r in rows:
        if r["category"] != 1 or r["source"] not in ("SVAMP", "MultiArith", "ASDiv"):
            continue
        orig = by_id[r["relevant_ids"][0]]
        a, b = nums(orig["question"]), nums(r["question"])
        missing = [x for x in a if a.count(x) - b.count(x) > 0]
        if len(a) - len(b) != 1 or len(set(missing)) != 1:
            continue
        kinds = find_ops(a, orig["answer"][0])
        if len(kinds) != 1:  # 運算類型不明確的題目先排除
            continue
        cands.append({
            "umwp_missing_id": r["id"], "umwp_orig_id": orig["id"], "source": r["source"],
            "op_type": kinds.pop(), "n_numbers": len(a),
            "complete_en": orig["question"].strip(), "missing_en": r["question"].strip(),
            "missing_value": missing[0], "answer": orig["answer"][0],
        })
    json.dump(cands, open(out, "w"), ensure_ascii=False, indent=1)
    from collections import Counter
    print(len(cands), Counter((c["op_type"], c["n_numbers"]) for c in cands))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
