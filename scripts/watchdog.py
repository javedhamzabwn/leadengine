#!/usr/bin/env python3
"""LeadEngine watchdog — 10-minute health/stall monitor.

Stdlib only (must run even when the project venv is broken).
Writes state to data/watchdog_state.json. Prints a short human-readable
report; exits 0 when all green, 1 when anything needs attention.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
STATE_FILE = os.path.join(DATA, "watchdog_state.json")
TASKS_FILE = os.path.join(ROOT, "TASKS.md")
VERBOSE = "--verbose" in sys.argv

issues: list[str] = []
notes: list[str] = []


def vprint(*a):
    if VERBOSE:
        print(*a)


def run(cmd, timeout=20):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=ROOT)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except Exception as e:
        return 127, "", str(e)


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {"runs": 0, "fail_counters": {}, "last_git_head": None,
                "last_todo_count": None, "last_tracebacks": []}


def save_state(s):
    os.makedirs(DATA, exist_ok=True)
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(s, f, indent=2)
    os.replace(tmp, STATE_FILE)


# ── 1. TASKS.md: unfinished P0/P1 ──────────────────────────────────────
def check_tasks():
    if not os.path.exists(TASKS_FILE):
        issues.append("TASKS.md missing")
        return
    text = open(TASKS_FILE).read()
    p0_open, p1_open, blocked = [], [], []
    # New ledger format: "### LEAD-006: title" followed by "- Priority: P0 · Status: **IN_PROGRESS**"
    for m in re.finditer(r"^#{2,4}\s*(LEAD-\d+):[^\n]*\n((?:[^\n]*\n){0,3})", text, re.M):
        task_id = m.group(1)
        head = m.group(0)
        status_m = re.search(r"Status:\s*\*\*(\w+)\*\*", head)
        prio_m = re.search(r"Priority:\s*(P\d)", head)
        status = status_m.group(1) if status_m else "TODO"
        prio = prio_m.group(1) if prio_m else None
        if status in ("TODO", "IN_PROGRESS"):
            if prio == "P0":
                p0_open.append(f"{task_id}({status})")
            elif prio == "P1":
                p1_open.append(task_id)
        if status == "BLOCKED":
            blocked.append(task_id)
    # Legacy checkbox format fallback
    for m in re.finditer(r"^- \[[ x]\]\s*(LEAD-\d+)[^\n]*", text, re.M):
        line = m.group(0)
        if "[ ]" in line[:8] and m.group(1) not in p0_open + p1_open:
            p1_open.append(m.group(1) + "(legacy)")
    if p0_open:
        issues.append(f"P0 unfinished: {', '.join(p0_open[:8])}")
    if blocked:
        issues.append(f"BLOCKED tasks: {', '.join(blocked[:8])}")
    notes.append(f"open P1: {len(p1_open)}")


# ── 2. Stall detection ─────────────────────────────────────────────────
def check_stall(state):
    rc, head, _ = run(["git", "log", "-1", "--format=%H %ct"])
    now = time.time()
    if rc == 0 and head:
        h, ct = head.split()
        age_min = (now - int(ct)) / 60
        state["last_git_head"] = h
        notes.append(f"last commit {age_min:.0f}m ago")
        if age_min > 45:
            # only a stall if there is unfinished work
            text = open(TASKS_FILE).read() if os.path.exists(TASKS_FILE) else ""
            if re.search(r"- \[ \]\s*LEAD-", text):
                issues.append(f"STALL? no commit for {age_min:.0f}m with open tasks")
    # file activity in backend/frontend/tests
    newest = 0
    for d in ("backend", "frontend", "tests", "scripts"):
        p = os.path.join(ROOT, d)
        if not os.path.isdir(p):
            continue
        for dp, _, fns in os.walk(p):
            if ".venv" in dp or "node_modules" in dp:
                continue
            for fn in fns:
                try:
                    mt = os.path.getmtime(os.path.join(dp, fn))
                    newest = max(newest, mt)
                except OSError:
                    pass
    if newest:
        idle_min = (now - newest) / 60
        notes.append(f"newest source change {idle_min:.0f}m ago")
        prev_idle = state.get("last_idle_min", 0)
        state["last_idle_min"] = idle_min
        if idle_min > 40 and prev_idle and idle_min > prev_idle + 9:
            issues.append(f"STALL? no source change for {idle_min:.0f}m and idle time growing")


# ── 3. Backend health ──────────────────────────────────────────────────
def check_backend(state=None):
    db = os.path.join(DATA, "leadengine.db")
    venv_py = os.path.join(ROOT, ".venv", "bin", "python")
    if not os.path.exists(db):
        issues.append("DB missing: data/leadengine.db not found")
        return
    # query via duckdb only if importable; else just check size
    size_mb = os.path.getsize(db) / 1e6
    notes.append(f"db size {size_mb:.1f}MB")
    try:
        sys.path.insert(0, os.path.join(ROOT, ".venv", "lib",
                                        f"python{sys.version_info[0]}.{sys.version_info[1]}",
                                        "site-packages"))
        import duckdb  # noqa
    except Exception:
        pass
    rc, out, err = run([venv_py,
        "-c",
        "import duckdb; c=duckdb.connect(%r, read_only=True); "
        "print(c.execute(\"SELECT COUNT(*) FROM company\").fetchone()[0])" % db], timeout=30)
    if rc != 0:
        err1 = err[:160]
        if "Could not set lock" in err:
            # writer (normalize) is mid-run; not a real failure
            notes.append("db locked by running writer (normalize in progress)")
            # clear any stale lock-failure counter so it doesn't escalate
            if state is not None:
                for k in [k for k in state.get("fail_counters", {})
                          if "DB unreadable" in k]:
                    state["fail_counters"].pop(k, None)
            return
        issues.append(f"DB unreadable/company table missing: {err1}")
    else:
        notes.append(f"company rows: {out.strip()}")
        if out.strip() == "0":
            issues.append("company table is empty")


# ── 4. API liveness (only when expected) ───────────────────────────────
def check_api():
    flag = os.path.join(DATA, "api_expected_running")
    if not os.path.exists(flag):
        vprint("api not expected running; skip")
        return
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=8) as r:
            body = r.read(120).decode()
            notes.append(f"api /health ok: {body[:60]}")
    except Exception as e:
        issues.append(f"API expected running but /health failed: {e}")


# ── 5. Background jobs ─────────────────────────────────────────────────
def check_procs():
    rc, out, _ = run(["ps", "aux"])
    if rc != 0:
        return
    for name in ("backend.normalize", "pytest", "uvicorn", "next-server", "next dev"):
        if name in out:
            notes.append(f"proc running: {name}")
    # normalize stuck? (running > 25 min is suspicious for 7.5k rows)
    for line in out.splitlines():
        if "backend.normalize" in line and "watchdog" not in line:
            parts = line.split()
            try:
                # ps aux: index 9 is elapsed time
                etime = parts[9]
                notes.append(f"normalize elapsed: {etime}")
            except IndexError:
                pass


# ── 6. New tracebacks in logs ──────────────────────────────────────────
def check_logs(state):
    tb = []
    for fn in ("backend.log", "normalize.log"):
        p = os.path.join(ROOT, fn)
        p2 = os.path.join(DATA, fn)
        for path in (p, p2):
            if os.path.exists(path):
                try:
                    with open(path, errors="replace") as f:
                        lines = f.readlines()[-400:]
                    tb += [l.strip()[:160] for l in lines if "Traceback" in l]
                except OSError:
                    pass
    new = [t for t in tb if t not in state.get("last_tracebacks", [])]
    state["last_tracebacks"] = tb[-20:]
    if new:
        issues.append(f"new tracebacks in logs ({len(new)}): {new[0][:120]}")


# ── 7. Disk ────────────────────────────────────────────────────────────
def check_disk():
    total, used, free = shutil.disk_usage(ROOT)
    free_gb = free / 1e9
    notes.append(f"disk free {free_gb:.1f}GB")
    if free_gb < 2:
        issues.append(f"disk low: {free_gb:.1f}GB free")


# ── 8. Dependencies importable ─────────────────────────────────────────
def check_deps():
    venv_py = os.path.join(ROOT, ".venv", "bin", "python")
    if not os.path.exists(venv_py):
        issues.append(".venv missing")
        return
    rc, out, err = run([venv_py, "-c",
                        "import fastapi, duckdb, pydantic; print('ok')"], timeout=30)
    if rc != 0 or "ok" not in out:
        issues.append(f"venv imports broken: {(err or out)[:160]}")


# ── 9. TODO/FIXME drift ────────────────────────────────────────────────
def check_todos(state):
    count = 0
    for dp, _, fns in os.walk(os.path.join(ROOT, "backend")):
        for fn in fns:
            if fn.endswith(".py"):
                try:
                    with open(os.path.join(dp, fn), errors="replace") as f:
                        count += len(re.findall(r"TODO|FIXME|XXX|HACK", f.read()))
                except OSError:
                    pass
    prev = state.get("last_todo_count")
    state["last_todo_count"] = count
    notes.append(f"TODO/FIXME markers: {count}")
    if prev is not None and count > prev + 5:
        issues.append(f"TODO markers jumped {prev} -> {count}")


def main():
    t0 = time.time()
    state = load_state()
    state["runs"] += 1
    state["last_run"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    for fn in (check_tasks, check_api, check_procs, check_deps):
        try:
            fn()
        except Exception as e:
            issues.append(f"watchdog self-error in {fn.__name__}: {e}")
    for fn in (check_backend, check_todos):
        try:
            fn(state)
        except Exception as e:
            issues.append(f"watchdog self-error in {fn.__name__}: {e}")
    try:
        check_stall(state)
    except Exception as e:
        issues.append(f"watchdog self-error in check_stall: {e}")
    try:
        check_logs(state)
    except Exception as e:
        issues.append(f"watchdog self-error in check_logs: {e}")
    try:
        check_disk()
    except Exception as e:
        issues.append(f"watchdog self-error in check_disk: {e}")

    # consecutive-failure tracking + escalation
    counters = state.setdefault("fail_counters", {})
    for issue in issues:
        key = issue[:80]
        counters[key] = counters.get(key, 0) + 1
    for key in list(counters):
        if not any(key == i[:80] for i in issues):
            counters.pop(key, None)
    escalate = [k for k, c in counters.items() if c >= 3]

    save_state(state)
    dt = time.time() - t0

    print(f"watchdog run #{state['runs']} ({dt:.1f}s) — "
          f"{'ALL GREEN' if not issues else f'{len(issues)} ISSUE(S)'}")
    for n in notes:
        print(f"  · {n}")
    for i in issues:
        c = counters.get(i[:80], 1)
        tag = "ESCALATE" if c >= 3 else f"seen {c}x"
        print(f"  ! [{tag}] {i}")
    if escalate:
        print("ESCALATE: " + "; ".join(escalate))

    # continuation hint: first IN_PROGRESS, else first TODO
    if os.path.exists(TASKS_FILE):
        text = open(TASKS_FILE).read()
        nxt = None
        for m in re.finditer(r"^#{2,4}\s*(LEAD-\d+):\s*([^\n]*)\n((?:[^\n]*\n){0,3})", text, re.M):
            head = m.group(0)
            sm = re.search(r"Status:\s*\*\*(\w+)\*\*", head)
            st = sm.group(1) if sm else "TODO"
            if st == "IN_PROGRESS":
                nxt = f"{m.group(1)}: {m.group(2).strip()}"
                break
            if st == "TODO" and nxt is None:
                nxt = f"{m.group(1)}: {m.group(2).strip()}"
        if nxt and not any("STALL" in i for i in issues):
            print(f"CONTINUE: next task → {nxt[:100]}")

    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
