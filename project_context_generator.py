#!/usr/bin/env python3
"""
Project Context Generator - CLI
Versión de línea de comandos para generar contexto de proyectos Python.
Multiplataforma: Windows, Linux, macOS
"""

import argparse
import ast
import sys
from pathlib import Path
from typing import List, Dict
from datetime import datetime


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
        
        return "\n".join(content)


def main():
    """Función principal CLI"""
    parser = argparse.ArgumentParser(
        description="🐍 Generador de Contexto de Proyectos Python",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  %(prog)s /ruta/proyecto                    # Genera contexto completo
  %(prog)s /ruta/proyecto --quick            # Estructura rápida (solo firmas)
  %(prog)s /ruta/proyecto --tree-only        # Solo árbol de directorios
  %(prog)s /ruta/proyecto --index-only       # Solo índice de módulos
  %(prog)s /ruta/proyecto -o contexto.md     # Especifica archivo de salida
  %(prog)s .                                 # Proyecto actual
  %(prog)s . --ui                            # Abre interfaz gráfica
        """
    )
    
    parser.add_argument(
        'project_path',
        type=str,
        nargs='?',
        default='.',
        help='Ruta del proyecto (default: directorio actual)'
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
        help='Abre la interfaz gráfica'
    )
    
    args = parser.parse_args()
    
    # Si se pide UI, importar y ejecutar
    if args.ui:
        try:
            from project_context_generator_ui import main as ui_main
            ui_main()
            return
        except ImportError:
            print("❌ Error: PyQt6 no está instalado")
            print("Instala con: pip install PyQt6")
            sys.exit(1)
    
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


if __name__ == "__main__":
    main()
