import subprocess
import os

env = os.environ.copy()
env["PYTHONPATH"] = "ProjectValidator"

p = subprocess.run(
    [r".venv\Scripts\python.exe", r"ProjectValidator\scratch\run_val.py"],
    env=env,
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace"
)

with open(r"ProjectValidator\scratch\out.txt", "w", encoding="utf-8") as f:
    f.write(p.stdout)
    f.write("\nSTDERR:\n")
    f.write(p.stderr)
