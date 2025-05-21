import mysql.connector
from mysql.connector import errorcode
import getpass
import pandas as pd
from functools import wraps
import os

# ==============================================
# CONFIGURACIÓN BÁSICA
# ==============================================
DB_CONFIG = {
    'host': 'localhost',
    'database': 'escuela',
    'port': 3306
}

# Tablas y columnas requeridas para importación CSV
TABLAS_IMPORTABLES = {
    'Alumno': ['numControl', 'apellidoPaterno', 'apellidoMaterno', 'nombre', 
               'discapacidad', 'direccion', 'fechaNacimiento', 'cvePE', 'ingreso', 'periodo'],
    'Materia': ['cveMateria', 'nombreMateria', 'horasTeoricas', 'horasPracticas'],
    'Personal': ['cvePersonal', 'apellidoPaterno', 'apellidoMaterno', 'nombre'],
    'Especialidad': ['cveEspecialidad', 'nombreEspecialidad', 'cvePE']
}

# ==============================================
# CLASE PARA MANEJAR LA BASE DE DATOS
# ==============================================
class DBEscuela:
    _conexion = None
    
    @classmethod
    def conectar(cls, usuario=None, contraseña=None):
        if cls._conexion is None or not cls._conexion.is_connected():
            try:
                cls._conexion = mysql.connector.connect(
                    host=DB_CONFIG['host'],
                    user=usuario,
                    password=contraseña,
                    database=DB_CONFIG['database'],
                    port=DB_CONFIG['port']
                )
                return cls._conexion
            except mysql.connector.Error as err:
                if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                    raise Exception("Usuario o contraseña incorrectos")
                elif err.errno == errorcode.ER_BAD_DB_ERROR:
                    raise Exception(f"La base de datos {DB_CONFIG['database']} no existe")
                else:
                    raise Exception(f"Error de conexión: {err}")
        return cls._conexion

    @classmethod
    def cerrar(cls):
        if cls._conexion and cls._conexion.is_connected():
            cls._conexion.close()
            cls._conexion = None

# ==============================================
# FUNCIONES PARA IMPORTACIÓN CSV
# ==============================================
def importar_desde_csv(usuario_actual, archivo, tabla):
    try:
        # Verificar permisos
        if usuario_actual['rol'] not in ['admin', 'asistente'] and tabla != 'Materia':
            print("❌ No tienes permisos para importar a esta tabla")
            return

        # Leer archivo CSV
        df = pd.read_csv(archivo, encoding='latin1')
        
        # Verificar columnas
        columnas_requeridas = TABLAS_IMPORTABLES.get(tabla)
        if not columnas_requeridas:
            print(f"❌ Tabla {tabla} no permitida para importación")
            return
            
        faltantes = [col for col in columnas_requeridas if col not in df.columns]
        if faltantes:
            print(f"❌ Faltan columnas requeridas: {', '.join(faltantes)}")
            return

        # Limpiar datos
        df = limpiar_datos(df, tabla)
        
        # Insertar en lotes
        cursor = usuario_actual['conn'].cursor()
        total, exitosos = 0, 0
        sql = f"INSERT INTO {tabla} ({', '.join(columnas_requeridas)}) VALUES ({', '.join(['%s']*len(columnas_requeridas))})"
        
        for _, fila in df.iterrows():
            try:
                valores = [fila[col] for col in columnas_requeridas]
                cursor.execute(sql, valores)
                exitosos += 1
            except mysql.connector.Error as err:
                print(f"Error en fila {total+1}: {err.msg}")
            total += 1
            
        usuario_actual['conn'].commit()
        print(f"✅ Importación completa: {exitosos}/{total} registros insertados")
        
    except Exception as e:
        usuario_actual['conn'].rollback()
        print(f"❌ Error durante la importación: {str(e)}")
    finally:
        if 'cursor' in locals():
            cursor.close()

