import os
import logging
from typing import Dict, List, Optional
import mysql.connector
import pandas as pd
from tkinter import Tk, filedialog, simpledialog, messagebox, ttk
from dotenv import load_dotenv

# ------------------------------
# Configuración inicial
# ------------------------------
load_dotenv()  # Carga variables de entorno desde .env
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='data_importer.log'
)

# ------------------------------
# Constantes y Configuración
# ------------------------------
INSTRUCCIONES_INSERT = {
    'Alumno': (
        "INSERT INTO Alumno (numControl, apellidoPaterno, apellidoMaterno, nombre, "
        "discapacidad, carrera, ingreso, periodo) VALUES (%(numControl)s, %(apellidoPaterno)s, "
        "%(apellidoMaterno)s, %(nombre)s, %(discapacidad)s, %(carrera)s, %(ingreso)s, %(periodo)s)"
    ),
    'Personal': (
        "INSERT INTO Personal (cvePersonal, apellidoPaterno, apellidoMaterno, nombre) "
        "VALUES (%(cvePersonal)s, %(apellidoPaterno)s, %(apellidoMaterno)s, %(nombre)s)"
    ),
    'Especialidad': (
        "INSERT INTO Especialidad (cveEspecialidad, nombreEspecialidad) "
        "VALUES (%(cveEspecialidad)s, %(nombreEspecialidad)s)"
    ),
    'Materia': (
        "INSERT INTO Materia (cveMateria, nombreMateria, horasTeoricas, horasPracticas) "
        "VALUES (%(cveMateria)s, %(nombreMateria)s, %(horasTeoricas)s, %(horasPracticas)s)"
    )
}

REQUIRED_COLUMNS = {
    'Alumno': ['numControl', 'apellidoPaterno', 'apellidoMaterno', 'nombre', 
               'discapacidad', 'carrera', 'ingreso', 'periodo'],
    'Personal': ['cvePersonal', 'apellidoPaterno', 'apellidoMaterno', 'nombre'],
    'Especialidad': ['cveEspecialidad', 'nombreEspecialidad'],
    'Materia': ['cveMateria', 'nombreMateria', 'horasTeoricas', 'horasPracticas']
}

# ------------------------------
# Clases de Utilidad
# ------------------------------
class DBManager:
    """Manejador singleton para conexiones a la base de datos"""
    _instance = None

    @classmethod
    def get_connection(cls) -> mysql.connector.MySQLConnection:
        if cls._instance is None or not cls._instance.is_connected():
            cls._instance = mysql.connector.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                user=os.getenv('DB_USER', 'root'),
                password=os.getenv('DB_PASS', '123456789'),
                database=os.getenv('DB_NAME', 'escuela'),
                autocommit=False
            )
        return cls._instance

# ------------------------------
# Funciones Principales
# ------------------------------
def validate_dataframe(df: pd.DataFrame, table_name: str) -> bool:
    """Valida que el DataFrame tenga las columnas requeridas"""
    required = REQUIRED_COLUMNS.get(table_name, [])
    missing = [col for col in required if col not in df.columns]
    
    if missing:
        logging.error(f"Columnas faltantes en CSV para {table_name}: {missing}")
        return False
    return True

def clean_data(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    """Limpieza básica de datos"""
    # Convertir booleanos para MySQL (1/0)
    if table_name == 'Alumno' and 'discapacidad' in df.columns:
        df['discapacidad'] = df['discapacidad'].astype(int)
    
    # Eliminar filas completamente vacías
    return df.dropna(how='all')

def import_data_to_db(df: pd.DataFrame, table_name: str) -> Dict[str, int]:
    """Importa los datos a la base de datos"""
    results = {'success': 0, 'errors': 0}
    conn = None
    cursor = None

    try:
        conn = DBManager.get_connection()
        cursor = conn.cursor()
        
        # Convertir DataFrame a lista de diccionarios
        data = df.to_dict('records')
        
        # Insertar en bloques de 100
        batch_size = 100
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            try:
                cursor.executemany(INSTRUCCIONES_INSERT[table_name], batch)
                results['success'] += len(batch)
            except mysql.connector.Error as e:
                logging.error(f"Error en lote {i//batch_size}: {e}")
                results['errors'] += len(batch)
                conn.rollback()  # Revertir el lote fallido
        
        conn.commit()
        
    except Exception as e:
        logging.error(f"Error general: {e}", exc_info=True)
        if conn:
            conn.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
    
    return results

def show_main_ui() -> Optional[Dict[str, str]]:
    """Muestra la interfaz gráfica y retorna la configuración"""
    root = Tk()
    root.title("Importador Escolar v2.0")
    root.geometry("400x300")
    
    # Variables de la UI
    file_path = tk.StringVar()
    table_name = tk.StringVar()
    results = None
    
    def on_submit():
        nonlocal results
        try:
            if not file_path.get():
                messagebox.showwarning("Advertencia", "Selecciona un archivo CSV")
                return
                
            if not table_name.get() in INSTRUCCIONES_INSERT:
                messagebox.showwarning("Advertencia", "Selecciona una tabla válida")
                return
                
            df = pd.read_csv(file_path.get(), encoding='latin1')
            df = clean_data(df, table_name.get())
            
            if not validate_dataframe(df, table_name.get()):
                messagebox.showerror("Error", "El CSV no tiene las columnas requeridas")
                return
                
            import_results = import_data_to_db(df, table_name.get())
            messagebox.showinfo(
                "Resultado",
                f"Datos importados:\n\nÉxitos: {import_results['success']}\nErrores: {import_results['errors']}"
            )
            root.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error:\n\n{str(e)}")
            logging.exception("Error en la interfaz")

    # Widgets de la UI
    ttk.Label(root, text="Seleccionar archivo CSV:").pack(pady=5)
    ttk.Entry(root, textvariable=file_path, width=40).pack(pady=5)
    ttk.Button(root, text="Examinar", command=lambda: file_path.set(
        filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
    )).pack(pady=5)

    ttk.Label(root, text="Seleccionar tabla destino:").pack(pady=5)
    ttk.Combobox(root, textvariable=table_name, 
                values=list(INSTRUCCIONES_INSERT.keys())).pack(pady=5)

    ttk.Button(root, text="Importar Datos", command=on_submit).pack(pady=20)
    
    root.mainloop()
    return results

# ------------------------------
# Punto de entrada principal
# ------------------------------
if __name__ == "__main__":
    try:
        print("Iniciando importador de datos...")
        show_main_ui()
    except Exception as e:
        logging.critical(f"Error no manejado: {e}", exc_info=True)
        messagebox.showerror("Error Crítico", f"El programa falló:\n\n{str(e)}")
    finally:
        conn = DBManager._instance
        if conn and conn.is_connected():
            conn.close()
        print("Programa terminado. Revise el archivo data_importer.log para detalles.")