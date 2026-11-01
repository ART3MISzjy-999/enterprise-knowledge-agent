"""Small, inspectable BM25 index: Chinese bigrams + curated query synonyms."""
import json
import math
import re
from collections import Counter
from pathlib import Path

SYNONYMS = {
    "年假": ("带薪休假", "带薪假", "休几天", "休假额度"),
    "报销": ("报账", "垫付", "费用申请"),
    "期限": ("多久", "最晚", "截止", "多长时间"),
    "实习生": ("实习同学", "intern"),
    "正式员工": ("全职", "转正员工"),
    "导出": ("输出视频", "渲染视频"),
}
STOP = {"公司", "员工", "我们", "可以", "多少", "什么", "怎么", "是否", "请问", "一下", "需要"}


def tokens(text: str, *, expand: bool = False) -> list[str]:
    text = text.lower()
    if expand:
        text += " " + " ".join(k for k, aliases in SYNONYMS.items()
                               if any(a in text for a in aliases))
    parts = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]+", text)
    out = []
    for part in parts:
        if re.fullmatch(r"[\u4e00-\u9fff]+", part):
            out.extend(part[i:i + 2] for i in range(len(part) - 1))
        else:
            out.append(part)
    return [t for t in out if t not in STOP]


class DocumentStore:
    def __init__(self, documents: list[dict]):
        if not isinstance(documents, list):
            raise ValueError("documents must be a list")
        self.documents = {}
        for doc in documents:
            if not isinstance(doc, dict):
                raise ValueError("document must be an object")
            doc = dict(doc)
            if not isinstance(doc.get("scope"), str) or not doc["scope"].strip():
                doc["scope"] = "未说明"
            for key in ("doc_id", "title", "version_date", "scope", "policy_key", "content"):
                if not isinstance(doc.get(key), str) or not doc[key].strip():
                    raise ValueError(f"Document requires non-empty {key}")
            if doc["doc_id"] in self.documents:
                raise ValueError("Duplicate doc_id")
            self.documents[doc["doc_id"]] = dict(doc)
        self.counts = {i: Counter(tokens(d["title"] + " " + d["scope"] + " " + d["content"]))
                       for i, d in self.documents.items()}
        self.df = Counter(t for counts in self.counts.values() for t in counts)
        self.avg_len = sum(map(lambda c: sum(c.values()), self.counts.values())) / max(1, len(self.counts))

    @classmethod
    def from_path(cls, path: Path):
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def version_peer_ids(self, doc):
        return [i for i, other in self.documents.items() if i != doc["doc_id"]
                and other["policy_key"] == doc["policy_key"]
                and (other["scope"] == doc["scope"] or "全体员工" in (other["scope"], doc["scope"]))]

    def search_documents(self, query: str, top_k: int = 5) -> dict:
        if not isinstance(query, str) or not query.strip() or len(query) > 500:
            raise ValueError("query must be 1..500 characters")
        if type(top_k) is not int or not 1 <= top_k <= 8:
            raise ValueError("top_k must be an integer in 1..8")
        query_tokens = set(tokens(query, expand=True))
        ranked = []
        n = len(self.documents)
        for doc_id, counts in self.counts.items():
            score = 0.0
            length = sum(counts.values())
            for term in query_tokens & counts.keys():
                freq = counts[term]
                idf = math.log(1 + (n - self.df[term] + 0.5) / (self.df[term] + 0.5))
                score += idf * freq * 2.5 / (freq + 1.5 * (0.25 + 0.75 * length / max(1, self.avg_len)))
            if score > 0:
                ranked.append((score, doc_id))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        results = []
        for score, doc_id in ranked[:top_k]:
            doc = self.documents[doc_id]
            results.append({k: v for k, v in doc.items() if k != "content"} | {
                "version_peer_ids": self.version_peer_ids(doc), "score": round(score, 4), "snippet": doc["content"][:100],
                "snippet_is_full": len(doc["content"]) <= 100,
            })
        return {"results": results, "total_hits": len(ranked), "truncated": len(ranked) > top_k}

    def read_document(self, doc_id: str) -> dict:
        if not isinstance(doc_id, str) or doc_id not in self.documents:
            raise ValueError("unknown doc_id")
        return dict(self.documents[doc_id]) | {"version_peer_ids": self.version_peer_ids(self.documents[doc_id])}
