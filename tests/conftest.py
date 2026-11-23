import pathlib
import sys

# Make `import app` / `import workers` work no matter where pytest is started from.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
