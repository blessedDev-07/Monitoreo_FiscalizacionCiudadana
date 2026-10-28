import { Component, OnInit, inject } from '@angular/core';
import { Ruta } from '../models/models';
import { ApiService } from '../services/api.service';

@Component({
  selector: 'app-rutas',
  standalone: true,
  template: `
    @for (r of rutas; track r.id) {
      <div class="tarjeta">
        <h2>{{ r.nombre }}
          @if (r.en_servicio) { <span class="etiqueta ACTIVO">En servicio ahora</span> }
        </h2>
        <p>Sector: <b>{{ r.sector_nombre }}</b> · Camión: <b>{{ r.camion_codigo ?? 'sin asignar' }}</b></p>
        <table>
          <thead><tr><th>Día</th><th>Inicio</th><th>Fin</th></tr></thead>
          <tbody>
            @for (h of r.horarios; track h.id) {
              <tr><td>{{ h.dia_nombre }}</td><td>{{ h.hora_inicio.slice(0, 5) }}</td><td>{{ h.hora_fin.slice(0, 5) }}</td></tr>
            }
          </tbody>
        </table>
        <p><b>Paradas:</b>
          @for (p of r.puntos; track p.id) { <span>{{ p.orden }}. {{ p.referencia }}{{ $last ? '' : ' → ' }}</span> }
        </p>
      </div>
    } @empty { <div class="tarjeta">No hay rutas registradas.</div> }
  `,
})
export class RutasComponent implements OnInit {
  private api = inject(ApiService);
  rutas: Ruta[] = [];
  ngOnInit(): void { this.api.rutas().subscribe(r => (this.rutas = r)); }
}
