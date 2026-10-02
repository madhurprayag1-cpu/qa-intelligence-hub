from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
from app.core.defects import DEFECT_REGISTRY, DefectDefinition

router = APIRouter(prefix="/defects", tags=["defects"])


class DefectSummary(BaseModel):
    id: str
    name: str
    category: str
    affected_endpoint: str
    description: str
    how_to_reproduce: str
    expected_qa_detection: str
    headers: Dict[str, str]


@router.get("", response_model=List[DefectSummary])
async def list_defects():
    """Returns documentation for all intentionally engineered defect scenarios."""
    return [
        DefectSummary(
            id=d.id,
            name=d.name,
            category=d.category,
            affected_endpoint=d.affected_endpoint,
            description=d.description,
            how_to_reproduce=d.how_to_reproduce,
            expected_qa_detection=d.expected_qa_detection,
            headers=d.headers,
        )
        for d in DEFECT_REGISTRY.values()
    ]


@router.get("/{defect_id}", response_model=DefectSummary)
async def get_defect(defect_id: str):
    """Retrieve details for a specific defect scenario by ID."""
    norm_id = defect_id.strip().upper()
    defect = DEFECT_REGISTRY.get(norm_id)
    if not defect:
        raise HTTPException(
            status_code=404,
            detail=f"Defect '{defect_id}' not found in registry. Supported: {list(DEFECT_REGISTRY.keys())}",
        )
    return DefectSummary(
        id=defect.id,
        name=defect.name,
        category=defect.category,
        affected_endpoint=defect.affected_endpoint,
        description=defect.description,
        how_to_reproduce=defect.how_to_reproduce,
        expected_qa_detection=defect.expected_qa_detection,
        headers=defect.headers,
    )
