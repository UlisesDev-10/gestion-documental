/**
 * Modelos de bitácora de auditoría inmutable.
 */

export interface AuditEntry {
  id: number;
  usuario_id: string | null;
  usuario?: {
    id: string;
    nombre_completo: string;
    email: string;
  };
  accion: string;
  entidad: string;
  entidad_id: string | null;
  detalle: Record<string, any>;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
}

export interface PaginatedAuditResponse {
  total: number;
  pagina: number;
  registros: AuditEntry[];
}
