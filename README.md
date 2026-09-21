# Sistema de Producción v3

## Flujo completo

1. **Programa de Corte** → Número de programa + Puntos (modelo, color, cantidades por talla)
2. **Trazo** → Confirmar que el trazo está listo
3. **Corte** → Asigna Número de Orden a cada punto
4. **Asignación** → Gerente pone maquilero y fecha de salida
5. **Habilitado** → Completo / Parcial
6. **Maquila** → Envío y Regreso (Terminado)

## Usuarios

| Usuario    | Contraseña     | Área      |
|------------|----------------|-----------|
| admin      | admin123       | Admin     |
| programa   | programa123    | Programa  |
| trazo      | trazo123       | Trazo     |
| corte      | corte123       | Corte     |
| gerente    | gerente123     | Gerente   |
| habilitado | habilitado123  | Habilitado|

## Deploy en Render

- Build: `pip install -r requirements.txt`
- Start: `gunicorn app:app`
- Variables: `DATABASE_URL` y `SECRET_KEY`
