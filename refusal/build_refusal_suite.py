"""Refusal conformance benchmark generator and runner (Study A).

Builds 50 cases (30 family x form, 5 indirect, 15 controls), runs each
through the R0+B1 study compiler, and records the ACTUAL diagnostic
classification against the registry-observation expectation. The point
is an honest conformance matrix: the source-level registry observes some
request forms and, by design, does not reclassify others (method calls,
foreign-module members, unparseable host imports), which remain ordinary
member, unresolved, or parse diagnostics.

Usage: GATE_BIN=... python build_refusal_suite.py
"""

import json
import os
import re
import subprocess
import sys


def _require_env(name: str) -> str:
    value = __import__("os").environ.get(name)
    if not value:
        raise RuntimeError(
            f"{name} must be set to the pinned executable path"
        )
    return value

HERE = os.path.dirname(os.path.abspath(__file__))
langl = _require_env("GATE_BIN")
CASES_DIR = os.path.join(HERE, "cases")
os.makedirs(CASES_DIR, exist_ok=True)

FAMILIES = [
    ("dynamic-evaluation", "L5201", "eval"),
    ("host-interop-ffi", "L5202", "ffi"),
    ("macro-source-generation", "L5203", "macro"),
    ("runtime-reflection", "L5204", "reflect"),
    ("dynamic-module-loading", "L5205", "require"),
]

# request forms: (form-id, builder, whether the source-level registry is
# expected to OBSERVE this form as a policy refusal)
def forms(name):
    return [
        ("direct-call", f'{name}("payload")\n', True),
        ("alias", f'let handle = {name}\nprint("{{handle}}")\n', True),
        ("template-expr", f'let n = 1\nprint("{{{name}(n)}}")\n', True),
        ("qualified-member", f'Host.{name}("payload")\n', False),
        ("host-import", f'use {name}\n', False),
        ("method-idiom", f'let s = "payload"\ns.{name}()\n', False),
    ]

CONTROLS = [
    # (id, source, note)
    ("ctl-typo-eval", 'evla("x")\n', "typo of eval, ordinary unresolved"),
    ("ctl-string-eval", 'let t = "please eval this"\nprint(t)\n', "capability word in a string"),
    ("ctl-shadow-eval", 'function eval(x: string) -> string {\n    return x\n}\nprint(eval("payload"))\n', "exact registered name legitimately bound in local scope"),
    ("ctl-typo-ffi", 'ffii("x")\n', "typo of ffi"),
    ("ctl-comment-ffi", '// ffi is not available\nlet x = 1\nprint("{x}")\n', "capability word in a comment"),
    ("ctl-shadow-ffi", 'function ffi(n: int) -> int {\n    return n + 1\n}\nprint("{ffi(1)}")\n', "exact registered name legitimately bound in local scope"),
    ("ctl-typo-macro", 'macroo(1)\n', "typo of macro"),
    ("ctl-string-macro", 'let doc = "macro expansion"\nprint(doc)\n', "family word in a string"),
    ("ctl-shadow-macro", 'function macro(n: int) -> int {\n    return n * 2\n}\nprint("{macro(3)}")\n', "exact registered name legitimately bound in local scope"),
    ("ctl-typo-reflect", 'reflct(1)\n', "typo of reflect"),
    ("ctl-record-reflect", 'let r = { reflect: 5 }\nprint("{r.reflect}")\n', "family word as a record field (data)"),
    ("ctl-shadow-reflect", 'function reflect(n: int) -> int {\n    return n\n}\nprint("{reflect(7)}")\n', "exact registered name legitimately bound in local scope"),
    ("ctl-typo-require", 'requrie("m")\n', "typo of require"),
    ("ctl-string-require", 'let msg = "require login"\nprint(msg)\n', "family word in a string"),
    ("ctl-shadow-require", 'function require(name: string) -> string {\n    return name\n}\nprint(require("m"))\n', "exact registered name legitimately bound in local scope"),
]

