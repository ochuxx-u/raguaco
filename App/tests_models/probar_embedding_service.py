"""Verificación local del EmbeddingService (equivalente a probar_embeddings.py).

Ejecuta el servicio real sobre el modelo descargado en `App/ai-models/` y
compara con la ruta de referencia (onnxruntime + tokenizers directos) para
confirmar que la vectorización es idéntica, no solo parecida.

Uso: cd App && ../venv/bin/python tests/probar_embedding_service.py
"""

import asyncio
import sys
from pathlib import Path

import numpy as np
import onnxruntime as rt
from tokenizers import Tokenizer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from infrastructure.embeddings.embedding_service import (  # noqa: E402
    EmbeddingError,
    EmbeddingService,
)

MODELO = Path(__file__).resolve().parents[1] / 'ai-models' / 'multilingual-e5-small'

fragmentos = [
    'Raguaco es un sistema RAG conversacional que responde preguntas apoyándose en documentos.',
    'La interfaz de voz permite dictar la pregunta y escuchar la respuesta con TTS.',
    'Los secretos de configuración se cargan desde variables de entorno y nunca se suben al repositorio.',
]
pregunta = '¿Qué es Raguaco?'


def referencia(textos: list[str]) -> np.ndarray:
    """Ruta de referencia: la del script original, sin el servicio."""
    sesion = rt.InferenceSession(str(MODELO / 'onnx' / 'model.onnx'), providers=['CPUExecutionProvider'])
    tok = Tokenizer.from_file(str(MODELO / 'onnx' / 'tokenizer.json'))
    tok.enable_truncation(max_length=512)
    tok.enable_padding(pad_id=tok.token_to_id('<pad>'), pad_token='<pad>')
    encs = tok.encode_batch(textos)
    ids = np.array([e.ids for e in encs], dtype=np.int64)
    mask = np.array([e.attention_mask for e in encs], dtype=np.int64)
    tipos = np.array([e.type_ids for e in encs], dtype=np.int64)
    salida = sesion.run(None, {'input_ids': ids, 'attention_mask': mask, 'token_type_ids': tipos})[0]
    m = np.expand_dims(mask, -1).astype(salida.dtype)
    v = np.sum(salida * m, axis=1) / np.clip(np.sum(m, axis=1), a_min=1e-9, a_max=None)
    return v / np.clip(np.linalg.norm(v, axis=1, keepdims=True), a_min=1e-12, a_max=None)


async def principal() -> None:
    servicio = EmbeddingService()
    assert servicio.configured, 'el modelo debería estar descargado; revisa ai-models/'
    print(f'configured: {servicio.configured} · dimension: {servicio.dimension}')

    V_pasajes = np.array(await servicio.embeber_pasajes(fragmentos))
    q = np.array(await servicio.embeber_consulta(pregunta))

    assert V_pasajes.shape == (3, 384), V_pasajes.shape
    assert q.shape == (384,), q.shape
    normas = np.linalg.norm(np.vstack([V_pasajes, q[None, :]]), axis=1)
    assert np.allclose(normas, 1.0, atol=1e-5), normas
    print(f'normas ~1: {np.round(normas, 6)}')

    sims = V_pasajes @ q
    orden = np.argsort(-sims)
    for i, s in enumerate(sims):
        print(f'  pasaje {i} · similitud = {s:.4f}')
    assert orden[0] == 0, 'la pregunta debe quedar más cerca del pasaje 0'

    # Vacíos y lote unitario no rompen nada.
    assert await servicio.embeber_pasajes([]) == []

    # Equivalencia numérica con la ruta de referencia (misma semántica exacta).
    esperado = referencia([f'passage: {t}' for t in fragmentos] + [f'query: {pregunta}'])
    obtenido = np.vstack([V_pasajes, q[None, :]])
    delta = float(np.max(np.abs(esperado - obtenido)))
    print(f'max |referencia - servicio| = {delta:.2e}')
    assert delta < 1e-4, delta

    # Modelo ausente: fallo claro, no stack trace opaco.
    roto = EmbeddingService(model_dir='ai-models/no-existe-xyz')
    assert not roto.configured
    try:
        await roto.embeber_consulta('proba')
    except EmbeddingError as exc:
        print(f'EmbeddingError esperado -> {str(exc)[:80]}...')
    else:
        raise AssertionError('debió levantar EmbeddingError con modelo ausente')

    print('OK -> EmbeddingService vectoriza igual que la referencia y avisa si falta el modelo')


if __name__ == '__main__':
    asyncio.run(principal())
