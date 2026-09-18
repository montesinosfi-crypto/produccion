# Sistema de Producción - Listo para Render

## Usuarios por defecto

| Usuario     | Contraseña      |
|-------------|-----------------|
| admin       | admin123        |
| corte       | corte123        |
| gerente     | gerente123      |
| habilitado  | habilitado123   |

## Cómo subirlo a Render (paso a paso)

### 1. Sube el código a GitHub
1. Crea un repositorio nuevo en GitHub (puede ser privado)
2. Sube todos los archivos de esta carpeta al repositorio

### 2. Crea la base de datos en Render
1. Entra a [https://render.com](https://render.com) e inicia sesión
2. New → PostgreSQL
3. Name: `produccion-db`
4. Plan: Free
5. Create Database
6. Copia la **Internal Database URL**

### 3. Crea el servicio Web
1. New → Web Service
2. Conecta tu repositorio de GitHub
3. Configuración:
   - Name: `sistema-produccion`
   - Runtime: Python
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
4. En Environment Variables agrega:
   - `DATABASE_URL` = (pega la Internal Database URL)
   - `SECRET_KEY` = cualquier texto secreto (ejemplo: `mi_clave_secreta_123`)
5. Create Web Service

### 4. Listo
Render te dará una dirección tipo:
```
https://sistema-produccion.onrender.com
```

Esa dirección **nunca cambia** y todos pueden entrar desde cualquier lugar.
