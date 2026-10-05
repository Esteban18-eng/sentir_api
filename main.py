from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
from con_db import obtener_conexion

app = FastAPI()


# ---------- Modelos (definen los campos que Swagger muestra en el body) ----------
class PersonaIn(BaseModel):
    nombre: str
    telefono: str
    tipo_persona: str

    model_config = {"json_schema_extra": {"example": {
        "nombre": "Ana Pérez", "telefono": "3001234567", "tipo_persona": "ciudadano"}}}


class EmergenciaIn(BaseModel):
    tipo: str
    descripcion: str
    estado: str
    id_persona: int

    model_config = {"json_schema_extra": {"example": {
        "tipo": "ACCIDENTE", "descripcion": "Accidente cerca de la universidad",
        "estado": "REPORTADA", "id_persona": 1}}}


class UbicacionIn(BaseModel):
    latitud: float
    longitud: float
    direccion: str
    id_emergencia: int

    model_config = {"json_schema_extra": {"example": {
        "latitud": 8.2501234, "longitud": -73.3556789,
        "direccion": "Calle 10 # 5-20", "id_emergencia": 1}}}


@app.get("/")
def root():
    return {"message": "API Sentir - FastAPI"}


# Convierte los resultados del cursor en diccionarios (para ver los nombres de columnas)
def a_diccionarios(cursor, filas):
    columnas = [col[0] for col in cursor.description]
    return [dict(zip(columnas, fila)) for fila in filas]


# ======================================================
# PERSONAS (referencia)
# ======================================================
@app.get("/personas")
def consultar_personas():
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT id_persona, nombre, telefono, tipo_persona
        FROM personas
        ORDER BY id_persona
    """)

    personas = a_diccionarios(cursor, cursor.fetchall())
    cursor.close()
    conexion.close()

    return personas


@app.post("/personas")
def guardar_persona(persona: PersonaIn):
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cursor.execute("""
        INSERT INTO personas (nombre, telefono, tipo_persona)
        VALUES (%s, %s, %s)
    """, (persona.nombre, persona.telefono, persona.tipo_persona))

    conexion.commit()
    cursor.close()
    conexion.close()

    return {"message": "Persona guardada correctamente"}


@app.put("/personas/{id_persona}")
def actualizar_persona(id_persona: int, persona: PersonaIn):
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cursor.execute("""
        UPDATE personas
        SET nombre = %s, telefono = %s, tipo_persona = %s
        WHERE id_persona = %s
    """, (persona.nombre, persona.telefono, persona.tipo_persona, id_persona))

    conexion.commit()
    filas_afectadas = cursor.rowcount
    cursor.close()
    conexion.close()

    if filas_afectadas == 0:
        raise HTTPException(status_code=404, detail="La persona no existe")

    return {"message": "Persona actualizada correctamente"}


@app.delete("/personas/{id_persona}")
def eliminar_persona(id_persona: int):
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:
        cursor.execute("""
            DELETE FROM personas
            WHERE id_persona = %s
        """, (id_persona,))
        conexion.commit()
        filas_afectadas = cursor.rowcount
    except psycopg2.errors.ForeignKeyViolation:
        conexion.rollback()
        raise HTTPException(
            status_code=409,
            detail="No se puede eliminar: la persona tiene emergencias asociadas"
        )
    finally:
        cursor.close()
        conexion.close()

    if filas_afectadas == 0:
        raise HTTPException(status_code=404, detail="La persona no existe")

    return {"message": "Persona eliminada correctamente"}


# ======================================================
# EMERGENCIAS
# ======================================================

# GET /emergencias -> SELECT
@app.get("/emergencias")
def consultar_emergencias():
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT id_emergencia, tipo, descripcion, fecha, estado, id_persona
        FROM emergencias
        ORDER BY id_emergencia
    """)

    emergencias = a_diccionarios(cursor, cursor.fetchall())
    cursor.close()
    conexion.close()

    return emergencias


