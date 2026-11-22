import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { HttpEventType } from '@angular/common/http';
import { TableModule } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { DialogModule } from 'primeng/dialog';
import { ProgressBarModule } from 'primeng/progressbar';
import { TagModule } from 'primeng/tag';
import { MessageService, ConfirmationService } from 'primeng/api';

import { DocumentService } from '../../core/services/document.service';
import { AuthService } from '../../core/services/auth.service';
import { Folder } from '../../core/models/folder.models';
import { FileItem } from '../../core/models/file.models';
import { FileSizePipe } from '../../shared/pipes/file-size.pipe';
import { FriendlyDatePipe } from '../../shared/pipes/friendly-date.pipe';

@Component({
  selector: 'app-explorer',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    TableModule,
    ButtonModule,
    InputTextModule,
    DialogModule,
    ProgressBarModule,
    TagModule,
    FileSizePipe,
    FriendlyDatePipe
  ],
  template: `
    <div class="flex flex-column gap-3">
      <!-- Encabezado con Migas de Pan y Acciones Principales -->
      <div class="flex flex-wrap justify-content-between align-items-center gap-3">
        <nav aria-label="Ruta de carpetas" class="flex align-items-center gap-2">
          <button pButton icon="pi pi-home" class="p-button-text p-button-sm" (click)="navigateToRoot()"></button>
          <span *ngFor="let crumb of breadcrumbs; let last = last" class="flex align-items-center gap-2">
            <i class="pi pi-chevron-right text-400 text-xs" aria-hidden="true"></i>
            <button
              pButton
              [label]="crumb.nombre"
              class="p-button-text p-button-sm font-medium"
              [disabled]="last"
              (click)="navigateToFolder(crumb)">
            </button>
          </span>
        </nav>

        <div class="flex gap-2">
          <!-- Alternar vista Lista / Cuadrícula -->
          <button
            pButton
            [icon]="viewMode === 'list' ? 'pi pi-th-large' : 'pi pi-list'"
            [label]="viewMode === 'list' ? 'Vista Cuadrícula' : 'Vista Lista'"
            class="p-button-outlined p-button-secondary"
            (click)="toggleViewMode()">
          </button>

          <!-- Acciones de edición (solo Editor y Administrador) -->
          <ng-container *ngIf="auth.isEditor()">
            <button
              pButton
              icon="pi pi-folder-plus"
              label="Nueva Carpeta"
              class="p-button-outlined"
              (click)="showCreateFolderModal = true">
            </button>
            <button
              pButton
              icon="pi pi-upload"
              label="Subir Archivo"
              class="p-button-primary"
              (click)="showUploadModal = true">
            </button>
          </ng-container>
        </div>
      </div>

      <!-- Barra de Filtros y Búsqueda -->
      <div class="surface-card p-3 border-round border-1 surface-border flex flex-wrap gap-3 align-items-center">
        <span class="p-input-icon-left flex-1 min-w-16rem">
          <i class="pi pi-search"></i>
          <input
            pInputText
            type="text"
            [(ngModel)]="searchTerm"
            placeholder="Buscar por nombre de documento o carpeta..."
            class="w-full" />
        </span>
      </div>

      <!-- Vista 1: Lista en Tabla Accesible -->
      <div *ngIf="viewMode === 'list'" class="surface-card border-round border-1 surface-border shadow-1">
        <p-table [value]="filteredFiles" [loading]="loading" responsiveLayout="stack" breakpoint="768px">
          <ng-template pTemplate="header">
            <tr>
              <th scope="col">Nombre</th>
              <th scope="col">Versión Actual</th>
              <th scope="col">Tamaño</th>
              <th scope="col">Estado de Edición</th>
              <th scope="col">Última Modificación</th>
              <th scope="col" class="text-right">Acciones</th>
            </tr>
          </ng-template>

          <ng-template pTemplate="body" let-file>
            <tr>
              <td>
                <a [routerLink]="['/documentos', file.id]" class="font-medium text-primary no-underline hover:underline flex align-items-center gap-2">
                  <i class="pi pi-file text-lg" aria-hidden="true"></i>
                  <span>{{ file.nombre }}</span>
                </a>
              </td>
              <td>
                <span class="font-semibold text-700">Versión {{ file.version_vigente?.numero_version || 1 }}</span>
              </td>
              <td>{{ file.version_vigente?.tamano_bytes | fileSize }}</td>
              <td>
                <p-tag
                  *ngIf="file.bloqueado"
                  severity="warning"
                  icon="pi pi-lock"
                  [value]="'En edición por ' + (file.bloqueado_por_nombre || 'otro usuario')">
                </p-tag>
                <p-tag *ngIf="!file.bloqueado" severity="success" icon="pi pi-check" value="Libre para editar"></p-tag>
              </td>
              <td>{{ file.updated_at | friendlyDate }}</td>
              <td class="text-right">
                <button
                  pButton
                  icon="pi pi-download"
                  class="p-button-text p-button-sm"
                  aria-label="Descargar archivo"
                  (click)="download(file)">
                </button>
                <button
                  *ngIf="auth.isEditor()"
                  pButton
                  icon="pi pi-trash"
                  class="p-button-text p-button-danger p-button-sm"
                  aria-label="Mover a papelera"
                  (click)="confirmDelete(file)">
                </button>
              </td>
            </tr>
          </ng-template>

          <ng-template pTemplate="emptymessage">
            <tr>
              <td colspan="6" class="text-center py-5 text-500">
                <i class="pi pi-folder-open text-4xl mb-2" aria-hidden="true"></i>
                <p class="m-0">Esta carpeta no contiene archivos en este momento.</p>
              </td>
            </tr>
          </ng-template>
        </p-table>
      </div>

      <!-- Vista 2: Cuadrícula de Tarjetas Visuales -->
      <div *ngIf="viewMode === 'grid'" class="grid">
        <!-- Carpetas primero -->
        <div *ngFor="let folder of folders" class="col-12 sm:col-6 md:col-4 lg:col-3">
          <div
            (click)="navigateToFolder(folder)"
            class="surface-card p-3 border-round border-1 surface-border shadow-1 hover:surface-100 cursor-pointer flex align-items-center gap-3">
            <i class="pi pi-folder text-primary text-3xl" aria-hidden="true"></i>
            <div class="overflow-hidden">
              <span class="font-bold text-900 block white-space-nowrap text-overflow-ellipsis">{{ folder.nombre }}</span>
              <span class="text-xs text-500">Carpeta</span>
            </div>
          </div>
        </div>

        <!-- Archivos -->
        <div *ngFor="let file of filteredFiles" class="col-12 sm:col-6 md:col-4 lg:col-3">
          <div class="surface-card p-3 border-round border-1 surface-border shadow-1 flex flex-column justify-content-between h-full">
            <div>
              <div class="flex justify-content-between align-items-start gap-2 mb-2">
                <i class="pi pi-file text-2xl text-600" aria-hidden="true"></i>
                <p-tag *ngIf="file.bloqueado" severity="warning" value="En edición" class="text-xs"></p-tag>
              </div>
              <a [routerLink]="['/documentos', file.id]" class="font-bold text-900 block no-underline hover:underline mb-1 text-overflow-ellipsis overflow-hidden">
                {{ file.nombre }}
              </a>
              <span class="text-xs text-500 block">Versión {{ file.version_vigente?.numero_version || 1 }} - {{ file.version_vigente?.tamano_bytes | fileSize }}</span>
            </div>

            <div class="flex justify-content-end gap-1 mt-3 pt-2 border-top-1 surface-border">
              <button pButton icon="pi pi-download" class="p-button-text p-button-sm" (click)="download(file)"></button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal de Subida de Archivos con Drag & Drop y Progreso -->
    <p-dialog
      header="Subir Documento Nuevo"
      [(visible)]="showUploadModal"
      [modal]="true"
      [style]="{width: '520px'}"
      (onHide)="resetUploadForm()">
      <div class="flex flex-column gap-3">
        <!-- Zona Drag & Drop -->
        <div
          class="surface-ground border-2 border-dashed surface-border border-round p-5 text-center cursor-pointer hover:surface-100"
          (click)="fileInput.click()">
          <i class="pi pi-cloud-upload text-4xl text-primary mb-2" aria-hidden="true"></i>
          <p class="font-medium text-900 m-0">Haz clic aquí o arrastra tu archivo</p>
          <span class="text-xs text-500">Archivos permitidos de hasta 500 MB</span>
          <input #fileInput type="file" (change)="onFileSelected($event)" class="hidden" />
        </div>

        <div *ngIf="selectedFile" class="surface-100 p-2 border-round flex justify-content-between align-items-center">
          <span class="font-medium text-sm">{{ selectedFile.name }} ({{ selectedFile.size | fileSize }})</span>
          <button pButton icon="pi pi-times" class="p-button-text p-button-sm p-button-danger" (click)="selectedFile = null"></button>
        </div>

        <div class="flex flex-column gap-1">
          <label for="comentario" class="font-medium text-sm text-800">Comentario del documento (obligatorio)</label>
          <input
            id="comentario"
            pInputText
            [(ngModel)]="uploadComment"
            placeholder="Ejemplo: Versión aprobada por el área contable" />
        </div>

        <div *ngIf="uploadProgress > 0" class="flex flex-column gap-1">
          <span class="text-xs text-secondary font-medium">Subiendo archivo: {{ uploadProgress }}%</span>
          <p-progressBar [value]="uploadProgress"></p-progressBar>
        </div>

        <div class="flex justify-content-end gap-2 mt-2">
          <button pButton label="Cancelar" class="p-button-text" (click)="showUploadModal = false"></button>
          <button
            pButton
            label="Guardar Documento"
            icon="pi pi-check"
            [disabled]="!selectedFile || !uploadComment || isUploading"
            (click)="executeUpload()">
          </button>
        </div>
      </div>
    </p-dialog>

    <!-- Modal Crear Carpeta -->
    <p-dialog header="Crear Nueva Carpeta" [(visible)]="showCreateFolderModal" [modal]="true" [style]="{width: '400px'}">
      <div class="flex flex-column gap-3">
        <div class="flex flex-column gap-1">
          <label for="folderName" class="font-medium text-sm text-800">Nombre de la carpeta</label>
          <input id="folderName" pInputText [(ngModel)]="newFolderName" placeholder="Ejemplo: Facturas 2026" />
        </div>
        <div class="flex justify-content-end gap-2 mt-2">
          <button pButton label="Cancelar" class="p-button-text" (click)="showCreateFolderModal = false"></button>
          <button pButton label="Crear" [disabled]="!newFolderName" (click)="createFolder()"></button>
        </div>
      </div>
    </p-dialog>
  `
})
export class ExplorerComponent implements OnInit {
  documentService = inject(DocumentService);
  auth = inject(AuthService);
  messageService = inject(MessageService);
  confirmService = inject(ConfirmationService);

