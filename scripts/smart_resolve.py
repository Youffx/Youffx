import sys
import os

def get_patch_added_lines(patch_path):
    added = set()
    if not os.path.exists(patch_path):
        return added
    with open(patch_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.startswith("+") and not line.startswith("+++"):
                added.add(line[1:].strip())
    return added

def smart_resolve_file(file_path, patch_path):
    added_lines = get_patch_added_lines(patch_path)
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    new_lines = []
    i = 0
    n = len(lines)
    while i < n:
        if lines[i].startswith("<<<<<<<"):
            ours = []
            theirs = []
            i += 1
            while i < n and not lines[i].startswith("======="):
                ours.append(lines[i])
                i += 1
            i += 1
            while i < n and not lines[i].startswith(">>>>>>>"):
                theirs.append(lines[i])
                i += 1
            i += 1
            ours_stripped = {l.strip() for l in ours}
            resolved_block = []
            for tl in theirs:
                ts = tl.strip()
                if ts in added_lines or ts in ours_stripped or ts == "":
                    resolved_block.append(tl)
            new_lines.extend(resolved_block)
        else:
            new_lines.append(lines[i])
            i += 1
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

if __name__ == "__main__":
    smart_resolve_file(sys.argv[1], sys.argv[2])
      
