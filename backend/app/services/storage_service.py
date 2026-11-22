import hashlib
import os
import shutil
from typing import AsyncGenerator, Tuple
from fastapi import UploadFile
import aiofiles

from app.core.config import settings
from app.core.exceptions import AppException


class StorageService:
    CHUNK_SIZE = 64 * 1024  # 64 KB por bloque

    def __init__(self, base_path: str = settings.STORAGE_PATH):
        self.base_path = os.path.abspath(base_path)
        os.makedirs(self.base_path, exist_ok=True)
        self.temp_path = os.path.join(self.base_path, "tmp")
        os.makedirs(self.temp_path, exist_ok=True)

    async def save_upload_stream(self, upload_file: UploadFile) -> Tuple[str, str, int]:
        """
        Lee el flujo del archivo por trozos:
        - Calcula el hash SHA-256 al vuelo.
        - Controla que no supere MAX_FILE_SIZE_BYTES (500 MB).
        - Deduplica: si el binario ya existe con ese hash, no duplica el archivo físico.
        Retorna: (sha256_hash, relative_storage_path, tamano_bytes)
        """
        hasher = hashlib.sha256()
        total_bytes = 0
        temp_filename = f"upload_{os.urandom(8).hex()}.tmp"
        temp_filepath = os.path.join(self.temp_path, temp_filename)

        try:
            async with aiofiles.open(temp_filepath, "wb") as f_out:
                while True:
                    chunk = await upload_file.read(self.CHUNK_SIZE)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    if total_bytes > settings.MAX_FILE_SIZE_BYTES:
                        raise AppException(
                            status_code=413,
                            codigo="ARCHIVO_DEMASIADO_GRANDE",
                            mensaje=f"El archivo supera el límite máximo permitido de {settings.MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB."
                        )
                    hasher.update(chunk)
                    await f_out.write(chunk)

            sha256_hash = hasher.hexdigest()

            # Estructura de almacenamiento: storage/ab/cd/hash_completo
            sub_dir = os.path.join(self.base_path, sha256_hash[:2], sha256_hash[2:4])
            os.makedirs(sub_dir, exist_ok=True)
            final_filepath = os.path.join(sub_dir, sha256_hash)
            relative_path = os.path.join(sha256_hash[:2], sha256_hash[2:4], sha256_hash).replace("\\", "/")

            if os.path.exists(final_filepath):
                # Deduplicación física: el contenido idéntico ya existe en disco
                if os.path.exists(temp_filepath):
                    os.remove(temp_filepath)
            else:
                shutil.move(temp_filepath, final_filepath)

            return sha256_hash, relative_path, total_bytes

        except Exception:
            if os.path.exists(temp_filepath):
                os.remove(temp_filepath)
            raise

    async def get_file_stream(self, relative_storage_path: str) -> AsyncGenerator[bytes, None]:
        """Generador asíncrono para transmisión en streaming de descarga."""
        full_path = os.path.join(self.base_path, relative_storage_path)
        if not os.path.exists(full_path):
            raise AppException(status_code=404, codigo="BINARIO_NO_ENCONTRADO", mensaje="El archivo físico no existe en el servidor.")

        async with aiofiles.open(full_path, "rb") as f_in:
            while True:
                chunk = await f_in.read(self.CHUNK_SIZE)
                if not chunk:
                    break
                yield chunk


storage_service = StorageService()
