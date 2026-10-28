import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from './auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [ReactiveFormsModule],
  template: `
    <div class="caja tarjeta">
      <h2>Iniciar sesión</h2>
      <form [formGroup]="form" (ngSubmit)="entrar()">
        <label>Usuario</label>
        <input formControlName="username" autocomplete="username" autofocus>
        <label>Contraseña</label>
        <input type="password" formControlName="password" autocomplete="current-password">
        <p><button type="submit" [disabled]="form.invalid || cargando">
          {{ cargando ? 'Ingresando…' : 'Ingresar' }}</button></p>
        @if (error) { <p class="error">{{ error }}</p> }
      </form>
    </div>
  `,
  styles: [`.caja { max-width: 380px; margin: 3rem auto; }`],
})
export class LoginComponent {
  private auth = inject(AuthService);
  private router = inject(Router);
  private fb = inject(FormBuilder);

  cargando = false;
  error = '';
  form = this.fb.nonNullable.group({
    username: ['', Validators.required],
    password: ['', Validators.required],
  });

  entrar(): void {
    this.error = '';
    this.cargando = true;
    const { username, password } = this.form.getRawValue();
    this.auth.login(username, password).subscribe({
      next: () => this.router.navigate(['/']),
      error: e => {
        this.cargando = false;
        this.error = e.error?.detail ?? 'No se pudo conectar con el servidor';
      },
    });
  }
}
