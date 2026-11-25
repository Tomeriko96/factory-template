"""Every config.json key the factory scripts read is documented (README.md or commands/config.md).

  python3 -I tests/config_keys_test.py

Parses every Python script in template/.factory/ and follows the values that come from
config.json (`config()`, `load_config()`, `json.load` in a function that opens config.json,
`self.cfg`) through `.get("key")`, `["key"]`, local variables and small helpers that take the key
as an argument (`limit(key, …)`, `pick(env, key, …)`). Each key path found must be documented:
a top-level key in backticks or quotes; a nested `a.b` as `a.b`, or `b` in backticks/quotes in a
paragraph that also names `a`.
"""
import ast, glob, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(ROOT, "template")
SCRIPTS = [p for p in sorted(glob.glob(os.path.join(T, ".factory", "*")))
           if os.path.isfile(p) and open(p, errors="replace").readline().startswith("#!") and
           "python" in open(p, errors="replace").readline()]
DOCS = {"README.md": open(os.path.join(ROOT, "README.md")).read(),
        "commands/config.md": open(os.path.join(T, ".claude", "skills", "factory", "commands", "config.md")).read()}

fails = []


def const(node):
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


FN = (ast.FunctionDef, ast.AsyncFunctionDef)


def own_nodes(fn):
    """The nodes of a function (or module) in source order, without those of nested functions."""
    out, stack = [], list(ast.iter_child_nodes(fn))
    while stack:
        n = stack.pop()
        out.append(n)
        if not isinstance(n, FN):
            stack.extend(ast.iter_child_nodes(n))
    return sorted((n for n in out if hasattr(n, "lineno")), key=lambda n: (n.lineno, n.col_offset))


def names_config_json(node):
    return any(const(a) == "config.json" for a in ast.walk(node))


class Reader:
    """Key paths read from config.json in one script."""

    def __init__(self, src):
        self.tree = ast.parse(src)
        self.paths = set()
        self.helpers = {}   # function name -> (index of the key parameter, config path it indexes, is a method)
        self.bound = {}     # function name -> {parameter index: config path}: f(config()) passes the config on

    def resolve(self, node, env, handles):
        """The config path a node evaluates to, or None."""
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name) and f.id in ("config", "load_config") and not node.args:
                return ()
            if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == "json" and node.args:
                a = node.args[0]
                if (f.attr == "load" and isinstance(a, ast.Name) and a.id in handles) or \
                        (f.attr == "loads" and names_config_json(a)):
                    return ()
            if isinstance(f, ast.Name) and f.id == "read_json" and node.args and names_config_json(node.args[0]):
                return ()
            if isinstance(f, ast.Attribute) and f.attr == "get" and node.args:
                base = self.resolve(f.value, env, handles)
                k = const(node.args[0])
                if base is not None and k:
                    return base + (k,)
        if isinstance(node, ast.Subscript):
            base = self.resolve(node.value, env, handles)
            k = const(node.slice)
            if base is not None and k:
                return base + (k,)
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
            return self.resolve(node.values[0], env, handles)
        if isinstance(node, ast.IfExp):
            return self.resolve(node.body, env, handles)
        if isinstance(node, ast.Name):
            return env.get(node.id)
        if isinstance(node, ast.Attribute) and node.attr == "cfg" and isinstance(node.value, ast.Name) \
                and node.value.id == "self":
            return ()
        return None

    def visit_fn(self, fn, env):
        env, handles = dict(env), set()
        params = [a.arg for a in fn.args.args] if isinstance(fn, FN) else []
        for p in params:
            env.pop(p, None)
        for i, path in self.bound.get(getattr(fn, "name", None), {}).items():
            if i < len(params):
                env[params[i]] = path
        nodes = own_nodes(fn)
        for n in nodes:
            if isinstance(n, ast.withitem) or isinstance(n, (ast.With, ast.AsyncWith)):
                for item in getattr(n, "items", []):
                    if isinstance(item.optional_vars, ast.Name) and names_config_json(item.context_expr):
                        handles.add(item.optional_vars.id)
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                p = self.resolve(n.value, env, handles)
                if p is not None:
                    env[n.targets[0].id] = p
                else:
                    env.pop(n.targets[0].id, None)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                for i, a in enumerate(n.args):
                    p = self.resolve(a, env, handles)
                    if p is not None:
                        self.bound.setdefault(n.func.id, {})[i] = p
            if isinstance(n, (ast.Call, ast.Subscript)) and not isinstance(n, ast.Assign):
                p = self.resolve(n, env, handles)
                if p:
                    self.paths.add(p)
                # a helper: X.get(<param>) on a config dict; the key comes from the caller
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "get" and n.args \
                        and isinstance(n.args[0], ast.Name) and n.args[0].id in params:
                    base = self.resolve(n.func.value, env, handles)
                    if base is not None:
                        self.helpers[fn.name] = (params.index(n.args[0].id), base, params[:1] == ["self"])
            if isinstance(n, ast.Assign):   # the value itself may read keys (x = cfg.get("a").get("b"))
                for sub in ast.walk(n.value):
                    if isinstance(sub, (ast.Call, ast.Subscript)):
                        p = self.resolve(sub, env, handles)
                        if p:
                            self.paths.add(p)
        for n in nodes:
            if isinstance(n, FN):
                self.visit_fn(n, env if isinstance(fn, FN) else {})

    def run(self):
        for _ in range(3):   # a second pass sees the parameters bound by the first
            self.visit_fn(self.tree, {})
        for n in ast.walk(self.tree):   # calls of the helpers with a constant key
            if not isinstance(n, ast.Call):
                continue
            name = n.func.id if isinstance(n.func, ast.Name) else n.func.attr if isinstance(n.func, ast.Attribute) else None
            if name in self.helpers:
                i, base, method = self.helpers[name]
                i -= 1 if method and isinstance(n.func, ast.Attribute) else 0
                if 0 <= i < len(n.args) and const(n.args[i]):
                    self.paths.add(base + (const(n.args[i]),))
        return self.paths


