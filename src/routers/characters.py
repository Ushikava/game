from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from db.models import Character
from routers.dependencies import CharacterServiceDep, CurrentUser, OnlineServiceDep
from schemas.characters import CharacterList, CharacterOut, CreateCharacterRequest, DeleteCharacterRequest
from schemas.game import OnlinePage

router = APIRouter(prefix="/characters", tags=["characters"])


@router.get("", response_model=CharacterList)
async def list_characters(user: CurrentUser, character_service: CharacterServiceDep) -> CharacterList:
    return await character_service.get_characters(user)


@router.get("/online", response_model=OnlinePage)
async def list_online(
    _: CurrentUser,
    online_service: OnlineServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    after: Annotated[int | None, Query(ge=1)] = None,
) -> OnlinePage:
    return online_service.get_page(after, limit)


@router.post("", response_model=CharacterOut, status_code=status.HTTP_201_CREATED)
async def create_character(
    body: CreateCharacterRequest, user: CurrentUser, character_service: CharacterServiceDep
) -> Character:
    return await character_service.create(user, body.name)


@router.delete("/{character_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_character(
    character_id: Annotated[int, Path(ge=1, le=2**31 - 1)],
    body: DeleteCharacterRequest,
    user: CurrentUser,
    character_service: CharacterServiceDep,
) -> None:
    await character_service.delete(user, character_id, body.name)
