import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { TableModule } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { MessageService } from 'primeng/api';
import { environment } from '../../../environments/environment';
import { FriendlyDatePipe } from '../../shared/pipes/friendly-date.pipe';

@Component({
  selector: 'app-trash',
  standalone: true,
  imports: [CommonModule, TableModule, ButtonModule, FriendlyDatePipe],
  template: `
    <div class="flex flex-column gap-3">
      <div class="flex justify-content-between align-items-center">
        <div>
          <h1 class="text-2xl font-bold text-900 m-0">Papelera de Reciclaje</h1>
          <p class="text-secondary text-sm m-0">Los documentos eliminados permanecen aquí y pueden ser recuperados.</p>
        </div>
      </div>

      <div class="surface-card border-round border-1 surface-border shadow-1">
        <p-table [value]="items" [loading]="loading">
          <ng-template pTemplate="header">
            <tr>
              <th scope="col">Tipo</th>
              <th scope="col">Nombre</th>
              <th scope="col">Fecha de Eliminación</th>
              <th scope="col" class="text-right">Acción</th>
            </tr>
          </ng-template>

          <ng-template pTemplate="body" let-item>
            <tr>
              <td>
                <i class="pi mr-2" [ngClass]="item.tipo === 'carpeta' ? 'pi-folder text-yellow-600' : 'pi-file text-blue-600'"></i>
                <span class="capitalize">{{ item.tipo }}</span>
              </td>
              <td class="font-bold text-900">{{ item.nombre }}</td>
              <td>{{ item.eliminado_en | friendlyDate }}</td>
              <td class="text-right">
                <button
                  pButton
                  icon="pi pi-replay"
                  label="Recuperar"
                  class="p-button-outlined p-button-sm"
                  (click)="restore(item)">
                </button>
              </td>
            </tr>
          </ng-template>

          <ng-template pTemplate="emptymessage">
            <tr>
              <td colspan="4" class="text-center py-5 text-500">
                <i class="pi pi-trash text-4xl mb-2" aria-hidden="true"></i>
                <p class="m-0">La papelera está vacía.</p>
              </td>
            </tr>
          </ng-template>
        </p-table>
      </div>
    </div>
  `
})
export class TrashComponent implements OnInit {
  private http = inject(HttpClient);
  private messageService = inject(MessageService);
  private readonly apiUrl = environment.apiUrl;

  items: any[] = [];
  loading = false;

  ngOnInit(): void {
    this.loadTrash();
  }

  loadTrash(): void {
    this.loading = true;
    this.http.get<any>(`${this.apiUrl}/papelera`).subscribe({
      next: res => {
        this.items = res.elementos;
        this.loading = false;
      },
      error: () => (this.loading = false)
    });
  }

  restore(item: any): void {
    const endpoint = item.tipo === 'archivo'
      ? `${this.apiUrl}/papelera/archivos/${item.id}/restaurar`
      : `${this.apiUrl}/papelera/carpetas/${item.id}/restaurar`;

    this.http.post(endpoint, {}).subscribe({
      next: () => {
        this.messageService.add({ severity: 'success', summary: 'Recuperado', detail: `Se recuperó "${item.nombre}" correctamente.` });
        this.loadTrash();
      }
    });
  }
}
