import json
import re
import sys
from pathlib import Path

import yaml
from pypdf import PdfReader

from llama_index.core import Document, Settings, VectorStoreIndex
from llama_index.core.node_parser import TokenTextSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K = 3
PREVIEW_LENGTH = 400
CORPUS_PATH = Path("corpus/hw03")
QUESTIONS_PATH = Path("reports/hw04/questions.yaml")
RAW_PATH = Path("reports/hw04/raw")


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
            Document(
                text=text,
                metadata={"source": path.name, "file_name": path.name},
            )
        )
    return documents


def build_nodes(documents):
    splitter = TokenTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    nodes = splitter.get_nodes_from_documents(documents)
    counts = {}
    for node in nodes:
        source = node.metadata.get("source") or node.metadata.get("file_name")
        counts[source] = counts.get(source, 0) + 1
        chunk_id = source + "::chunk_" + str(counts[source])
        node.metadata["source"] = source
        node.metadata["chunk_id"] = chunk_id
    return nodes


def load_questions():
    return yaml.safe_load(QUESTIONS_PATH.read_text())


def preview_text(text):
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= PREVIEW_LENGTH:
        return compact
    return compact[:PREVIEW_LENGTH]


def retrieve_question(index, question):
    nodes = index.as_retriever(similarity_top_k=TOP_K).retrieve(question["question"])
    hits = []
    for rank, node in enumerate(nodes, start=1):
        chunk_text = node.node.get_content()
        hits.append(
            {
                "rank": rank,
                "source": node.node.metadata.get("source", ""),
                "chunk_id": node.node.metadata.get("chunk_id", ""),
                "score": None if node.score is None else float(node.score),
                "text": chunk_text,
            }
        )
    return hits


def retrieval_check(question, hits):
    top_sources = [hit["source"] for hit in hits]
    expected = question.get("expected_sources") or []
    if question["category"] in ("not_in_documents", "unrelated"):
        return {
            "id": question["id"],
            "expected_source_in_top3": False,
            "top_sources": top_sources,
            "notes": "Unsupported question. Vector search still returned the nearest chunks.",
        }
    if question["id"] == "q2":
        missing = [source for source in expected if source not in top_sources]
        found = len(missing) == 0
        if found:
            notes = "Both expected sources are in the top 3."
        else:
            notes = "Missing from top 3: " + ", ".join(missing)
        return {
            "id": question["id"],
            "expected_source_in_top3": found,
            "top_sources": top_sources,
            "notes": notes,
        }
    found_sources = [source for source in expected if source in top_sources]
    if found_sources:
        notes = "Expected source in top 3: " + ", ".join(found_sources)
    else:
        notes = "None of the expected sources appeared in the top 3."
    if question["category"] == "ambiguous":
        notes = notes + " The question is intentionally broad."
    return {
        "id": question["id"],
        "expected_source_in_top3": len(found_sources) > 0,
        "top_sources": top_sources,
        "notes": notes,
    }


def print_report(documents, nodes, dimension, questions, results):
    print("HW4 RAG RETRIEVAL")
    print("Documents:", len(documents))
    print("Chunks:", len(nodes))
    print("Embedding:", MODEL_NAME)
    print("Dimension:", dimension)
    print("Chunk size:", CHUNK_SIZE)
    print("Overlap:", CHUNK_OVERLAP)
    print("Top-k:", TOP_K)
    print()
    for question, hits in zip(questions, results):
        print(question["id"], question["category"])
        print(question["question"])
        for hit in hits:
            print("rank", hit["rank"])
            print("source:", hit["source"])
            print("chunk_id:", hit["chunk_id"])
            print("score:", None if hit["score"] is None else round(hit["score"], 6))
            print(preview_text(hit["text"]))
            print()


def main():
    if len(sys.argv) > 1 and sys.argv[1] != "--retrieve-only":
        raise SystemExit("Only retrieval is implemented. Use: python3.11 rag.py --retrieve-only")
    documents = load_documents()
    nodes = build_nodes(documents)
    embed_model = HuggingFaceEmbedding(model_name=MODEL_NAME)
    dimension = len(embed_model.get_text_embedding("rental housing"))
    Settings.llm = None
    Settings.embed_model = embed_model
    index = VectorStoreIndex(nodes)
    questions = load_questions()
    results = []
    checks = []
    saved_questions = []
    for question in questions:
        hits = retrieve_question(index, question)
        results.append(hits)
        checks.append(retrieval_check(question, hits))
        saved_questions.append(
            {
                "id": question["id"],
                "category": question["category"],
                "question": question["question"],
                "expected_sources": question.get("expected_sources") or [],
                "answerable": question["answerable"],
                "hits": hits,
            }
        )
    RAW_PATH.mkdir(parents=True, exist_ok=True)
    payload = {
        "embedding_model": MODEL_NAME,
        "embedding_dimension": dimension,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "top_k": TOP_K,
        "document_count": len(documents),
        "chunk_count": len(nodes),
        "questions": saved_questions,
    }
    (RAW_PATH / "rag_retrievals.json").write_text(json.dumps(payload, indent=2) + "\n")
    (RAW_PATH / "rag_retrieval_check.json").write_text(json.dumps(checks, indent=2) + "\n")
    print_report(documents, nodes, dimension, questions, results)


if __name__ == "__main__":
    main()
