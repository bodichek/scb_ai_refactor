import os

def count_lines(root="."):
    total = 0
    for subdir, _, files in os.walk(root):
        # složky, které nechceš počítat
        if any(skip in subdir for skip in [".venv", "migrations", "static", "media"]):
            continue
        for f in files:
            if f.endswith(".py"):
                with open(os.path.join(subdir, f), "r", encoding="utf-8", errors="ignore") as fh:
                    total += sum(1 for _ in fh)
    return total

print("Celkový počet řádků:", count_lines())
