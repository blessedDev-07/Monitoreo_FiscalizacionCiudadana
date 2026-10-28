import { Component, OnInit, inject } from '@angular/core';
import { Camion } from '../models/models';
import { ApiService } from '../services/api.service';

@Component({
  selector: 'app-camiones',
  standalone: true,
  template: `
    <div class="tarjeta">
      <h2>Flota de camiones</h2>
      <table>
        <thead><tr><th>Código</th><th>Placa</th><th>Operador</th><th>Capacidad</th><th>Estado</th><th>Última posición</th></tr></thead>
        <tbody>
          @for (c of camiones; track c.id) {
            <tr>
              <td>{{ c.codigo }}</td><td>{{ c.placa }}</td><td>{{ c.operador_nombre ?? '—' }}</td>
              <td>{{ c.capacidad_kg }} kg</td>
              <td><span [class]="'etiqueta ' + c.estado">{{ c.estado }}</span></td>
              <td>
                @if (c.ultima_posicion) { {{ c.ultima_posicion.latitud }}, {{ c.ultima_posicion.longitud }} }
                @else { sin datos }
              </td>
            </tr>
          }
        </tbody>
      </table>
    </div>
  `,
})
export class CamionesComponent implements OnInit {
  private api = inject(ApiService);
  camiones: Camion[] = [];
  ngOnInit(): void { this.api.camiones().subscribe(c => (this.camiones = c)); }
}
