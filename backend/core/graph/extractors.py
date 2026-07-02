"""
core/graph/extractors.py — Advanced Tree-sitter extraction logic for the Repository Index.

Extracts:
- Classes
- Functions
- Call Graph (Function Calls)
- API Routes (e.g., FastAPI, Express)
- Database Models (e.g., ORM models)
"""

from tree_sitter import Parser, Language
import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
import tree_sitter_typescript as tstypescript

PY_LANGUAGE = Language(tspython.language(), "python")
JS_LANGUAGE = Language(tsjavascript.language(), "javascript")
TS_LANGUAGE = Language(tstypescript.language_typescript(), "typescript")

LANGUAGE_MAP = {
    "python": PY_LANGUAGE,
    "javascript": JS_LANGUAGE,
    "typescript": TS_LANGUAGE,
}

def extract_advanced_metadata(source_bytes: bytes, language: str) -> dict:
    """
    Returns a dictionary of extracted components from the AST.
    """
    lang_obj = LANGUAGE_MAP.get(language)
    if not lang_obj:
        return {"classes": [], "functions": [], "calls": [], "routes": [], "models": []}
    
    parser = Parser()
    parser.set_language(lang_obj)
    tree = parser.parse(source_bytes)
    
    metadata = {
        "classes": [],
        "functions": [],
        "calls": [],
        "routes": [],
        "models": [],
    }

    if language == "python":
        _extract_python(tree, source_bytes, metadata)
    elif language in ("javascript", "typescript"):
        _extract_js_ts(tree, source_bytes, metadata)

    # Deduplicate calls
    metadata["calls"] = list(set(metadata["calls"]))
    
    return metadata

def _get_text(node, source_bytes):
    return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="ignore")

def _extract_python(tree, source_bytes, metadata):
    root = tree.root_node
    stack = [root]
    
    while stack:
        node = stack.pop()
        
        # 1. Classes & Database Models
        if node.type == "class_definition":
            name_node = next((c for c in node.children if c.type == "identifier"), None)
            if name_node:
                class_name = _get_text(name_node, source_bytes)
                metadata["classes"].append(class_name)
                
                # Check for DB Models (inheriting from Base, Model, BaseModel, etc.)
                args_node = next((c for c in node.children if c.type == "argument_list"), None)
                if args_node:
                    base_classes = _get_text(args_node, source_bytes)
                    if any(x in base_classes for x in ["Base", "Model", "BaseModel", "Document"]):
                        metadata["models"].append(class_name)

        # 2. Functions & API Routes
        elif node.type == "function_definition":
            name_node = next((c for c in node.children if c.type == "identifier"), None)
            if name_node:
                func_name = _get_text(name_node, source_bytes)
                metadata["functions"].append(func_name)
            
            # Check for API Routes via decorators
            # A decorated function usually has a "decorator" child, but tree-sitter python
            # wraps the function_definition and decorators in a decorated_definition node.
            # So we handle decorated_definition below.

        elif node.type == "decorated_definition":
            # Extract decorators
            decorators = [c for c in node.children if c.type == "decorator"]
            for dec in decorators:
                dec_text = _get_text(dec, source_bytes)
                if any(verb in dec_text for verb in [".get", ".post", ".put", ".delete", ".patch", ".route"]):
                    metadata["routes"].append(dec_text.strip("@ "))
            
            # Add the function definition inside back to stack
            func_def = next((c for c in node.children if c.type == "function_definition"), None)
            class_def = next((c for c in node.children if c.type == "class_definition"), None)
            if func_def: stack.append(func_def)
            if class_def: stack.append(class_def)
            continue # Already pushed children

        # 3. Call Graph
        elif node.type == "call":
            func_node = node.children[0] if node.children else None
            if func_node:
                call_text = _get_text(func_node, source_bytes)
                metadata["calls"].append(call_text)

        stack.extend(node.children)

def _extract_js_ts(tree, source_bytes, metadata):
    root = tree.root_node
    stack = [root]
    
    while stack:
        node = stack.pop()
        
        # 1. Classes & Database Models
        if node.type == "class_declaration":
            name_node = next((c for c in node.children if c.type == "identifier"), None)
            if name_node:
                class_name = _get_text(name_node, source_bytes)
                metadata["classes"].append(class_name)
                
                # Check for DB Models (extends Model, Schema, etc.)
                extends_node = next((c for c in node.children if c.type == "class_heritage"), None)
                if extends_node:
                    base_classes = _get_text(extends_node, source_bytes)
                    if any(x in base_classes for x in ["Model", "Schema", "Document", "Entity"]):
                        metadata["models"].append(class_name)

        # 2. Functions (including arrow functions assigned to variables)
        elif node.type in ("function_declaration", "method_definition"):
            name_node = next((c for c in node.children if c.type in ("identifier", "property_identifier")), None)
            if name_node:
                func_name = _get_text(name_node, source_bytes)
                metadata["functions"].append(func_name)
                
        elif node.type == "variable_declarator":
            name_node = next((c for c in node.children if c.type == "identifier"), None)
            value_node = next((c for c in node.children if c.type == "arrow_function"), None)
            if name_node and value_node:
                func_name = _get_text(name_node, source_bytes)
                metadata["functions"].append(func_name)

        # 3. API Routes & Call Graph
        elif node.type == "call_expression":
            func_node = node.children[0] if node.children else None
            if func_node:
                call_text = _get_text(func_node, source_bytes)
                metadata["calls"].append(call_text)
                
                # Check for API Routes (e.g. app.get('/path'))
                if any(verb in call_text for verb in [".get", ".post", ".put", ".delete", ".patch", ".all"]):
                    args_node = next((c for c in node.children if c.type == "arguments"), None)
                    if args_node and len(args_node.children) > 1: # ( <route>, <handler> )
                        route_arg = args_node.children[1] # children[0] is '(', children[1] is the first arg
                        if route_arg.type == "string":
                            route_path = _get_text(route_arg, source_bytes).strip("'\"`")
                            metadata["routes"].append(f"{call_text}('{route_path}')")

        stack.extend(node.children)
