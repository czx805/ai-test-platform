import subprocess
import shlex

REPO_DIR = r"D:\aitest\wukong\ai-test-platform"
VENV_PY = r"D:\aitest\wukong\ai-test-platform\venvs\Scripts\python.exe"

cmd = f'"{VENV_PY}" -m pytest tests/test_login.py -v -n auto'
cmd_list = shlex.split(cmd)

print(f"Running: {cmd_list}")
result = subprocess.run(
    cmd_list,
    capture_output=True,
    text=True,
    cwd=REPO_DIR,
    timeout=120
)
print("STDOUT:")
print(result.stdout[:500])
print("\nSTDERR:")
print(result.stderr[:500])