def documented(path):
    text = "\n".join(DOCS.values())
    q = lambda k: re.search(rf"[`\"]{re.escape(k)}[`\"]|`{re.escape(k)}[.:` (]", text) is not None
    if len(path) == 1:
        return q(path[0])
    dotted = ".".join(path)
    if re.search(rf"\b{re.escape(dotted)}\b", text):
        return True
    for doc in DOCS.values():
        for para in re.split(r"\n(?=- )|\n\s*\n", doc):
            if re.search(rf"[`\"]{re.escape(path[-2])}[`\".:]|\b{re.escape(path[-2])}\.", para) and \
                    re.search(rf"[`\"]{re.escape(path[-1])}[`\"]|`{re.escape(path[-1])}[.:` (=]", para):
                return True
    return False


found = {}
for p in SCRIPTS:
    for path in Reader(open(p).read()).run():
        found.setdefault(path, set()).add(os.path.basename(p))

# sanity: the walker sees what we know the scripts read, so an empty result cannot pass silently
for known in [("delivery", "auto_merge_held"), ("limits", "heavy_slots"), ("limits", "review_min_lines"),
              ("validate",), ("docs", "rules"), ("issues", "allowed_authors"), ("ci",)]:
    if known not in found:
        fails.append(f"the walker no longer finds {'.'.join(known)}: the test lost track of the config reads")
for path, where in sorted(found.items()):
    if not documented(path):
        fails.append(f"config key {'.'.join(path)} (read by {', '.join(sorted(where))}) is not documented "
                     "in README.md or commands/config.md")

for f in fails:
    print("FAIL", f)
print(f"config_keys_test: {len(found) - len(fails)}/{len(found)} keys documented" + ("" if not fails else f", {len(fails)} failure(s)"))
sys.exit(1 if fails else 0)
