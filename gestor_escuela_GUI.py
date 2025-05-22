import mysql.connector
from mysql.connector import errorcode
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
import os
import getpass
from functools import wraps

# ==============================================
# CONFIGURACIÓN BÁSICA
# ==============================================
DB_CONFIG = {
    'host': 'localhost',
    'database': 'escuela',
    'port': 3306
    
}# por si acaso agrega para la contraseña de la base de datos


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
            messagebox.showerror("Error", "No tienes permisos para importar a esta tabla")
            return

        # Leer archivo CSV
        df = pd.read_csv(archivo, encoding='latin1')
        
        # Verificar columnas
        columnas_requeridas = TABLAS_IMPORTABLES.get(tabla)
        if not columnas_requeridas:
            messagebox.showerror("Error", f"Tabla {tabla} no permitida para importación")
            return
            
        faltantes = [col for col in columnas_requeridas if col not in df.columns]
        if faltantes:
            messagebox.showerror("Error", f"Faltan columnas requeridas: {', '.join(faltantes)}")
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
        messagebox.showinfo("Éxito", f"Importación completa: {exitosos}/{total} registros insertados")
        
    except Exception as e:
        usuario_actual['conn'].rollback()
        messagebox.showerror("Error", f"Error durante la importación: {str(e)}")
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
                messagebox.showerror("Acceso denegado", "No tienes los permisos necesarios")
                return None
            return func(usuario_actual, *args, **kwargs)
        return wrapper
    return decorador

