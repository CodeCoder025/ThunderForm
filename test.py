import os
import shutil
import sys
print("Python executable:", sys.executable)
print("Current directory:", os.getcwd())
print("NPM executable:", shutil.which("npm"))
print("NPX executable:", shutil.which("npx"))