import { HttpClient } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { tap } from 'rxjs';
import { environment } from '../../environments/environment';
import { LoginRespuesta, Usuario } from '../models/models';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private http = inject(HttpClient);
  private router = inject(Router);

  usuario = signal<Usuario | null>(JSON.parse(localStorage.getItem('usuario') ?? 'null'));

  get token(): string | null {
    return localStorage.getItem('token');
  }

  estaLogueado(): boolean {
    return !!this.token;
  }

  login(username: string, password: string) {
    return this.http
      .post<LoginRespuesta>(`${environment.apiUrl}/login/`, { username, password })
      .pipe(
        tap(r => {
          localStorage.setItem('token', r.token);
          localStorage.setItem('usuario', JSON.stringify(r.usuario));
          this.usuario.set(r.usuario);
        }),
      );
  }

  logout(): void {
    if (this.token) {
      this.http.post(`${environment.apiUrl}/logout/`, {}).subscribe({ error: () => {} });
    }
    this.limpiarSesion();
  }

  limpiarSesion(): void {
    localStorage.removeItem('token');
    localStorage.removeItem('usuario');
    this.usuario.set(null);
    this.router.navigate(['/login']);
  }
}
