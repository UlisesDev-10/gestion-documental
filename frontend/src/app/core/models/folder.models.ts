/**
 * Modelos de carpetas para navegación jerárquica.
 */

export interface Folder {
  id: string;
  nombre: string;
  carpeta_padre_id: string | null;
  creado_por: string;
  en_papelera: boolean;
  eliminado_en: string | null;
  created_at: string;
  updated_at: string;
  subcarpetas_count?: number;
  archivos_count?: number;
}

export interface CreateFolderRequest {
  nombre: string;
  carpeta_padre_id?: string | null;
}

export interface RenameFolderRequest {
  nuevo_nombre: string;
}

export interface MoveFolderRequest {
  nueva_carpeta_padre_id: string | null;
}
