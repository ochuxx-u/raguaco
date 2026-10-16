from fastapi import APIRouter

router = APIRouter(prefix='/api/v1/documents', tags=['documents'])

@router.get('/')
async def documents():
    return {'message': 'Has accedido a documentos'}