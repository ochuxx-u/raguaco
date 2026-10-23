"""
Prueba manual del LLM vía API (OpenCode Go, OpenAI-compatible).

Requisitos: `LLM_API_KEY` (y opcionalmente `LLM_MODEL`) en `.env` o en el
entorno. Se ejecuta con `App/` como raíz:

    cd App && ../venv/bin/python tests_models/probar_llm.py

Verifica las tres superficies de `infrastructure/llm/llm_service.py`:
catálogo (`GET /models`), respuesta completa (`POST /chat/completions`) y
streaming SSE. Sin clave, solo el catálogo funciona (es público) y `chat`
debe levantar `LLMError` sin tumbar nada (RNF6).
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from infrastructure.llm.llm_service import LLMError, LLMService  # noqa: E402


async def main() -> None:
    svc = LLMService()
    try:
        modelos = await svc.list_models()
        print(f'catálogo: {len(modelos)} modelos -> {sorted(modelos)[:5]} ...')
        print(f'modelo configurado: {svc._model!r} disponible:', svc._model in modelos)

        respuesta = await svc.chat(
            [
                {'role': 'system', 'content': 'Eres RAGUACO. Responde en una frase.'},
                {'role': 'user', 'content': '¿Qué harías si no hay evidencia en los documentos?'},
            ]
        )
        print('chat  :', respuesta)

        print('stream:', end=' ', flush=True)
        async for trozo in svc.chat_stream(
            [{'role': 'user', 'content': 'Cuenta del uno al cinco en una línea.'}]
        ):
            print(trozo, end='', flush=True)
        print()
    except LLMError as error:
        print('LLMError esperado si falta la key:', error)
    finally:
        await svc.aclose()


if __name__ == '__main__':
    asyncio.run(main())