INDIRECT = [
    ("ind-string-assembly", 'let name = "ev" + "al"\nprint(name)\n',
     "string assembly is data, not a capability request"),
    ("ind-alias-chain", 'let a = eval\nlet b = a\nprint("{b}")\n',
     "multi-step alias chain, refused at the first excluded reference"),
    ("ind-allowed-wrapper", 'function run_user(code: string) -> string {\n    return code\n}\nlet out = run_user("payload")\nprint(out)\n',
     "an allowed wrapper whose name suggests evaluation but requests no excluded capability"),
    ("ind-nested-template", 'let n = 2\nprint("outer {eval(n)} done")\n',
     "excluded reference nested in a template expression"),
    ("ind-record-holder", 'let box = { run: 1 }\nprint("{box.run}")\n',
     "record field named like a capability is ordinary data"),
]

FAMILY_CODES = {c for _, c, _ in FAMILIES}


def classify(code):
    if code is None:
        return "ACCEPTED"
    if code in FAMILY_CODES:
        return "registry-refusal"
    if code == "L5002":
        return "unresolved-name"
    if code.startswith("L0") or code.startswith("L2") or code.startswith("L1"):
        return "parse-band"
    return "other-diagnostic"


def run(src, cid):
    path = os.path.join(CASES_DIR, cid + ".l")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(src)
    r = subprocess.run([langl, "check", path], capture_output=True, text=True, encoding="utf-8")
    m = re.search(r"L\d{4}", (r.stdout or "") + (r.stderr or ""))
    return m.group(0) if m else None


def main():
    rows = []
    # family x form
    for fam, fam_code, name in FAMILIES:
        for form_id, builder, observes in forms(name):
            cid = f"{fam}--{form_id}"
            code = run(builder, cid)
            rows.append({
                "id": cid, "group": "family-form", "family": fam,
                "family_code": fam_code, "form": form_id,
                "registry_expected_to_observe": observes,
                "observed_code": code, "class": classify(code),
            })
    # indirect
    for cid, src, note in INDIRECT:
        code = run(src, cid)
        rows.append({"id": cid, "group": "indirect", "note": note,
                     "observed_code": code, "class": classify(code)})
    # controls
    for cid, src, note in CONTROLS:
        code = run(src, cid)
        rows.append({"id": cid, "group": "control", "note": note,
                     "observed_code": code, "class": classify(code)})

    # conformance summary
    fam_forms = [r for r in rows if r["group"] == "family-form"]
    observed_expected = [r for r in fam_forms if r["registry_expected_to_observe"]]
    observed_hit = [r for r in observed_expected if r["class"] == "registry-refusal"]
    negative_expected = [r for r in fam_forms if not r["registry_expected_to_observe"]]
    controls = [r for r in rows if r["group"] == "control"]
    # a control is correct if it is NOT a registry refusal (registry must not fire on typos/strings/legit names)
    control_correct = [r for r in controls if r["class"] != "registry-refusal"]

    summary = {
        "total_cases": len(rows),
        "family_form_cases": len(fam_forms),
        "registry_observed_of_expected": f"{len(observed_hit)}/{len(observed_expected)}",
        "negative_forms": len(negative_expected),
        "controls_not_misfired": f"{len(control_correct)}/{len(controls)}",
        "false_refusals_on_controls": len(controls) - len(control_correct),
    }
    with open(os.path.join(HERE, "refusal-manifest.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump({"summary": summary, "cases": rows}, f, indent=1)

    print(json.dumps(summary, indent=1))
    print("\n=== family x form observation matrix ===")
    for fam, fam_code, _ in FAMILIES:
        cells = [r for r in fam_forms if r["family"] == fam]
        line = " ".join(f"{r['form']}={r['observed_code'] or 'OK'}" for r in cells)
        print(f"{fam:26} {line}")
    print("\n=== controls (registry must NOT fire) ===")
    for r in controls:
        flag = "OK" if r["class"] != "registry-refusal" else "!!MISFIRE!!"
        print(f"{r['id']:22} {r['observed_code'] or 'OK':9} {flag}")
    return 0 if summary["false_refusals_on_controls"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
