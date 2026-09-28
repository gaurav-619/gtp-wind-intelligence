import glob
import re

files = glob.glob('app/**/*.py', recursive=True)
widget_pattern = re.compile(r'st\.(selectbox|slider|text_input|multiselect|radio|button|checkbox|number_input)\s*\(')

total_widgets = 0
duplicates_found = False

for f in sorted(files):
    with open(f, 'r', encoding='utf-8') as fh:
        lines = fh.readlines()
    
    file_keys = {}
    print(f"\n=== File: {f} ===")
    for idx, line in enumerate(lines, 1):
        m = widget_pattern.search(line)
        if m:
            widget_type = m.group(1)
            # Check if key= is within this call block
            chunk = "".join(lines[idx-1:min(idx+12, len(lines))])
            key_m = re.search(r'key\s*=\s*["\']([^"\']+)["\']', chunk)
            if key_m:
                key_name = key_m.group(1)
                status = f'key="{key_name}"'
                if key_name in file_keys:
                    print(f'  Line {idx}: [DUPLICATE KEY] st.{widget_type} key="{key_name}" already used at line {file_keys[key_name]}')
                    duplicates_found = True
                else:
                    file_keys[key_name] = idx
                    print(f'  Line {idx}: [OK] st.{widget_type} ({status})')
            else:
                print(f'  Line {idx}: [NO KEY] st.{widget_type} (single instance or keyless)')
            total_widgets += 1

if not duplicates_found:
    print(f"\nPASS: Verified {total_widgets} Streamlit widgets across all pages. ZERO duplicate keys found!")
else:
    print("\nFAIL: Duplicate keys detected!")
