import os
import json
from datetime import datetime

print('=== JETinc Collage & Defrag Builder Initialized ===')
target_dir = r'F:\JETinc'
output_json = r'F:\JETinc\JETcity_Launchpad\jetinc_build\collage_defrag_manifest.json'

fragments = []
for root, dirs, files in os.walk(target_dir):
    for file in files:
        if any(ext in file.lower() for ext in ['.py', '.json', '.txt', '.log']):
            full_path = os.path.join(root, file)
            try:
                size = os.path.getsize(full_path)
            except OSError:
                size = 0
            
            fragments.append({
                'file_name': file,
                'path': full_path,
                'size_bytes': size,
                'defrag_status': 'indexed_clean',
                'timestamp': datetime.utcnow().isoformat()
            })

build_data = {
    'total_fragments': len(fragments),
    'engine': 'GenOne-Collage-Defrag',
    'manifest': fragments
}

with open(output_json, 'w') as f:
    json.dump(build_data, f, indent=4)

print(f'Defrag and Collage synthesis complete. Total fragments processed: {len(fragments)}')
print(f'Output manifest saved to: {output_json}')
