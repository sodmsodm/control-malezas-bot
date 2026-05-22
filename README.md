# ControlMalezasBot — Instrucciones de instalación

## Opción A: Correr en tu computadora (para probar)

### 1. Instalar Python
- Descargá Python desde https://www.python.org/downloads/
- Instalá con la opción "Add to PATH" marcada

### 2. Instalar dependencias
Abrí una terminal (cmd en Windows) y ejecutá:
```
pip install python-telegram-bot==20.7 anthropic==0.25.0
```

### 3. Configurar credenciales
El archivo .env ya tiene tus credenciales configuradas.
El bot las lee automáticamente.

### 4. Correr el bot
```
python bot.py
```
El bot queda corriendo mientras la terminal esté abierta.

---

## Opción B: Subir a Railway (corre 24/7 gratis)

### 1. Crear cuenta en Railway
- Entrá a https://railway.app
- Registrate con GitHub (necesitás cuenta de GitHub)

### 2. Subir el código a GitHub
- Creá repositorio nuevo en https://github.com/new
- Subí todos estos archivos

### 3. Crear proyecto en Railway
- "New Project" → "Deploy from GitHub repo"
- Seleccioná tu repositorio

### 4. Agregar variables de entorno en Railway
En el panel de Railway → Variables:
- TELEGRAM_TOKEN = (tu token)
- ANTHROPIC_API_KEY = (tu API key)

### 5. El bot queda corriendo solo 24/7

---

## Comandos del bot
- /start — Mensaje de bienvenida
- /nuevo — Reinicia la conversación

## Ejemplos de preguntas
- "¿Qué herbicidas uso para crucíferas en PEE de soja?"
- "Control de yuyo colorado en maíz post-emergente"
- "Opciones para Parietaria en barbecho largo"
- "¿Qué puedo usar en Girasol CL para malezas generales?"
