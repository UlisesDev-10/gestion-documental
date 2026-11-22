import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { User } from '../models/auth.models';
import { PaginatedAuditResponse } from '../models/audit.models';

@Injectable({ providedIn: 'root' })
export class AdminService {
  private readonly apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getUsers(pagina: number = 1, limite: number = 20): Observable<any> {
    return this.http.get(`${this.apiUrl}/usuarios?pagina=${pagina}&limite=${limite}`);
  }

  createUser(userData: Partial<User> & { password?: string }): Observable<User> {
    return this.http.post<User>(`${this.apiUrl}/usuarios`, userData);
  }

  updateUser(id: string, userData: Partial<User>): Observable<User> {
    return this.http.patch<User>(`${this.apiUrl}/usuarios/${id}`, userData);
  }

  deactivateUser(id: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/usuarios/${id}`);
  }

  getAuditLogs(filtros: any = {}): Observable<PaginatedAuditResponse> {
    let params = new HttpParams();
    Object.keys(filtros).forEach(key => {
      if (filtros[key]) params = params.set(key, filtros[key]);
    });
    return this.http.get<PaginatedAuditResponse>(`${this.apiUrl}/bitacora`, { params });
  }
}
