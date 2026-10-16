from fastapi import APIRouter

router = APIRouter(prefix='/api/v1/conversations', tags=['conversations'])

@router.get('/')
async def conversations():
    return {'message': 'Has accedido a conversaciones'}