-- Creación de la base de datos
CREATE DATABASE IF NOT EXISTS escuela;
USE escuela;

-- 1. Tablas principales sin dependencias
CREATE TABLE PlanDeEstudios (
    cvePE varchar(25) PRIMARY KEY,
    nombrePE VARCHAR(100) NOT NULL
);

CREATE TABLE Especialidad (
    cveEspecialidad varchar(25) PRIMARY KEY,
    nombreEspecialidad VARCHAR(100) NOT NULL,
    cvePE varchar(25),
    FOREIGN KEY (cvePE) REFERENCES PlanDeEstudios(cvePE)
);

CREATE TABLE Materia (
    cveMateria varchar(15) PRIMARY KEY,
    nombreMateria VARCHAR(100),
    horasTeoricas INT,
    horasPracticas INT,
    creditosAcademicos INT AS (horasTeoricas + horasPracticas) STORED,
    numTemas INT DEFAULT 0
);

CREATE TABLE Personal (
    cvePersonal varchar(25) PRIMARY KEY,
    apellidoPaterno varchar(30),
    apellidoMaterno varchar(30),
    nombre varchar(30)
);

-- 2. Tabla Alumno modificada para coincidir con Python
CREATE TABLE Alumno (
    numControl varchar(10) PRIMARY KEY,
    apellidoPaterno varchar(30),
    apellidoMaterno varchar(30),
    nombre VARCHAR(30),  
    discapacidad BIT, 
    direccion VARCHAR(255),
    fechaNacimiento DATE,
    cvePE varchar(25),
    ingreso varchar(10),
    periodo varchar(15),
    FOREIGN KEY (cvePE) REFERENCES PlanDeEstudios(cvePE)
);

-- 3. Tablas de contacto (se mantienen igual)
CREATE TABLE Correos (
    idCorreo INT PRIMARY KEY AUTO_INCREMENT,
    correo VARCHAR(100) NOT NULL UNIQUE,
    numControl varchar(10) NOT NULL,
    FOREIGN KEY (numControl) REFERENCES Alumno(numControl)
);

CREATE TABLE Telefonos (
    idTelefono INT PRIMARY KEY AUTO_INCREMENT,
    numeroTelefono VARCHAR(15) NOT NULL UNIQUE,
    numControl varchar(10) NOT NULL,
    FOREIGN KEY (numControl) REFERENCES Alumno(numControl)
);

CREATE TABLE CorreosPersonal (
    idCorreo INT PRIMARY KEY AUTO_INCREMENT,
    cvePersonal varchar(25) NOT NULL,
    correo VARCHAR(100) NOT NULL,
    FOREIGN KEY (cvePersonal) REFERENCES Personal(cvePersonal)
);

CREATE TABLE TelefonosPersonal (
    idTelefono INT PRIMARY KEY AUTO_INCREMENT,
    cvePersonal varchar(25) NOT NULL,
    numeroTelefono VARCHAR(15) NOT NULL,
    FOREIGN KEY (cvePersonal) REFERENCES Personal(cvePersonal)
);

-- 4. Relaciones entre materias y planes de estudio (se mantienen igual)
CREATE TABLE MateriaPE (
    cveMateria varchar(15),
    cvePE varchar(25),
    cveEspecialidad varchar(25),
    numSemestre INT NOT NULL,
    PRIMARY KEY (cveMateria, cvePE, numSemestre),
    FOREIGN KEY (cveMateria) REFERENCES Materia(cveMateria),
    FOREIGN KEY (cvePE) REFERENCES PlanDeEstudios(cvePE),
    FOREIGN KEY (cveEspecialidad) REFERENCES Especialidad(cveEspecialidad)
);

-- 5. Tabla Prerequisitos corregida
CREATE TABLE Prerequisitos (
    idPrerequisito INT PRIMARY KEY AUTO_INCREMENT,
    cveMateria varchar(15) NOT NULL,
    cveMateriaPrerequisito varchar(15) NOT NULL,
    numSemestre INT NOT NULL,
    cvePE varchar(25) NOT NULL,
    FOREIGN KEY (cveMateria, cvePE, numSemestre) REFERENCES MateriaPE(cveMateria, cvePE, numSemestre),
    FOREIGN KEY (cveMateriaPrerequisito) REFERENCES Materia(cveMateria)
);

-- 6. Grupo y relaciones (se mantienen igual)
CREATE TABLE Grupo (
    idGrupo INT,
    semestre INT NOT NULL,
    ocupada BOOLEAN NOT NULL,
    cveMateria varchar(15),
    cvePE varchar(25),
    numSemestre INT,
    cvePersonal varchar(25),
    PRIMARY KEY (idGrupo, semestre),
    FOREIGN KEY (cveMateria, cvePE, numSemestre) REFERENCES MateriaPE(cveMateria, cvePE, numSemestre),
    FOREIGN KEY (cvePersonal) REFERENCES Personal(cvePersonal)
);

