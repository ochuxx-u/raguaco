from fastapi import APIRouter

router = APIRouter(prefix='/api/v1/voice', tags=['voice'])

@router.get('/')
async def voice():
    return {'message': 'Has accedido al modo voz xd'}