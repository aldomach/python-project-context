#!/usr/bin/env python3
"""
Project Context Generator - UI
Interfaz gráfica para generar contexto de proyectos Python.
Multiplataforma: Windows, Linux, macOS
"""

import sys
import ast
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QLineEdit, QTextEdit, QFileDialog,
        QCheckBox, QGroupBox, QProgressBar, QTabWidget, QMessageBox,
        QSplitter, QComboBox
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal
    from PyQt6.QtGui import QFont, QTextCursor
except ImportError:
    print("PyQt6 no está instalado. Instalando...")
    print("Ejecuta: pip install PyQt6")
    sys.exit(1)


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


class ContextGeneratorWorker(QThread):
    """Worker thread para generar contexto sin bloquear la UI"""
    
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, project_path: Path, options: dict):
        super().__init__()
        self.project_path = project_path
        self.options = options
    
    def run(self):
        try:
            content = self.generate_context()
            self.finished.emit(content)
        except Exception as e:
            self.error.emit(str(e))
    
    def generate_context(self) -> str:
        """Genera el contexto del proyecto"""
        project_name = self.project_path.name
        content = []
        
        # Encabezado
        content.append(f"# Contexto del Proyecto: {project_name}\n")
        content.append(f"**Generado:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        content.append(f"**Ruta:** `{self.project_path}`\n")
        
        self.progress.emit(10, "Generando árbol de directorios...")
        
        # Árbol de directorios
        if self.options.get('tree', True):
            content.append("## 📁 Estructura de Directorios\n")
            content.append("```")
            content.append(f"{project_name}/")
            tree_lines = self._generate_tree(self.project_path)
            content.extend(tree_lines)
            content.append("```\n")
        
        self.progress.emit(30, "Buscando archivos Python...")
        
        # Buscar archivos Python
        python_files = self._find_python_files()
        total_files = len(python_files)
        
        self.progress.emit(40, f"Encontrados {total_files} archivos Python")
        
        # Índice de módulos
        if self.options.get('index', True):
            content.append(self._generate_module_index(python_files))
            content.append("\n")
        
        self.progress.emit(50, "Extrayendo estructura de código...")
        
        # Estructura de código
        if self.options.get('structure', True):
            content.append("## 🔧 Estructura de Código\n")
            
            for i, py_file in enumerate(python_files):
                progress = 50 + int((i / total_files) * 40)
                rel_path = py_file.relative_to(self.project_path)
                self.progress.emit(progress, f"Procesando: {rel_path}")
                
                content.append(f"\n### 📄 {rel_path}\n")
                
                if self.options.get('full_structure', False):
                    content.append("```python")
                    content.append(self._process_python_file(py_file))
                    content.append("```\n")
                else:
                    content.append(self._extract_quick_structure(py_file))
                    content.append("\n")
        
        self.progress.emit(100, "¡Completado!")
        
        return "\n".join(content)
    
    def _generate_tree(self, root_path: Path, prefix: str = "", is_last: bool = True) -> List[str]:
        """Genera árbol de directorios"""
        lines = []
        ignore_dirs = {'__pycache__', '.git', 'venv', 'env', '.venv', 'node_modules', '.idea', '.vscode'}
        ignore_exts = {'.pyc', '.pyo', '.pyd', '.so', '.dll'}
        
        try:
            items = sorted(root_path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
            items = [item for item in items if item.name not in ignore_dirs 
                     and not any(item.name.endswith(ext) for ext in ignore_exts)]
        except PermissionError:
            return lines
        
        for i, item in enumerate(items):
            is_last_item = (i == len(items) - 1)
            current_prefix = "└── " if is_last_item else "├── "
            
            if item.is_dir():
                lines.append(f"{prefix}{current_prefix}{item.name}/")
                extension = "    " if is_last_item else "│   "
                lines.extend(self._generate_tree(item, prefix + extension, is_last_item))
            else:
                lines.append(f"{prefix}{current_prefix}{item.name}")
        
        return lines
    
    def _find_python_files(self) -> List[Path]:
        """Encuentra todos los archivos Python"""
        python_files = []
        ignore_dirs = {'__pycache__', '.git', 'venv', 'env', '.venv', 'node_modules'}
        
        for item in self.project_path.rglob('*.py'):
            if not any(ignore_dir in item.parts for ignore_dir in ignore_dirs):
                python_files.append(item)
        
        return sorted(python_files)
    
    def _generate_module_index(self, python_files: List[Path]) -> str:
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
    
    def _process_python_file(self, file_path: Path) -> str:
        """Procesa archivo Python con estructura completa"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            output = []
            
            # Extraer imports
            imports = self._extract_imports(tree)
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
    
    def _extract_quick_structure(self, file_path: Path) -> str:
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
    
    def _extract_imports(self, tree):
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
# Generar contexto completo
python project_context_generator.py /ruta/proyecto --full

# Solo árbol de directorios
python project_context_generator.py /ruta/proyecto --tree-only

# Solo índice de módulos
python project_context_generator.py /ruta/proyecto --index-only
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
        options = {
            'tree': self.tree_check.isChecked(),
            'index': self.index_check.isChecked(),
            'structure': self.structure_check.isChecked(),
            'full_structure': self.detail_combo.currentIndex() == 1
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


def main():
    """Función principal"""
    app = QApplication(sys.argv)
    
    # Estilo de la aplicación
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
