import mysql.connector
import pandas as pd
from tkinter import Tk, Button, Toplevel, Entry, Label, filedialog, messagebox
from tkinter.simpledialog import askstring

# Conexión a la base de datos
conexion = mysql.connector.connect(
    host="localhost",
    user="root",
    password="mysqlsebas",
    database="escuela"
)
cursor = conexion.cursor()

# Ventana principal
root = Tk()
root.withdraw()  # Ocultar ventana principal al inicio

# Verificar credenciales de usuario
def login():
    login_win = Toplevel()
    login_win.title("Iniciar sesión")

    Label(login_win, text="Usuario:").grid(row=0, column=0)
    Label(login_win, text="Contraseña:").grid(row=1, column=0)

    entry_user = Entry(login_win)
    entry_pass = Entry(login_win, show='*')
    entry_user.grid(row=0, column=1)
    entry_pass.grid(row=1, column=1)

    def validar():
        usuario = entry_user.get()
        clave = entry_pass.get()

        cursor.execute("SELECT rol FROM Usuario WHERE usuario=%s AND contraseña=%s", (usuario, clave))
        resultado = cursor.fetchone()
        if resultado:
            rol = resultado[0]
            login_win.destroy()
            mostrar_menu_por_rol(rol)
            root.deiconify()  # Mostrar la ventana principal
        else:
            messagebox.showerror("Error", "Usuario o contraseña incorrectos")

    Button(login_win, text="Ingresar", command=validar).grid(row=2, columnspan=2)

# Mostrar botones según el rol
def mostrar_menu_por_rol(rol):
    Label(root, text=f"Rol: {rol.upper()}", font=("Arial", 12, "bold")).pack(pady=5)
    if rol == 'admin':
        mostrar_admin()
    elif rol == 'docente':
        mostrar_docente()
    elif rol == 'usuario':
        mostrar_usuario()

def mostrar_admin():
    Button(root, text="Insertar Alumno desde CSV", command=lambda: insertar_desde_csv('Alumno')).pack(pady=2)
    Button(root, text="Insertar Personal desde CSV", command=lambda: insertar_desde_csv('Personal')).pack(pady=2)
    Button(root, text="Insertar Especialidad desde CSV", command=lambda: insertar_desde_csv('Especialidad')).pack(pady=2)
    Button(root, text="Insertar Materia desde CSV", command=lambda: insertar_desde_csv('Materia')).pack(pady=2)
    Button(root, text="Insertar Grupo Manualmente", command=formulario_grupo).pack(pady=5)
    Button(root, text="Insertar Hora Disponible Manualmente", command=formulario_horadisp).pack(pady=5)
    Button(root, text="Cerrar sesión", command=cerrar_sesion).pack(pady=10)

def mostrar_docente():
    Button(root, text="Insertar Grupo Manualmente", command=formulario_grupo).pack(pady=5)
    Button(root, text="Insertar Hora Disponible Manualmente", command=formulario_horadisp).pack(pady=5)
    Button(root, text="Cerrar sesión", command=cerrar_sesion).pack(pady=10)

def mostrar_usuario():
    Label(root, text="Acceso solo para consulta.").pack(pady=10)
    Button(root, text="Cerrar sesión", command=cerrar_sesion).pack(pady=10)

def cerrar_sesion():
    for widget in root.winfo_children():
        widget.destroy()
    root.withdraw()
    login()