def limpiar_datos(df, tabla):
    """Prepara los datos para la inserción en MySQL"""
    # Convertir booleanos a 1/0
    if tabla == 'Alumno' and 'discapacidad' in df.columns:
        df['discapacidad'] = df['discapacidad'].astype(int)
    
    # Convertir fechas
    if tabla == 'Alumno' and 'fechaNacimiento' in df.columns:
        df['fechaNacimiento'] = pd.to_datetime(df['fechaNacimiento']).dt.strftime('%Y-%m-%d')
    
    # Manejar valores nulos
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].fillna('')
    
    return df.dropna(how='all')

# ==============================================
# SISTEMA DE AUTENTICACIÓN
# ==============================================
def login():
    print("\n=== SISTEMA DE GESTIÓN ESCOLAR ===")
    print("Usuarios de prueba:")
    print("1. admin@localhost (Admin123#) - Rol: Administrador")
    print("2. mariagarcia@localhost (Prof123#) - Rol: Profesor")
    print("3. asistente1@localhost (Asist123#) - Rol: Asistente")
    print("4. invitado@localhost (Consulta123#) - Rol: Consulta\n")
    
    usuario = input("Usuario: ")
    contraseña = getpass.getpass("Contraseña: ")
    
    try:
        conn = DBEscuela.conectar(usuario.split('@')[0], contraseña)
        rol = obtener_rol(conn, usuario)
        return {'usuario': usuario, 'rol': rol, 'conn': conn}
    except Exception as e:
        print(f"\nError: {str(e)}")
        return None

def obtener_rol(conexion, usuario):
    cursor = conexion.cursor(dictionary=True)
    try:
        cursor.execute("SHOW GRANTS FOR %s", (usuario,))
        grants = cursor.fetchall()
        
        if any("ALL PRIVILEGES" in grant['Grants for {}@localhost'.format(usuario.split('@')[0])] for grant in grants):
            return 'admin'
        elif any("`profesor`" in grant['Grants for {}@localhost'.format(usuario.split('@')[0])] for grant in grants):
            return 'profesor'
        elif any("`asistente`" in grant['Grants for {}@localhost'.format(usuario.split('@')[0])] for grant in grants):
            return 'asistente'
        else:
            return 'consulta'
    finally:
        cursor.close()

# ==============================================
# DECORADORES PARA CONTROL DE ACCESO
# ==============================================
def requiere_rol(*roles_permitidos):
    def decorador(func):
        def wrapper(usuario_actual, *args, **kwargs):
            if usuario_actual['rol'] not in roles_permitidos:
                print("\n⚠️ Acceso denegado. No tienes los permisos necesarios.")
                return None
            return func(usuario_actual, *args, **kwargs)
        return wrapper
    return decorador

# ==============================================
# MENÚS POR ROL (CON IMPORTACIÓN CSV)
# ==============================================
def menu_administrador(usuario_actual):
    while True:
        print("\n=== MENÚ ADMINISTRADOR ===")
        print("1. Ver todos los alumnos")
        print("2. Importar datos desde CSV")
        print("3. Crear nuevo usuario")
        print("4. Ver todas las materias")
        print("5. Salir")
        
        opcion = input("Seleccione una opción: ")
        
        if opcion == '1':
            ver_alumnos(usuario_actual)
        elif opcion == '2':
            importar_csv(usuario_actual)
        elif opcion == '3':
            crear_usuario(usuario_actual)
        elif opcion == '4':
            ver_materias(usuario_actual)
        elif opcion == '5':
            break
        else:
            print("Opción no válida")

def menu_asistente(usuario_actual):
    while True:
        print("\n=== MENÚ ASISTENTE ===")
        print("1. Registrar nuevo alumno")
        print("2. Importar alumnos desde CSV")
        print("3. Ver lista de alumnos")
        print("4. Salir")
        
        opcion = input("Seleccione una opción: ")
        
        if opcion == '1':
            registrar_alumno(usuario_actual)
        elif opcion == '2':
            importar_csv(usuario_actual)
        elif opcion == '3':
            ver_alumnos(usuario_actual)
        elif opcion == '4':
            break
        else:
            print("Opción no válida")

