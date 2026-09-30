import sys
from pathlib import Path

# Garante que "src.*" resolva rodando o pytest de qualquer pasta.
sys.path.insert(0, str(Path(__file__).parent))