# Funciones para insertar desde CSV
def insertar_desde_csv(tabla):
    archivo_csv = filedialog.askopenfilename(title=f"Selecciona el archivo CSV para {tabla}", filetypes=[("CSV files", "*.csv")])
    if not archivo_csv:
        return
    try:
        df = pd.read_csv(archivo_csv, encoding='latin1')
        df = df.where(pd.notnull(df), None)

        if tabla == 'Alumno':
            for _, row in df.iterrows():
                cursor.execute("""
                    INSERT INTO Alumno (numControl, apellidoPaterno, apellidoMaterno, nombre, discapacidad, carrera, ingreso, periodo, direccion, fechaNacimiento, cvePE)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, tuple(row))

        elif tabla == 'Personal':
            for _, row in df.iterrows():
                cursor.execute("""
                    INSERT INTO Personal (cvePersonal, apellidoPaterno, apellidoMaterno, nombre, RFC, fechaIngreso, fechaCumpleaños, direccion, puesto)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, tuple(row))

        elif tabla == 'Especialidad':
            for _, row in df.iterrows():
                cursor.execute("""
                    INSERT INTO Especialidad (cveEspecialidad, nombreEspecialidad, cvePE)
                    VALUES (%s, %s, %s)
                """, tuple(row))

        elif tabla == 'Materia':
            for _, row in df.iterrows():
                cursor.execute("""
                    INSERT INTO Materia (cveMateria, nombreMateria, horasTeoricas, horasPracticas)
                    VALUES (%s, %s, %s, %s)
                """, tuple(row))

        conexion.commit()
        messagebox.showinfo("Éxito", f"Datos insertados en la tabla {tabla} correctamente.")

    except Exception as e:
        messagebox.showerror("Error", f"Ocurrió un error: {e}")

# Funciones para formularios manuales
def formulario_grupo():
    def guardar():
        try:
            valores = (
                int(e_idGrupo.get()), int(e_semestre.get()), bool(int(e_ocupada.get())),
                e_cveMateria.get(), e_cvePE.get(), int(e_numSemestre.get()), e_cvePersonal.get()
            )
            cursor.execute("SELECT 1 FROM MateriaPE WHERE cveMateria=%s AND cvePE=%s AND numSemestre=%s", (valores[3], valores[4], valores[5]))
            if not cursor.fetchone():
                messagebox.showerror("Error", "La combinación cveMateria, cvePE y numSemestre no existe en MateriaPE")
                return
            cursor.execute("SELECT 1 FROM Personal WHERE cvePersonal=%s", (valores[6],))
            if not cursor.fetchone():
                messagebox.showerror("Error", "El cvePersonal no existe")
                return
            cursor.execute("""
                INSERT INTO Grupo (idGrupo, semestre, ocupada, cveMateria, cvePE, numSemestre, cvePersonal)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, valores)
            conexion.commit()
            messagebox.showinfo("Éxito", "Grupo insertado correctamente")
            form.destroy()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    form = Toplevel(root)
    form.title("Insertar Grupo")

    etiquetas = ["idGrupo", "semestre", "ocupada (0/1)", "cveMateria", "cvePE", "numSemestre", "cvePersonal"]
    entradas = []
    for i, texto in enumerate(etiquetas):
        Label(form, text=texto).grid(row=i, column=0)
        entrada = Entry(form)
        entrada.grid(row=i, column=1)
        entradas.append(entrada)

    e_idGrupo, e_semestre, e_ocupada, e_cveMateria, e_cvePE, e_numSemestre, e_cvePersonal = entradas
    Button(form, text="Guardar", command=guardar).grid(row=len(etiquetas), columnspan=2)

def formulario_horadisp():
    def guardar():
        try:
            valores = (
                int(e_idGrupo.get()), int(e_semestre.get()), e_hora.get(), e_dia.get(), int(e_cveEA.get()), int(e_numEd.get())
            )
            cursor.execute("SELECT 1 FROM EspacioAcademico WHERE cveEA=%s AND numEd=%s", (valores[4], valores[5]))
            if not cursor.fetchone():
                messagebox.showerror("Error", "El espacio académico no existe")
                return
            cursor.execute("""
                INSERT INTO HoraDisp (idGrupo, semestre, hora, dia, cveEA, numEd)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, valores)
            conexion.commit()
            messagebox.showinfo("Éxito", "Hora disponible insertada correctamente")
            form.destroy()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    form = Toplevel(root)
    form.title("Insertar Hora Disponible")
    etiquetas = ["idGrupo", "semestre", "hora (HH:MM:SS)", "día", "cveEA", "numEd"]
    entradas = []
    for i, texto in enumerate(etiquetas):
        Label(form, text=texto).grid(row=i, column=0)
        entrada = Entry(form)
        entrada.grid(row=i, column=1)
        entradas.append(entrada)

    e_idGrupo, e_semestre, e_hora, e_dia, e_cveEA, e_numEd = entradas
    Button(form, text="Guardar", command=guardar).grid(row=len(etiquetas), columnspan=2)

# Inicia con la pantalla de login
login()

root.mainloop()