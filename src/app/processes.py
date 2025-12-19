import subprocess

def scan_processes():
    """
    Returns processes as:
    (pid:int, name:str, cpu:float, mem:float, cmd:str)
    """
    try:
        out = subprocess.check_output(
            ["ps", "-eo", "pid,comm,%cpu,%mem,args", "--no-headers"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        print("ps failed:", e)
        return []

    rows = []

    for line in out.splitlines():
        parts = line.strip().split(None, 4)
        if len(parts) < 5:
            continue

        try:
            pid = int(parts[0])
            name = parts[1]
            cpu = float(parts[2])
            mem = float(parts[3])
            cmd = parts[4]
        except Exception:
            continue

        # Filter kernel threads ONLY (they look like "[kworker/0:1]")
        if cmd.startswith("[") and cmd.endswith("]"):
            continue

        rows.append((pid, name, cpu, mem, cmd))

    return rows
