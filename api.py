"""HTTP adapter for the deterministic D&D orchestrator.

The API is intentionally stateless: callers send the character state needed for
an action and receive the resulting state changes. Persistence belongs to the
campaign/backend layer, not this rules service.
"""
from __future__ import annotations

import os
import secrets
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from orchestrator import FERRAMENTAS_CONHECIDAS, OrquestradorAcoes

app = FastAPI(
    title="DND Core Orchestrator",
    version="1.0.0",
    description="API HTTP para executar ações estruturadas pelo Orquestrador e Rule Engine.",
)

_API_KEY = os.getenv("ORCHESTRATOR_API_KEY", "").strip()


async def verify_api_key(authorization: str | None = Header(default=None)) -> None:
    """Require a bearer key when ORCHESTRATOR_API_KEY is configured."""
    if not _API_KEY:
        return
    expected = f"Bearer {_API_KEY}"
    if authorization is None or not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Credencial ausente ou inválida")


class ActionRequest(BaseModel):
    ferramenta: str = Field(
        description="Uma das ferramentas aceitas: resolver_regra, consultar_monstro, sugerir_monstros"
    )
    argumentos: dict[str, Any] = Field(default_factory=dict)
    personagens: list[dict[str, Any]] = Field(default_factory=list)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "dnd-core-orchestrator"}


@app.get("/v1/tools", dependencies=[Depends(verify_api_key)])
async def tools() -> dict[str, list[str]]:
    return {"tools": sorted(FERRAMENTAS_CONHECIDAS)}


@app.post("/v1/action", dependencies=[Depends(verify_api_key)])
async def execute_action(request: ActionRequest) -> dict[str, Any]:
    if request.ferramenta not in FERRAMENTAS_CONHECIDAS:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "ferramenta_desconhecida",
                "accepted": sorted(FERRAMENTAS_CONHECIDAS),
            },
        )

    orchestrator = OrquestradorAcoes()
    result = orchestrator.executar_ferramenta(
        request.ferramenta,
        request.argumentos,
        personagens=request.personagens,
    )
    return {
        "status": result.status,
        "dados": result.dados,
        "alteracoes": result.alteracoes,
        "rolagens": result.rolagens,
    }
