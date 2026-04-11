from pathlib import Path

path = Path('cloudservice/requirements.txt')
lines = path.read_text().splitlines()
needle = 'django-db-geventpool==4.0.8'
if 'djongo==' not in "".join(lines):
    try:
        idx = lines.index(needle) + 1
    except ValueError:
        idx = len(lines)
    lines.insert(idx, 'djongo==1.5.4')
    path.write_text("\n".join(lines) + "\n")
