import re, pathlib

root = pathlib.Path("frontend/src")
config_path = root / "config.js"
config_path.write_text(
    'export const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";\n',
    encoding='utf-8'
)

double_quote_pat = re.compile(r'"http://localhost:8000([^"]*)"')
backtick_pat = re.compile(r'`http://localhost:8000([^`]*)`')
jsx_attr_pat = re.compile(r'(\w+)=(`\$\{API_BASE_URL\}[^`]*`)')

changed_files = []
for f in root.rglob("*.jsx"):
    text = f.read_text(encoding='utf-8')
    orig = text
    text = double_quote_pat.sub(r'`${API_BASE_URL}\1`', text)
    text = backtick_pat.sub(r'`${API_BASE_URL}\1`', text)
    text = jsx_attr_pat.sub(r'\1={\2}', text)
    if text != orig:
        depth = len(f.relative_to(root).parts) - 1
        rel = "./" if depth == 0 else "../" * depth
        import_line = f'import {{ API_BASE_URL }} from "{rel}config";'
        if import_line not in text:
            lines = text.split("\n")
            last_import_idx = 0
            for i, line in enumerate(lines):
                if line.strip().startswith("import "):
                    last_import_idx = i
            lines.insert(last_import_idx + 1, import_line)
            text = "\n".join(lines)
        f.write_text(text, encoding='utf-8')
        changed_files.append(str(f))

print("Changed files:")
for c in changed_files:
    print(" -", c)
