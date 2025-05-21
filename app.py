import mysql.connector
import pandas as pd
from tkinter import Tk, filedialog, simpledialog

# Conexión a MySQL
conexion = mysql.connector.connect(
    host="localhost",
    user="root",
    password="123456789",
    database="escuela"
)
cursor = conexion.cursor()

# Interfaz para elegir archivo CSV
root = Tk()
root.withdraw()
archivo_csv = filedialog.askopenfilename(title="Selecciona el archivo CSV", filetypes=[("CSV files", "*.csv")])
tabla_destino = simpledialog.askstring("Tabla", "¿A qué tabla deseas insertar los datos? (Alumno, Personal, Especialidad, Materia)")

# Leer CSV
df = pd.read_csv(archivo_csv, encoding='latin1')

# Diccionario de inserciones por tabla
instrucciones_insert = {
    'Alumno': (
        "INSERT INTO Alumno (numControl, apellidoPaterno, apellidoMaterno, nombre, discapacidad, carrera, ingreso, periodo) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
    ),
    'Personal': (
        "INSERT INTO Personal (cvePersonal, apellidoPaterno, apellidoMaterno, nombre) "
        "VALUES (%s, %s, %s, %s)"
    ),
    'Especialidad': (
        "INSERT INTO Especialidad (cveEspecialidad, nombreEspecialidad) "
        "VALUES (%s, %s)"
    ),
    'Materia': (
        "INSERT INTO Materia (cveMateria, nombreMateria, horasTeoricas, horasPracticas) "
        "VALUES (%s, %s, %s, %s)"
    )
}

# Ejecutar inserciones
try:
    if tabla_destino not in instrucciones_insert:
        raise ValueError("Tabla no válida.")

    for _, row in df.iterrows():
        if tabla_destino == 'Alumno':
            values = (
                row['numControl'], row['apellidoPaterno'], row['apellidoMaterno'],
                row['nombre'], bool(row['discapacidad']), row['carrera'], row['ingreso'],
                row['periodo']
            )
        elif tabla_destino == 'Personal':
            values = (
                row['cvePersonal'], row['apellidoPaterno'], row['apellidoMaterno'], row['nombre']
            )
        elif tabla_destino == 'Especialidad' :
            values = (row['cveEspecialidad'], row['nombreEspecialidad'])
        elif tabla_destino == 'Materia':
            values = (row['cveMateria'], row['nombreMateria'], row['horasTeoricas'], row['horasPracticas'])
        
        cursor.execute(instrucciones_insert[tabla_destino], values)

    conexion.commit()
    print(f"✅ Datos insertados en la tabla {tabla_destino} correctamente.")

except Exception as e:
    print(f"❌ Error: {e}")

finally:
    cursor.close()
    conexion.close()