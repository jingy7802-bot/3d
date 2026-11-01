"""python reassemble.py --output restored_text"""
import argparse,hashlib,json
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('--output',default='restored_text');args=parser.parse_args()
base=Path(__file__).resolve().parent;dest=Path(args.output).resolve();m=json.loads((base/'manifest.json').read_text(encoding='utf-8'))
for item in m['files']:
    target=dest/item['path']
    if not target.resolve().is_relative_to(dest):raise ValueError('Invalid destination path')
    chunks=[]
    for part in item['parts']:
        data=(base/part['path']).read_bytes()
        assert hashlib.sha256(data).hexdigest()==part['sha256'],part['path']
        chunks.append(data)
    data=b''.join(chunks);assert hashlib.sha256(data).hexdigest()==item['sha256'],item['path']
    if target.exists() and target.read_bytes()!=data:raise FileExistsError('Refusing to overwrite changed file: '+str(target))
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
print('Restored and verified',len(m['files']),'text files to',dest)
