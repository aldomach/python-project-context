# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.0.0/).

---

## [0.0.4] - 2026-02-05

### Agregado
- Selector de **estilo de árbol de directorios** en la UI: ASCII, Unicode, ASCII+, Simple, Dots
- Soporte del parámetro `tree_style` en la lógica de generación

### Corregido
- Eliminada la redirección de `sys.stdout` con `io.TextIOWrapper` que causaba problemas de encoding en algunos entornos

---

## [0.0.3] - 2026-02-05

### Cambiado
- **Unificación completa** de CLI y UI en un solo archivo `project_context_generator.py`
- La UI (PyQt6) se importa dinámicamente solo si no se pasan argumentos CLI
- Eliminado el archivo separado `project_context_generator_ui.py`

### Agregado
- Corrección de encoding UTF-8 en stdout (`io.TextIOWrapper`) para compatibilidad en Windows
- Mensaje de error amigable cuando PyQt6 no está instalado

### Corregido
- Comportamiento del modo CLI: detecta correctamente si se pasaron argumentos para no abrir la UI

---

## [0.0.2] - 2026-02-05

### Agregado
- **Interfaz gráfica** con PyQt6 en archivo separado (`project_context_generator_ui.py`)
  - Selector de directorio
  - Checkboxes para secciones (árbol, índice, estructura de código)
  - Selector de nivel de detalle (completa / rápida)
  - Vista previa del resultado
  - Botón de copia al portapapeles
- Flag `--ui` en el CLI para abrir la interfaz gráfica desde la terminal
- Soporte de `*args` y `**kwargs` en la extracción de firmas de funciones
- Método `extract_quick_structure` para estructura rápida (solo firmas)
- Opción `--quick` en el CLI

### Corregido
- Manejo de nodos `ast.Subscript` y `ast.Constant` en `_get_name`
- Encoding al leer archivos Python (forzado a UTF-8)

---

## [0.0.1] - 2026-02-04

### Agregado
- Versión inicial del generador de contexto en modo **CLI puro**
- Generación de árbol de directorios con caracteres Unicode (└──, ├──, │)
- Índice de módulos agrupado por directorio con docstring de cada archivo
- Extracción de estructura de código: clases, métodos y funciones con firmas completas y docstrings
- Ignorado automático de directorios comunes (`__pycache__`, `.git`, `venv`, etc.)
- Guardado del resultado en `PROJECT_CONTEXT.md` en la raíz del proyecto
- Argumento `-o/--output` para especificar ruta de salida
- Flags `--tree-only`, `--index-only`, `--structure-only` para salida parcial
- Flag `-v/--verbose` para progreso detallado
- Compatibilidad multiplataforma: Windows, Linux, macOS
