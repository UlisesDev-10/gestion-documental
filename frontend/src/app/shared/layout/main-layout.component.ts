import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { TagModule } from 'primeng/tag';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-main-layout',
  standalone: true,
  imports: [CommonModule, RouterModule, ButtonModule, TagModule],
  template: `
    <div class="layout-wrapper flex flex-column h-screen">
      <!-- Barra superior accesible -->
      <header class="topbar flex justify-content-between align-items-center px-4 py-2 surface-card border-bottom-1 surface-border shadow-1">
        <div class="flex align-items-center gap-3">
          <i class="pi pi-folder-open text-primary text-2xl" aria-hidden="true"></i>
          <span class="font-bold text-xl text-900">Gestión Documental</span>
        </div>

        <div class="flex align-items-center gap-3">
          <div class="text-right hidden sm:block">
            <div class="font-medium text-900">{{ auth.currentUser()?.nombre_completo }}</div>
            <p-tag [value]="auth.currentUser()?.rol || ''" severity="info" class="text-xs"></p-tag>
          </div>
          <button
            pButton
            icon="pi pi-sign-out"
            label="Salir"
            class="p-button-text p-button-secondary"
            aria-label="Cerrar sesión"
            (click)="auth.logout()">
          </button>
        </div>
      </header>

      <!-- Cuerpo con menú lateral y contenido principal -->
      <div class="flex flex-1 overflow-hidden">
        <aside class="sidebar w-16rem surface-card border-right-1 surface-border p-3 flex flex-column gap-2" role="navigation" aria-label="Menú principal">
          <a
            routerLink="/explorer"
            routerLinkActive="surface-100 text-primary font-semibold"
            class="flex align-items-center gap-3 px-3 py-2 text-700 border-round hover:surface-100 no-underline cursor-pointer">
            <i class="pi pi-folder text-lg" aria-hidden="true"></i>
            <span>Mis Documentos</span>
          </a>

          <a
            routerLink="/papelera"
            routerLinkActive="surface-100 text-primary font-semibold"
            class="flex align-items-center gap-3 px-3 py-2 text-700 border-round hover:surface-100 no-underline cursor-pointer">
            <i class="pi pi-trash text-lg" aria-hidden="true"></i>
            <span>Papelera</span>
          </a>

          <!-- Solo visible para Administrador -->
          <ng-container *ngIf="auth.isAdmin()">
            <div class="border-top-1 surface-border my-2"></div>
            <span class="text-xs text-500 uppercase font-semibold px-3">Administración</span>
            <a
              routerLink="/admin"
              routerLinkActive="surface-100 text-primary font-semibold"
              class="flex align-items-center gap-3 px-3 py-2 text-700 border-round hover:surface-100 no-underline cursor-pointer">
              <i class="pi pi-cog text-lg" aria-hidden="true"></i>
              <span>Panel de Control</span>
            </a>
          </ng-container>
        </aside>

        <main class="flex-1 overflow-y-auto p-4 surface-ground" role="main">
          <router-outlet></router-outlet>
        </main>
      </div>
    </div>
  `
})
export class MainLayoutComponent {
  auth = inject(AuthService);
}
