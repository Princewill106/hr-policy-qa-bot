"""HR Policy Q&A Bot (TF-IDF retrieval + optional grounded LLM answers)."""
import argparse
import math
import re
from collections import Counter
from pathlib import Path

import llm

STOP = set("a an the of to and or in on for is are do does i my me we our can how what when who "
           "with be at by it this that if as from you your get much many".split())
THRESHOLD = 0.25


def tokens(text):
    return [t[:-1] if t.endswith("s") and len(t) > 3 else t
            for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOP]


def load_sections(path):
    parts = re.split(r"^##\s+", Path(path).read_text(encoding="utf-8"), flags=re.M)[1:]
    return [{"title": p.splitlines()[0].strip(), "text": " ".join(p.splitlines()[1:]).strip()}
            for p in parts]


class Index:
    def __init__(self, docs):
        self.docs = docs
        self.tfs = [Counter(tokens(d["title"] + " " + d["text"])) for d in docs]
        df = Counter(t for tf in self.tfs for t in tf)
        n = len(docs)
        self.idf = {t: math.log((n + 1) / (c + 1)) + 1 for t, c in df.items()}
        self.vecs = [self._vec(tf) for tf in self.tfs]

    def _vec(self, tf):
        v = {t: c * self.idf.get(t, 0) for t, c in tf.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1
        return {t: x / norm for t, x in v.items()}

    def search(self, q):
        qv = self._vec(Counter(tokens(q)))
        scores = [sum(qv.get(t, 0) * w for t, w in dv.items()) for dv in self.vecs]
        best = max(range(len(scores)), key=scores.__getitem__)
        return self.docs[best], scores[best]


def answer(index, q):
    doc, score = index.search(q)
    if score < THRESHOLD:
        return {"answer": "I'm not sure the handbook covers that. I've passed your question to HR.",
                "source": None, "confidence": round(score, 2)}
    qt = set(tokens(q))
    sentences = re.split(r"(?<=[.!?])\s+", doc["text"])
    ranked = sorted(sentences, key=lambda s: -len(qt & set(tokens(s))))
    text = " ".join(ranked[:2])
    ai = llm.complete(f"Answer the question using ONLY this policy text. If it doesn't contain the "
                      f"answer, say so.\nPolicy ({doc['title']}): {doc['text']}\nQuestion: {q}")
    return {"answer": (ai or text).strip(), "source": doc["title"], "confidence": round(score, 2)}


DEMO_QUESTIONS = [
    "How many annual leave days do I get?",
    "What is the transport allowance for client visits?",
    "Who approves overtime?",
    "Can I work from home on Fridays?",
    "What's the company's stance on crypto investments?",
]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--handbook", default="handbook.md")
    ap.add_argument("--ask")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    index = Index(load_sections(a.handbook))
    for q in ([a.ask] if a.ask else DEMO_QUESTIONS):
        r = answer(index, q)
        print(f"Q: {q}")
        print(f"A: {r['answer']}")
        print(f"   source: {r['source'] or '-'} (confidence {r['confidence']})\n")


if __name__ == "__main__":
    main()
