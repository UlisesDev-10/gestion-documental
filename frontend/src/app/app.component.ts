import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { ToastModule } from 'primeng/toast';
import { ConfirmDialogModule } from 'primeng/confirmdialog';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, ToastModule, ConfirmDialogModule],
  template: `
    <p-toast position="top-right" [baseZIndex]="5000"></p-toast>
    <p-confirmDialog [style]="{width: '450px'}"></p-confirmDialog>
    <router-outlet></router-outlet>
  `
})
export class AppComponent {}
