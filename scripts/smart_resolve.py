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
            marker_ours = lines[i]
            ours = []
            theirs = []
            
            i += 1
            while i < n and not lines[i].startswith("======="):
                ours.append(lines[i])
                i += 1
            
            marker_eq = lines[i] if i < n else ""
            if i < n:
                i += 1
                
            while i < n and not lines[i].startswith(">>>>>>>"):
                theirs.append(lines[i])
                i += 1
            
            marker_theirs = lines[i] if i < n else ""
            if i < n:
                i += 1
            
            ours_stripped = [l.strip() for l in ours]
            theirs_stripped = [l.strip() for l in theirs]
            
            resolved = False
            resolved_block = []
            
            if ours_stripped == theirs_stripped:
                resolved_block = ours
                resolved = True
            elif not ours and theirs:
                if all(l in added_lines or l == "" for l in theirs_stripped):
                    resolved_block = theirs
                    resolved = True
            elif not theirs and ours:
                resolved_block = ours
                resolved = True
            
            if resolved:
                new_lines.extend(resolved_block)
            else:
                new_lines.append(marker_ours)
                new_lines.extend(ours)
                if marker_eq:
                    new_lines.append(marker_eq)
                new_lines.extend(theirs)
                if marker_theirs:
                    new_lines.append(marker_theirs)
        else:
            new_lines.append(lines[i])
            i += 1
            
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

if __name__ == "__main__":
    if len(sys.argv) > 2:
        smart_resolve_file(sys.argv[1], sys.argv[2])
        
