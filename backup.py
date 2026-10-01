"""Create a consistent online SQLite backup (including uploaded files)."""
import argparse,sqlite3,os,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parent
if (ROOT/'.env').exists():
 for line in (ROOT/'.env').read_text().splitlines():
  if line.strip() and not line.lstrip().startswith('#') and '=' in line:
   k,v=line.split('=',1);os.environ.setdefault(k.strip(),v.strip().strip('"').strip("'"))
parser=argparse.ArgumentParser();parser.add_argument('--output',default=str(ROOT/'backups'));args=parser.parse_args()
source=Path(os.environ.get('ETHAN_DATA_DIR',str(ROOT/'data')))/'lms.sqlite3'
if not source.exists():raise SystemExit('No runtime database found. Set ETHAN_DATA_DIR if needed.')
folder=Path(args.output);folder.mkdir(parents=True,exist_ok=True);target=folder/('ethan-lms-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S')+'.sqlite3')
with sqlite3.connect(source) as src,sqlite3.connect(target) as dst:src.backup(dst)
os.chmod(target,0o600)
print('Backup created:',target)
