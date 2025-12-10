"""
PDF preprocessing module for N8N Financial Judge.

This module handles PDF text extraction and chunking for large documents.
"""

import logging
import re
from pathlib import Path
from typing import Any

import PyPDF2

logger = logging.getLogger(__name__)

# Maximum chunk size in characters
MAX_CHUNK_SIZE = 1500
CHUNK_OVERLAP = 200


class PDFPreprocessor:
    """Handles PDF text extraction and chunking."""

    def __init__(self, max_chunk_size: int = MAX_CHUNK_SIZE, overlap_size: int = CHUNK_OVERLAP):
        """
        Initialize the PDF preprocessor.

        Args:
            max_chunk_size: Maximum size of each chunk in characters (default: 1500)
        """

        self.max_chunk_size = max_chunk_size
        self.overlap_size = overlap_size

    def extract_text_from_pdf(self, pdf_path: Path) -> list[str]:
        """
        Extract text from PDF file, returning a list of strings where each string represents a page.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            List of strings, where each string contains the text from one page

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            Exception: If PDF extraction fails
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        logger.info(f"Extracting text from PDF: {pdf_path.name}")

        try:
            page_texts = []
            with open(pdf_path, "rb") as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                num_pages = len(pdf_reader.pages)

                logger.info(f"PDF has {num_pages} pages")

                for page_num, page in enumerate(pdf_reader.pages, 1):
                    try:
                        text = page.extract_text()
                        # Always append, even if empty, to maintain page index correspondence
                        page_texts.append(text or "")
                        if page_num % 10 == 0:
                            logger.debug(f"Processed {page_num}/{num_pages} pages")
                    except Exception as e:
                        logger.warning(f"Failed to extract text from page {page_num}: {e}")
                        # Append empty string to maintain page index correspondence
                        page_texts.append("")
                        continue

            total_chars = sum(len(text) for text in page_texts)
            logger.info(f"Extracted {total_chars} characters from {len(page_texts)} pages")

            return page_texts

        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {e}")
            raise

    def chunk_text(self, page_texts: list[str]) -> list[dict[str, Any]]:
        """
        Split text from pages into chunks of maximum size, preserving page information.

        Attempts to split at paragraph boundaries when possible.

        Args:
            page_texts: List of strings, where each string contains text from one page

        Returns:
            List of chunk dictionaries with keys:
                - chunk_index: 0-based chunk index
                - chunk_text: The chunk text
                - total_chunks: Total number of chunks
                - char_count: Number of characters in this chunk
                - is_last: Whether this is the last chunk
                - page_index: 0-based page index where this chunk starts
                - page_range: Tuple of (start_page, end_page) indices for this chunk
        """
        if not page_texts or not any(page_texts):
            return []

        # Combine all pages with indexed page separators so we can recover page indices via regex later
        # Format: --- PAGE BREAK [N] --- where N is the 0-based index of the NEXT page
        combined_parts: list[str] = []
        for i, page_text in enumerate(page_texts):
            if i > 0:
                combined_parts.append(f"\n\n--- PAGE BREAK [{i}] ---\n\n")
            combined_parts.append(page_text)
        combined_text = "".join(combined_parts)

        # If combined text is smaller than max chunk size, return as single chunk
        if len(combined_text) <= self.max_chunk_size:
            return [
                {
                    "chunk_index": 0,
                    "chunk_text": combined_text,
                    "total_chunks": 1,
                    "char_count": len(combined_text),
                    "is_last": True,
                    "page_index": 0,
                    "page_range": (0, len(page_texts) - 1),
                }
            ]

        # Split text into chunks
        chunks: list[str] = []
        current_pos = 0
        text_length = len(combined_text)

        while current_pos < text_length:
            # Calculate chunk end position
            chunk_end = min(current_pos + self.max_chunk_size, text_length)

            # If not at the end, try to find a good breaking point
            if chunk_end < text_length:
                # Try to break at paragraph (double newline)
                last_paragraph = combined_text.rfind("\n\n", current_pos, chunk_end)
                if last_paragraph > current_pos:
                    chunk_end = last_paragraph + 2  # Include the double newline

                # If no paragraph break, try single newline
                elif (
                    last_newline := combined_text.rfind("\n", current_pos, chunk_end)
                ) > current_pos:
                    chunk_end = last_newline + 1

                # If no newline, try to break at sentence (period + space)
                elif (
                    last_sentence := combined_text.rfind(". ", current_pos, chunk_end)
                ) > current_pos:
                    chunk_end = last_sentence + 2

                # If no good break point, try space
                elif (last_space := combined_text.rfind(" ", current_pos, chunk_end)) > current_pos:
                    chunk_end = last_space + 1

            # Extract chunk
            chunk_text = combined_text[current_pos:chunk_end].strip()
            if chunk_text:  # Only add non-empty chunks
                chunks.append(chunk_text)
            # Move position forward with overlap
            if chunk_end - current_pos > self.overlap_size * 3:
                current_pos = chunk_end - self.overlap_size
            else:
                current_pos = chunk_end

        # Create chunk metadata with page information
        total_chunks = len(chunks)
        chunk_dicts = []
        page_idx = 1

        page_break_regex = re.compile(r"--- PAGE BREAK \[(\d+)\] ---")

        for idx, chunk_text in enumerate(chunks):
            match = page_break_regex.search(chunk_text)
            if match:
                page_idx = (
                    int(match.group(1)) + 1
                )  # update the page_idx when we are touching the next page

            chunk_dicts.append(
                {
                    "chunk_index": idx,
                    "chunk_text": chunk_text,
                    "total_chunks": total_chunks,
                    "char_count": len(chunk_text),
                    "is_last": idx == total_chunks - 1,
                    "page_index": page_idx,
                }
            )

        logger.info(
            f"Split text into {total_chunks} chunks " f"(max size: {self.max_chunk_size:,} chars)"
        )

        return chunk_dicts

    def _calculate_page_range(self, chunk_text: str, page_texts: list[str]) -> tuple[int, int]:
        """
        Calculate the page range for a chunk based on its content.

        Args:
            chunk_text: The chunk text to analyze
            page_texts: List of page texts

        Returns:
            Tuple of (start_page_index, end_page_index)
        """
        # Find which pages this chunk spans by looking for page break markers
        page_breaks = chunk_text.count("--- PAGE BREAK ---")

        if page_breaks == 0:
            # Chunk is entirely within one page
            # Find which page by checking if chunk content appears in any page
            for i, page_text in enumerate(page_texts):
                if page_text and chunk_text.replace("--- PAGE BREAK ---", "").strip() in page_text:
                    return (i, i)
            return (0, 0)  # Default fallback

        # Chunk spans multiple pages
        start_page = 0
        end_page = len(page_texts) - 1

        # More sophisticated logic could be added here to determine exact page boundaries
        # For now, we'll use a simple approach based on page break count
        if page_breaks > 0:
            end_page = min(page_breaks, len(page_texts) - 1)

        return (start_page, end_page)

    def preprocess_pdf(self, pdf_path: Path) -> list[dict[str, Any]]:
        """
        Extract text from PDF and chunk it, preserving page information.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            List of chunk dictionaries ready for processing, each containing page metadata

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            ImportError: If PyPDF2 is not installed
            Exception: If preprocessing fails
        """
        # Extract text as list of page strings
        page_texts = self.extract_text_from_pdf(pdf_path)

        # Chunk text with page information
        chunks = self.chunk_text(page_texts)

        total_chars = sum(len(text) for text in page_texts)
        logger.info(
            f"Preprocessed PDF: {len(chunks)} chunk(s), {len(page_texts)} page(s), "
            f"total {total_chars:,} characters"
        )

        return chunks


def preprocess_pdf(pdf_path: Path, max_chunk_size: int = MAX_CHUNK_SIZE) -> list[dict[str, Any]]:
    """
    Convenience function to preprocess a PDF file.

    Args:
        pdf_path: Path to the PDF file
        max_chunk_size: Maximum chunk size in characters (default: 1500)

    Returns:
        List of chunk dictionaries

    Raises:
        FileNotFoundError: If PDF file doesn't exist
        ImportError: If PyPDF2 is not installed
        Exception: If preprocessing fails
    """
    preprocessor = PDFPreprocessor(max_chunk_size)
    return preprocessor.preprocess_pdf(pdf_path)
