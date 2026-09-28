import csv
import json
import re
import sys
import time
from pathlib import Path

import yaml
from pypdf import PdfReader

from llama_index.core import Document, Settings, VectorStoreIndex
from llama_index.core.node_parser import TokenTextSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from src.model_client import MODEL
from src.model_client import complete


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K = 3
CONTEXT_CANDIDATES = 5
CONTEXT_LIMIT = 3
SCORE_THRESHOLD = 0.40
DUPLICATE_JACCARD = 0.55
TEMPERATURE = 0.0
PREVIEW_LENGTH = 400
SUMMARY_LENGTH = 360
REFUSAL = "I cannot answer this question from the provided documents"
FTC_LOSS_SOURCE = "ftc_rental_scams_data_spotlight.html"
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


def retrieve_question(index, question, top_k=TOP_K):
    nodes = index.as_retriever(similarity_top_k=top_k).retrieve(question["question"])
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


def word_set(text):
    compact = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    return set(re.sub(r"\s+", " ", compact).split())


def jaccard(left, right):
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def drop_near_duplicates(hits):
    kept = []
    for hit in hits:
        words = word_set(hit["text"])
        duplicate = False
        for earlier in kept:
            if jaccard(words, word_set(earlier["text"])) >= DUPLICATE_JACCARD:
                duplicate = True
                break
        if not duplicate:
            kept.append(hit)
    return kept


def select_context(hits):
    strong = []
    for hit in hits:
        if hit["score"] >= SCORE_THRESHOLD:
            strong.append(hit)
    unique = drop_near_duplicates(strong)
    selected = []
    used_sources = set()
    for hit in unique:
        if hit["source"] in used_sources:
            continue
        selected.append(hit)
        used_sources.add(hit["source"])
        if len(selected) == CONTEXT_LIMIT:
            break
    if len(selected) < CONTEXT_LIMIT:
        chosen = {hit["chunk_id"] for hit in selected}
        for hit in unique:
            if hit["chunk_id"] in chosen:
                continue
            selected.append(hit)
            chosen.add(hit["chunk_id"])
            if len(selected) == CONTEXT_LIMIT:
                break
    selected.sort(key=lambda hit: hit["score"], reverse=True)
    return selected


def ask_model(messages):
    started = time.perf_counter()
    result = complete(messages, temperature=TEMPERATURE)
    elapsed = (time.perf_counter() - started) * 1000
    return result["message"].strip(), round(elapsed, 3)


def basic_prompt(question, hits):
    parts = ["Question:", question, "", "Context:"]
    for hit in hits:
        parts.append(hit["text"])
        parts.append("")
    parts.append("Answer the question using the context.")
    return "\n".join(parts)


def labeled_context(selected):
    blocks = []
    for number, hit in enumerate(selected, start=1):
        blocks.append("[" + str(number) + "] " + hit["source"] + "\n" + hit["text"])
    context = "\n\n".join(blocks)
    if not context:
        return "No documents were retrieved."
    return context


