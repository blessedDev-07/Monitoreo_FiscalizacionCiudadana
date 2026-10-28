import { Routes } from '@angular/router';
import { CamionesComponent } from './pages/camiones.component';
import { DashboardComponent } from './pages/dashboard.component';
import { IncidenciasComponent } from './pages/incidencias.component';
import { RutasComponent } from './pages/rutas.component';

export const routes: Routes = [
  { path: '', component: DashboardComponent },
  { path: 'incidencias', component: IncidenciasComponent },
  { path: 'rutas', component: RutasComponent },
  { path: 'camiones', component: CamionesComponent },
  { path: '**', redirectTo: '' },
];
