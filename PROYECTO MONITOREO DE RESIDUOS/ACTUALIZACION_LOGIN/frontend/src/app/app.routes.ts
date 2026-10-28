import { Routes } from '@angular/router';
import { authGuard } from './auth/auth.guard';
import { LoginComponent } from './auth/login.component';
import { CamionesComponent } from './pages/camiones.component';
import { DashboardComponent } from './pages/dashboard.component';
import { IncidenciasComponent } from './pages/incidencias.component';
import { RutasComponent } from './pages/rutas.component';

export const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: '', component: DashboardComponent, canActivate: [authGuard] },
  { path: 'incidencias', component: IncidenciasComponent, canActivate: [authGuard] },
  { path: 'rutas', component: RutasComponent, canActivate: [authGuard] },
  { path: 'camiones', component: CamionesComponent, canActivate: [authGuard] },
  { path: '**', redirectTo: '' },
];
