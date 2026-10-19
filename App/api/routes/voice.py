from fastapi import APIRouter

router = APIRouter(prefix='/v1/voice', tags=['voice'])

@router.get('/')
async def voice():
    return {'message': 'Has accedido al modo voz xd'}