import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'friendlyDate',
  standalone: true
})
export class FriendlyDatePipe implements PipeTransform {
  transform(isoDateString?: string | null): string {
    if (!isoDateString) return '-';
    const date = new Date(isoDateString);
    return date.toLocaleDateString('es-ES', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
}