  currentFolderId: string | null = null;
  breadcrumbs: Folder[] = [];
  folders: Folder[] = [];
  files: FileItem[] = [];
  loading = false;
  viewMode: 'list' | 'grid' = 'list';
  searchTerm = '';

  // Modales
  showUploadModal = false;
  showCreateFolderModal = false;
  selectedFile: File | null = null;
  uploadComment = '';
  uploadProgress = 0;
  isUploading = false;
  newFolderName = '';

  ngOnInit(): void {
    this.loadContent();
  }

  get filteredFiles(): FileItem[] {
    if (!this.searchTerm) return this.files;
    return this.files.filter(f => f.nombre.toLowerCase().includes(this.searchTerm.toLowerCase()));
  }

  loadContent(): void {
    this.loading = true;
    this.documentService.getFolders(this.currentFolderId).subscribe({
      next: folders => {
        this.folders = folders;
        if (this.currentFolderId) {
          this.documentService.getFilesInFolder(this.currentFolderId).subscribe({
            next: files => {
              this.files = files;
              this.loading = false;
            },
            error: () => (this.loading = false)
          });
        } else {
          this.files = [];
          this.loading = false;
        }
      },
      error: () => (this.loading = false)
    });
  }

  navigateToFolder(folder: Folder): void {
    this.currentFolderId = folder.id;
    this.breadcrumbs.push(folder);
    this.loadContent();
  }

