# Instrucciones para sincronizar la base de datos

## ¿Por qué hay que hacer esto?
Tu BD tiene columnas (categoria, peso_kg, etc.) que fueron agregadas por migraciones
que se perdieron (0002 y 0003 no estaban en el ZIP). Ahora el código las reconoce
correctamente, pero hay que decirle a Django que esas migraciones "ya se aplicaron".

## Pasos a seguir (en orden):

### 1. Activa tu entorno virtual si lo tienes
```
cd C:\Users\abdyN\OneDrive\Documentos\GU\8VO CUATRIMESTRE\abel_project\net-fight
```

### 2. Aplica la migración nueva con --fake-initial para columnas que ya existen
```
python manage.py migrate events 0002 --fake
```

Si ese comando falla porque dice que 0002 ya existe, prueba:
```
python manage.py migrate events 0002_userprofile_full_update --fake
```

### 3. Si ninguno funciona, aplica sin --fake (para columnas que aún NO existen)
```
python manage.py migrate
```

### 4. Verifica que no haya errores pendientes
```
python manage.py showmigrations events
```
Deberías ver todas con [X].

### 5. Corre el servidor
```
python manage.py runserver
```

## IMPORTANTE: carpeta media/perfiles/
Django guardará las fotos de perfil en media/perfiles/
Esta carpeta se crea automáticamente al subir la primera foto.
