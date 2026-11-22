# Contrato de la API REST (/api/v1) - Fase 1: Núcleo Indispensable

Este documento define el contrato formal acordado entre el frontend y el backend para la Fase 1 del proyecto.

---

## 1. Convenciones Generales
- **URL Base**: `/api/v1`
- **Formato**: JSON (`application/json`) para todas las solicitudes y respuestas de metadatos.
- **Transmisión de Archivos**: `multipart/form-data` en subidas y `application/octet-stream` en descargas.
- **Autenticación**: `Authorization: Bearer <access_token>`

### Formato de Errores Unificado
```json
{
  "error": {
    "codigo": "CODIGO_ERROR",
    "mensaje": "Descripción en lenguaje sencillo para el usuario",
    "detalle": {}
  }
}
```

---

## 2. Endpoints por Módulo

### 2.1 Autenticación (`/auth`)
| Método | Ruta | Descripción | Roles | Códigos HTTP |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/auth/login` | Inicia sesión con `email` y `password`. Retorna tokens y usuario. | Público | `200`, `401` |
| `POST` | `/auth/refresh` | Emite un nuevo `access_token` usando `refresh_token`. | Público | `200`, `401` |
| `POST` | `/auth/logout` | Revoca tokens de sesión y registra en bitácora. | Autenticado | `204` |
| `GET` | `/auth/me` | Obtiene los datos del usuario en sesión actual. | Autenticado | `200`, `401` |

### 2.2 Usuarios y Roles (`/usuarios`)
| Método | Ruta | Descripción | Roles | Códigos HTTP |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/usuarios` | Listado paginado de usuarios (filtros: `rol`, `activo`). | Administrador | `200`, `401`, `403` |
| `POST` | `/usuarios` | Da de alta un usuario y asigna su rol inicial. | Administrador | `201`, `400`, `409` |
| `GET` | `/usuarios/{id}` | Consulta el perfil de un usuario específico. | Administrador | `200`, `404` |
| `PATCH` | `/usuarios/{id}` | Modifica nombre, rol o estado `activo`. | Administrador | `200`, `400`, `404` |
| `DELETE` | `/usuarios/{id}` | Baja lógica del usuario (`activo = false`). | Administrador | `204`, `404` |

### 2.3 Carpetas (`/carpetas`)
| Método | Ruta | Descripción | Roles | Códigos HTTP |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/carpetas` | Lista subcarpetas (param `carpeta_padre_id` opcional). | Lector, Revisor, Editor, Admin | `200` |
| `POST` | `/carpetas` | Crea una nueva subcarpeta en la ruta indicada. | Editor, Admin | `201`, `400`, `403` |
| `PATCH` | `/carpetas/{id}/renombrar`| Cambia el nombre visible de la carpeta. | Editor, Admin | `200`, `400`, `403` |
| `PATCH` | `/carpetas/{id}/mover` | Mueve una carpeta a otra ubicación jerárquica. | Editor, Admin | `200`, `400`, `409` |
| `DELETE` | `/carpetas/{id}` | Mueve la carpeta y su contenido a la papelera. | Editor, Admin | `204`, `403` |

### 2.4 Archivos y Versiones (`/archivos`)
| Método | Ruta | Descripción | Roles | Códigos HTTP |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/archivos/subir` | Carga inicial atómica (archivo <= 500 MB, v1, SHA-256). | Editor, Admin | `201`, `400`, `413` |
| `POST` | `/archivos/{id}/versiones`| Sube nueva versión (N+1) con comentario obligatorio. Libera bloqueo. | Editor, Admin | `201`, `400`, `409`, `413` |
| `GET` | `/archivos/{id}` | Retorna metadatos del archivo y su versión vigente. | Todos (con permiso) | `200`, `404` |
| `GET` | `/archivos/{id}/descargar`| Transmisión en streaming de la versión vigente o `version_id`. | Todos (con permiso) | `200`, `404` |
| `GET` | `/archivos/{id}/versiones`| Consulta el historial cronológico completo de versiones. | Todos (con permiso) | `200`, `404` |
| `POST` | `/archivos/{id}/versiones/{vid}/restaurar`| Restaura versión creando una versión N+1 idéntica. | Editor, Admin | `201`, `400`, `404` |
| `PATCH` | `/archivos/{id}/renombrar`| Renombra el archivo. | Editor, Admin | `200`, `400`, `403` |
| `PATCH` | `/archivos/{id}/mover` | Cambia el archivo de carpeta. | Editor, Admin | `200`, `400`, `403` |
| `DELETE` | `/archivos/{id}` | Envía el archivo a la papelera. | Editor, Admin | `204`, `403` |

### 2.5 Bloqueo y Concurrencia (`/archivos/{id}/bloquear`)
| Método | Ruta | Descripción | Roles | Códigos HTTP |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/archivos/{id}/bloquear` | Adquiere bloqueo exclusivo por TTL (default: 30 min). | Editor, Admin | `200`, `409` |
| `POST` | `/archivos/{id}/desbloquear` | Libera el bloqueo voluntariamente. | Editor (titular), Admin | `200`, `403` |
| `POST` | `/archivos/{id}/forzar-desbloqueo` | Fuerza la liberación del archivo de otro usuario. | Solo Administrador | `200`, `403` |

### 2.6 Búsqueda Básica (`/busqueda`)
| Método | Ruta | Descripción | Roles | Códigos HTTP |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/busqueda` | Búsqueda por nombre (trigramas), extensión, autor, fecha. | Todos | `200` |

### 2.7 Papelera (`/papelera`)
| Método | Ruta | Descripción | Roles | Códigos HTTP |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/papelera` | Listado de archivos y carpetas eliminados. | Editor, Admin | `200` |
| `POST` | `/papelera/archivos/{id}/restaurar` | Restaura el archivo a su ubicación original. | Editor, Admin | `200`, `404` |
| `POST` | `/papelera/carpetas/{id}/restaurar` | Restaura la carpeta a su ubicación original. | Editor, Admin | `200`, `404` |
| `DELETE` | `/papelera/vaciar` | Limpieza definitiva de elementos en papelera. | Solo Administrador | `204`, `403` |

### 2.8 Bitácora de Auditoría (`/bitacora`)
| Método | Ruta | Descripción | Roles | Códigos HTTP |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/bitacora` | Consulta cronológica de acciones registradas. | Solo Administrador | `200`, `401`, `403` |