# ==============================================
# CLASE PRINCIPAL DE LA APLICACIÓN
# ==============================================
class SistemaEscolarApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Gestión Escolar")
        self.root.geometry("800x600")
        
        self.usuario_actual = None
        self.conexion = None
        
        # Configurar estilo
        self.style = ttk.Style()
        self.style.configure('TFrame', background='#f0f0f0')
        self.style.configure('TLabel', background='#f0f0f0', font=('Arial', 10))
        self.style.configure('TButton', font=('Arial', 10))
        self.style.configure('Title.TLabel', font=('Arial', 16, 'bold'))
        
        self.mostrar_pantalla_login()
    
    def mostrar_pantalla_login(self):
        """Muestra la pantalla de inicio de sesión"""
        self.limpiar_pantalla()
        
        frame = ttk.Frame(self.root)
        frame.pack(expand=True, padx=50, pady=50)
        
        ttk.Label(frame, text="SISTEMA DE GESTIÓN ESCOLAR", style='Title.TLabel').grid(row=0, column=0, columnspan=2, pady=20)
        
        ttk.Label(frame, text="Usuario:").grid(row=1, column=0, sticky='e', padx=5, pady=5)
        self.usuario_entry = ttk.Entry(frame, width=30)
        self.usuario_entry.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(frame, text="Contraseña:").grid(row=2, column=0, sticky='e', padx=5, pady=5)
        self.password_entry = ttk.Entry(frame, width=30, show='*')
        self.password_entry.grid(row=2, column=1, padx=5, pady=5)
        
        ttk.Button(frame, text="Iniciar sesión", command=self.login).grid(row=3, column=0, columnspan=2, pady=15)
        
        # Información de usuarios de prueba
        info_frame = ttk.LabelFrame(frame, text="Usuarios de prueba")
        info_frame.grid(row=4, column=0, columnspan=2, pady=10, padx=5, sticky='ew')
        
        info_text = """1. admin@localhost (Admin123#) - Rol: Administrador
2. mariagarcia@localhost (Prof123#) - Rol: Profesor
3. asistente1@localhost (Asist123#) - Rol: Asistente
4. invitado@localhost (Consulta123#) - Rol: Consulta"""
        
        ttk.Label(info_frame, text=info_text, justify='left').pack(padx=5, pady=5)
    
    def login(self):
        """Maneja el proceso de inicio de sesión"""
        usuario = self.usuario_entry.get()
        contraseña = self.password_entry.get()
        
        try:
            conn = DBEscuela.conectar(usuario.split('@')[0], contraseña)
            rol = obtener_rol(conn, usuario)
            self.usuario_actual = {'usuario': usuario, 'rol': rol, 'conn': conn}
            
            # Mostrar el menú según el rol
            if rol == 'admin':
                self.menu_administrador()
            elif rol == 'profesor':
                self.menu_profesor()
            elif rol == 'asistente':
                self.menu_asistente()
            else:
                self.menu_consulta()
                
            messagebox.showinfo("Bienvenido", f"Bienvenido {usuario} (Rol: {rol})")
            
        except Exception as e:
            messagebox.showerror("Error de autenticación", str(e))
    
    def limpiar_pantalla(self):
        """Limpia todos los widgets de la pantalla"""
        for widget in self.root.winfo_children():
            widget.destroy()
    
    def menu_administrador(self):
        """Muestra el menú para administradores"""
        self.limpiar_pantalla()
        
        # Barra de título
        title_frame = ttk.Frame(self.root)
        title_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(title_frame, text=f"Menú Administrador - Usuario: {self.usuario_actual['usuario']}", 
                 style='Title.TLabel').pack(side='left')
        
        ttk.Button(title_frame, text="Cerrar sesión", command=self.mostrar_pantalla_login).pack(side='right')
        
        # Menú de opciones
        menu_frame = ttk.Frame(self.root)
        menu_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        ttk.Button(menu_frame, text="Ver todos los alumnos", 
                  command=lambda: self.ver_alumnos()).grid(row=0, column=0, padx=10, pady=10, sticky='ew')
        
        ttk.Button(menu_frame, text="Importar datos desde CSV", 
                  command=lambda: self.importar_csv()).grid(row=0, column=1, padx=10, pady=10, sticky='ew')
        
        ttk.Button(menu_frame, text="Crear nuevo usuario", 
                  command=lambda: self.crear_usuario()).grid(row=1, column=0, padx=10, pady=10, sticky='ew')
        
        ttk.Button(menu_frame, text="Ver todas las materias", 
                  command=lambda: self.ver_materias()).grid(row=1, column=1, padx=10, pady=10, sticky='ew')
        
        ttk.Button(menu_frame, text="Salir", 
                  command=self.root.quit).grid(row=2, column=0, columnspan=2, pady=20, sticky='ew')
    
    def menu_asistente(self):
        """Muestra el menú para asistentes"""
        self.limpiar_pantalla()
        
        # Barra de título
        title_frame = ttk.Frame(self.root)
        title_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(title_frame, text=f"Menú Asistente - Usuario: {self.usuario_actual['usuario']}", 
                 style='Title.TLabel').pack(side='left')
        
        ttk.Button(title_frame, text="Cerrar sesión", command=self.mostrar_pantalla_login).pack(side='right')
        
        # Menú de opciones
        menu_frame = ttk.Frame(self.root)
        menu_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        ttk.Button(menu_frame, text="Registrar nuevo alumno", 
                  command=lambda: self.registrar_alumno()).grid(row=0, column=0, padx=10, pady=10, sticky='ew')
        
        ttk.Button(menu_frame, text="Importar alumnos desde CSV", 
                  command=lambda: self.importar_csv()).grid(row=0, column=1, padx=10, pady=10, sticky='ew')
        
        ttk.Button(menu_frame, text="Ver lista de alumnos", 
                  command=lambda: self.ver_alumnos()).grid(row=1, column=0, padx=10, pady=10, sticky='ew')
        
        ttk.Button(menu_frame, text="Salir", 
                  command=self.root.quit).grid(row=2, column=0, columnspan=2, pady=20, sticky='ew')
    
    def menu_profesor(self):
        """Muestra el menú para profesores (simplificado)"""
        self.limpiar_pantalla()
        
        title_frame = ttk.Frame(self.root)
        title_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(title_frame, text=f"Menú Profesor - Usuario: {self.usuario_actual['usuario']}", 
                 style='Title.TLabel').pack(side='left')
        
        ttk.Button(title_frame, text="Cerrar sesión", command=self.mostrar_pantalla_login).pack(side='right')
        
        messagebox.showinfo("Información", "Menú de profesor (funcionalidad simplificada)")
        self.root.quit()
    
    def menu_consulta(self):
        """Muestra el menú para usuarios de solo consulta"""
        self.limpiar_pantalla()
        
        title_frame = ttk.Frame(self.root)
        title_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(title_frame, text=f"Menú Consulta - Usuario: {self.usuario_actual['usuario']}", 
                 style='Title.TLabel').pack(side='left')
        
        ttk.Button(title_frame, text="Cerrar sesión", command=self.mostrar_pantalla_login).pack(side='right')
        
        messagebox.showinfo("Información", "Menú de consulta (funcionalidad simplificada)")
        self.root.quit()
    
    @requiere_rol('admin', 'asistente')
    def registrar_alumno(self, usuario_actual=None):
        """Registra un nuevo alumno (simplificado)"""
        messagebox.showinfo("Información", "(Simulación) Alumno registrado correctamente")
    
    @requiere_rol('admin')
    def crear_usuario(self, usuario_actual=None):
        """Crea un nuevo usuario"""
        # Crear ventana emergente
        popup = tk.Toplevel(self.root)
        popup.title("Crear nuevo usuario")
        popup.geometry("400x300")
        
        ttk.Label(popup, text="Crear nuevo usuario", style='Title.TLabel').pack(pady=10)
        
        # Formulario
        form_frame = ttk.Frame(popup)
        form_frame.pack(padx=20, pady=10, fill='x')
        
        ttk.Label(form_frame, text="Nombre de usuario:").grid(row=0, column=0, sticky='e', pady=5)
        usuario_entry = ttk.Entry(form_frame)
        usuario_entry.grid(row=0, column=1, sticky='ew', pady=5, padx=5)
        
        ttk.Label(form_frame, text="Contraseña:").grid(row=1, column=0, sticky='e', pady=5)
        password_entry = ttk.Entry(form_frame, show='*')
        password_entry.grid(row=1, column=1, sticky='ew', pady=5, padx=5)
        
        ttk.Label(form_frame, text="Rol:").grid(row=2, column=0, sticky='e', pady=5)
        rol_combobox = ttk.Combobox(form_frame, values=['admin', 'profesor', 'asistente', 'consulta'])
        rol_combobox.grid(row=2, column=1, sticky='ew', pady=5, padx=5)
        
        # Botones
        button_frame = ttk.Frame(popup)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Crear", command=lambda: self.procesar_crear_usuario(
            usuario_entry.get(), password_entry.get(), rol_combobox.get(), popup)).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Cancelar", command=popup.destroy).pack(side='left', padx=5)
    
    def procesar_crear_usuario(self, usuario, password, rol, popup):
        """Procesa la creación de un nuevo usuario"""
        if not usuario or not password or not rol:
            messagebox.showerror("Error", "Todos los campos son obligatorios")
            return
            
        try:
            cursor = self.usuario_actual['conn'].cursor()
            cursor.execute(f"CREATE USER '{usuario}'@'localhost' IDENTIFIED BY '{password}'")
            cursor.execute(f"GRANT '{rol}' TO '{usuario}'@'localhost'")
            self.usuario_actual['conn'].commit()
            messagebox.showinfo("Éxito", f"Usuario {usuario} creado con rol {rol}")
            popup.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Error al crear usuario: {str(e)}")
        finally:
            if 'cursor' in locals():
                cursor.close()
    
    def ver_alumnos(self):
        """Muestra una lista de alumnos en una nueva ventana"""
        try:
            cursor = self.usuario_actual['conn'].cursor(dictionary=True)
            cursor.execute("SELECT * FROM Alumno LIMIT 50")
            alumnos = cursor.fetchall()
            
            # Crear ventana emergente
            popup = tk.Toplevel(self.root)
            popup.title("Lista de Alumnos")
            popup.geometry("800x600")
            
            # Frame para el árbol
            tree_frame = ttk.Frame(popup)
            tree_frame.pack(fill='both', expand=True, padx=10, pady=10)
            
            # Crear Treeview
            tree = ttk.Treeview(tree_frame, columns=('numControl', 'nombre', 'apellidos', 'ingreso'), show='headings')
            
            # Configurar columnas
            tree.heading('numControl', text='Núm. Control')
            tree.heading('nombre', text='Nombre')
            tree.heading('apellidos', text='Apellidos')
            tree.heading('ingreso', text='Ingreso')
            
            tree.column('numControl', width=100)
            tree.column('nombre', width=150)
            tree.column('apellidos', width=200)
            tree.column('ingreso', width=100)
            
            # Añadir datos
            for alumno in alumnos:
                apellidos = f"{alumno['apellidoPaterno']} {alumno['apellidoMaterno']}"
                tree.insert('', 'end', values=(
                    alumno['numControl'],
                    alumno['nombre'],
                    apellidos,
                    alumno['ingreso']
                ))
            
            # Añadir scrollbar
            scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            
            # Empaquetar
            tree.pack(side='left', fill='both', expand=True)
            scrollbar.pack(side='right', fill='y')
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al obtener alumnos: {str(e)}")
        finally:
            if 'cursor' in locals():
                cursor.close()
    
    def ver_materias(self):
        """Muestra una lista de materias en una nueva ventana"""
        try:
            cursor = self.usuario_actual['conn'].cursor(dictionary=True)
            cursor.execute("SELECT * FROM Materia LIMIT 50")
            materias = cursor.fetchall()
            
            # Crear ventana emergente
            popup = tk.Toplevel(self.root)
            popup.title("Lista de Materias")
            popup.geometry("600x400")
            
            # Frame para el árbol
            tree_frame = ttk.Frame(popup)
            tree_frame.pack(fill='both', expand=True, padx=10, pady=10)
            
            # Crear Treeview
            tree = ttk.Treeview(tree_frame, columns=('clave', 'nombre', 'horas'), show='headings')
            
            # Configurar columnas
            tree.heading('clave', text='Clave')
            tree.heading('nombre', text='Nombre')
            tree.heading('horas', text='Horas (T/P)')
            
            tree.column('clave', width=100)
            tree.column('nombre', width=300)
            tree.column('horas', width=100)
            
            # Añadir datos
            for materia in materias:
                horas = f"{materia['horasTeoricas']}/{materia['horasPracticas']}"
                tree.insert('', 'end', values=(
                    materia['cveMateria'],
                    materia['nombreMateria'],
                    horas
                ))
            
            # Añadir scrollbar
            scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            
            # Empaquetar
            tree.pack(side='left', fill='both', expand=True)
            scrollbar.pack(side='right', fill='y')
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al obtener materias: {str(e)}")
        finally:
            if 'cursor' in locals():
                cursor.close()
    
    def importar_csv(self):
        """Muestra la interfaz para importar datos desde CSV"""
        # Crear ventana emergente
        popup = tk.Toplevel(self.root)
        popup.title("Importar desde CSV")
        popup.geometry("500x300")
        
        ttk.Label(popup, text="Importar datos desde CSV", style='Title.TLabel').pack(pady=10)
        
        # Frame principal
        main_frame = ttk.Frame(popup)
        main_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Selección de tabla
        ttk.Label(main_frame, text="Tabla destino:").grid(row=0, column=0, sticky='e', pady=5)
        self.tabla_combobox = ttk.Combobox(main_frame, values=list(TABLAS_IMPORTABLES.keys()))
        self.tabla_combobox.grid(row=0, column=1, sticky='ew', pady=5, padx=5)
        
        # Verificar permisos para asistentes
        if self.usuario_actual['rol'] == 'asistente':
            self.tabla_combobox.set('Alumno')
            self.tabla_combobox.config(state='disabled')
        
        # Selección de archivo
        ttk.Label(main_frame, text="Archivo CSV:").grid(row=1, column=0, sticky='e', pady=5)
        self.archivo_entry = ttk.Entry(main_frame)
        self.archivo_entry.grid(row=1, column=1, sticky='ew', pady=5, padx=5)
        ttk.Button(main_frame, text="Examinar", command=self.seleccionar_archivo).grid(row=1, column=2, padx=5)
        
        # Botones
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=3, pady=15)
        
        ttk.Button(button_frame, text="Importar", command=lambda: self.procesar_importacion(popup)).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Cancelar", command=popup.destroy).pack(side='left', padx=5)
    
    def seleccionar_archivo(self):
        """Abre el diálogo para seleccionar archivo"""
        archivo = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if archivo:
            self.archivo_entry.delete(0, tk.END)
            self.archivo_entry.insert(0, archivo)
    
    def procesar_importacion(self, popup):
        """Procesa la importación de datos desde CSV"""
        tabla = self.tabla_combobox.get()
        archivo = self.archivo_entry.get()
        
        if not tabla or not archivo:
            messagebox.showerror("Error", "Debes seleccionar una tabla y un archivo")
            return
            
        # Verificar permisos específicos
        if self.usuario_actual['rol'] == 'asistente' and tabla != 'Alumno':
            messagebox.showerror("Error", "Solo puedes importar datos de alumnos")
            return
            
        if not os.path.exists(archivo):
            messagebox.showerror("Error", "El archivo no existe")
            return
            
        # Confirmar importación
        if messagebox.askyesno("Confirmar", f"¿Importar datos a la tabla {tabla}?"):
            importar_desde_csv(self.usuario_actual, archivo, tabla)
            popup.destroy()

# ==============================================
# EJECUCIÓN PRINCIPAL
# ==============================================
if __name__ == "__main__":
    root = tk.Tk()
    app = SistemaEscolarApp(root)
    root.mainloop()
    DBEscuela.cerrar()