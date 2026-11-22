import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TableModule } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { TagModule } from 'primeng/tag';
import { DialogModule } from 'primeng/dialog';
import { InputTextModule } from 'primeng/inputtext';
import { DropdownModule } from 'primeng/dropdown';
import { MessageService } from 'primeng/api';

import { AdminService } from '../../core/services/admin.service';
import { User, UserRole } from '../../core/models/auth.models';
import { AuditEntry } from '../../core/models/audit.models';
import { FriendlyDatePipe } from '../../shared/pipes/friendly-date.pipe';

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    TableModule,
    ButtonModule,
    TagModule,
    DialogModule,
    InputTextModule,
    DropdownModule,
    FriendlyDatePipe
  ],
  template: `
    <div class="flex flex-column gap-4">
      <div>
        <h1 class="text-2xl font-bold text-900 m-0">Panel de Control del Sistema</h1>
        <p class="text-secondary text-sm m-0">Administración de accesos de usuarios y registro de auditoría.</p>
      </div>

      <!-- Pestañas de navegación interna -->
      <div class="flex gap-2 border-bottom-1 surface-border pb-2">
        <button
          pButton
          label="Usuarios y Roles"
          icon="pi pi-users"
          [class.p-button-outlined]="activeTab !== 'users'"
          (click)="activeTab = 'users'">
        </button>
        <button
          pButton
          label="Bitácora de Seguridad"
          icon="pi pi-shield"
          [class.p-button-outlined]="activeTab !== 'audit'"
          (click)="activeTab = 'audit'; loadAuditLogs()">
        </button>
      </div>

      <!-- Pestaña 1: Usuarios -->
      <div *ngIf="activeTab === 'users'" class="surface-card p-3 border-round border-1 surface-border shadow-1">
        <div class="flex justify-content-between align-items-center mb-3">
          <h2 class="text-lg font-bold text-900 m-0">Cuentas Registradas</h2>
          <button pButton icon="pi pi-user-plus" label="Registrar Usuario" (click)="showCreateUserModal = true"></button>
        </div>

        <p-table [value]="users" [loading]="loadingUsers">
          <ng-template pTemplate="header">
            <tr>
              <th scope="col">Nombre</th>
              <th scope="col">Correo</th>
              <th scope="col">Rol Asignado</th>
              <th scope="col">Estado</th>
              <th scope="col" class="text-right">Acciones</th>
            </tr>
          </ng-template>

          <ng-template pTemplate="body" let-u>
            <tr>
              <td class="font-medium text-900">{{ u.nombre_completo }}</td>
              <td>{{ u.email }}</td>
              <td>
                <p-tag [value]="u.rol" [severity]="getRoleSeverity(u.rol)"></p-tag>
              </td>
              <td>
                <p-tag [value]="u.activo ? 'Activo' : 'Desactivado'" [severity]="u.activo ? 'success' : 'danger'"></p-tag>
              </td>
              <td class="text-right">
                <button
                  *ngIf="u.activo"
                  pButton
                  icon="pi pi-ban"
                  class="p-button-text p-button-danger p-button-sm"
                  aria-label="Desactivar usuario"
                  (click)="deactivateUser(u)">
                </button>
              </td>
            </tr>
          </ng-template>
        </p-table>
      </div>

      <!-- Pestaña 2: Bitácora -->
      <div *ngIf="activeTab === 'audit'" class="surface-card p-3 border-round border-1 surface-border shadow-1">
        <h2 class="text-lg font-bold text-900 mb-3">Historial de Acciones Relevantes (Inmutable)</h2>

        <p-table [value]="auditLogs" [loading]="loadingAudit">
          <ng-template pTemplate="header">
            <tr>
              <th scope="col">Fecha y Hora</th>
              <th scope="col">Usuario</th>
              <th scope="col">Acción Realizada</th>
              <th scope="col">Objeto</th>
              <th scope="col">Dirección IP</th>
            </tr>
          </ng-template>

          <ng-template pTemplate="body" let-log>
            <tr>
              <td>{{ log.created_at | friendlyDate }}</td>
              <td class="font-medium">{{ log.usuario_nombre || 'Sistema / Invitado' }}</td>
              <td>
                <p-tag [value]="log.accion" severity="info"></p-tag>
              </td>
              <td>{{ log.entidad }}</td>
              <td class="text-500 font-mono text-xs">{{ log.ip_address || '-' }}</td>
            </tr>
          </ng-template>
        </p-table>
      </div>
    </div>

    <!-- Modal Crear Usuario -->
    <p-dialog header="Dar de Alta Usuario" [(visible)]="showCreateUserModal" [modal]="true" [style]="{width: '450px'}">
      <div class="flex flex-column gap-3">
        <div class="flex flex-column gap-1">
          <label for="newFullName" class="font-medium text-sm text-800">Nombre Completo</label>
          <input id="newFullName" pInputText [(ngModel)]="newFullName" placeholder="Nombre y Apellidos" />
        </div>

        <div class="flex flex-column gap-1">
          <label for="newEmail" class="font-medium text-sm text-800">Correo Electrónico</label>
          <input id="newEmail" pInputText type="email" [(ngModel)]="newEmail" placeholder="usuario@empresa.com" />
        </div>

        <div class="flex flex-column gap-1">
          <label for="newPassword" class="font-medium text-sm text-800">Contraseña Inicial</label>
          <input id="newPassword" pInputText type="password" [(ngModel)]="newPassword" placeholder="Al menos 8 caracteres" />
        </div>

        <div class="flex flex-column gap-1">
          <label class="font-medium text-sm text-800">Rol en la Plataforma</label>
          <p-dropdown [options]="rolesList" [(ngModel)]="selectedRole" placeholder="Selecciona un rol"></p-dropdown>
        </div>

        <div class="flex justify-content-end gap-2 mt-2">
          <button pButton label="Cancelar" class="p-button-text" (click)="showCreateUserModal = false"></button>
          <button pButton label="Guardar Usuario" [disabled]="!newFullName || !newEmail || !newPassword" (click)="saveUser()"></button>
        </div>
      </div>
    </p-dialog>
  `
})
export class AdminComponent implements OnInit {
  private adminService = inject(AdminService);
  private messageService = inject(MessageService);

