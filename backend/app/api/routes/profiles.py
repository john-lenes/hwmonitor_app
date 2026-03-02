"""Endpoints REST de perfis de ventoinha."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.models.profile import FanProfile, FanProfileCreate, FanProfileUpdate

router = APIRouter()


@router.get("/", response_model=list[FanProfile])
async def list_profiles(request: Request) -> list[FanProfile]:
    """Retorna todos os perfis de ventoinha (padrões + personalizados)."""
    return request.app.state.profile_manager.list_profiles()


@router.get("/active", response_model=FanProfile)
async def get_active_profile(request: Request) -> FanProfile:
    """Retorna o perfil ativo no momento."""
    profile = request.app.state.profile_manager.get_active_profile()
    if not profile:
        raise HTTPException(status_code=404, detail="Perfil ativo não encontrado")
    return profile


@router.get("/{profile_id}", response_model=FanProfile)
async def get_profile(profile_id: str, request: Request) -> FanProfile:
    """Retorna os dados de um perfil específico pelo ID."""
    profile = request.app.state.profile_manager.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")
    return profile


@router.post("/", response_model=FanProfile, status_code=201)
async def create_profile(body: FanProfileCreate, request: Request) -> FanProfile:
    """Cria um novo perfil de ventoinha personalizado."""
    return request.app.state.profile_manager.create_profile(body)


@router.put("/{profile_id}", response_model=FanProfile)
async def update_profile(profile_id: str, body: FanProfileUpdate, request: Request) -> FanProfile:
    """Atualiza um perfil personalizado existente."""
    profile = request.app.state.profile_manager.update_profile(profile_id, body)
    if not profile:
        raise HTTPException(
            status_code=400,
            detail="Perfil não encontrado ou é um perfil padrão",
        )
    return profile


@router.delete("/{profile_id}", status_code=204, response_model=None)
async def delete_profile(profile_id: str, request: Request) -> None:
    """Exclui um perfil personalizado de ventoinha."""
    deleted = request.app.state.profile_manager.delete_profile(profile_id)
    if not deleted:
        raise HTTPException(
            status_code=400,
            detail="Perfil não encontrado ou é um perfil padrão",
        )


@router.post("/{profile_id}/activate", response_model=FanProfile)
async def activate_profile(profile_id: str, request: Request) -> FanProfile:
    """Define um perfil como ativo."""
    profile = request.app.state.profile_manager.activate_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")
    return profile
