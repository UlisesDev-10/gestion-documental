import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { environment } from '../../../environments/environment';
import { LoginRequest, LoginResponse, User, UserRole } from '../models/auth.models';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly baseUrl = `${environment.apiUrl}/auth`;
  readonly currentUser = signal<User | null>(this.getStoredUser());

  constructor(private http: HttpClient) {}

  login(credentials: LoginRequest): Observable<LoginResponse> {
    return this.http.post<LoginResponse>(`${this.baseUrl}/login`, credentials).pipe(
      tap(res => {
        localStorage.setItem('access_token', res.access_token);
        localStorage.setItem('refresh_token', res.refresh_token);
        localStorage.setItem('user_info', JSON.stringify(res.usuario));
        this.currentUser.set(res.usuario);
      })
    );
  }

  logout(): void {
    this.http.post(`${this.baseUrl}/logout`, {}).subscribe({
      next: () => this.clearSession(),
      error: () => this.clearSession()
    });
  }

  clearSession(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user_info');
    this.currentUser.set(null);
  }

  getAccessToken(): string | null {
    return localStorage.getItem('access_token');
  }

  isAuthenticated(): boolean {
    return !!this.getAccessToken();
  }

  hasRole(allowedRoles: UserRole[]): boolean {
    const user = this.currentUser();
    return user ? allowedRoles.includes(user.rol) : false;
  }

  isAdmin(): boolean {
    return this.hasRole(['administrador']);
  }

  isEditor(): boolean {
    return this.hasRole(['editor', 'administrador']);
  }

  private getStoredUser(): User | null {
    const raw = localStorage.getItem('user_info');
    return raw ? JSON.parse(raw) : null;
  }
}
