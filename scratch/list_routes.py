import re

def list_file_routes(filepath):
    print(f"\n--- Routes in {filepath} ---")
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    lines = content.split('\n')
    for idx, line in enumerate(lines):
        if '@app.' in line or '@router.' in line or 'router.get' in line or 'router.post' in line:
            print(f"Line {idx+1}: {line.strip()}")

list_file_routes('api/main.py')
list_file_routes('api/analytics.py')
