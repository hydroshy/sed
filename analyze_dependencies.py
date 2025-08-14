#!/usr/bin/env python3
"""
Dependency analyzer for SED project
Identifies circular dependencies, unused modules, and generates dependency graph
"""

import os
import ast
import json
from collections import defaultdict, deque

class DependencyAnalyzer:
    def __init__(self, root_dir='.'):
        self.root_dir = root_dir
        self.dependencies = defaultdict(set)
        self.reverse_deps = defaultdict(set)
        self.module_files = {}
        self.all_modules = set()
        
    def analyze(self):
        """Main analysis function"""
        print("Analyzing dependencies...")
        self._scan_modules()
        self._find_circular_dependencies()
        self._find_unused_modules()
        self._find_heavy_dependencies()
        self._generate_report()
        
    def _scan_modules(self):
        """Scan all Python modules and their imports"""
        for root, dirs, files in os.walk(self.root_dir):
            # Skip certain directories
            if any(skip in root for skip in ['backup', '__pycache__', '.git', 'test']):
                continue
                
            for fname in files:
                if fname.endswith('.py'):
                    filepath = os.path.join(root, fname)
                    module_name = self._get_module_name(filepath)
                    self.module_files[module_name] = filepath
                    self.all_modules.add(module_name)
                    
                    # Parse imports
                    imports = self._parse_imports(filepath)
                    self.dependencies[module_name] = imports
                    
                    # Build reverse dependencies
                    for imp in imports:
                        self.reverse_deps[imp].add(module_name)
    
    def _get_module_name(self, filepath):
        """Convert filepath to module name"""
        rel_path = os.path.relpath(filepath, self.root_dir)
        module = rel_path.replace(os.sep, '.').replace('.py', '')
        return module
    
    def _parse_imports(self, filepath):
        """Parse imports from a Python file"""
        imports = set()
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
                
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        # Only track local imports
                        if not alias.name.startswith(('PyQt', 'numpy', 'cv2', 'sys', 'os')):
                            imports.add(alias.name)
                            
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.level == 0:
                        # Only track local imports
                        if not node.module.startswith(('PyQt', 'numpy', 'cv2', 'sys', 'os')):
                            imports.add(node.module)
                            
        except Exception as e:
            print(f"Error parsing {filepath}: {e}")
            
        return imports
    
    def _find_circular_dependencies(self):
        """Find circular dependencies using DFS"""
        print("\n=== CIRCULAR DEPENDENCIES ===")
        visited = set()
        rec_stack = set()
        cycles = []
        
        def dfs(module, path):
            visited.add(module)
            rec_stack.add(module)
            path.append(module)
            
            for dep in self.dependencies.get(module, []):
                if dep not in visited:
                    if dfs(dep, path):
                        return True
                elif dep in rec_stack:
                    # Found cycle
                    cycle_start = path.index(dep)
                    cycle = path[cycle_start:] + [dep]
                    cycles.append(cycle)
                    return True
            
            path.pop()
            rec_stack.remove(module)
            return False
        
        for module in self.all_modules:
            if module not in visited:
                dfs(module, [])
        
        if cycles:
            print("Found circular dependencies:")
            for cycle in cycles:
                print(f"  Cycle: {' -> '.join(cycle)}")
        else:
            print("✓ No circular dependencies found")
    
    def _find_unused_modules(self):
        """Find modules that are never imported"""
        print("\n=== POTENTIALLY UNUSED MODULES ===")
        
        # Exclude main entry points and test files
        exclude_patterns = ['main', '__init__', 'run', 'test', 'example', 'cleanup', 'analyze']
        
        unused = []
        for module in self.all_modules:
            # Check if module is imported anywhere
            if module not in self.reverse_deps or not self.reverse_deps[module]:
                # Check if it's not an entry point
                if not any(pattern in module for pattern in exclude_patterns):
                    unused.append(module)
        
        if unused:
            print("Modules that are never imported:")
            for module in sorted(unused)[:20]:  # Show first 20
                print(f"  - {module}")
        else:
            print("✓ All modules appear to be used")
    
    def _find_heavy_dependencies(self):
        """Find modules with too many dependencies"""
        print("\n=== HEAVY DEPENDENCIES ===")
        
        heavy = []
        for module, deps in self.dependencies.items():
            if len(deps) > 10:  # Threshold for heavy dependency
                heavy.append((module, len(deps)))
        
        if heavy:
            print("Modules with many dependencies (>10):")
            for module, count in sorted(heavy, key=lambda x: x[1], reverse=True)[:10]:
                print(f"  - {module}: {count} dependencies")
        else:
            print("✓ No overly heavy dependencies found")
    
    def _generate_report(self):
        """Generate dependency report"""
        print("\n=== DEPENDENCY STATISTICS ===")
        
        # Calculate statistics
        total_modules = len(self.all_modules)
        total_deps = sum(len(deps) for deps in self.dependencies.values())
        avg_deps = total_deps / total_modules if total_modules > 0 else 0
        
        # Find most depended upon
        most_depended = sorted(
            [(mod, len(deps)) for mod, deps in self.reverse_deps.items()],
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        print(f"Total modules: {total_modules}")
        print(f"Total dependencies: {total_deps}")
        print(f"Average dependencies per module: {avg_deps:.2f}")
        
        print("\nMost depended upon modules:")
        for module, count in most_depended:
            print(f"  - {module}: used by {count} modules")
        
        # Generate JSON report
        report = {
            'total_modules': total_modules,
            'total_dependencies': total_deps,
            'average_dependencies': avg_deps,
            'dependencies': {mod: list(deps) for mod, deps in self.dependencies.items()},
            'reverse_dependencies': {mod: list(deps) for mod, deps in self.reverse_deps.items()}
        }
        
        with open('dependency_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print("\n✓ Full report saved to dependency_report.json")
    
    def generate_dot_graph(self):
        """Generate Graphviz DOT file for visualization"""
        print("\n=== GENERATING DEPENDENCY GRAPH ===")
        
        dot_content = ["digraph dependencies {"]
        dot_content.append('  rankdir=LR;')
        dot_content.append('  node [shape=box];')
        
        # Group by directory
        dirs = defaultdict(list)
        for module in self.all_modules:
            dir_name = module.split('.')[0] if '.' in module else 'root'
            dirs[dir_name].append(module)
        
        # Create subgraphs for each directory
        for dir_name, modules in dirs.items():
            if dir_name != 'root':
                dot_content.append(f'  subgraph cluster_{dir_name} {{')
                dot_content.append(f'    label="{dir_name}";')
                dot_content.append('    style=filled;')
                dot_content.append('    color=lightgrey;')
                
                for module in modules:
                    short_name = module.split('.')[-1]
                    dot_content.append(f'    "{module}" [label="{short_name}"];')
                
                dot_content.append('  }')
        
        # Add edges
        for module, deps in self.dependencies.items():
            for dep in deps:
                if dep in self.all_modules:  # Only include internal dependencies
                    dot_content.append(f'  "{module}" -> "{dep}";')
        
        dot_content.append('}')
        
        with open('dependency_graph.dot', 'w') as f:
            f.write('\n'.join(dot_content))
        
        print("✓ Dependency graph saved to dependency_graph.dot")
        print("  To visualize: dot -Tpng dependency_graph.dot -o dependency_graph.png")

def main():
    analyzer = DependencyAnalyzer()
    analyzer.analyze()
    analyzer.generate_dot_graph()
    
    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)
    print("\nFiles generated:")
    print("  - dependency_report.json: Detailed dependency data")
    print("  - dependency_graph.dot: Graphviz visualization file")
    print("\nRecommendations:")
    print("  1. Review and break circular dependencies if found")
    print("  2. Consider removing or merging unused modules")
    print("  3. Refactor modules with heavy dependencies")

if __name__ == "__main__":
    main()
