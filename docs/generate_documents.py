"""Build the report and manual from the supplied MUST LaTeX cover (XeLaTeX)."""
from pathlib import Path
import shutil
import subprocess
import tempfile


def main():
    docs = Path(__file__).resolve().parent
    sources = docs / 'latex'
    if not shutil.which('xelatex'):
        raise SystemExit('XeLaTeX is required. Use TeX Live, MiKTeX or Overleaf (XeLaTeX).')
    with tempfile.TemporaryDirectory(prefix='taskgraph-tex-') as temp:
        for stem, output in [('report', 'TaskGraph_BD1_Report.pdf'),
                             ('manual', 'TaskGraph_Manual.pdf')]:
            log_path = Path(temp) / (stem + '-build.txt')
            with log_path.open('w') as log:
                for _ in range(2):
                    result = subprocess.run(['xelatex', '-interaction=nonstopmode', '-halt-on-error',
                        '-output-directory', temp, stem + '.tex'], cwd=sources,
                        stdout=log, stderr=subprocess.STDOUT)
                    if result.returncode:
                        raise SystemExit(log_path.read_text(errors='replace')[-8000:])
            shutil.copy2(Path(temp) / (stem + '.pdf'), docs / output)
            shutil.copy2(log_path, docs / (stem + '-latex-build.log'))
            print('Created', output)


if __name__ == '__main__':
    main()