  navigateToRoot(): void {
    this.currentFolderId = null;
    this.breadcrumbs = [];
    this.loadContent();
  }

  toggleViewMode(): void {
    this.viewMode = this.viewMode === 'list' ? 'grid' : 'list';
  }

  onFileSelected(event: any): void {
    if (event.target.files && event.target.files.length > 0) {
      this.selectedFile = event.target.files[0];
    }
  }

  executeUpload(): void {
    if (!this.selectedFile || !this.currentFolderId || !this.uploadComment) return;
    this.isUploading = true;
    this.uploadProgress = 0;

    this.documentService.uploadFileWithProgress(this.currentFolderId, this.selectedFile, this.uploadComment).subscribe({
      next: (event: any) => {
        if (event.type === HttpEventType.UploadProgress && event.total) {
          this.uploadProgress = Math.round((100 * event.loaded) / event.total);
        } else if (event.type === HttpEventType.Response) {
          this.messageService.add({ severity: 'success', summary: 'Completado', detail: 'Archivo guardado correctamente.' });
          this.showUploadModal = false;
          this.resetUploadForm();
          this.loadContent();
        }
      },
      error: () => {
        this.isUploading = false;
      }
    });
  }

  createFolder(): void {
    if (!this.newFolderName) return;
    this.documentService.createFolder({ nombre: this.newFolderName, carpeta_padre_id: this.currentFolderId }).subscribe({
      next: () => {
        this.messageService.add({ severity: 'success', summary: 'Creada', detail: 'Carpeta creada exitosamente.' });
        this.showCreateFolderModal = false;
        this.newFolderName = '';
        this.loadContent();
      }
    });
  }

  download(file: FileItem): void {
    this.documentService.downloadFile(file.id).subscribe({
      next: blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = file.nombre;
        a.click();
        window.URL.revokeObjectURL(url);
      }
    });
  }

  confirmDelete(file: FileItem): void {
    this.confirmService.confirm({
      message: `¿Deseas enviar "${file.nombre}" a la papelera? Podrás recuperarlo después si lo necesitas.`,
      header: 'Confirmar eliminación',
      icon: 'pi pi-exclamation-triangle',
      acceptLabel: 'Enviar a papelera',
      rejectLabel: 'Cancelar',
      accept: () => {
        this.documentService.deleteFile(file.id).subscribe({
          next: () => {
            this.messageService.add({ severity: 'info', summary: 'Eliminado', detail: 'Documento enviado a la papelera.' });
            this.loadContent();
          }
        });
      }
    });
  }

  resetUploadForm(): void {
    this.selectedFile = null;
    this.uploadComment = '';
    this.uploadProgress = 0;
    this.isUploading = false;
  }
}
