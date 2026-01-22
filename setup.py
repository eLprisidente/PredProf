import os
import sys
import subprocess

# Используем правильный Python для запуска pipenv
def run_pipenv(args):
    # На Mac/Linux может быть проблема с путями, используем sys.executable
    cmd = [sys.executable, "-m", "pipenv"] + args
    return subprocess.run(cmd)

# 1. Установить pipenv если нет
try:
    run_pipenv(["--version"])
except:
    subprocess.run([sys.executable, "-m", "pip", "install", "--user", "pipenv"])

# 2. Установить зависимости
if os.path.exists("Pipfile"):
    run_pipenv(["install"])
elif os.path.exists("requirements.txt"):
    run_pipenv(["install", "-r", "requirements.txt"])
else:
    run_pipenv(["install"])