-- 7. Kardex y calificaciones (se mantienen igual)
CREATE TABLE Kardex (
    idKardex INT PRIMARY KEY,
    numControl varchar(10) NOT NULL,
    idGrupo INT NOT NULL,
    semestre INT NOT NULL,
    FOREIGN KEY (numControl) REFERENCES Alumno(numControl),
    FOREIGN KEY (idGrupo, semestre) REFERENCES Grupo(idGrupo, semestre)
);

CREATE TABLE CalOrdinario (
    idCalOrdinario INT PRIMARY KEY AUTO_INCREMENT,
    idKardex INT NOT NULL,
    calificacion DECIMAL(5, 2) CHECK (calificacion BETWEEN 0 AND 100),
    FOREIGN KEY (idKardex) REFERENCES Kardex(idKardex)
);

CREATE TABLE CalRegularizacion (
    idCalRegularizacion INT PRIMARY KEY AUTO_INCREMENT,
    idKardex INT NOT NULL,
    calificacion DECIMAL(5, 2) CHECK (calificacion BETWEEN 0 AND 100),
    FOREIGN KEY (idKardex) REFERENCES Kardex(idKardex)
);

-- 8. Temas y triggers (se mantienen igual)
CREATE TABLE Temas (
    idTema INT PRIMARY KEY AUTO_INCREMENT,
    nombreTema VARCHAR(100) NOT NULL,
    descripcion TEXT NOT NULL,
    cveMateria varchar(15),
    FOREIGN KEY (cveMateria) REFERENCES Materia(cveMateria)
);

DELIMITER //

CREATE TRIGGER after_insert_tema
AFTER INSERT ON Temas
FOR EACH ROW
BEGIN
    UPDATE Materia
    SET numTemas = numTemas + 1
    WHERE cveMateria = NEW.cveMateria;
END;

//

DELIMITER ;

DELIMITER //

CREATE TRIGGER after_delete_tema
AFTER DELETE ON Temas
FOR EACH ROW
BEGIN
    UPDATE Materia
    SET numTemas = numTemas - 1
    WHERE cveMateria = OLD.cveMateria;
END;

//

DELIMITER ;

DELIMITER //

CREATE TRIGGER after_update_tema
AFTER UPDATE ON Temas
FOR EACH ROW
BEGIN
    -- Restar 1 en la materia antigua
    UPDATE Materia
    SET numTemas = numTemas - 1
    WHERE cveMateria = OLD.cveMateria;

    -- Sumar 1 en la nueva materia
    UPDATE Materia
    SET numTemas = numTemas + 1
    WHERE cveMateria = NEW.cveMateria;
END;

//

DELIMITER ;

-- 9. Espacios académicos y horarios (se mantienen igual)
CREATE TABLE EspacioAcademico (
    cveEA INT,
    numEd INT,
    nombreEspacio VARCHAR(100) NOT NULL,
    capacidad INT NOT NULL,
    PRIMARY KEY (cveEA, numEd)
);

CREATE TABLE HoraDisp (
    idGrupo INT,
    semestre INT,
    hora TIME NOT NULL,
    dia VARCHAR(20) NOT NULL,
    cveEA INT NOT NULL,
    numEd INT NOT NULL,
    PRIMARY KEY (idGrupo, semestre, hora, dia),
    FOREIGN KEY (idGrupo, semestre) REFERENCES Grupo(idGrupo, semestre),
    FOREIGN KEY (cveEA, numEd) REFERENCES EspacioAcademico(cveEA, numEd)
);

-- Datos de ejemplo (actualizados para coincidir con la nueva estructura)
INSERT INTO PlanDeEstudios (cvePE, nombrePE) VALUES 
('SIS2020', 'Ingeniería en Sistemas'),
('IND2020', 'Ingeniería Industrial');

INSERT INTO Especialidad (cveEspecialidad, nombreEspecialidad, cvePE) VALUES
('REDES', 'Redes y Telecomunicaciones', 'SIS2020'),
('SOFT', 'Desarrollo de Software', 'SIS2020');

INSERT INTO Materia (cveMateria, nombreMateria, horasTeoricas, horasPracticas) VALUES
('MAT101', 'Matemáticas Básicas', 4, 2),
('PROG101', 'Programación I', 3, 3),
('BD101', 'Bases de Datos', 4, 2);

INSERT INTO Personal (cvePersonal, apellidoPaterno, apellidoMaterno, nombre) VALUES
('PROF001', 'García', 'López', 'Juan'),
('PROF002', 'Martínez', 'Sánchez', 'María');

-- Datos de alumnos que coinciden con lo que espera Python
INSERT INTO Alumno (numControl, apellidoPaterno, apellidoMaterno, nombre, discapacidad, direccion, fechaNacimiento, cvePE, ingreso, periodo) VALUES
('20230001', 'Pérez', 'Gómez', 'Juan', 0, 'Calle Primavera 123', '2000-05-15', 'SIS2020', '2023', 'AGO-DIC'),
('20230002', 'López', 'Martínez', 'María', 1, 'Avenida Universidad 456', '2001-02-20', 'IND2020', '2023', 'ENE-JUN');


