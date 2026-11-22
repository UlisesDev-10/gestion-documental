import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { CardModule } from 'primeng/card';
import { InputTextModule } from 'primeng/inputtext';
import { ButtonModule } from 'primeng/button';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule, CardModule, InputTextModule, ButtonModule],
  template: `
    <div class="flex align-items-center justify-content-center min-h-screen surface-ground p-4">
      <p-card class="w-full max-w-28rem shadow-3 border-round-xl">
        <ng-template pTemplate="header">
          <div class="text-center pt-5 pb-2">
            <i class="pi pi-file-o text-primary text-5xl mb-2" aria-hidden="true"></i>
            <h1 class="text-2xl font-bold text-900 m-0">Plataforma Documental</h1>
            <p class="text-secondary text-sm mt-1">Ingresa tu correo y contraseña para entrar</p>
          </div>
        </ng-template>

        <form (ngSubmit)="onLogin()" class="flex flex-column gap-3">
          <div class="flex flex-column gap-1">
            <label for="email" class="font-medium text-800">Correo Electrónico</label>
            <input
              id="email"
              type="email"
              pInputText
              [(ngModel)]="email"
              name="email"
              placeholder="ejemplo@empresa.com"
              required
              class="w-full"
              aria-required="true" />
          </div>

          <div class="flex flex-column gap-1">
            <label for="password" class="font-medium text-800">Contraseña</label>
            <input
              id="password"
              type="password"
              pInputText
              [(ngModel)]="password"
              name="password"
              placeholder="Tu contraseña de acceso"
              required
              class="w-full"
              aria-required="true" />
          </div>

          <button
            pButton
            type="submit"
            label="Iniciar Sesión"
            icon="pi pi-sign-in"
            [loading]="loading"
            class="w-full mt-3 p-button-primary">
          </button>
        </form>
      </p-card>
    </div>
  `
})
export class LoginComponent {
  email = '';
  password = '';
  loading = false;

  private auth = inject(AuthService);
  private router = inject(Router);

  onLogin(): void {
    if (!this.email || !this.password) return;
    this.loading = true;
    this.auth.login({ email: this.email, password: this.password }).subscribe({
      next: () => {
        this.loading = false;
        this.router.navigate(['/explorer']);
      },
      error: () => {
        this.loading = false;
      }
    });
  }
}
