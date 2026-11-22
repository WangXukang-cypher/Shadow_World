from fastapi import APIRouter

from app.api.dependencies import ServiceDep, UserIdDep

router = APIRouter(prefix="/people", tags=["people"])


@router.get("")
async def list_people(service: ServiceDep, user_id: UserIdDep):
    people = await service.people.list(user_id)
    return [
        {
            "id": p.id,
            "name": p.name,
            "nickname": p.nickname,
            "relationship": p.relationship,
            "traits": p.traits,
            "birthday": p.birthday,
            "notes": p.notes,
            "mention_count": p.mention_count,
        }
        for p in people
    ]


@router.get("/graph")
async def get_social_graph(service: ServiceDep, user_id: UserIdDep):
    return await service.people.get_social_graph(user_id)


@router.get("/commitments")
async def list_commitments(service: ServiceDep, user_id: UserIdDep):
    commitments = await service.people.list_commitments(user_id)
    return [
        {
            "id": c.id,
            "person_id": c.person_id,
            "content": c.content,
            "status": c.status,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in commitments
    ]


@router.delete("/{person_id}", status_code=204)
async def delete_person(person_id: str, service: ServiceDep, user_id: UserIdDep):
    await service.people.delete(user_id, person_id)