# GET /emergencias/{id} -> SELECT + WHERE
@app.get("/emergencias/{id_emergencia}")
def consultar_emergencia(id_emergencia: int):
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT id_emergencia, tipo, descripcion, fecha, estado, id_persona
        FROM emergencias
        WHERE id_emergencia = %s
    """, (id_emergencia,))

    filas = a_diccionarios(cursor, cursor.fetchall())
    cursor.close()
    conexion.close()

    if not filas:
        raise HTTPException(status_code=404, detail="La emergencia no existe")

    return filas[0]


# POST /emergencias -> INSERT
@app.post("/emergencias")
def guardar_emergencia(emergencia: EmergenciaIn):
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:
        cursor.execute("""
            INSERT INTO emergencias (tipo, descripcion, estado, id_persona)
            VALUES (%s, %s, %s, %s)
        """, (emergencia.tipo, emergencia.descripcion,
              emergencia.estado, emergencia.id_persona))
        conexion.commit()
    except psycopg2.errors.ForeignKeyViolation:
        conexion.rollback()
        raise HTTPException(status_code=400, detail="La persona indicada no existe")
    finally:
        cursor.close()
        conexion.close()

    return {"message": "Emergencia guardada correctamente"}


# PUT /emergencias/{id} -> UPDATE + WHERE
@app.put("/emergencias/{id_emergencia}")
def actualizar_emergencia(id_emergencia: int, emergencia: EmergenciaIn):
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:
        cursor.execute("""
            UPDATE emergencias
            SET tipo = %s, descripcion = %s, estado = %s, id_persona = %s
            WHERE id_emergencia = %s
        """, (emergencia.tipo, emergencia.descripcion,
              emergencia.estado, emergencia.id_persona, id_emergencia))
        conexion.commit()
        filas_afectadas = cursor.rowcount
    except psycopg2.errors.ForeignKeyViolation:
        conexion.rollback()
        raise HTTPException(status_code=400, detail="La persona indicada no existe")
    finally:
        cursor.close()
        conexion.close()

    if filas_afectadas == 0:
        raise HTTPException(status_code=404, detail="La emergencia no existe")

    return {"message": "Emergencia actualizada correctamente"}


# DELETE /emergencias/{id} -> DELETE + WHERE
@app.delete("/emergencias/{id_emergencia}")
def eliminar_emergencia(id_emergencia: int):
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:
        cursor.execute("""
            DELETE FROM emergencias
            WHERE id_emergencia = %s
        """, (id_emergencia,))
        conexion.commit()
        filas_afectadas = cursor.rowcount
    except psycopg2.errors.ForeignKeyViolation:
        conexion.rollback()
        raise HTTPException(
            status_code=409,
            detail="No se puede eliminar: la emergencia tiene ubicaciones asociadas"
        )
    finally:
        cursor.close()
        conexion.close()

    if filas_afectadas == 0:
        raise HTTPException(status_code=404, detail="La emergencia no existe")

    return {"message": "Emergencia eliminada correctamente"}


# ======================================================
# UBICACIONES
# ======================================================

# GET /ubicaciones -> SELECT
@app.get("/ubicaciones")
def consultar_ubicaciones():
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT id_ubicacion, latitud, longitud, direccion, id_emergencia
        FROM ubicaciones
        ORDER BY id_ubicacion
    """)

    ubicaciones = a_diccionarios(cursor, cursor.fetchall())
    cursor.close()
    conexion.close()

    return ubicaciones


