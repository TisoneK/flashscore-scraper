import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.cli.cli_manager import main

if __name__ == "__main__":
    main()