def context_messages(question, selected):
    system = (
        "You answer only from context supplied in the user message. "
        "Do not use outside knowledge. "
        "Every factual claim in a non-refusal answer must be supported by the provided context. "
        "Include at least one citation such as [1] or [2]. "
        "If a claim cannot be supported by a labeled source, omit it. "
        "Do not invent extra screening factors, legal rules, numbers, or examples. "
        "If the context does not contain the answer, reply with exactly this sentence and no other characters: "
        + REFUSAL
    )
    user = (
        "Use only facts explicitly present in the selected context.\n"
        "Omit any claim that is not supported by a selected chunk.\n"
        "Every factual answer must contain at least one source citation.\n"
        "Citations must use exactly [1], [2], or [3], matching the labeled context.\n"
        "Do not invent extra screening factors, legal rules, numbers, or examples.\n"
        "Prefer a concise answer.\n"
        "Answer only from the provided context.\n"
        "Cite source numbers such as [1] or [2].\n"
        "Do not use outside knowledge.\n"
        "If the evidence is insufficient, output exactly:\n"
        + REFUSAL
        + "\n\nQuestion:\n"
        + question
        + "\n\nContext:\n"
        + labeled_context(selected)
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def repair_messages(question, selected, answer):
    messages = context_messages(question, selected)
    messages.append({"role": "assistant", "content": answer})
    messages.append({
        "role": "user",
        "content": (
            "Rewrite the previous answer using the same labeled context. "
            "Every factual claim in a non-refusal answer must be supported by the provided context. "
            "Include at least one citation such as [1] or [2]. "
            "If a claim cannot be supported by a labeled source, omit it. "
            "Do not invent extra screening factors, legal rules, numbers, or examples. "
            "If the evidence is insufficient, output exactly:\n"
            + REFUSAL
        ),
    })
    return messages


def cited_numbers(answer):
    return [int(number) for number in re.findall(r"\[(\d+)\]", answer)]


def citation_valid(answer, selected_count):
    if answer == REFUSAL:
        return False
    numbers = cited_numbers(answer)
    if not numbers:
        return False
    for number in numbers:
        if number < 1 or number > selected_count or number > 3:
            return False
    return True


def citation_text(answer):
    numbers = re.findall(r"\[\d+\]", answer)
    found = []
    for number in numbers:
        if number not in found:
            found.append(number)
    return " ".join(found)


def print_hits(question_id, hits):
    print(question_id)
    for hit in hits:
        print("rank", hit["rank"])
        print("source:", hit["source"])
        print("chunk_id:", hit["chunk_id"])
        print("score:", round(hit["score"], 6))
        print(hit["text"])
        print()


def short_text(text):
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= SUMMARY_LENGTH:
        return compact
    return compact[:SUMMARY_LENGTH] + "..."


def result_row(question, configuration, answer, latency_ms, hits, citations, extra):
    row = {
        "question_id": question["id"],
        "category": question["category"],
        "configuration": configuration,
        "question": question["question"],
        "answer": answer,
        "retrieved_sources": [hit["source"] for hit in hits],
        "grounded_sources_or_citations": citations,
        "refused": answer == REFUSAL,
        "latency_ms": latency_ms,
    }
    row.update(extra)
    return row


def run_no_rag(question):
    answer, latency_ms = ask_model([{"role": "user", "content": question["question"]}])
    return result_row(question, "no_rag", answer, latency_ms, [], "", {})


def run_basic(index, question, top_k):
    hits = retrieve_question(index, question, top_k)
    print_hits(question["id"], hits)
    answer, latency_ms = ask_model([
        {"role": "user", "content": basic_prompt(question["question"], hits)}
    ])
    return result_row(
        question,
        "basic_rag",
        answer,
        latency_ms,
        hits,
        "",
        {"top_k": top_k, "hits": hits},
    )


def run_context(index, question):
    candidates = retrieve_question(index, question, CONTEXT_CANDIDATES)
    selected = select_context(candidates)
    print(question["id"], "context candidates", CONTEXT_CANDIDATES)
    for hit in candidates:
        print("rank", hit["rank"], "source:", hit["source"], "score:", round(hit["score"], 6))
    print(question["id"], "selected context")
    for number, hit in enumerate(selected, start=1):
        print("[" + str(number) + "]", hit["source"], "score:", round(hit["score"], 6), hit["chunk_id"])
    if question["id"] == "q2":
        present = any(hit["source"] == FTC_LOSS_SOURCE for hit in candidates)
        print("q2 FTC scam-loss source in top 5:", present)
    answer, latency_ms = ask_model(context_messages(question["question"], selected))
    return result_row(
        question,
        "context_rag",
        answer,
        latency_ms,
        selected,
        citation_text(answer),
        {
            "candidate_sources": [hit["source"] for hit in candidates],
            "candidate_scores": [hit["score"] for hit in candidates],
            "selected_sources": [hit["source"] for hit in selected],
            "selected": selected,
            "candidates": candidates,
        },
    )


def write_comparison(rows, q2_ftc_in_top5):
    payload = {
        "model": MODEL,
        "temperature": TEMPERATURE,
        "score_threshold": SCORE_THRESHOLD,
        "duplicate_jaccard": DUPLICATE_JACCARD,
        "context_candidates": CONTEXT_CANDIDATES,
        "context_limit": CONTEXT_LIMIT,
        "q2_ftc_loss_source_in_top5": q2_ftc_in_top5,
        "rows": rows,
    }
    (RAW_PATH / "rag_comparison.json").write_text(json.dumps(payload, indent=2) + "\n")
    fieldnames = [
        "question_id",
        "category",
        "configuration",
        "question",
        "answer",
        "retrieved_sources",
        "candidate_sources",
        "selected_sources",
        "grounded_sources_or_citations",
        "refused",
        "latency_ms",
    ]
    with (RAW_PATH / "rag_comparison.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "question_id": row["question_id"],
                "category": row["category"],
                "configuration": row["configuration"],
                "question": row["question"],
                "answer": row["answer"],
                "retrieved_sources": " | ".join(row["retrieved_sources"]),
                "candidate_sources": " | ".join(row.get("candidate_sources") or []),
                "selected_sources": " | ".join(row.get("selected_sources") or row["retrieved_sources"]),
                "grounded_sources_or_citations": row["grounded_sources_or_citations"],
                "refused": row["refused"],
                "latency_ms": row["latency_ms"],
            })


