/**
/**
 * Modelos de autenticación y roles de usuario.
 */

export type UserRole = 'administrador' | 'editor' | 'revisor' | 'lector';

export interface User {
  id: string;
  email: string;
  nombre_completo: string;
  rol: UserRole;
  activo: boolean;
  created_at: string;
  updated_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  usuario: User;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}
