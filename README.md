# 🐍 Project Context Generator

Genera un archivo de contexto completo de proyectos Python en formato Markdown, ideal para compartir con LLMs o documentar proyectos rápidamente.

Extrae la estructura de directorios, índice de módulos y firmas de clases/funciones sin incluir la implementación.

---

## ✨ Características

- **Árbol de directorios** con múltiples estilos visuales (ASCII, Unicode, Simple, Dots)
- **Índice de módulos** agrupado por directorio con docstrings
- **Estructura de código** con firmas de clases y funciones, tipos y docstrings
- **Doble modo de uso**: interfaz gráfica (PyQt6) o línea de comandos
- **Multiplataforma**: Windows, Linux, macOS
- **Un solo archivo**: sin dependencias externas para el modo CLI

---

## 🚀 Uso rápido

### Interfaz gráfica

```bash
python project_context_generator.py
```

### Línea de comandos

```bash
# Generar contexto completo
python project_context_generator.py /ruta/a/tu/proyecto

# Guardar en un archivo específico
python project_context_generator.py /ruta/proyecto -o contexto.md

# Solo árbol de directorios
python project_context_generator.py /ruta/proyecto --tree-only

# Solo índice de módulos
python project_context_generator.py /ruta/proyecto --index-only

# Solo estructura de código
python project_context_generator.py /ruta/proyecto --structure-only

# Estructura rápida (solo firmas, sin tipos ni docstrings)
python project_context_generator.py /ruta/proyecto --quick

# Modo verbose
python project_context_generator.py /ruta/proyecto -v
```

---

## 📦 Instalación

No requiere instalación. Solo descarga el archivo y ejecútalo.

Para usar la **interfaz gráfica**, instala PySide6:

```bash
pip install PySide6
```

---

## 🖥️ Interfaz gráfica

La UI ofrece:

- Selector de directorio con botón de exploración
- Checkboxes para elegir qué secciones incluir (árbol, índice, estructura)
- Selector de detalle de estructura (completa o rápida)
- Selector de estilo de árbol (ASCII, Unicode, ASCII+, Simple, Dots)
- Vista previa del resultado en tiempo real
- Botón de copia al portapapeles

---

## ⚙️ Opciones CLI

| Argumento | Descripción |
|---|---|
| `project_path` | Ruta del proyecto a analizar |
| `-o, --output` | Archivo de salida (por defecto: `PROJECT_CONTEXT.md` en la raíz del proyecto) |
| `--tree-only` | Solo genera el árbol de directorios |
| `--index-only` | Solo genera el índice de módulos |
| `--structure-only` | Solo genera la estructura de código |
| `--quick` | Estructura rápida (solo firmas) |
| `--full` | Estructura completa con tipos y docstrings (por defecto) |
| `-v, --verbose` | Muestra progreso detallado |

---

## 📄 Ejemplo de salida

```markdown
# Contexto del Proyecto: mi_proyecto

**Generado:** 2026-02-05 17:31:00
**Ruta:** `/home/user/mi_proyecto`

## 📁 Estructura de Directorios

\```
mi_proyecto/
├── src/
│   ├── core.py
│   └── utils.py
├── tests/
│   └── test_core.py
└── main.py
\```

## 📚 Índice de Módulos

### src/
- **core.py**: Lógica principal del proyecto
- **utils.py**: Funciones auxiliares

## 🔧 Estructura de Código

### 📄 src/core.py

\```python
class MyClass:
    """Clase principal"""

    def __init__(self: MyClass, name: str):
        ...

    def process(self: MyClass, data: List[str]) -> Dict:
        """Procesa los datos de entrada"""
        ...
\```
```

---

## 🗂️ Archivos ignorados

Por defecto se ignoran:

- Directorios: `__pycache__`, `.git`, `venv`, `env`, `.venv`, `node_modules`, `.idea`, `.vscode`
- Extensiones: `.pyc`, `.pyo`, `.pyd`, `.so`, `.dll`

---

## 📋 Requisitos

- Python 3.8+
- PySide6 (solo para la interfaz gráfica): `pip install PySide6`

---

## 📝 Licencia

MIT License — libre para uso personal y comercial.
