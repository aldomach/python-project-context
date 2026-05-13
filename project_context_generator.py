#!/usr/bin/env python3
"""
Python Project Context Generator - Unified
Interfaz gráfica y línea de comandos en un solo archivo.
Multiplataforma: Windows, Linux, macOS

Uso:
    python project_context_generator.py              # Abre la UI
    python project_context_generator.py <directorio> # Modo CLI
    python project_context_generator.py --help       # Ayuda

VERSION: 0.0.5
"""

import argparse
import ast
import sys
from pathlib import Path
from typing import List, Dict
from datetime import datetime


# ============================================================================
# CORE - Lógica compartida entre CLI y UI
# ============================================================================

class CodeStructureExtractor(ast.NodeVisitor):
    """Extrae la estructura de un archivo Python sin implementación"""
    
    def __init__(self):
        self.output = []
        self.indent_level = 0
    
    def indent(self):
        return "    " * self.indent_level
    
    def visit_ClassDef(self, node):
        docstring = ast.get_docstring(node) or ""
        if docstring:
            docstring = f'    """{docstring.split(chr(10))[0]}"""'
        
        bases = ", ".join(self._get_name(base) for base in node.bases)
        bases_str = f"({bases})" if bases else ""
        
        self.output.append(f"\n{self.indent()}class {node.name}{bases_str}:")
        if docstring:
            self.output.append(f"{self.indent()}{docstring}")
        
        self.indent_level += 1
        
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                self.visit_FunctionDef(item)
        
        self.indent_level -= 1
    
    def visit_FunctionDef(self, node):
        docstring = ast.get_docstring(node) or ""
        args = self._get_function_signature(node)
        returns = f" -> {self._get_name(node.returns)}" if node.returns else ""
        
        self.output.append(f"{self.indent()}def {node.name}({args}){returns}:")
        
        if docstring:
            self.output.append(f'{self.indent()}    """{docstring.split(chr(10))[0]}"""')
        
        self.output.append(f"{self.indent()}    ...")
        self.output.append("")
    
    def _get_function_signature(self, node):
        args_list = []
        
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {self._get_name(arg.annotation)}"
            args_list.append(arg_str)
        
        if node.args.vararg:
            args_list.append(f"*{node.args.vararg.arg}")
        
        if node.args.kwarg:
            args_list.append(f"**{node.args.kwarg.arg}")
        
        return ", ".join(args_list)
    
    def _get_name(self, node):
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Subscript):
            return f"{self._get_name(node.value)}[{self._get_name(node.slice)}]"
        elif isinstance(node, ast.Constant):
            return repr(node.value)
        else:
            return ast.unparse(node)


