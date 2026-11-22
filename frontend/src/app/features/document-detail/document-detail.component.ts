import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { HttpEventType } from '@angular/common/http';
import { TimelineModule } from 'primeng/timeline';
import { ButtonModule } from 'primeng/button';
import { TagModule } from 'primeng/tag';
import { DialogModule } from 'primeng/dialog';
import { InputTextModule } from 'primeng/inputtext';
import { ProgressBarModule } from 'primeng/progressbar';
import { MessageService, ConfirmationService } from 'primeng/api';

import { DocumentService } from '../../core/services/document.service';
import { LockService } from '../../core/services/lock.service';
import { AuthService } from '../../core/services/auth.service';
import { FileItem, VersionInfo } from '../../core/models/file.models';
import { FileSizePipe } from '../../shared/pipes/file-size.pipe';
import { FriendlyDatePipe } from '../../shared/pipes/friendly-date.pipe';

@Component({
  selector: 'app-document-detail',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    TimelineModule,
    ButtonModule,
    TagModule,
    DialogModule,
    InputTextModule,
    ProgressBarModule,
    FileSizePipe,
    FriendlyDatePipe
  ],
  template: `
    <div class="flex flex-column gap-4" *ngIf="file">
      <!-- Barra superior con regreso y título -->
      <div class="flex justify-content-between align-items-center flex-wrap gap-2">
        <div class="flex align-items-center gap-3">
          <button pButton icon="pi pi-arrow-left" class="p-button-outlined p-button-sm" routerLink="/explorer"></button>
          <div>
            <h1 class="text-2xl font-bold text-900 m-0">{{ file.nombre }}</h1>
            <span class="text-xs text-500">Documento activo</span>
          </div>
        </div>

        <div class="flex gap-2">
          <button pButton icon="pi pi-download" label="Descargar Documento" (click)="downloadCurrent()"></button>
        </div>
      </div>

      <!-- Tarjeta de Estado del Archivo y Bloqueo Concurrente -->
      <div class="surface-card p-4 border-round border-1 surface-border shadow-1 flex flex-wrap justify-content-between align-items-center gap-3">
        <div class="flex align-items-center gap-3">
          <i class="pi text-3xl" [ngClass]="file.bloqueado ? 'pi-lock text-orange-500' : 'pi-check-circle text-green-500'" aria-hidden="true"></i>
          <div>
            <div class="font-bold text-lg text-900">
              {{ file.bloqueado ? 'Documento en edición' : 'Documento libre para trabajar' }}
            </div>
            <p class="text-secondary text-sm m-0" *ngIf="file.bloqueado">
              Está siendo editado por <strong>{{ file.bloqueado_por_nombre || 'otro usuario' }}</strong> desde las {{ file.bloqueado_en | friendlyDate }}.
            </p>
            <p class="text-secondary text-sm m-0" *ngIf="!file.bloqueado">
              Cualquier persona autorizada puede bloquear este archivo para hacer cambios sin riesgo de sobrescritura.
            </p>
          </div>
        </div>

        <!-- Botones de Acción de Bloqueo -->
        <div class="flex gap-2" *ngIf="auth.isEditor()">
          <button
            *ngIf="!file.bloqueado"
            pButton
            icon="pi pi-lock"
            label="Bloquear para editar"
            class="p-button-warning"
            (click)="lock()">
          </button>
          <button
            *ngIf="file.bloqueado && isMyLock()"
            pButton
            icon="pi pi-lock-open"
            label="Liberar edición"
            class="p-button-secondary"
            (click)="unlock()">
          </button>
          <!-- Forzar liberación para Administradores -->
          <button
            *ngIf="file.bloqueado && !isMyLock() && auth.isAdmin()"
            pButton
            icon="pi pi-exclamation-circle"
            label="Forzar liberación (Admin)"
            class="p-button-danger p-button-outlined"
            (click)="forceUnlock()">
          </button>
          <button
            pButton
            icon="pi pi-upload"
            label="Subir nueva versión"
            class="p-button-primary"
            [disabled]="file.bloqueado && !isMyLock()"
            (click)="showNewVersionModal = true">
          </button>
        </div>
      </div>

      <!-- Sección de Historial de Versiones (PrimeNG Timeline) -->
      <div class="surface-card p-4 border-round border-1 surface-border shadow-1">
        <h2 class="text-xl font-bold text-900 mb-4">Línea de Tiempo del Documento</h2>

        <p-timeline [value]="versions" align="alternate">
          <ng-template pTemplate="marker" let-ver>
            <span class="flex w-2rem h-2rem align-items-center justify-content-center text-white border-circle z-1 shadow-1"
                  [ngClass]="ver.es_vigente ? 'bg-primary' : 'bg-500'">
              <i class="pi" [ngClass]="ver.es_vigente ? 'pi-star' : 'pi-history'"></i>
            </span>
          </ng-template>

          <ng-template pTemplate="content" let-ver>
            <div class="surface-100 p-3 border-round border-1 surface-border mb-3 shadow-1">
              <div class="flex justify-content-between align-items-center mb-2">
                <span class="font-bold text-lg text-900">Versión {{ ver.numero_version }}</span>
                <p-tag *ngIf="ver.es_vigente" severity="success" value="Versión Vigente"></p-tag>
              </div>

              <p class="text-800 font-medium m-0 mb-2">"{{ ver.comentario }}"</p>
              <div class="text-xs text-500 mb-3">
                Guardado por <strong>{{ ver.autor_nombre || 'Usuario' }}</strong> el {{ ver.created_at | friendlyDate }} ({{ ver.tamano_bytes | fileSize }})
              </div>

              <div class="flex gap-2">
                <button
                  pButton
                  icon="pi pi-download"
                  label="Descargar esta versión"
                  class="p-button-text p-button-sm"
                  (click)="downloadSpecificVersion(ver)">
                </button>
                <button
                  *ngIf="!ver.es_vigente && auth.isEditor()"
                  pButton
                  icon="pi pi-replay"
                  label="Restaurar a esta versión"
                  class="p-button-outlined p-button-sm p-button-warning"
                  (click)="confirmRestore(ver)">
                </button>
              </div>
            </div>
          </ng-template>
        </p-timeline>
      </div>
    </div>

    <!-- Modal Subir Nueva Versión -->
    <p-dialog header="Subir Nueva Versión del Documento" [(visible)]="showNewVersionModal" [modal]="true" [style]="{width: '500px'}">
      <div class="flex flex-column gap-3">
        <div
          class="surface-ground border-2 border-dashed surface-border border-round p-4 text-center cursor-pointer hover:surface-100"
          (click)="vInput.click()">
          <i class="pi pi-cloud-upload text-3xl text-primary mb-2"></i>
          <p class="font-medium text-sm m-0">Selecciona el nuevo archivo con tus cambios guardados</p>
          <input #vInput type="file" (change)="onNewVersionFileSelected($event)" class="hidden" />
        </div>

        <div *ngIf="selectedNewVersionFile" class="surface-100 p-2 border-round flex justify-content-between align-items-center">
          <span class="text-sm font-medium">{{ selectedNewVersionFile.name }} ({{ selectedNewVersionFile.size | fileSize }})</span>
        </div>

        <div class="flex flex-column gap-1">
          <label for="comentarioCambio" class="font-medium text-sm text-800">¿Qué cambios hiciste en esta versión? (Obligatorio)</label>
          <input
            id="comentarioCambio"
            pInputText
            [(ngModel)]="newVersionComment"
            placeholder="Ejemplo: Se corrigieron las cifras del mes de octubre" />
        </div>

        <div *ngIf="uploadProgress > 0">
          <p-progressBar [value]="uploadProgress"></p-progressBar>
        </div>

        <div class="flex justify-content-end gap-2 mt-2">
          <button pButton label="Cancelar" class="p-button-text" (click)="showNewVersionModal = false"></button>
          <button
            pButton
            label="Guardar Nueva Versión"
            icon="pi pi-check"
            [disabled]="!selectedNewVersionFile || !newVersionComment || isUploading"
            (click)="executeUploadNewVersion()">
          </button>
        </div>
      </div>
    </p-dialog>
  `
})
export class DocumentDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private docService = inject(DocumentService);
  private lockService = inject(LockService);
  auth = inject(AuthService);
  messageService = inject(MessageService);
  confirmService = inject(ConfirmationService);

  file: FileItem | null = null;
  versions: VersionInfo[] = [];
  showNewVersionModal = false;
  selectedNewVersionFile: File | null = null;
  newVersionComment = '';
  uploadProgress = 0;
  isUploading = false;

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.loadFile(id);
    }
  }

  loadFile(id: string): void {
    this.docService.getFileDetails(id).subscribe(file => {
      this.file = file;
      this.loadVersions(id);
    });
  }

  loadVersions(fileId: string): void {
    this.docService.getVersionHistory(fileId).subscribe(versions => {
      this.versions = versions;
    });
  }

  isMyLock(): boolean {
    const user = this.auth.currentUser();
    return !!(this.file?.bloqueado && this.file.bloqueado_por_id === user?.id);
  }

  lock(): void {
    if (!this.file) return;
    this.lockService.lockFile(this.file.id).subscribe({
      next: () => {
        this.messageService.add({ severity: 'success', summary: 'Bloqueado', detail: 'Archivo bloqueado para tu uso exclusivo.' });
        this.loadFile(this.file!.id);
      }
    });
  }

  unlock(): void {
    if (!this.file) return;
    this.lockService.unlockFile(this.file.id).subscribe({
      next: () => {
        this.messageService.add({ severity: 'info', summary: 'Liberado', detail: 'El archivo ahora está disponible para los demás.' });
        this.loadFile(this.file!.id);
      }
    });
  }

  forceUnlock(): void {
    if (!this.file) return;
    this.lockService.forceUnlockFile(this.file.id).subscribe({
      next: () => {
        this.messageService.add({ severity: 'warn', summary: 'Liberado forzoso', detail: 'Bloqueo liberado por el administrador.' });
        this.loadFile(this.file!.id);
      }
    });
  }

  downloadCurrent(): void {
    if (!this.file) return;
    this.docService.downloadFile(this.file.id).subscribe(blob => this.triggerDownload(blob, this.file!.nombre));
  }

  downloadSpecificVersion(ver: VersionInfo): void {
    if (!this.file) return;
    this.docService.downloadFile(this.file.id, ver.id).subscribe(blob => this.triggerDownload(blob, `v${ver.numero_version}_${this.file!.nombre}`));
  }

  private triggerDownload(blob: Blob, filename: string): void {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    window.URL.revokeObjectURL(url);
  }

  onNewVersionFileSelected(event: any): void {
    if (event.target.files && event.target.files.length > 0) {
      this.selectedNewVersionFile = event.target.files[0];
    }
  }

  executeUploadNewVersion(): void {
    if (!this.file || !this.selectedNewVersionFile || !this.newVersionComment) return;
    this.isUploading = true;
    this.uploadProgress = 0;

    this.docService.uploadNewVersionWithProgress(this.file.id, this.selectedNewVersionFile, this.newVersionComment).subscribe({
      next: (event: any) => {
        if (event.type === HttpEventType.UploadProgress && event.total) {
          this.uploadProgress = Math.round((100 * event.loaded) / event.total);
        } else if (event.type === HttpEventType.Response) {
          this.messageService.add({ severity: 'success', summary: 'Versión guardada', detail: 'Nueva versión subida con éxito.' });
          this.showNewVersionModal = false;
          this.selectedNewVersionFile = null;
          this.newVersionComment = '';
          this.isUploading = false;
          this.loadFile(this.file!.id);
        }
      },
      error: () => (this.isUploading = false)
    });
  }

  confirmRestore(ver: VersionInfo): void {
    if (!this.file) return;
    this.confirmService.confirm({
      message: `¿Deseas restaurar el documento a como estaba en la Versión ${ver.numero_version}? Se creará una versión nueva con ese contenido anterior y ningún cambio se perderá.`,
      header: 'Confirmar restauración',
      icon: 'pi pi-replay',
      acceptLabel: 'Sí, restaurar',
      rejectLabel: 'Cancelar',
      accept: () => {
        const comentario = `Restauración a partir de la versión ${ver.numero_version}`;
        this.docService.restoreVersion(this.file!.id, ver.id, { comentario }).subscribe({
          next: () => {
            this.messageService.add({ severity: 'success', summary: 'Restaurado', detail: 'Se ha creado la nueva versión con el contenido solicitado.' });
            this.loadFile(this.file!.id);
          }
        });
      }
    });
  }
}
