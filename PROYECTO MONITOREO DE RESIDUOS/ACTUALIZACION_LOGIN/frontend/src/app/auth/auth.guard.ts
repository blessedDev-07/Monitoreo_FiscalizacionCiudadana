import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from './auth.service';

/** Si no hay sesión, manda al usuario a /login. */
export const authGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  return auth.estaLogueado() ? true : inject(Router).createUrlTree(['/login']);
};
