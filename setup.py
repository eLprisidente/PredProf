import os
import sys
import subprocess

def run_pipenv(args):
    cmd = [sys.executable, "-m", "pipenv"] + args
    return subprocess.run(cmd)

try:
    run_pipenv(["--version"])
except:
    subprocess.run([sys.executable, "-m", "pip", "install", "--user", "pipenv"])

if os.path.exists("Pipfile"):
    run_pipenv(["install"])
elif os.path.exists("requirements.txt"):
    run_pipenv(["install", "-r", "requirements.txt"])
else:
    run_pipenv(["install"])