class ProjectContextGenerator:
    """Generador de contexto de proyecto"""
    
    def __init__(self, project_path: Path, verbose: bool = False):
        self.project_path = project_path
        self.verbose = verbose
        self.ignore_dirs = {'__pycache__', '.git', 'venv', 'env', '.venv', 'node_modules', '.idea', '.vscode'}
        self.ignore_exts = {'.pyc', '.pyo', '.pyd', '.so', '.dll'}
    
    def log(self, message: str):
        """Imprime mensaje si verbose está activo"""
        if self.verbose:
            print(f"  {message}")
    
    def generate_tree(self, root_path: Path, prefix: str = "", is_last: bool = True) -> List[str]:
        """Genera árbol de directorios"""
        lines = []
        
        try:
            items = sorted(root_path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
            items = [item for item in items if item.name not in self.ignore_dirs 
                     and not any(item.name.endswith(ext) for ext in self.ignore_exts)]
        except PermissionError:
            return lines
        
        for i, item in enumerate(items):
            is_last_item = (i == len(items) - 1)
            current_prefix = "└── " if is_last_item else "├── "
            
            if item.is_dir():
                lines.append(f"{prefix}{current_prefix}{item.name}/")
                extension = "    " if is_last_item else "│   "
                lines.extend(self.generate_tree(item, prefix + extension, is_last_item))
            else:
                lines.append(f"{prefix}{current_prefix}{item.name}")
        
        return lines
    
    def find_python_files(self) -> List[Path]:
        """Encuentra todos los archivos Python"""
        python_files = []
        
        for item in self.project_path.rglob('*.py'):
            if not any(ignore_dir in item.parts for ignore_dir in self.ignore_dirs):
                python_files.append(item)
        
        return sorted(python_files)
    
    def generate_module_index(self, python_files: List[Path]) -> str:
        """Genera índice de módulos"""
        output = ["## 📚 Índice de Módulos\n"]
        
        modules_by_dir: Dict[str, List[Path]] = {}
        for file in python_files:
            rel_path = file.relative_to(self.project_path)
            dir_name = str(rel_path.parent) if rel_path.parent != Path('.') else "📦 root"
            
            if dir_name not in modules_by_dir:
                modules_by_dir[dir_name] = []
            modules_by_dir[dir_name].append(file)
        
        for dir_name in sorted(modules_by_dir.keys()):
            output.append(f"\n### {dir_name}/")
            for file in modules_by_dir[dir_name]:
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        tree = ast.parse(f.read())
                        docstring = ast.get_docstring(tree) or "Sin descripción"
                        docstring = docstring.split('\n')[0]
                except:
                    docstring = "Sin descripción"
                
                output.append(f"- **{file.name}**: {docstring}")
        
        return "\n".join(output)
    
    def process_python_file(self, file_path: Path) -> str:
        """Procesa archivo Python con estructura completa"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            output = []
            
            # Extraer imports
            imports = self.extract_imports(tree)
            if imports:
                output.append("# Imports:")
                output.extend(imports)
                output.append("")
            
            # Extraer estructura
            extractor = CodeStructureExtractor()
            for node in tree.body:
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    extractor.visit(node)
            
            output.extend(extractor.output)
            
            return "\n".join(output)
        
        except Exception as e:
            return f"# Error procesando archivo: {e}\n"
    
    def extract_quick_structure(self, file_path: Path) -> str:
        """Extrae estructura rápida (solo firmas)"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
            
            lines = ["```python"]
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    bases = ", ".join(b.id if hasattr(b, 'id') else str(b) for b in node.bases)
                    bases_str = f"({bases})" if bases else ""
                    doc = ast.get_docstring(node) or ""
                    doc = f'  # {doc.split(chr(10))[0][:60]}' if doc else ""
                    lines.append(f"class {node.name}{bases_str}:{doc}")
                    
                elif isinstance(node, ast.FunctionDef):
                    args = ", ".join(arg.arg for arg in node.args.args)
                    doc = ast.get_docstring(node) or ""
                    doc = f'  # {doc.split(chr(10))[0][:60]}' if doc else ""
                    lines.append(f"    def {node.name}({args}):{doc}")
            
            lines.append("```")
            return "\n".join(lines)
        
        except Exception as e:
            return f"```\n# Error: {e}\n```"
    
    def extract_imports(self, tree):
        """Extrae imports de un módulo"""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(f"import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = ", ".join(alias.name for alias in node.names)
                imports.append(f"from {module} import {names}")
        return imports
    
    def generate_context(self, include_tree: bool = True, include_index: bool = True,
                        include_structure: bool = True, full_structure: bool = False) -> str:
        """Genera el contexto completo del proyecto"""
        
        project_name = self.project_path.name
        content = []
        
        # Encabezado
        content.append(f"# Contexto del Proyecto: {project_name}\n")
        content.append(f"**Generado:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        content.append(f"**Ruta:** `{self.project_path}`\n")
        
        try:
            # Árbol de directorios
            if include_tree:
                self.log("Generando árbol de directorios...")
                content.append("## 📁 Estructura de Directorios\n")
                content.append("```")
                content.append(f"{project_name}/")
                tree_lines = self.generate_tree(self.project_path)
                content.extend(tree_lines)
                content.append("```\n")
            
            # Buscar archivos Python
            self.log("Buscando archivos Python...")
            python_files = self.find_python_files()
            self.log(f"Encontrados {len(python_files)} archivos Python")
            
            # Índice de módulos
            if include_index:
                self.log("Generando índice de módulos...")
                content.append(self.generate_module_index(python_files))
                content.append("\n")
            
            # Estructura de código
            if include_structure:
                self.log("Extrayendo estructura de código...")
                content.append("## 🔧 Estructura de Código\n")
                
                for py_file in python_files:
                    rel_path = py_file.relative_to(self.project_path)
                    self.log(f"Procesando: {rel_path}")
                    
                    content.append(f"\n### 📄 {rel_path}\n")
                    
                    if full_structure:
                        content.append("```python")
                        content.append(self.process_python_file(py_file))
                        content.append("```\n")
                    else:
                        content.append(self.extract_quick_structure(py_file))
                        content.append("\n")
        
        except Exception as e:
            content.append(f"\n⚠️ Error durante la generación: {e}\n")
            if self.verbose:
                import traceback
                content.append(f"\n```\n{traceback.format_exc()}\n```\n")
        
        return "\n".join(content)


# ============================================================================
# CLI - Interfaz de línea de comandos
# ============================================================================

def run_cli():
    """Ejecuta la interfaz de línea de comandos"""
    parser = argparse.ArgumentParser(
        description="🐍 Generador de Contexto de Proyectos Python",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  %(prog)s                           # Abre interfaz gráfica
  %(prog)s /ruta/proyecto            # Genera contexto por CLI
  %(prog)s . --quick                 # Estructura rápida (solo firmas)
  %(prog)s . --tree-only             # Solo árbol de directorios
  %(prog)s . -o contexto.md          # Especifica archivo de salida
  %(prog)s --ui                      # Fuerza abrir UI
        """
    )
    
    parser.add_argument(
        'project_path',
        type=str,
        nargs='?',
        help='Ruta del proyecto (omitir para abrir UI)'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        help='Archivo de salida (default: PROJECT_CONTEXT.md)'
    )
    
    parser.add_argument(
        '--tree-only',
        action='store_true',
        help='Solo genera árbol de directorios'
    )
    
    parser.add_argument(
        '--index-only',
        action='store_true',
        help='Solo genera índice de módulos'
    )
    
    parser.add_argument(
        '--structure-only',
        action='store_true',
        help='Solo genera estructura de código'
    )
    
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Estructura rápida (solo firmas)'
    )
    
    parser.add_argument(
        '--full',
        action='store_true',
        help='Estructura completa con tipos y docstrings (default)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Muestra progreso detallado'
    )
    
    parser.add_argument(
        '--ui',
        action='store_true',
        help='Fuerza abrir interfaz gráfica'
    )
    
    args = parser.parse_args()
    
    # Si no hay argumentos o se pide UI explícitamente, abrir UI
    if args.project_path is None or args.ui:
        return run_ui()
    
    # Validar ruta del proyecto
    project_path = Path(args.project_path).resolve()
    
    if not project_path.exists():
        print(f"❌ Error: {project_path} no existe")
        sys.exit(1)
    
    if not project_path.is_dir():
        print(f"❌ Error: {project_path} no es un directorio")
        sys.exit(1)
    
    # Determinar qué incluir
    if args.tree_only:
        include_tree, include_index, include_structure = True, False, False
    elif args.index_only:
        include_tree, include_index, include_structure = False, True, False
    elif args.structure_only:
        include_tree, include_index, include_structure = False, False, True
    else:
        include_tree, include_index, include_structure = True, True, True
    
    full_structure = not args.quick
    
    # Nombre del archivo de salida
    output_file = Path(args.output) if args.output else project_path / "PROJECT_CONTEXT.md"
    
    # Generar contexto
    print(f"\n🐍 Generando contexto de: {project_path.name}")
    print(f"📁 Ruta: {project_path}")
    
    generator = ProjectContextGenerator(project_path, verbose=args.verbose)
    
    try:
        content = generator.generate_context(
            include_tree=include_tree,
            include_index=include_index,
            include_structure=include_structure,
            full_structure=full_structure
        )
        
        # Guardar archivo
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"\n✅ Contexto generado exitosamente")
        print(f"💾 Guardado en: {output_file}")
        print(f"📊 Tamaño: {len(content):,} caracteres")
        
        # Contar archivos procesados
        python_files = generator.find_python_files()
        print(f"📦 Archivos procesados: {len(python_files)}")
        
    except Exception as e:
        print(f"\n❌ Error al generar contexto: {e}")
        sys.exit(1)


# ============================================================================
# UI - Interfaz gráfica (PySide6)
# ============================================================================

def run_ui():
    """Ejecuta la interfaz gráfica"""
    try:
        from PySide6.QtWidgets import (
            QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
            QPushButton, QLabel, QLineEdit, QTextEdit, QFileDialog,
            QCheckBox, QGroupBox, QProgressBar, QTabWidget, QMessageBox,
            QComboBox
        )
        from PySide6.QtCore import Qt, QThread, Signal
        from PySide6.QtGui import QFont
    except ImportError:
        print("❌ Error: PySide6 no está instalado")
        print("\nPara usar la interfaz gráfica, instala PySide6:")
        print("  pip install PySide6")
        print("\nO usa el modo CLI:")
        print("  python project_context_generator.py <directorio>")
        sys.exit(1)
    
    class ContextGeneratorWorker(QThread):
        """Worker thread para generar contexto sin bloquear la UI"""
        
        progress = Signal(int, str)
        finished = Signal(str)
        error = Signal(str)
        
        def __init__(self, project_path: Path, options: dict):
            super().__init__()
            self.project_path = project_path
            self.options = options
        
        def run(self):
            try:
                generator = ProjectContextGenerator(self.project_path, verbose=False)
                
                self.progress.emit(10, "Iniciando generación...")
                
                content = generator.generate_context(
                    include_tree=self.options.get('tree', True),
                    include_index=self.options.get('index', True),
                    include_structure=self.options.get('structure', True),
                    full_structure=self.options.get('full_structure', False)
                )
                
                self.progress.emit(100, "¡Completado!")
                self.finished.emit(content)
                
            except Exception as e:
                self.error.emit(str(e))
    
    class MainWindow(QMainWindow):
        """Ventana principal de la aplicación"""
        
        def __init__(self):
            super().__init__()
            self.setWindowTitle("🐍 Python Project Context Generator")
            self.setGeometry(100, 100, 1200, 800)
            
            self.worker = None
            self.init_ui()
        
        def init_ui(self):
            """Inicializa la interfaz de usuario"""
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            main_layout = QVBoxLayout(central_widget)
            
            # Título
            title = QLabel("Python Project Context Generator")
            title_font = QFont()
            title_font.setPointSize(16)
            title_font.setBold(True)
            title.setFont(title_font)
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            main_layout.addWidget(title)
            
            # Selector de proyecto
            project_group = QGroupBox("📁 Proyecto")
            project_layout = QHBoxLayout()
            
            self.project_path_input = QLineEdit()
            self.project_path_input.setPlaceholderText("Selecciona la carpeta del proyecto...")
            project_layout.addWidget(self.project_path_input)
            
            browse_btn = QPushButton("Examinar...")
            browse_btn.clicked.connect(self.browse_project)
            project_layout.addWidget(browse_btn)
            
            project_group.setLayout(project_layout)
            main_layout.addWidget(project_group)
            
            # Opciones
            options_group = QGroupBox("⚙️ Opciones de Generación")
            options_layout = QVBoxLayout()
            
            # Fila 1
            row1 = QHBoxLayout()
            self.tree_check = QCheckBox("Árbol de directorios")
            self.tree_check.setChecked(True)
            row1.addWidget(self.tree_check)
            
            self.index_check = QCheckBox("Índice de módulos")
            self.index_check.setChecked(True)
            row1.addWidget(self.index_check)
            
            self.structure_check = QCheckBox("Estructura de código")
            self.structure_check.setChecked(True)
            row1.addWidget(self.structure_check)
            
            options_layout.addLayout(row1)
            
            # Fila 2
            row2 = QHBoxLayout()
            
            structure_label = QLabel("Nivel de detalle:")
            row2.addWidget(structure_label)
            
            self.detail_combo = QComboBox()
            self.detail_combo.addItems(["Firmas rápidas", "Estructura completa"])
            row2.addWidget(self.detail_combo)
            
            row2.addWidget(QLabel("    Estilo de árbol:"))
            
            self.tree_style_combo = QComboBox()
            self.tree_style_combo.addItems(["ASCII", "Unicode", "ASCII +", "Simple", "Dots"])
            self.tree_style_combo.setCurrentIndex(0)  # ASCII por defecto
            self.tree_style_combo.setToolTip("Estilo de caracteres para el árbol de directorios")
            row2.addWidget(self.tree_style_combo)
            
            row2.addStretch()
            
            options_layout.addLayout(row2)
            
            options_group.setLayout(options_layout)
            main_layout.addWidget(options_group)
            
            # Botones de acción
            buttons_layout = QHBoxLayout()
            
            self.generate_btn = QPushButton("🚀 Generar Contexto")
            self.generate_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    padding: 10px;
                    font-size: 14px;
                    font-weight: bold;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
                QPushButton:disabled {
                    background-color: #cccccc;
                }
            """)
            self.generate_btn.clicked.connect(self.generate_context)
            buttons_layout.addWidget(self.generate_btn)
            
            self.save_btn = QPushButton("💾 Guardar como...")
            self.save_btn.setEnabled(False)
            self.save_btn.clicked.connect(self.save_context)
            buttons_layout.addWidget(self.save_btn)
            
            self.copy_btn = QPushButton("📋 Copiar al portapapeles")
            self.copy_btn.setEnabled(False)
            self.copy_btn.clicked.connect(self.copy_to_clipboard)
            buttons_layout.addWidget(self.copy_btn)
            
            main_layout.addLayout(buttons_layout)
            
            # Barra de progreso
            self.progress_bar = QProgressBar()
            self.progress_bar.setVisible(False)
            main_layout.addWidget(self.progress_bar)
            
            self.status_label = QLabel("")
            self.status_label.setStyleSheet("color: #666; font-style: italic;")
            main_layout.addWidget(self.status_label)
            
            # Tabs para vista previa y ayuda
            self.tabs = QTabWidget()
            
            # Tab de vista previa
            self.preview_text = QTextEdit()
            self.preview_text.setReadOnly(True)
            self.preview_text.setFont(QFont("Courier", 10))
            self.tabs.addTab(self.preview_text, "📄 Vista Previa")
            
            # Tab de ayuda
            help_text = QTextEdit()
            help_text.setReadOnly(True)
            help_text.setHtml("""
                <h2>📖 Ayuda de Uso</h2>
                
                <h3>¿Qué hace esta herramienta?</h3>
                <p>Genera un archivo de contexto de tu proyecto Python que incluye:</p>
                <ul>
                    <li><b>Árbol de directorios:</b> Estructura completa del proyecto</li>
                    <li><b>Índice de módulos:</b> Lista de archivos con sus descripciones</li>
                    <li><b>Estructura de código:</b> Firmas de clases y funciones sin implementación</li>
                </ul>
                
                <h3>¿Para qué sirve?</h3>
                <p>Perfecto para compartir con Claude u otros LLMs para que entiendan tu proyecto sin pasarle todo el código completo.</p>
                
                <h3>Opciones:</h3>
                <ul>
                    <li><b>Firmas rápidas:</b> Solo nombres de clases/funciones (más compacto)</li>
                    <li><b>Estructura completa:</b> Incluye tipos de argumentos y docstrings</li>
                </ul>
                
                <h3>Uso por consola:</h3>
                <pre>
# Abrir UI (sin argumentos)
python project_context_generator.py

# Generar por CLI
python project_context_generator.py /ruta/proyecto

# Solo árbol de directorios
python project_context_generator.py . --tree-only

# Estructura rápida
python project_context_generator.py . --quick
                </pre>
                
                <h3>💡 Tip:</h3>
                <p>Guarda el archivo generado como <code>PROJECT_CONTEXT.md</code> y pásaselo a Claude al inicio de cada conversación sobre tu proyecto.</p>
            """)
            self.tabs.addTab(help_text, "❓ Ayuda")
            
            main_layout.addWidget(self.tabs)
        
        def browse_project(self):
            """Abre diálogo para seleccionar proyecto"""
            folder = QFileDialog.getExistingDirectory(
                self,
                "Seleccionar carpeta del proyecto",
                str(Path.home())
            )
            
            if folder:
                self.project_path_input.setText(folder)
        
        def generate_context(self):
            """Genera el contexto del proyecto"""
            project_path = self.project_path_input.text().strip()
            
            if not project_path:
                QMessageBox.warning(self, "Error", "Por favor selecciona un proyecto")
                return
            
            project_path = Path(project_path)
            
            if not project_path.exists():
                QMessageBox.warning(self, "Error", "La ruta del proyecto no existe")
                return
            
            # Preparar opciones
            tree_style_map = {0: 'ascii', 1: 'unicode', 2: 'ascii_plus', 3: 'simple', 4: 'dots'}
            
            options = {
                'tree': self.tree_check.isChecked(),
                'index': self.index_check.isChecked(),
                'structure': self.structure_check.isChecked(),
                'full_structure': self.detail_combo.currentIndex() == 1,
                'tree_style': tree_style_map[self.tree_style_combo.currentIndex()]
            }
            
            # Deshabilitar botones
            self.generate_btn.setEnabled(False)
            self.save_btn.setEnabled(False)
            self.copy_btn.setEnabled(False)
            
            # Mostrar barra de progreso
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            # Crear y ejecutar worker
            self.worker = ContextGeneratorWorker(project_path, options)
            self.worker.progress.connect(self.update_progress)
            self.worker.finished.connect(self.on_generation_finished)
            self.worker.error.connect(self.on_generation_error)
            self.worker.start()
        
        def update_progress(self, value: int, message: str):
            """Actualiza la barra de progreso"""
            self.progress_bar.setValue(value)
            self.status_label.setText(message)
        
        def on_generation_finished(self, content: str):
            """Maneja la finalización de la generación"""
            self.preview_text.setPlainText(content)
            
            # Habilitar botones
            self.generate_btn.setEnabled(True)
            self.save_btn.setEnabled(True)
            self.copy_btn.setEnabled(True)
            
            # Ocultar barra de progreso
            self.progress_bar.setVisible(False)
            self.status_label.setText("✅ Contexto generado exitosamente")
            
            # Cambiar a tab de vista previa
            self.tabs.setCurrentIndex(0)
            
            QMessageBox.information(self, "Éxito", "¡Contexto generado exitosamente!")
        
        def on_generation_error(self, error_msg: str):
            """Maneja errores en la generación"""
            self.generate_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
            self.status_label.setText("❌ Error al generar contexto")
            
            QMessageBox.critical(self, "Error", f"Error al generar contexto:\n{error_msg}")
        
        def save_context(self):
            """Guarda el contexto en un archivo"""
            content = self.preview_text.toPlainText()
            
            if not content:
                QMessageBox.warning(self, "Error", "No hay contenido para guardar")
                return
            
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Guardar contexto",
                str(Path.home() / "PROJECT_CONTEXT.md"),
                "Markdown Files (*.md);;All Files (*)"
            )
            
            if file_path:
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    QMessageBox.information(self, "Éxito", f"Contexto guardado en:\n{file_path}")
                    self.status_label.setText(f"💾 Guardado en: {Path(file_path).name}")
                
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Error al guardar:\n{str(e)}")
        
        def copy_to_clipboard(self):
            """Copia el contenido al portapapeles"""
            content = self.preview_text.toPlainText()
            
            if content:
                clipboard = QApplication.clipboard()
                clipboard.setText(content)
                
                QMessageBox.information(self, "Copiado", "¡Contenido copiado al portapapeles!")
                self.status_label.setText("📋 Copiado al portapapeles")
    
    # Ejecutar UI
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


# ============================================================================
# MAIN - Punto de entrada
# ============================================================================

def main():
    """Función principal"""
    # Si no hay argumentos de línea de comandos (solo el nombre del script), abrir UI
    if len(sys.argv) == 1:
        run_ui()
    else:
        run_cli()


if __name__ == "__main__":
    main()
