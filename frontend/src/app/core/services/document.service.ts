import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent, HttpRequest } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Folder, CreateFolderRequest, RenameFolderRequest, MoveFolderRequest } from '../models/folder.models';
import { FileItem, VersionInfo, RestoreVersionRequest } from '../models/file.models';

@Injectable({ providedIn: 'root' })
export class DocumentService {
  private readonly apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  // --- Carpetas ---
  getFolders(carpetaPadreId?: string | null): Observable<Folder[]> {
    const url = carpetaPadreId
      ? `${this.apiUrl}/carpetas?carpeta_padre_id=${carpetaPadreId}`
      : `${this.apiUrl}/carpetas`;
    return this.http.get<Folder[]>(url);
  }

  createFolder(req: CreateFolderRequest): Observable<Folder> {
    return this.http.post<Folder>(`${this.apiUrl}/carpetas`, req);
  }

  renameFolder(id: string, req: RenameFolderRequest): Observable<Folder> {
    return this.http.patch<Folder>(`${this.apiUrl}/carpetas/${id}/renombrar`, req);
  }

  moveFolder(id: string, req: MoveFolderRequest): Observable<Folder> {
    return this.http.patch<Folder>(`${this.apiUrl}/carpetas/${id}/mover`, req);
  }

  deleteFolder(id: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/carpetas/${id}`);
  }

  // --- Archivos ---
  getFilesInFolder(carpetaId: string): Observable<FileItem[]> {
    return this.http.get<FileItem[]>(`${this.apiUrl}/archivos?carpeta_id=${carpetaId}`);
  }

  getFileDetails(id: string): Observable<FileItem> {
    return this.http.get<FileItem>(`${this.apiUrl}/archivos/${id}`);
  }

  uploadFileWithProgress(carpetaId: string, file: File, comentario: string): Observable<HttpEvent<any>> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('carpeta_id', carpetaId);
    formData.append('comentario', comentario);

    const req = new HttpRequest('POST', `${this.apiUrl}/archivos/subir`, formData, {
      reportProgress: true
    });
    return this.http.request(req);
  }

  uploadNewVersionWithProgress(archivoId: string, file: File, comentario: string): Observable<HttpEvent<any>> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('comentario', comentario);

    const req = new HttpRequest('POST', `${this.apiUrl}/archivos/${archivoId}/versiones`, formData, {
      reportProgress: true
    });
    return this.http.request(req);
  }

  downloadFile(archivoId: string, versionId?: string): Observable<Blob> {
    const url = versionId
      ? `${this.apiUrl}/archivos/${archivoId}/descargar?version_id=${versionId}`
      : `${this.apiUrl}/archivos/${archivoId}/descargar`;
    return this.http.get(url, { responseType: 'blob' });
  }

  getVersionHistory(archivoId: string): Observable<VersionInfo[]> {
    return this.http.get<VersionInfo[]>(`${this.apiUrl}/archivos/${archivoId}/versiones`);
  }

  restoreVersion(archivoId: string, versionId: string, req: RestoreVersionRequest): Observable<VersionInfo> {
    return this.http.post<VersionInfo>(`${this.apiUrl}/archivos/${archivoId}/versiones/${versionId}/restaurar`, req);
  }

  deleteFile(archivoId: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/archivos/${archivoId}`);
  }
}
