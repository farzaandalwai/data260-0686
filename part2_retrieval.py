import json
import random
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from pypdf import PdfReader

from llama_index.core import Document, Settings, VectorStoreIndex
from llama_index.core.node_parser import (
    SemanticSplitterNodeParser,
    SentenceWindowNodeParser,
    TokenTextSplitter,
)
from llama_index.embeddings.huggingface import HuggingFaceEmbedding


SEED = 686
TOP_K = 5
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
CORPUS_PATH = Path("corpus/hw03")
QUESTIONS_PATH = Path("reports/hw03/questions.yaml")
RAW_PATH = Path("reports/hw03/raw")
METRICS_PATH = Path("reports/hw03/METRICS.md")
PREVIEW_LENGTH = 240


def read_pdf(path):
    reader = PdfReader(path)
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages)


def read_html(path):
    raw = path.read_text(errors="replace")
    raw = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", raw).strip()


def load_documents():
    documents = []
    for path in sorted(CORPUS_PATH.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() == ".pdf":
            text = read_pdf(path)
        else:
            text = read_html(path)
        documents.append(
            Document(text=text, metadata={"file_name": path.name})
        )
    return documents


def cosine_similarity(left, right):
    left_vector = np.asarray(left, dtype=float)
    right_vector = np.asarray(right, dtype=float)
    denominator = np.linalg.norm(left_vector) * np.linalg.norm(right_vector)
    if denominator == 0:
        return 0.0
    return float(np.dot(left_vector, right_vector) / denominator)


def preview_text(text):
    compact = re.sub(r"\s+", " ", text).strip()
    return compact[:PREVIEW_LENGTH]


def build_parser(name, embed_model):
    if name == "token":
        return TokenTextSplitter(chunk_size=256, chunk_overlap=32)
    if name == "semantic":
        return SemanticSplitterNodeParser.from_defaults(
            embed_model=embed_model,
            buffer_size=1,
            breakpoint_percentile_threshold=95,
        )
    if name == "sentence_window":
        return SentenceWindowNodeParser.from_defaults(window_size=3)
    raise ValueError(name)


def retrieve_question(index, embed_model, question):
    query_vector = embed_model.get_query_embedding(question["question"])
    started = time.perf_counter()
    nodes = index.as_retriever(similarity_top_k=TOP_K).retrieve(question["question"])
    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    hits = []
    for rank, node in enumerate(nodes, start=1):
        chunk_text = node.node.get_content()
        chunk_vector = embed_model.get_text_embedding(chunk_text)
        hits.append(
            {
                "rank": rank,
                "source": node.node.metadata.get("file_name", ""),
                "store_score": None if node.score is None else round(float(node.score), 6),
                "cosine_similarity": round(cosine_similarity(query_vector, chunk_vector), 6),
                "chunk_length": len(chunk_text),
                "text_preview": preview_text(chunk_text),
                "chunk_vector_shape": [len(chunk_vector)],
            }
        )
    expected_source = question["expected_source"]
    return {
        "id": question["id"],
        "question": question["question"],
        "expected_source": expected_source,
        "query_embedding_dimension": len(query_vector),
        "query_embedding_first_8": [round(value, 6) for value in query_vector[:8]],
        "query_vector_shape": [len(query_vector)],
        "latency_ms": latency_ms,
        "recall_hit": any(hit["source"] == expected_source for hit in hits),
        "hits": hits,
    }


def recall_at_k(results):
    if not results:
        return 0.0
    hits = sum(1 for result in results if result["recall_hit"])
    return round(hits / len(results), 4)


def mean_latency(results):
    if not results:
        return 0.0
    return round(sum(result["latency_ms"] for result in results) / len(results), 2)


def wrong_retrieval(chunker_results):
    best = None
    for chunker_name, results in chunker_results.items():
        for result in results:
            for hit in result["hits"]:
                if hit["source"] == result["expected_source"]:
                    continue
                candidate = {
                    "chunker": chunker_name,
                    "question_id": result["id"],
                    "expected_source": result["expected_source"],
                    "retrieved_source": hit["source"],
                    "rank": hit["rank"],
                    "store_score": hit["store_score"],
                    "cosine_similarity": hit["cosine_similarity"],
                    "text_preview": hit["text_preview"],
                }
                if best is None or (hit["store_score"] or 0) > (best["store_score"] or 0):
                    best = candidate
    return best


def write_metrics(chunker_results, node_counts, wrong_example):
    lines = [
        "# HW3 Metrics",
        "",
        f"Embedding model: {MODEL_NAME}",
        f"Top-k: {TOP_K}",
        f"Seed: {SEED}",
        "",
        "## Retrieval Comparison",
        "",
        "| Chunker | Nodes | Recall@5 | Mean latency (ms) |",
        "|---|---:|---:|---:|",
    ]
    for name in chunker_results:
        lines.append(
            f"| {name} | {node_counts[name]} | {recall_at_k(chunker_results[name])} | {mean_latency(chunker_results[name])} |"
        )
    lines.extend(
        [
            "",
            "Recall@5 is the share of the five questions whose expected source file appears in the top 5 retrieved chunks.",
            "",
            "## Confidently Scored Wrong Retrieval",
            "",
        ]
    )
    if wrong_example is None:
        lines.append("No retrieved chunk came from a different source than expected.")
    else:
        lines.extend(
            [
                f"- Chunker: {wrong_example['chunker']}",
                f"- Question: {wrong_example['question_id']}",
                f"- Expected source: {wrong_example['expected_source']}",
                f"- Retrieved source: {wrong_example['retrieved_source']}",
                f"- Rank: {wrong_example['rank']}",
                f"- Store score: {wrong_example['store_score']}",
                f"- Cosine similarity: {wrong_example['cosine_similarity']}",
                f"- Preview: {wrong_example['text_preview']}",
            ]
        )
    lines.append("")
    METRICS_PATH.write_text("\n".join(lines))


def save_outputs(chunker_results, node_counts):
    RAW_PATH.mkdir(parents=True, exist_ok=True)
    payload = {
        "seed": SEED,
        "model": MODEL_NAME,
        "top_k": TOP_K,
        "node_counts": node_counts,
        "chunkers": chunker_results,
    }
    json_path = RAW_PATH / "retrieval_runs.json"
    json_path.write_text(json.dumps(payload, indent=2))

    rows = []
    for chunker_name, results in chunker_results.items():
        for result in results:
            for hit in result["hits"]:
                rows.append(
                    {
                        "chunker": chunker_name,
                        "question_id": result["id"],
                        "expected_source": result["expected_source"],
                        "rank": hit["rank"],
                        "source": hit["source"],
                        "store_score": hit["store_score"],
                        "cosine_similarity": hit["cosine_similarity"],
                        "chunk_length": hit["chunk_length"],
                        "latency_ms": result["latency_ms"],
                        "query_embedding_dimension": result["query_embedding_dimension"],
                        "query_embedding_first_8": json.dumps(result["query_embedding_first_8"]),
                        "query_vector_shape": json.dumps(result["query_vector_shape"]),
                        "chunk_vector_shape": json.dumps(hit["chunk_vector_shape"]),
                        "text_preview": hit["text_preview"],
                    }
                )
    pd.DataFrame(rows).to_csv(RAW_PATH / "retrieval_runs.csv", index=False)
    return json_path


def main():
    random.seed(SEED)
    np.random.seed(SEED)
    questions = yaml.safe_load(QUESTIONS_PATH.read_text())
    documents = load_documents()
    embed_model = HuggingFaceEmbedding(model_name=MODEL_NAME)
    Settings.embed_model = embed_model
    Settings.llm = None

    chunker_results = {}
    node_counts = {}
    for name in ["token", "semantic", "sentence_window"]:
        print(f"Building {name} index")
        parser = build_parser(name, embed_model)
        nodes = parser.get_nodes_from_documents(documents)
        node_counts[name] = len(nodes)
        index = VectorStoreIndex(nodes)
        results = []
        for question in questions:
            print(f"Retrieving {name} {question['id']}")
            results.append(retrieve_question(index, embed_model, question))
        chunker_results[name] = results
        print(name, "nodes", node_counts[name], "recall", recall_at_k(results))

    wrong_example = wrong_retrieval(chunker_results)
    save_outputs(chunker_results, node_counts)
    write_metrics(chunker_results, node_counts, wrong_example)
    print("Wrote reports/hw03/raw/retrieval_runs.json")
    print("Wrote reports/hw03/raw/retrieval_runs.csv")
    print("Wrote reports/hw03/METRICS.md")


if __name__ == "__main__":
    main()
