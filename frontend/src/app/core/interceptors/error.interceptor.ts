import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { MessageService } from 'primeng/api';
import { AuthService } from '../services/auth.service';

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const messageService = inject(MessageService);
  const auth = inject(AuthService);
  const router = inject(Router);

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      let mensajeAmigable = 'Ocurrió un error inesperado. Por favor intenta de nuevo.';

      if (error.status === 401) {
        auth.clearSession();
        router.navigate(['/login']);
        mensajeAmigable = 'Tu sesión ha terminado. Por favor ingresa nuevamente con tu correo y contraseña.';
      } else if (error.status === 403) {
        mensajeAmigable = 'No tienes permiso para realizar esta acción con tu rol actual.';
      } else if (error.status === 409) {
        mensajeAmigable = error.error?.error?.mensaje || 'El documento está siendo editado por otra persona en este momento.';
      } else if (error.status === 413) {
        mensajeAmigable = 'El archivo supera el tamaño máximo permitido de 500 MB.';
      } else if (error.error?.error?.mensaje) {
        mensajeAmigable = error.error.error.mensaje;
      }

      messageService.add({
        severity: error.status === 409 ? 'warn' : 'error',
        summary: error.status === 409 ? 'Documento en uso' : 'Aviso',
        detail: mensajeAmigable,
        life: 6000
      });

      return throwError(() => error);
    })
  );
};
