import sys
sys.path.insert(0, r'C:\Users\tison\Dev\flashscore-scraper')
from src.cli.cli_manager import CLIManager
print('creating')
c = CLIManager()
print('created')
try:
    del c
    print('deleted')
except Exception as e:
    print('delete error', e)
