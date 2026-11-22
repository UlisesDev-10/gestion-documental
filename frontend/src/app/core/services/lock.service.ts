import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { LockResponse } from '../models/file.models';

@Injectable({ providedIn: 'root' })
export class LockService {
  private readonly apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  lockFile(archivoId: string, duracionMinutos: number = 30): Observable<LockResponse> {
    return this.http.post<LockResponse>(`${this.apiUrl}/archivos/${archivoId}/bloquear`, {
      duracion_minutos: duracionMinutos
    });
  }

  unlockFile(archivoId: string): Observable<LockResponse> {
    return this.http.post<LockResponse>(`${this.apiUrl}/archivos/${archivoId}/desbloquear`, {});
  }

  forceUnlockFile(archivoId: string): Observable<LockResponse> {
    return this.http.post<LockResponse>(`${this.apiUrl}/archivos/${archivoId}/forzar-desbloqueo`, {});
  }
}
