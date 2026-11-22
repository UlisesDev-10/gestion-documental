/**
 * Modelos de archivos, versiones inmutables y bloqueos concurrentes.
 */

export interface VersionInfo {
  id: string;
  archivo_id: string;
  numero_version: number;
  autor_id: string;
  autor_nombre?: string;
  comentario: string;
  tamano_bytes: number;
  sha256_hash: string;
  mime_type: string;
  created_at: string;
  es_vigente?: boolean;
}

export interface FileItem {
  id: string;
  carpeta_id: string;
  nombre: string;
  version_vigente_id: string | null;
  version_vigente?: VersionInfo | null;
  bloqueado_por?: {
    id: string;
    nombre_completo: string;
  } | null;
  bloqueado_en?: string | null;
  bloqueo_expira_en?: string | null;
  en_papelera: boolean;
  eliminado_en?: string | null;
  created_at: string;
  updated_at: string;
}

export interface LockResponse {
  archivo_id: string;
  bloqueado: boolean;
  bloqueado_por?: {
    id: string;
    nombre_completo: string;
  };
  bloqueado_en?: string;
  bloqueo_expira_en?: string;
}

export interface RestoreVersionRequest {
  comentario: string;
}
