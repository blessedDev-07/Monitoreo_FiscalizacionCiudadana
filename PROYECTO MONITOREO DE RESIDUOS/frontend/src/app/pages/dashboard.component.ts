import { AfterViewInit, Component, OnDestroy, OnInit, inject } from '@angular/core';
import * as L from 'leaflet';
import { interval, startWith, Subscription, switchMap } from 'rxjs';
import { PosicionGPS, ResumenGeneral } from '../models/models';
import { ApiService } from '../services/api.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  template: `
    <div class="rejilla">
      <div class="tarjeta"><div>Camiones activos</div>
        <div class="num">{{ resumen?.camiones_activos ?? '–' }} / {{ resumen?.camiones_total ?? '–' }}</div></div>
      <div class="tarjeta"><div>Incidencias pendientes</div>
        <div class="num">{{ resumen?.incidencias_pendientes ?? '–' }}</div></div>
    </div>

    <div class="tarjeta">
      <h2>Camiones en tiempo real</h2>
      <div id="mapa"></div>
      <small>Se actualiza cada 4 segundos. Si no ves camiones ejecuta: <code>python manage.py simular_gps</code></small>
    </div>

    <div class="tarjeta">
      <h2>Cumplimiento e incidencias por sector</h2>
      <table>
        <thead><tr><th>Sector</th><th>Recorridos</th><th>Cumplimiento</th><th>Incidencias</th><th>Pendientes</th></tr></thead>
        <tbody>
          @for (s of resumen?.sectores; track s.sector) {
            <tr>
              <td>{{ s.sector }}</td>
              <td>{{ s.recorridos_cumplidos }} / {{ s.recorridos_total }}</td>
              <td>{{ s.porcentaje_cumplimiento }} %</td>
              <td>{{ s.incidencias_total }}</td>
              <td>{{ s.incidencias_pendientes }}</td>
            </tr>
          }
        </tbody>
      </table>
    </div>
  `,
  styles: [`#mapa { height: 420px; border-radius: 10px; margin-bottom: .5rem; }`],
})
export class DashboardComponent implements OnInit, AfterViewInit, OnDestroy {
  private api = inject(ApiService);
  resumen: ResumenGeneral | null = null;
  private mapa?: L.Map;
  private marcadores = new Map<number, L.Marker>();
  private suscripcion = new Subscription();

  ngOnInit(): void {
    this.api.resumen().subscribe(r => (this.resumen = r));
  }

  ngAfterViewInit(): void {
    this.mapa = L.map('mapa').setView([-9.93, -76.24], 14);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap',
    }).addTo(this.mapa);

    this.suscripcion.add(
      interval(4000)
        .pipe(startWith(0), switchMap(() => this.api.posicionesActuales()))
        .subscribe(posiciones => this.dibujar(posiciones)),
    );
  }

  private dibujar(posiciones: PosicionGPS[]): void {
    for (const p of posiciones) {
      const punto: L.LatLngExpression = [Number(p.latitud), Number(p.longitud)];
      const existente = this.marcadores.get(p.camion);
      if (existente) {
        existente.setLatLng(punto);
      } else {
        const icono = L.divIcon({ html: '🚛', className: 'icono-camion', iconSize: [28, 28] });
        const m = L.marker(punto, { icon: icono })
          .addTo(this.mapa!)
          .bindTooltip(p.camion_codigo, { permanent: true, direction: 'top' });
        this.marcadores.set(p.camion, m);
      }
    }
  }

  ngOnDestroy(): void {
    this.suscripcion.unsubscribe();
    this.mapa?.remove();
  }
}
