import json
from pathlib import Path

import yaml


RAW_PATH = Path("reports/hw03/raw/retrieval_runs.json")
CHUNK_STATS_PATH = Path("reports/hw03/raw/chunk_stats.json")
QUESTIONS_PATH = Path("reports/hw03/questions.yaml")
METRICS_PATH = Path("reports/hw03/METRICS.md")
TECHNIQUE_ORDER = ["token", "semantic", "sentence_window"]
TECHNIQUE_NAMES = {
    "token": "TokenTextSplitter",
    "semantic": "SemanticSplitterNodeParser",
    "sentence_window": "SentenceWindowNodeParser",
}


def mean(values):
    return sum(values) / len(values)


def load_inputs():
    data = json.loads(RAW_PATH.read_text())
    chunk_stats = json.loads(CHUNK_STATS_PATH.read_text())
    questions = yaml.safe_load(QUESTIONS_PATH.read_text())
    answers = {item["id"]: item["expected_answer"] for item in questions}
    return data, answers, chunk_stats


def technique_rows(data, chunk_stats):
    rows = []
    for key in TECHNIQUE_ORDER:
        results = data["chunkers"][key]
        technique = TECHNIQUE_NAMES[key]
        top1 = [
            next(hit["cosine_similarity"] for hit in result["hits"] if hit["rank"] == 1)
            for result in results
        ]
        cosines = [hit["cosine_similarity"] for result in results for hit in result["hits"]]
        recall_hits = sum(1 for result in results if result["recall_hit"])
        rows.append(
            {
                "technique": technique,
                "chunks": chunk_stats[technique]["chunks"],
                "avg_chunk_length": chunk_stats[technique]["avg_chunk_length"],
                "top1_cosine": mean(top1),
                "mean5_cosine": mean(cosines),
                "recall": recall_hits / len(results),
                "latency_ms": mean([result["latency_ms"] for result in results]),
            }
        )
    return rows


def wrong_retrieval(data):
    best = None
    for key in TECHNIQUE_ORDER:
        for result in data["chunkers"][key]:
            for hit in result["hits"]:
                if hit["source"] == result["expected_source"]:
                    continue
                candidate = {
                    "technique": TECHNIQUE_NAMES[key],
                    "question_id": result["id"],
                    "expected_source": result["expected_source"],
                    "retrieved_source": hit["source"],
                    "rank": hit["rank"],
                    "store_score": hit["store_score"],
                    "cosine_similarity": hit["cosine_similarity"],
                    "text_preview": hit["text_preview"],
                }
                if best is None or hit["store_score"] > best["store_score"]:
                    best = candidate
    return best


def write_metrics(data, rows, wrong_example):
    lines = [
        "# HW3 Metrics",
        "",
        f"Embedding model: {data['model']}",
        f"Top-k: {data['top_k']}",
        f"Seed: {data['seed']}",
        "",
        "## Retrieval Comparison",
        "",
        "| Technique | Chunks | Avg chunk length | Top-1 cosine | Mean@5 cosine | Recall@5 | Mean retrieval latency (ms) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {technique} | {chunks} | {avg_chunk_length:.2f} | {top1_cosine:.6f} | {mean5_cosine:.6f} | {recall:.1f} | {latency_ms:.2f} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "Avg chunk length is the mean character length of every chunk produced by that chunker.",
            "Top-1 cosine is the mean rank-1 cosine similarity across the five questions.",
            "Mean@5 cosine is the mean cosine similarity of all retrieved top-5 chunks.",
            "Recall@5 is the share of the five questions whose expected source file appears in the top 5 retrieved chunks.",
            "",
            "## Confidently Scored Wrong Retrieval",
            "",
            f"- Technique: {wrong_example['technique']}",
            f"- Question: {wrong_example['question_id']}",
            f"- Expected source: {wrong_example['expected_source']}",
            f"- Retrieved source: {wrong_example['retrieved_source']}",
            f"- Rank: {wrong_example['rank']}",
            f"- Store score: {wrong_example['store_score']}",
            f"- Cosine similarity: {wrong_example['cosine_similarity']}",
            f"- Preview: {wrong_example['text_preview']}",
            "",
        ]
    )
    METRICS_PATH.write_text("\n".join(lines))


def print_comparison(rows):
    print("Technique | Chunks | Avg chunk length | Top-1 cosine | Mean@5 cosine | Recall@5 | Mean retrieval latency (ms)")
    for row in rows:
        print(
            "{technique} | {chunks} | {avg_chunk_length:.2f} | {top1_cosine:.6f} | {mean5_cosine:.6f} | {recall:.1f} | {latency_ms:.2f}".format(
                **row
            )
        )


def print_per_question(data):
    print("Question ID | Technique | Top-ranked source | Top-1 cosine | Expected source | Expected source found in top 5")
    for key in TECHNIQUE_ORDER:
        for result in data["chunkers"][key]:
            top = next(hit for hit in result["hits"] if hit["rank"] == 1)
            found = "YES" if result["recall_hit"] else "NO"
            print(
                f"{result['id']} | {TECHNIQUE_NAMES[key]} | {top['source']} | {top['cosine_similarity']:.6f} | {result['expected_source']} | {found}"
            )


def print_screenshot_block(data, answers, key):
    result = next(item for item in data["chunkers"][key] if item["id"] == "q3")
    document_shape = [len(result["hits"]), result["hits"][0]["chunk_vector_shape"][0]]
    print(f"SCREENSHOT {TECHNIQUE_NAMES[key]} q3")
    print(f"Technique: {TECHNIQUE_NAMES[key]}")
    print(f"Question: {result['question']}")
    print(f"Expected answer: {answers[result['id']]}")
    print(f"Expected source: {result['expected_source']}")
    print(f"Embedding model: {data['model']}")
    print(f"Query embedding dimension: {result['query_embedding_dimension']}")
    print(f"First 8 embedding values: {result['query_embedding_first_8']}")
    print(f"Query vector shape: {result['query_vector_shape']}")
    print(f"Document matrix shape: {document_shape}")
    print(f"Top-k: {data['top_k']}")
    print(f"Retrieval latency ms: {result['latency_ms']}")
    print("rank | store_score | cosine_similarity | chunk_length | source | preview")
    for hit in result["hits"]:
        print(
            f"{hit['rank']} | {hit['store_score']} | {hit['cosine_similarity']} | {hit['chunk_length']} | {hit['source']} | {hit['text_preview']}"
        )


def main():
    data, answers, chunk_stats = load_inputs()
    rows = technique_rows(data, chunk_stats)
    wrong_example = wrong_retrieval(data)
    write_metrics(data, rows, wrong_example)
    print_comparison(rows)
    print()
    print_per_question(data)
    print()
    for key in TECHNIQUE_ORDER:
        print_screenshot_block(data, answers, key)
        print()
    print(f"Wrote {METRICS_PATH}")


if __name__ == "__main__":
    main()