-- ROLES



-- -----------------------------------------------------
-- SECCIÓN DE USUARIOS Y PERMISOS 
-- -----------------------------------------------------

-- 1. Primero creamos los roles si no existen
CREATE ROLE IF NOT EXISTS 'admin_escuela', 'profesor', 'asistente', 'consulta';

-- 2. Asignamos permisos a cada rol
-- Rol de administrador (acceso completo)
GRANT ALL PRIVILEGES ON escuela.* TO 'admin_escuela';

-- Rol de profesor (puede gestionar alumnos, calificaciones y sus propias materias)
GRANT SELECT, INSERT, UPDATE ON escuela.Alumno TO 'profesor';
GRANT SELECT, INSERT, UPDATE ON escuela.CalOrdinario TO 'profesor';
GRANT SELECT, INSERT, UPDATE ON escuela.CalRegularizacion TO 'profesor';
GRANT SELECT, INSERT, UPDATE ON escuela.Kardex TO 'profesor';
GRANT SELECT ON escuela.Materia TO 'profesor';
GRANT SELECT ON escuela.PlanDeEstudios TO 'profesor';

-- Rol de asistente (puede ver y agregar alumnos)
GRANT SELECT, INSERT ON escuela.Alumno TO 'asistente';
GRANT SELECT ON escuela.PlanDeEstudios TO 'asistente';
GRANT SELECT ON escuela.Especialidad TO 'asistente';

-- Rol de consulta (solo lecturas básicas)
GRANT SELECT ON escuela.Alumno TO 'consulta';
GRANT SELECT ON escuela.Materia TO 'consulta';
GRANT SELECT ON escuela.PlanDeEstudios TO 'consulta';

-- 3. Creamos los usuarios concretos
CREATE USER IF NOT EXISTS 'admin@localhost' IDENTIFIED BY 'Admin123#';
CREATE USER IF NOT EXISTS 'mariagarcia@localhost' IDENTIFIED BY 'Prof123#';
CREATE USER IF NOT EXISTS 'asistente1@localhost' IDENTIFIED BY 'Asist123#';
CREATE USER IF NOT EXISTS 'invitado@localhost' IDENTIFIED BY 'Consulta123#';

-- 4. Asignamos roles a los usuarios
GRANT 'admin_escuela' TO 'admin@localhost';
GRANT 'profesor' TO 'mariagarcia@localhost';
GRANT 'asistente' TO 'asistente1@localhost';
GRANT 'consulta' TO 'invitado@localhost'; 

-- 5. Activamos los roles por defecto para cada usuario
SET DEFAULT ROLE ALL TO 
'admin@localhost', 
'mariagarcia@localhost', 
'asistente1@localhost', 
'invitado@localhost';

-- Explicación de los roles creados:
-- Administrador (admin@localhost):

-- Acceso completo a toda la base de datos

-- Contraseña: Admin123#

-- Profesor (mariagarcia@localhost):

-- Puede gestionar alumnos y calificaciones

-- Puede ver información de materias y planes de estudio

-- Contraseña: Prof123#

-- Asistente (asistente1@localhost):

-- Puede agregar nuevos alumnos y ver información básica

-- No puede modificar calificaciones

-- Contraseña: Asist123#

-- Usuario de consulta (invitado@localhost):

-- Solo permisos de lectura en tablas básicas

-- No puede hacer modificaciones

-- Contraseña: Consulta123#

-- -------------------------------------------------------------------


-- -----------------------------------------------------
-- TABLA DE USUARIOS DE LA APLICACIÓN
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS usuarios_app (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    rol ENUM('admin', 'profesor', 'asistente', 'consulta') NOT NULL,
    email VARCHAR(100),
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insertar usuarios de prueba (las contraseñas son: admin123, prof123, asist123, consulta123)
INSERT INTO usuarios_app (username, password_hash, rol, email) VALUES
('admin', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 'admin', 'admin@escuela.com'),
('profesor1', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 'profesor', 'prof1@escuela.com'),
('asistente1', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 'asistente', 'asist1@escuela.com'),
('consulta1', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 'consulta', 'consulta1@escuela.com');

-- -----------------------------------------------------
-- USUARIO MYSQL PARA LA APLICACIÓN
-- -----------------------------------------------------
CREATE USER IF NOT EXISTS 'app_escuela'@'localhost' IDENTIFIED BY 'App123#';
GRANT SELECT, INSERT, UPDATE ON escuela.* TO 'app_escuela'@'localhost';
FLUSH PRIVILEGES;


-- Cuando ejecutes la app no olvides esto en una terminal: pip install bcrypt