def write_k_sweep(runs):
    payload = {
        "question_id": "q2",
        "configuration": "basic_rag",
        "model": MODEL,
        "temperature": TEMPERATURE,
        "ftc_loss_source": FTC_LOSS_SOURCE,
        "runs": runs,
    }
    (RAW_PATH / "rag_k_sweep.json").write_text(json.dumps(payload, indent=2) + "\n")


def print_comparison(rows, sweep_runs, q2_ftc_in_top5):
    print("HW4 RAG COMPARISON")
    print("Model:", MODEL)
    print("Temperature:", TEMPERATURE)
    print("Score threshold:", SCORE_THRESHOLD)
    print("Duplicate Jaccard:", DUPLICATE_JACCARD)
    print("q2 FTC scam-loss source in top 5:", q2_ftc_in_top5)
    print()
    order = ["no_rag", "basic_rag", "context_rag"]
    labels = {"no_rag": "No RAG", "basic_rag": "Basic RAG", "context_rag": "Context RAG"}
    questions = []
    for row in rows:
        if row["question_id"] not in questions:
            questions.append(row["question_id"])
    for question_id in questions:
        print(question_id.upper())
        for configuration in order:
            for row in rows:
                if row["question_id"] == question_id and row["configuration"] == configuration:
                    print(labels[configuration] + ":", short_text(row["answer"]))
        print()
    print("K SWEEP Q2")
    for run in sweep_runs:
        sources = []
        for hit in run["hits"]:
            sources.append(hit["source"] + " " + str(round(hit["score"], 6)))
        print("k=" + str(run["k"]))
        print("FTC scam-loss source:", run["ftc_source_present"])
        print("sources:", " | ".join(sources))
        print(short_text(run["answer"]))
        print()


def run_compare():
    documents = load_documents()
    nodes = build_nodes(documents)
    embed_model = HuggingFaceEmbedding(model_name=MODEL_NAME)
    Settings.llm = None
    Settings.embed_model = embed_model
    index = VectorStoreIndex(nodes)
    questions = load_questions()
    rows = []
    q2_ftc_in_top5 = False
    for question in questions:
        print("RUN", question["id"], "no_rag")
        rows.append(run_no_rag(question))
        print("RUN", question["id"], "basic_rag")
        rows.append(run_basic(index, question, TOP_K))
        print("RUN", question["id"], "context_rag")
        context_row = run_context(index, question)
        if question["id"] == "q2":
            q2_ftc_in_top5 = FTC_LOSS_SOURCE in context_row["candidate_sources"]
        rows.append(context_row)
    sweep_runs = []
    q2 = None
    for question in questions:
        if question["id"] == "q2":
            q2 = question
    for top_k in (1, 3, 5):
        print("RUN q2 k", top_k)
        hits = retrieve_question(index, q2, top_k)
        print_hits("q2 k=" + str(top_k), hits)
        answer, latency_ms = ask_model([
            {"role": "user", "content": basic_prompt(q2["question"], hits)}
        ])
        sweep_runs.append({
            "k": top_k,
            "hits": hits,
            "sources": [hit["source"] for hit in hits],
            "scores": [hit["score"] for hit in hits],
            "answer": answer,
            "latency_ms": latency_ms,
            "ftc_source_present": any(hit["source"] == FTC_LOSS_SOURCE for hit in hits),
        })
    RAW_PATH.mkdir(parents=True, exist_ok=True)
    write_comparison(rows, q2_ftc_in_top5)
    write_k_sweep(sweep_runs)
    print_comparison(rows, sweep_runs, q2_ftc_in_top5)
    for question_id in ("q5", "q6"):
        for row in rows:
            if row["question_id"] == question_id and row["configuration"] == "context_rag":
                status = "PASS" if row["answer"] == REFUSAL else "FAIL"
                print("CONTEXT REFUSAL", question_id + ":", status)


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


