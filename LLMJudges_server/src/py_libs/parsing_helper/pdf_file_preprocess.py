"""
Local PDF preprocessing helpers for FastAPI endpoints.

This module mirrors the chunking and aggregation performed by the async
`upload_pdf` helper in `n8n_client.py`, but without issuing HTTP requests
to the downstream N8N workflow. Instead, it returns the same aggregated
payload structure so API consumers can inspect chunk data locally.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Iterable

from LLMJudges_server.src.py_libs.parsing_helper.pdf_preprocessor import preprocess_pdf

logger = logging.getLogger(__name__)

# Keep default batch sizing consistent with the async uploader.
DEFAULT_BATCH_SIZE = 150


def _batched_chunks(
    chunks: list[dict[str, Any]], batch_size: int
) -> Iterable[tuple[int, list[dict[str, Any]]]]:
    """Yield chunk slices with their batch index."""
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero")

    total_chunks = len(chunks)
    batch_index = 0
    for start in range(0, total_chunks, batch_size):
        end = min(start + batch_size, total_chunks)
        yield batch_index, chunks[start:end]
        batch_index += 1


def preprocess_pdf_file(
    file_path: Path,
    company_ticker: str = "Unknown Company",
    report_type: str = "10-K",
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, Any]:
    """
    Preprocess a PDF file into chunks and organize them into batches.

    Args:
        pdf_file_company_ticker: Name of the PDF file in the company_data folder.
        company_ticker: Ticker symbol metadata.
        report_type: Report type metadata (e.g., 10-K, 10-Q).
        batch_size: Max number of chunks per batch (mirrors uploader default).

    Returns:
        Dictionary matching the aggregated_result structure from upload_pdf().
    """
    if not file_path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    logger.info("Locally preprocessing PDF for %s (%s)", company_ticker, report_type)
    chunks = preprocess_pdf(file_path)
    total_chunks = len(chunks)
    total_characters = sum(chunk.get("char_count", 0) for chunk in chunks)
    total_batches = (total_chunks + batch_size - 1) // batch_size if total_chunks else 0

    batch_results: list[dict[str, Any]] = []
    for batch_index, batch_chunks in _batched_chunks(chunks, batch_size):
        batch_payload = {
            "batch_index": batch_index,
            "batch_size": batch_size,
            "chunk_count": len(batch_chunks),
            "is_last_batch": batch_index == total_batches - 1 if total_batches else True,
            "chunks": [
                {
                    "chunk_index": chunk_data.get("chunk_index"),
                    "chunk_text": chunk_data.get("chunk_text"),
                    "total_chunks": chunk_data.get("total_chunks"),
                    "is_last_chunk": chunk_data.get("is_last"),
                    "chunk_char_count": chunk_data.get("char_count"),
                    "page_index": chunk_data.get("page_index"),
                }
                for chunk_data in batch_chunks
            ],
        }
        batch_results.append(batch_payload)

    aggregated_result = {
        "success": True,
        "preprocessed": True,
        "file_name": file_path.name,
        "company_ticker": company_ticker,
        "report_type": report_type,
        "total_chunks": total_chunks,
        "total_batches": total_batches,
        "batch_size": batch_size,
        "batch_results": batch_results,
        "summary": {
            "total_characters": total_characters,
            "chunks_processed": total_chunks,
            "batches_sent": total_batches,
        },
    }

    return aggregated_result
