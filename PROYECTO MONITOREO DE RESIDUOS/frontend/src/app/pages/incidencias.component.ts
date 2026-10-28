import { DatePipe } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { EstadoIncidencia, Incidencia, Sector, TIPOS_INCIDENCIA } from '../models/models';
import { ApiService } from '../services/api.service';

@Component({
  selector: 'app-incidencias',
  standalone: true,
  imports: [ReactiveFormsModule, DatePipe],
  template: `
    <div class="tarjeta">
      <h2>Reportar incidencia</h2>
      <form [formGroup]="form" (ngSubmit)="enviar()">
        <label>Tipo de reporte</label>
        <select formControlName="tipo">
          @for (t of tipos; track t) { <option [value]="t">{{ t }}</option> }
        </select>
        <label>Sector</label>
        <select formControlName="sector">
          @for (s of sectores; track s.id) { <option [ngValue]="s.id">{{ s.nombre }}</option> }
        </select>
        <label>Descripción</label>
        <textarea rows="3" formControlName="descripcion"></textarea>
        <p><button type="submit" [disabled]="form.invalid">Enviar reporte</button></p>
        @if (mensaje) { <p class="ok">{{ mensaje }}</p> }
        @if (error) { <p class="error">{{ error }}</p> }
      </form>
    </div>

    <div class="tarjeta">
      <h2>Incidencias reportadas</h2>
      <table>
        <thead><tr><th>Fecha</th><th>Tipo</th><th>Sector</th><th>Estado</th><th>Acción</th></tr></thead>
        <tbody>
          @for (i of incidencias; track i.id) {
            <tr>
              <td>{{ i.fecha_creacion | date: 'dd/MM/yyyy HH:mm' }}</td>
              <td>{{ i.tipo }}<br><small>{{ i.descripcion }}</small></td>
              <td>{{ i.sector_nombre }}</td>
              <td><span [class]="'etiqueta ' + i.estado">{{ i.estado }}</span></td>
              <td>
                @if (i.estado === 'PENDIENTE') { <button (click)="cambiar(i, 'EN_PROCESO')">Atender</button> }
                @if (i.estado === 'EN_PROCESO') { <button (click)="cambiar(i, 'RESUELTA')">Resolver</button> }
              </td>
            </tr>
          } @empty { <tr><td colspan="5">Aún no hay reportes.</td></tr> }
        </tbody>
      </table>
    </div>
  `,
})
export class IncidenciasComponent implements OnInit {
  private api = inject(ApiService);
  private fb = inject(FormBuilder);

  tipos = TIPOS_INCIDENCIA;
  sectores: Sector[] = [];
  incidencias: Incidencia[] = [];
  mensaje = '';
  error = '';

  form = this.fb.nonNullable.group({
    tipo: [TIPOS_INCIDENCIA[0] as string, Validators.required],
    sector: [0, [Validators.required, Validators.min(1)]],
    descripcion: [''],
  });

  ngOnInit(): void {
    this.api.sectores().subscribe(s => {
      this.sectores = s;
      if (s.length) this.form.patchValue({ sector: s[0].id });
    });
    this.cargar();
  }

  cargar(): void {
    this.api.incidencias().subscribe(i => (this.incidencias = i));
  }

  enviar(): void {
    this.mensaje = this.error = '';
    this.api.crearIncidencia(this.form.getRawValue()).subscribe({
      next: () => {
        this.mensaje = 'Reporte enviado correctamente.';
        this.form.patchValue({ descripcion: '' });
        this.cargar();
      },
      error: e => (this.error = JSON.stringify(e.error)),
    });
  }

  cambiar(i: Incidencia, estado: EstadoIncidencia): void {
    this.api.cambiarEstado(i.id, estado).subscribe(() => this.cargar());
  }
}