JUDGMENTS = [
    ("q1", "no_rag", "n/a", True, False, True, True, "The suspicion warning is factually right. No context was supplied, so it is not grounded."),
    ("q1", "basic_rag", True, True, True, True, True, "The FTC listing-scams chunk supports the cash-wire warning."),
    ("q1", "context_rag", True, True, True, True, True, "The cited [1] chunk says a Western Union or MoneyGram wire is like sending cash and is hard to recover."),
    ("q2", "no_rag", "n/a", False, False, False, True, "The model declined and did not state the deposit limit or the FTC loss totals."),
    ("q2", "basic_rag", False, False, False, True, True, "California chunks only. The answer misstates a two-month rule and has no FTC loss figure."),
    ("q2", "context_rag", False, False, True, False, True, "The exact refusal matches the incomplete window. The question itself is answerable, so this is not an unsupported-question refusal."),
    ("q3", "no_rag", "n/a", True, False, True, True, "Inaccurate screening reports are a real problem. The answer is not grounded because no context was supplied."),
    ("q3", "basic_rag", True, True, True, True, True, "CFPB chunks support inaccurate reports and housing harm."),
    ("q3", "context_rag", True, True, True, True, True, "One repair call added [2]. That chunk says report contents vary and predictive value is unproven."),
    ("q4", "no_rag", "n/a", True, False, True, True, "A broad screening checklist answers the ambiguous question. It is not grounded in supplied chunks."),
    ("q4", "basic_rag", True, True, True, True, True, "HUD chunks support transparency, denial reasons, and fair housing."),
    ("q4", "context_rag", True, True, True, True, False, "No number-of-children claim. The Fair Housing sentences are in selected chunk [2], but the answer labels them [1] and then appends the refusal sentence."),
    ("q5", "no_rag", "n/a", False, False, False, True, "It stated a Nevada two-month limit and a statute. That is not a correct answer."),
    ("q5", "basic_rag", False, False, False, False, True, "It treated California deposit text as a Nevada answer and did not recognize the missing evidence."),
    ("q5", "context_rag", True, True, True, True, True, "Exact refusal. The California chunks do not state a Nevada limit."),
    ("q6", "no_rag", "n/a", True, False, False, True, "Tokyo is factually correct and ungrounded. It did not refuse the unsupported question."),
    ("q6", "basic_rag", True, True, True, True, True, "It correctly said the capital is not in the retrieved rental text, without the exact refusal sentence."),
    ("q6", "context_rag", True, True, True, True, True, "All five scores were below 0.40, so the context was empty and the model used the exact refusal."),
]


def evaluation_rows():
    rows = []
    for item in JUDGMENTS:
        rows.append({
            "question_id": item[0],
            "configuration": item[1],
            "correct_retrieval": item[2],
            "correct_answer": item[3],
            "grounded": item[4],
            "refused_when_needed": item[5],
            "format_compliance": item[6],
            "notes": item[7],
        })
    return rows


def robustness_count(rows, configuration):
    passed = 0
    for row in rows:
        if row["configuration"] != configuration:
            continue
        if row["question_id"] == "q4" and row["correct_answer"] is True:
            passed += 1
        if row["question_id"] in ("q5", "q6") and row["refused_when_needed"] is True:
            passed += 1
    return passed, 3


def count_flag(rows, configuration, field, question_ids=None):
    chosen = []
    for row in rows:
        if row["configuration"] != configuration:
            continue
        if question_ids and row["question_id"] not in question_ids:
            continue
        if field == "correct_retrieval" and row[field] == "n/a":
            continue
        chosen.append(row)
    passed = 0
    for row in chosen:
        if row[field] is True:
            passed += 1
    return passed, len(chosen)