def importar_csv(usuario_actual):
    print("\n--- Importar desde CSV ---")
    print("Tablas disponibles para importación:")
    for i, tabla in enumerate(TABLAS_IMPORTABLES.keys(), 1):
        print(f"{i}. {tabla}")
    
    try:
        eleccion = int(input("Seleccione tabla a importar (número): ")) - 1
        tabla = list(TABLAS_IMPORTABLES.keys())[eleccion]
        
        # Verificar permisos específicos
        if usuario_actual['rol'] == 'asistente' and tabla != 'Alumno':
            print("❌ Solo puedes importar datos de alumnos")
            return
            
        archivo = input("Ruta del archivo CSV: ").strip('"')
        if not os.path.exists(archivo):
            print("❌ El archivo no existe")
            return
            
        confirmar = input(f"¿Importar datos a {tabla}? (s/n): ").lower()
        if confirmar == 's':
            importar_desde_csv(usuario_actual, archivo, tabla)
    except (ValueError, IndexError):
        print("❌ Selección inválida")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

# ==============================================
# FUNCIONES COMUNES
# ==============================================
@requiere_rol('admin', 'asistente')
def registrar_alumno(usuario_actual):
    print("\n--- Registrar nuevo alumno ---")
    # Implementación simplificada
    print("(Simulación) Alumno registrado correctamente")

@requiere_rol('admin')
def crear_usuario(usuario_actual):
    print("\n--- Crear nuevo usuario ---")
    usuario = input("Nombre de usuario (sin @localhost): ")
    contraseña = getpass.getpass("Contraseña: ")
    rol = input("Rol (admin/profesor/asistente/consulta): ")
    
    try:
        cursor = usuario_actual['conn'].cursor()
        cursor.execute(f"CREATE USER '{usuario}'@'localhost' IDENTIFIED BY '{contraseña}'")
        cursor.execute(f"GRANT '{rol}' TO '{usuario}'@'localhost'")
        usuario_actual['conn'].commit()
        print(f"✅ Usuario {usuario} creado con rol {rol}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    finally:
        cursor.close()

def ver_alumnos(usuario_actual):
    cursor = usuario_actual['conn'].cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM Alumno LIMIT 10")
        alumnos = cursor.fetchall()
        
        print("\n--- LISTA DE ALUMNOS ---")
        for alumno in alumnos:
            print(f"{alumno['numControl']} - {alumno['nombre']} {alumno['apellidoPaterno']}")
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        cursor.close()

def ver_materias(usuario_actual):
    cursor = usuario_actual['conn'].cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM Materia LIMIT 10")
        materias = cursor.fetchall()
        
        print("\n--- LISTA DE MATERIAS ---")
        for materia in materias:
            print(f"{materia['cveMateria']} - {materia['nombreMateria']}")
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        cursor.close()

# ==============================================
# EJECUCIÓN PRINCIPAL
# ==============================================
def main():
    usuario_actual = None
    
    while not usuario_actual:
        usuario_actual = login()
        if not usuario_actual:
            print("Intente nuevamente o presione Ctrl+C para salir")
    
    print(f"\nBienvenido {usuario_actual['usuario']} (Rol: {usuario_actual['rol']})")
    
    try:
        if usuario_actual['rol'] == 'admin':
            menu_administrador(usuario_actual)
        elif usuario_actual['rol'] == 'profesor':
            menu_profesor(usuario_actual)
        elif usuario_actual['rol'] == 'asistente':
            menu_asistente(usuario_actual)
        else:
            menu_consulta(usuario_actual)
            
    except KeyboardInterrupt:
        print("\nSaliendo del sistema...")
    finally:
        DBEscuela.cerrar()

if __name__ == "__main__":
    main()