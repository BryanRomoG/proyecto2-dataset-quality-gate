"""Crea un release del dataset: tag git semver + push del cache DVC.

No inventa versionado propio — usa exactamente el mecanismo que ya pide el
AC (releases con tag semver) sobre lo que dvc.lock ya versiona.
"""

import argparse
import subprocess
import sys


def run(cmd: list[str]) -> None:
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("version", help="Ej. v1.0.0")
    parser.add_argument("-m", "--message", required=True)
    parser.add_argument("--remote", default="dev", help="Remote DVC al que se hace push")
    parser.add_argument("--skip-push", action="store_true", help="No hacer dvc push (ensayo)")
    args = parser.parse_args()

    if not args.version.startswith("v"):
        sys.exit(f"la versión debe empezar con 'v' (semver), recibí: {args.version}")

    status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if status.stdout.strip():
        sys.exit("hay cambios sin commitear — commitea o descarta antes de crear el release")

    if not args.skip_push:
        run(["dvc", "push", "-r", args.remote])

    run(["git", "tag", "-a", args.version, "-m", args.message])
    print(f"\nRelease {args.version} creado. Falta: git push origin {args.version}")