def write_evaluation(rows):
    fieldnames = [
        "question_id",
        "configuration",
        "correct_retrieval",
        "correct_answer",
        "grounded",
        "refused_when_needed",
        "format_compliance",
    ]
    with (RAW_PATH / "rag_evaluation.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row[name] for name in fieldnames})
    (RAW_PATH / "rag_evaluation.json").write_text(json.dumps(rows, indent=2) + "\n")


def print_evaluation(rows):
    print("EVALUATION")
    print("question configuration retrieval answer grounded refused format")
    for row in rows:
        print(
            row["question_id"],
            row["configuration"],
            row["correct_retrieval"],
            row["correct_answer"],
            row["grounded"],
            row["refused_when_needed"],
            row["format_compliance"],
        )
    print()
    print("SUMMARY")
    print("accuracy = correct_answer / 6")
    print("faithfulness = grounded / 6")
    print("format compliance = format_compliance / 6")
    print("robustness = q4 correct_answer plus q5 and q6 refused_when_needed, divided by 3")
    for configuration in ("no_rag", "basic_rag", "context_rag"):
        accuracy = count_flag(rows, configuration, "correct_answer")
        faith = count_flag(rows, configuration, "grounded")
        form = count_flag(rows, configuration, "format_compliance")
        robust = robustness_count(rows, configuration)
        print(
            configuration,
            "accuracy", str(accuracy[0]) + "/6",
            "faithfulness", str(faith[0]) + "/6",
            "format", str(form[0]) + "/6",
            "robustness", str(robust[0]) + "/3",
        )


def check_context_refusals():
    data = json.loads((RAW_PATH / "rag_comparison.json").read_text())
    print("CONTEXT REFUSALS")
    for question_id in ("q5", "q6"):
        answer = ""
        for row in data["rows"]:
            if row["question_id"] == question_id and row["configuration"] == "context_rag":
                answer = row["answer"]
        status = "PASS" if answer == REFUSAL else "FAIL"
        print(question_id + ":", status)


def run_evaluate():
    data = json.loads((RAW_PATH / "rag_comparison.json").read_text())
    seen = [(row["question_id"], row["configuration"]) for row in data["rows"]]
    expected = [(item[0], item[1]) for item in JUDGMENTS]
    if seen != expected:
        raise SystemExit("Comparison rows do not match the evaluation rows.")
    rows = evaluation_rows()
    write_evaluation(rows)
    print_evaluation(rows)
    check_context_refusals()


def regenerate_context_rows():
    path = RAW_PATH / "rag_comparison.json"
    data = json.loads(path.read_text())
    targets = {"q1", "q3", "q4"}
    print("CONTEXT REGENERATION")
    print("Targets: q1 q3 q4")
    print("Retrieval rerun: no")
    for row in data["rows"]:
        if row["configuration"] != "context_rag" or row["question_id"] not in targets:
            continue
        selected = row["selected"]
        answer, latency_ms = ask_model(context_messages(row["question"], selected))
        repair_used = False
        if not citation_valid(answer, len(selected)):
            repaired, repair_ms = ask_model(repair_messages(row["question"], selected, answer))
            answer = repaired
            latency_ms = round(latency_ms + repair_ms, 3)
            repair_used = True
        row["answer"] = answer
        row["latency_ms"] = latency_ms
        row["grounded_sources_or_citations"] = citation_text(answer)
        row["refused"] = answer == REFUSAL
        row["repair_call"] = repair_used
        status = "PASS" if citation_valid(answer, len(selected)) else "FAIL"
        print(row["question_id"], "citation", status, "repair", repair_used)
        print(answer)
        print()
    path.write_text(json.dumps(data, indent=2) + "\n")
    write_comparison(data["rows"], data["q2_ftc_loss_source_in_top5"])
    repaired = data.get("context_repair_calls") or {}
    for row in data["rows"]:
        if row.get("repair_call") is not None and row["question_id"] in targets and row["configuration"] == "context_rag":
            repaired[row["question_id"]] = row["repair_call"]
    fresh = json.loads(path.read_text())
    fresh["context_repair_calls"] = repaired
    path.write_text(json.dumps(fresh, indent=2) + "\n")


def main():
    if len(sys.argv) == 2 and sys.argv[1] == "--compare":
        run_compare()
        return
    if len(sys.argv) == 2 and sys.argv[1] == "--regen-context":
        regenerate_context_rows()
        return
    if len(sys.argv) == 2 and sys.argv[1] == "--evaluate":
        run_evaluate()
        return
    if len(sys.argv) != 2 or sys.argv[1] != "--retrieve-only":
        raise SystemExit("Use: python3.11 rag.py --retrieve-only, --compare, --regen-context, or --evaluate")
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
