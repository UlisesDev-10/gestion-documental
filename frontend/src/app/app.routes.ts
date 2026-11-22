import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { adminGuard } from './core/guards/admin.guard';
import { MainLayoutComponent } from './shared/layout/main-layout.component';

export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () => import('./features/auth/login.component').then(m => m.LoginComponent)
  },
  {
    path: '',
    component: MainLayoutComponent,
    canActivate: [authGuard],
    children: [
      { path: '', redirectTo: 'explorer', pathMatch: 'full' },
      {
        path: 'explorer',
        loadComponent: () => import('./features/explorer/explorer.component').then(m => m.ExplorerComponent)
      },
      {
        path: 'documentos/:id',
        loadComponent: () => import('./features/document-detail/document-detail.component').then(m => m.DocumentDetailComponent)
      },
      {
        path: 'papelera',
        loadComponent: () => import('./features/trash/trash.component').then(m => m.TrashComponent)
      },
      {
        path: 'admin',
        canActivate: [adminGuard],
        loadComponent: () => import('./features/admin/admin.component').then(m => m.AdminComponent)
      }
    ]
  },
  { path: '**', redirectTo: 'explorer' }
];
