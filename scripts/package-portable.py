"""Wrap audited per-GPU stages as portable ZIPs."""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path, PureWindowsPath
import re
import tempfile
import zipfile

FLAVORS = ("NVIDIA", "AMD")
PLAYER = "veyra_qml_ui.exe"
RETIRED_UPDATE_FILES = {"veyra_update_worker.exe", "portable-update-trust.json"}


def canonical_version(value):
    parts = value.split(".")
    if len(parts) != 3 or any(not re.fullmatch(r"0|[1-9][0-9]{0,4}", p) or int(p) > 65535 for p in parts):
        raise argparse.ArgumentTypeError("expected a three-part Windows version")
    return value


def stem(version, flavor):
    return f"Veyra-{version}-{flavor}-win64-portable"


def numeric_version(value):
    return canonical_version(value.split("-", 1)[0])


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def safe_path(name):
    return (
        0 < len(name) < 500
        and not re.search(r'[\x00-\x1f\\:"*?<>|]', name)
        and all(part not in {"", ".", ".."} and not part.endswith((" ", "."))
                and not PureWindowsPath(part).is_reserved() for part in name.split("/"))
    )


@contextmanager
def new_artifact(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    with tempfile.TemporaryDirectory(prefix="portable-", dir=path.parent) as scratch:
        temporary = Path(scratch) / path.name
        yield temporary
        if path.exists():
            raise FileExistsError(path)
        temporary.rename(path)


def wrap(args):
    metadata = args.stage / "package-manifest.json"
    manifest = json.loads(metadata.read_text(encoding="utf-8-sig"))
    flavor = manifest.get("gpuPackage")
    if flavor not in FLAVORS or numeric_version(manifest["version"]) != args.version:
        raise ValueError("stage version or GPU package does not match")
    if not args.local_test and (manifest.get("localOnly") or not manifest.get("releaseReady")):
        raise ValueError("the stage must pass the normal publisher audit")
    if digest(args.stage / PLAYER) != digest(args.build / PLAYER):
        raise ValueError("use the stage, player and launcher from the same build")
    prefix = stem(args.version, flavor)
    destination = args.output / f"{prefix}.zip"
    rows = manifest["files"]
    names = {row["path"].casefold() for row in rows}
    needed = {PLAYER, "qt6core.dll", "platforms/qwindows.dll", "qml/veyra/main.qml"}
    if len(names) != len(rows) or not needed <= names or names & RETIRED_UPDATE_FILES:
        raise ValueError("duplicate, missing or reserved paths in audited stage")
    with new_artifact(destination) as temporary, \
            zipfile.ZipFile(temporary, "x", zipfile.ZIP_DEFLATED, compresslevel=3, allowZip64=False) as bundle:
        bundle.writestr(f"{prefix}/portable-package.txt", f"VEYRA_PORTABLE_V1\n{flavor}\n")
        bundle.writestr(f"{prefix}/current-version.txt", f"{args.version}\n\n")
        bundle.write(args.build / "veyra_portable_launcher.exe", f"{prefix}/Veyra.exe")
        version_path = f"{prefix}/versions/{args.version}"
        bundle.write(metadata, f"{version_path}/package-manifest.json")
        for row in rows:
            name = row["path"]
            if (not safe_path(name) or name.casefold() == "package-manifest.json"
                    or name.casefold().startswith(("logs/", "runtime_local/user-data-2.0.0/", "runtime_local/luts/"))):
                raise ValueError(f"invalid or user-specific stage path: {name}")
            source = args.stage / name
            if (not source.is_file() or source.resolve() != args.stage.resolve() / name
                    or source.stat().st_size != row["size"] or digest(source) != row["sha256"].lower()):
                raise ValueError(f"stage file does not match publisher audit: {name}")
            bundle.write(source, f"{version_path}/{name}")
        bundle.writestr(f"{prefix}/START-HERE.txt",
                        "运行 Veyra.exe。2.1.9 用户先退出旧版，再按需复制旧目录中的\n"
                        "runtime_local/user-data-2.0.0 与 runtime_local/luts 到新版根目录的 runtime_local。\n"
                        "\n"
                        "Start Veyra.exe. To migrate from 2.1.9, close it, then copy\n"
                        "runtime_local/user-data-2.0.0 and runtime_local/luts to this folder's runtime_local.\n")
    print(destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", type=canonical_version, required=True)
    for option in ("stage", "build", "output"):
        parser.add_argument("--" + option, type=Path, required=True)
    parser.add_argument("--local-test", action="store_true", help="allow a stage marked for local tests")
    wrap(parser.parse_args())


if __name__ == "__main__":
    main()
