import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  Camion, EstadoIncidencia, Incidencia, PosicionGPS, ResumenGeneral, Ruta, Sector,
} from '../models/models';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);
  private base = environment.apiUrl;

  sectores(): Observable<Sector[]> {
    return this.http.get<Sector[]>(`${this.base}/sectores/`);
  }
  camiones(): Observable<Camion[]> {
    return this.http.get<Camion[]>(`${this.base}/camiones/`);
  }
  posicionesActuales(): Observable<PosicionGPS[]> {
    return this.http.get<PosicionGPS[]>(`${this.base}/camiones/posiciones-actuales/`);
  }
  rutas(): Observable<Ruta[]> {
    return this.http.get<Ruta[]>(`${this.base}/rutas/`);
  }
  incidencias(estado?: string): Observable<Incidencia[]> {
    const q = estado ? `?estado=${estado}` : '';
    return this.http.get<Incidencia[]>(`${this.base}/incidencias/${q}`);
  }
  crearIncidencia(datos: { sector: number; tipo: string; descripcion: string }): Observable<Incidencia> {
    return this.http.post<Incidencia>(`${this.base}/incidencias/`, datos);
  }
  cambiarEstado(id: number, estado: EstadoIncidencia): Observable<Incidencia> {
    return this.http.post<Incidencia>(`${this.base}/incidencias/${id}/cambiar-estado/`, { estado });
  }
  resumen(): Observable<ResumenGeneral> {
    return this.http.get<ResumenGeneral>(`${this.base}/estadisticas/resumen/`);
  }
}