  activeTab: 'users' | 'audit' = 'users';
  users: User[] = [];
  auditLogs: AuditEntry[] = [];
  loadingUsers = false;
  loadingAudit = false;

  showCreateUserModal = false;
  newFullName = '';
  newEmail = '';
  newPassword = '';
  selectedRole: UserRole = 'lector';

  rolesList = [
    { label: 'Lector (Solo lectura y descarga)', value: 'lector' },
    { label: 'Revisor (Revisión y comentarios)', value: 'revisor' },
    { label: 'Editor (Subir y bloquear archivos)', value: 'editor' },
    { label: 'Administrador (Control total)', value: 'administrador' }
  ];

  ngOnInit(): void {
    this.loadUsers();
  }

  loadUsers(): void {
    this.loadingUsers = true;
    this.adminService.getUsers().subscribe({
      next: res => {
        this.users = res.items;
        this.loadingUsers = false;
      },
      error: () => (this.loadingUsers = false)
    });
  }

  loadAuditLogs(): void {
    this.loadingAudit = true;
    this.adminService.getAuditLogs().subscribe({
      next: res => {
        this.auditLogs = res.registros;
        this.loadingAudit = false;
      },
      error: () => (this.loadingAudit = false)
    });
  }

  saveUser(): void {
    this.adminService.createUser({
      nombre_completo: this.newFullName,
      email: this.newEmail,
      password: this.newPassword,
      rol: this.selectedRole
    }).subscribe({
      next: () => {
        this.messageService.add({ severity: 'success', summary: 'Registrado', detail: 'Usuario creado exitosamente.' });
        this.showCreateUserModal = false;
        this.newFullName = '';
        this.newEmail = '';
        this.newPassword = '';
        this.loadUsers();
      }
    });
  }

  deactivateUser(u: User): void {
    this.adminService.deactivateUser(u.id).subscribe({
      next: () => {
        this.messageService.add({ severity: 'info', summary: 'Desactivado', detail: `La cuenta de ${u.nombre_completo} fue desactivada.` });
        this.loadUsers();
      }
    });
  }

  getRoleSeverity(rol: string): 'success' | 'info' | 'warning' | 'danger' | undefined {
    switch (rol) {
      case 'administrador': return 'danger';
      case 'editor': return 'warning';
      case 'revisor': return 'info';
      default: return undefined;
    }
  }
}
