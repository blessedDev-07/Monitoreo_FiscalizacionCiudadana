import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { AuthService } from './auth.service';

/** Agrega "Authorization: Token ..." a cada petición y cierra sesión si el token ya no vale. */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const token = auth.token;
  const peticion = token ? req.clone({ setHeaders: { Authorization: `Token ${token}` } }) : req;

  return next(peticion).pipe(
    catchError(error => {
      if (error.status === 401 && !req.url.includes('/login/')) {
        auth.limpiarSesion();
      }
      return throwError(() => error);
    }),
  );
};
