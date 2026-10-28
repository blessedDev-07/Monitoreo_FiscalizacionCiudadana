import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <header>
      <h1>♻ Monitoreo de Residuos Sólidos – Amarilis</h1>
      <nav>
        <a routerLink="/" routerLinkActive="activo" [routerLinkActiveOptions]="{ exact: true }">Panel</a>
        <a routerLink="/rutas" routerLinkActive="activo">Rutas y horarios</a>
        <a routerLink="/camiones" routerLinkActive="activo">Camiones</a>
        <a routerLink="/incidencias" routerLinkActive="activo">Incidencias</a>
      </nav>
    </header>
    <main class="contenedor"><router-outlet /></main>
  `,
  styles: [`
    header { background: var(--verde); color: #fff; padding: .8rem 1.2rem; }
    header h1 { font-size: 1.3rem; margin: 0 0 .5rem; }
    nav a { color: #fff; text-decoration: none; margin-right: 1rem; padding: .25rem .7rem; border-radius: 999px; }
    nav a.activo, nav a:hover { background: rgba(255,255,255,.25); }
  `],
})
export class AppComponent {}
