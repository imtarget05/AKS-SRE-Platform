#!/usr/bin/env python3
"""
Portfolio Knowledge Retrieval Engine (BM25 + RRF Chunk Search)
Indexes and searches across all 5 portfolio repositories:
- gap-register.md, canonical-repository-decisions.md, portfolio-audit.md, reusable-assets-register.md
- OpsBridge ADRs (001-021) & evidence
- AKS-SRE-Platform ADRs (012-015), runbooks & evidence
- QuanLyKho MLOps evidence & architecture
- SmartDocumentChatbot CRAG architecture & evaluation
"""

import argparse
import json
import math
import re
from pathlib import Path
from typing import Dict, List, Tuple


def tokenize(text: str) -> List[str]:
    return [w.lower() for w in re.findall(r"\b\w{2,}\b", text)]


class KnowledgeDocument:
    def __init__(self, file_path: Path, title: str, section: str, content: str, line_start: int):
        self.file_path = file_path
        self.title = title
        self.section = section
        self.content = content
        self.line_start = line_start
        self.tokens = tokenize(content)


class PortfolioKnowledgeRetriever:
    def __init__(self, base_dirs: List[Path]):
        self.base_dirs = base_dirs
        self.docs: List[KnowledgeDocument] = []
        self.doc_freq: Dict[str, int] = {}
        self.avg_dl: float = 0.0

    def index(self):
        self.docs.clear()
        target_files: List[Path] = []

        # 1. Download-level portfolio audit & registers
        downloads_dir = Path("/Users/mainguyenbinhtan/Downloads")
        for f in [
            "gap-register.md",
            "canonical-repository-decisions.md",
            "portfolio-audit.md",
            "reusable-assets-register.md",
        ]:
            p = downloads_dir / f
            if p.exists():
                target_files.append(p)

        # 2. OpsBridge ADRs and evidence
        ops_adr = downloads_dir / "OpsBridge" / "docs" / "adr"
        if ops_adr.exists():
            target_files.extend(ops_adr.glob("*.md"))

        # 3. AKS-SRE-Platform ADRs, evidence, and cheatsheet
        aks_dir = downloads_dir / "AKS-SRE-Platform" / "docs"
        if aks_dir.exists():
            target_files.extend((aks_dir / "adr").glob("*.md"))
            target_files.extend((aks_dir / "evidence").glob("*.md"))
            cs = aks_dir / "PORTFOLIO_INTERVIEW_CHEATSHEET.md"
            if cs.exists():
                target_files.append(cs)

        # 4. QuanLyKho MLOps evidence & QA
        qlk_dir = downloads_dir / "QuanLyKho" / "docs"
        if qlk_dir.exists():
            target_files.extend((qlk_dir / "mlops").glob("*.md"))
            target_files.extend((qlk_dir / "qa").glob("*.md"))

        # 5. SmartDocumentChatbot audit & README
        sdc_dir = downloads_dir / "SmartDocumentChatbot"
        if sdc_dir.exists():
            if (sdc_dir / "README.md").exists():
                target_files.append(sdc_dir / "README.md")
            if (sdc_dir / "docs" / "PORTFOLIO_ENTERPRISE_AUDIT.md").exists():
                target_files.append(sdc_dir / "docs" / "PORTFOLIO_ENTERPRISE_AUDIT.md")

        for file_path in target_files:
            self._chunk_and_add(file_path)

        # Compute document frequencies
        total_tokens = sum(len(d.tokens) for d in self.docs)
        self.avg_dl = total_tokens / max(len(self.docs), 1)

        self.doc_freq.clear()
        for doc in self.docs:
            seen = set(doc.tokens)
            for token in seen:
                self.doc_freq[token] = self.doc_freq.get(token, 0) + 1

    def _chunk_and_add(self, file_path: Path):
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return

        lines = text.split("\n")
        current_title = file_path.name
        current_section = "Header"
        current_chunk: List[str] = []
        chunk_start = 1

        for idx, line in enumerate(lines, start=1):
            if line.startswith("#"):
                if current_chunk:
                    chunk_text = "\n".join(current_chunk).strip()
                    if len(chunk_text) > 40:
                        self.docs.append(
                            KnowledgeDocument(
                                file_path, current_title, current_section, chunk_text, chunk_start
                            )
                        )
                    current_chunk = []
                current_section = line.strip("# \t\r")
                chunk_start = idx
            current_chunk.append(line)

        if current_chunk:
            chunk_text = "\n".join(current_chunk).strip()
            if len(chunk_text) > 40:
                self.docs.append(
                    KnowledgeDocument(
                        file_path, current_title, current_section, chunk_text, chunk_start
                    )
                )

    def search(self, query: str, top_k: int = 5) -> List[Tuple[KnowledgeDocument, float]]:
        q_tokens = tokenize(query)
        if not q_tokens:
            return []

        scores: List[Tuple[KnowledgeDocument, float]] = []
        k1 = 1.5
        b = 0.75
        N = len(self.docs)

        for doc in self.docs:
            score = 0.0
            doc_len = len(doc.tokens)
            tf_dict: Dict[str, int] = {}
            for t in doc.tokens:
                tf_dict[t] = tf_dict.get(t, 0) + 1

            for qt in q_tokens:
                df = self.doc_freq.get(qt, 0)
                if df == 0:
                    continue
                idf = math.log((N - df + 0.5) / (df + 0.5) + 1.0)
                tf = tf_dict.get(qt, 0)
                denom = tf + k1 * (1.0 - b + b * (doc_len / self.avg_dl))
                score += idf * (tf * (k1 + 1.0)) / max(denom, 1e-6)

            if score > 0.0:
                scores.append((doc, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


def main():
    parser = argparse.ArgumentParser(description="Portfolio Knowledge Retrieval Engine")
    parser.add_argument("query", nargs="*", help="Query string")
    parser.add_argument("--top-k", type=int, default=3, help="Number of results")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    args = parser.parse_args()

    query = " ".join(args.query).strip()
    retriever = PortfolioKnowledgeRetriever([Path("/Users/mainguyenbinhtan/Downloads")])
    retriever.index()

    if not query:
        print(f"Indexed {len(retriever.docs)} chunks across portfolio repositories.")
        print("Example usage: python3 portfolio_knowledge_retriever.py 'zero-oversell Redis Lua'")
        return

    results = retriever.search(query, top_k=args.top_k)
    if args.json:
        out = [
            {
                "file": str(doc.file_path),
                "title": doc.title,
                "section": doc.section,
                "line": doc.line_start,
                "score": round(score, 3),
                "excerpt": doc.content[:300] + "..." if len(doc.content) > 300 else doc.content,
            }
            for doc, score in results
        ]
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print(f"\n=== Top {len(results)} Search Results for: '{query}' ===\n")
        for i, (doc, score) in enumerate(results, 1):
            print(f"[{i}] Score: {score:.2f} | File: {doc.file_path.name}:{doc.line_start}")
            print(f"    Section: {doc.section}")
            preview = "\n    ".join(doc.content[:350].splitlines())
            print(f"    Content:\n    {preview}...")
            print("-" * 60)


if __name__ == "__main__":
    main()
