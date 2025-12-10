"""
FastAPI router for LLMJudges financial analysis endpoints.

This module provides REST API endpoints for the LLMJudges system,
allowing users to submit financial documents and text for analysis.
"""

import logging
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from LLMJudges_server.src.py_libs.parsing_helper.pdf_file_preprocess import (
    preprocess_pdf_file,
)
from LLMJudges_server.src.py_libs.parsing_helper.report_log_preprocess import (
    get_preprocessed_by_execution_id,
)

logger = logging.getLogger(__name__)

# N8N configuration - use environment variable or default to Docker service name
N8N_BASE_URL = os.getenv("N8N_BASE_URL", "http://n8n:5678")
BASE_PDF_PATH = "LLMJudges_server/data/company_data"

router = APIRouter(prefix="/llm-judges", tags=["LLM Judges"])

# Global workflow instance (in production, consider using dependency injection)
_workflow_instance = None



class ExecutionIdRequest(BaseModel):
    execution_id: str = Field(..., description="n8n execution id or numeric id")


class PDFPreprocessRequest(BaseModel):
    pdf_file_company_ticker: list[str] = Field(..., description="List of company tickers")
    report_type: list[str] = Field(
        ..., description="List of financial report types (10-K, 10-Q, etc.)"
    )


@router.get("/report/{execution_id}")
async def get_report_by_execution_id(execution_id: str) -> dict[str, Any]:
    """Return preprocessed report_text for a given execution id.

    Accepts either the `n8n_execution_id` or the numeric table `id`.
    """
    try:
        payload = get_preprocessed_by_execution_id(execution_id)
        return payload
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Failed to preprocess report for execution_id=%s", execution_id)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post("/report")
async def post_report_by_execution_id(req: ExecutionIdRequest) -> dict[str, Any]:
    """POST variant accepting JSON body with `execution_id`."""
    return await get_report_by_execution_id(req.execution_id)


@router.post("/pdf/preprocess")
async def preprocess_pdf_endpoint(req: PDFPreprocessRequest) -> list[dict[str, Any]]:
    """Preprocess a PDF locally and return chunk metadata identical to upload_pdf."""
    all_parsed_data = []

    try:
        for company_idx in range(len(req.pdf_file_company_ticker)):
            pdf_file_paths = list(
                (BASE_PDF_PATH / Path(req.pdf_file_company_ticker[company_idx])).iterdir()
            )
            for pdf_file_path in pdf_file_paths:
                all_parsed_data.append(
                    preprocess_pdf_file(
                        file_path=pdf_file_path,
                        company_ticker=req.pdf_file_company_ticker[company_idx],
                        report_type=req.report_type[company_idx],
                    )
                )
        return all_parsed_data
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:  # pragma: no cover - defensive logging
        logger.exception("Failed to preprocess PDF at %s", req.pdf_file_company_ticker[company_idx])
        raise HTTPException(status_code=500, detail="Failed to preprocess PDF") from e


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    try:

        return {
            "status": "healthy",
            "timestamp": "2023-12-01T00:00:00Z",  # Would use actual timestamp
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    pass