# GET /ubicaciones/{id} -> SELECT + WHERE
@app.get("/ubicaciones/{id_ubicacion}")
def consultar_ubicacion(id_ubicacion: int):
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT id_ubicacion, latitud, longitud, direccion, id_emergencia
        FROM ubicaciones
        WHERE id_ubicacion = %s
    """, (id_ubicacion,))

    filas = a_diccionarios(cursor, cursor.fetchall())
    cursor.close()
    conexion.close()

    if not filas:
        raise HTTPException(status_code=404, detail="La ubicación no existe")

    return filas[0]


# POST /ubicaciones -> INSERT
@app.post("/ubicaciones")
def guardar_ubicacion(ubicacion: UbicacionIn):
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:
        cursor.execute("""
            INSERT INTO ubicaciones (latitud, longitud, direccion, id_emergencia)
            VALUES (%s, %s, %s, %s)
        """, (ubicacion.latitud, ubicacion.longitud,
              ubicacion.direccion, ubicacion.id_emergencia))
        conexion.commit()
    except psycopg2.errors.ForeignKeyViolation:
        conexion.rollback()
        raise HTTPException(status_code=400, detail="La emergencia indicada no existe")
    finally:
        cursor.close()
        conexion.close()

    return {"message": "Ubicación guardada correctamente"}


# PUT /ubicaciones/{id} -> UPDATE + WHERE
@app.put("/ubicaciones/{id_ubicacion}")
def actualizar_ubicacion(id_ubicacion: int, ubicacion: UbicacionIn):
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:
        cursor.execute("""
            UPDATE ubicaciones
            SET latitud = %s, longitud = %s, direccion = %s, id_emergencia = %s
            WHERE id_ubicacion = %s
        """, (ubicacion.latitud, ubicacion.longitud,
              ubicacion.direccion, ubicacion.id_emergencia, id_ubicacion))
        conexion.commit()
        filas_afectadas = cursor.rowcount
    except psycopg2.errors.ForeignKeyViolation:
        conexion.rollback()
        raise HTTPException(status_code=400, detail="La emergencia indicada no existe")
    finally:
        cursor.close()
        conexion.close()

    if filas_afectadas == 0:
        raise HTTPException(status_code=404, detail="La ubicación no existe")

    return {"message": "Ubicación actualizada correctamente"}


# DELETE /ubicaciones/{id} -> DELETE + WHERE
@app.delete("/ubicaciones/{id_ubicacion}")
def eliminar_ubicacion(id_ubicacion: int):
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cursor.execute("""
        DELETE FROM ubicaciones
        WHERE id_ubicacion = %s
    """, (id_ubicacion,))

    conexion.commit()
    filas_afectadas = cursor.rowcount
    cursor.close()
    conexion.close()

    if filas_afectadas == 0:
        raise HTTPException(status_code=404, detail="La ubicación no existe")

    return {"message": "Ubicación eliminada correctamente"}


# ======================================================
# INTEGRACIÓN
# ======================================================

# GET /emergencias/{id}/ubicacion
@app.get("/emergencias/{id_emergencia}/ubicacion")
def ubicacion_de_emergencia(id_emergencia: int):
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cursor.execute("SELECT 1 FROM emergencias WHERE id_emergencia = %s", (id_emergencia,))
    if cursor.fetchone() is None:
        cursor.close()
        conexion.close()
        raise HTTPException(status_code=404, detail="La emergencia no existe")

    cursor.execute("""
        SELECT id_ubicacion, latitud, longitud, direccion, id_emergencia
        FROM ubicaciones
        WHERE id_emergencia = %s
    """, (id_emergencia,))

    ubicaciones = a_diccionarios(cursor, cursor.fetchall())
    cursor.close()
    conexion.close()

    if not ubicaciones:
        raise HTTPException(status_code=404, detail="La emergencia no tiene ubicación registrada")

    return ubicaciones[0]


# GET /emergencias/{id}/detalle  (emergencia + persona + ubicación)
@app.get("/emergencias/{id_emergencia}/detalle")
def detalle_de_emergencia(id_emergencia: int):
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT e.id_emergencia, e.tipo, e.descripcion, e.fecha, e.estado,
               p.id_persona, p.nombre, p.telefono, p.tipo_persona,
               u.id_ubicacion, u.latitud, u.longitud, u.direccion
        FROM emergencias e
        JOIN personas p ON e.id_persona = p.id_persona
        LEFT JOIN ubicaciones u ON u.id_emergencia = e.id_emergencia
        WHERE e.id_emergencia = %s
    """, (id_emergencia,))

    fila = cursor.fetchone()
    cursor.close()
    conexion.close()

    if fila is None:
        raise HTTPException(status_code=404, detail="La emergencia no existe")

    return {
        "emergencia": {
            "id_emergencia": fila[0], "tipo": fila[1], "descripcion": fila[2],
            "fecha": fila[3], "estado": fila[4]
        },
        "persona": {
            "id_persona": fila[5], "nombre": fila[6],
            "telefono": fila[7], "tipo_persona": fila[8]
        },
        "ubicacion": None if fila[9] is None else {
            "id_ubicacion": fila[9], "latitud": fila[10],
            "longitud": fila[11], "direccion": fila[12]
        }
    }