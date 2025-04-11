import mysql.connector
import pandas as pd
from tkinter import Tk, Button, Toplevel, Entry, Label, filedialog, messagebox

# Conexión a la base de datos
conexion = mysql.connector.connect(
    host="localhost",
    user="root",
    password="mysqlsebas",
    database="escuela"
)
cursor = conexion.cursor()

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
            # Validaciones de existencia
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

# Ventana principal
root = Tk()
root.title("Sistema de Inserción de Datos")
root.geometry("300x200")  # <-- Aquí ajustas el tamaño


# Botones de inserción desde CSV
Button(root, text="Insertar Alumno desde CSV", command=lambda: insertar_desde_csv('Alumno')).pack(pady=2)
Button(root, text="Insertar Personal desde CSV", command=lambda: insertar_desde_csv('Personal')).pack(pady=2)
Button(root, text="Insertar Especialidad desde CSV", command=lambda: insertar_desde_csv('Especialidad')).pack(pady=2)
Button(root, text="Insertar Materia desde CSV", command=lambda: insertar_desde_csv('Materia')).pack(pady=2)

# Botones de inserciones manuales
Button(root, text="Insertar Grupo Manualmente", command=formulario_grupo).pack(pady=5)
Button(root, text="Insertar Hora Disponible Manualmente", command=formulario_horadisp).pack(pady=5)

root.mainloop()
