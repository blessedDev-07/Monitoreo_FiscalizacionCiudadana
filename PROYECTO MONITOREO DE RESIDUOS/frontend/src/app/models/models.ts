// Interfaces TypeScript: reflejan las clases del diagrama UML / la API de Django.

export type Rol = 'CIUDADANO' | 'OPERADOR' | 'ADMINISTRADOR';
export type EstadoCamion = 'ACTIVO' | 'MANTENIMIENTO' | 'INACTIVO';
export type EstadoIncidencia = 'PENDIENTE' | 'EN_PROCESO' | 'RESUELTA';

export const TIPOS_INCIDENCIA = [
  'No pasó el camión',
  'Conducta inadecuada',
  'Quema de basura',
  'Otros',
] as const;

export interface Sector {
  id: number;
  nombre: string;
  descripcion: string;
}

export interface PosicionGPS {
  id: number;
  camion: number;
  camion_codigo: string;
  latitud: string;
  longitud: string;
  velocidad_kmh: number;
  fecha_hora: string;
}

export interface Camion {
  id: number;
  codigo: string;
  placa: string;
  capacidad_kg: number;
  estado: EstadoCamion;
  operador: number | null;
  operador_nombre: string | null;
  ultima_posicion: PosicionGPS | null;
}

export interface PuntoRuta {
  id: number;
  ruta: number;
  orden: number;
  latitud: string;
  longitud: string;
  referencia: string;
}

export interface Horario {
  id: number;
  ruta: number;
  dia_semana: number;
  dia_nombre: string;
  hora_inicio: string;
  hora_fin: string;
}

export interface Ruta {
  id: number;
  nombre: string;
  sector: number;
  sector_nombre: string;
  camion: number | null;
  camion_codigo: string | null;
  activa: boolean;
  en_servicio: boolean;
  horarios: Horario[];
  puntos: PuntoRuta[];
}

export interface Incidencia {
  id: number;
  sector: number;
  sector_nombre: string;
  tipo: string;
  descripcion: string;
  latitud: string | null;
  longitud: string | null;
  estado: EstadoIncidencia;
  fecha_creacion: string;
  fecha_resolucion: string | null;
}

export interface ResumenSector {
  sector: string;
  incidencias_total: number;
  incidencias_pendientes: number;
  incidencias_resueltas: number;
  recorridos_total: number;
  recorridos_cumplidos: number;
  porcentaje_cumplimiento: number;
}

export interface ResumenGeneral {
  camiones_total: number;
  camiones_activos: number;
  incidencias_pendientes: number;
  sectores: ResumenSector[];
}
