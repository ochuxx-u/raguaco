from fastapi import APIRouter

router = APIRouter(prefix='/v1/queries', tags=['queries'])

@router.get('/')
async def queries():
    return {'message': 'Has accedido a queries'}