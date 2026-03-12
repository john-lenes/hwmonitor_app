"""Endpoints REST de perfis de ventoinha – /api/v1/profiles/..."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.deps import ProfileManagerDep
from app.models.profile import FanProfile, FanProfileCreate, FanProfileUpdate

router = APIRouter()


@router.get(
    "/",
    response_model=list[FanProfile],
    summary="Lista todos os perfis",
    description="Retorna todos os perfis de ventoinha (4 embutidos + personalizados).",
)
async def list_profiles(manager: ProfileManagerDep) -> list[FanProfile]:
    return manager.list_profiles()


@router.get(
    "/active",
    response_model=FanProfile,
    summary="Perfil ativo",
    description="Retorna o perfil de ventoinha atualmente ativo.",
)
async def get_active_profile(manager: ProfileManagerDep) -> FanProfile:
    profile = manager.get_active_profile()
    if not profile:
        raise HTTPException(status_code=404, detail="Nenhum perfil ativo encontrado.")
    return profile


@router.get(
    "/{profile_id}",
    response_model=FanProfile,
    summary="Busca perfil por ID",
)
async def get_profile(profile_id: str, manager: ProfileManagerDep) -> FanProfile:
    profile = manager.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Perfil '{profile_id}' não encontrado.")
    return profile


@router.post(
    "/",
    response_model=FanProfile,
    status_code=201,
    summary="Cria novo perfil",
    description="Cria um novo perfil personalizado com curva temperatura→velocidade.",
)
async def create_profile(body: FanProfileCreate, manager: ProfileManagerDep) -> FanProfile:
    return manager.create_profile(body)


@router.put(
    "/{profile_id}",
    response_model=FanProfile,
    summary="Atualiza perfil",
    description=(
        "Atualiza um perfil existente. "
        "Perfis embutidos podem ser editados (override persistido em JSON). "
        "Para restaurar ao padrão, use o endpoint `/reset`."
    ),
)
async def update_profile(
    profile_id: str,
    body: FanProfileUpdate,
    manager: ProfileManagerDep,
) -> FanProfile:
    profile = manager.update_profile(profile_id, body)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Perfil '{profile_id}' não encontrado.")
    return profile


@router.post(
    "/{profile_id}/reset",
    response_model=FanProfile,
    summary="Restaura perfil embutido ao padrão",
)
async def reset_profile_to_default(
    profile_id: str,
    manager: ProfileManagerDep,
) -> FanProfile:
    profile = manager.reset_to_default(profile_id)
    if not profile:
        raise HTTPException(
            status_code=400,
            detail=f"Perfil '{profile_id}' não encontrado ou não é embutido.",
        )
    return profile


@router.delete(
    "/{profile_id}",
    status_code=204,
    response_model=None,
    summary="Exclui perfil personalizado",
    description="Exclui um perfil personalizado. Perfis embutidos não podem ser excluídos.",
)
async def delete_profile(profile_id: str, manager: ProfileManagerDep) -> None:
    if not manager.delete_profile(profile_id):
        raise HTTPException(
            status_code=400,
            detail=f"Perfil '{profile_id}' não encontrado ou é embutido (não pode ser excluído).",
        )


@router.post(
    "/{profile_id}/activate",
    response_model=FanProfile,
    summary="Ativa um perfil",
    description="Define o perfil especificado como o perfil ativo.",
)
async def activate_profile(profile_id: str, manager: ProfileManagerDep) -> FanProfile:
    profile = manager.activate_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Perfil '{profile_id}' não encontrado.")
    return profile
