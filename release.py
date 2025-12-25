#!/usr/bin/env python3
import os
import re
import sys
import shutil
import subprocess
from pathlib import Path

# -------------------------
# CONFIG & STATE
# -------------------------
APP_NAME = "SimplyToast"
TAG_PREFIX = "v"

TAG_CREATED = False
TAG = None

ROOT = Path(__file__).resolve().parent
BUILD_DIR = ROOT / "build"
OUT_DIR = ROOT / "out"


def run(cmd, cwd=None):
    subprocess.run(cmd, cwd=cwd, check=True)


def cleanup_on_failure(exit_code):
    global TAG_CREATED, TAG

    if exit_code != 0:
        print(f"⚠️ Script failed with exit code {exit_code}. Cleaning up...")

        # 1. Remove build artifacts
        shutil.rmtree(BUILD_DIR, ignore_errors=True)
        shutil.rmtree(OUT_DIR, ignore_errors=True)

        # 2. Rollback git changes
        subprocess.run(
            ["git", "reset", "--hard", "HEAD"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # 3. Delete tag if created
        if TAG_CREATED and TAG:
            subprocess.run(["git", "tag", "-d", TAG])

        print("🧹 Environment restored to original state.")


def main():
    global TAG_CREATED, TAG

    # -------------------------
    # ARGUMENTS & PREFLIGHT
    # -------------------------
    if len(sys.argv) < 2:
        print("❌ Usage: ./release.py <version> (e.g. 1.2.3)")
        sys.exit(1)

    VERSION = sys.argv[1]

    if not re.match(r"^[0-9]+(\.[0-9]+)+$", VERSION):
        print("❌ Usage: ./release.py <version> (e.g. 1.2.3)")
        sys.exit(1)

    TAG = f"{TAG_PREFIX}{VERSION}"

    CURRENT_BRANCH = (
        subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True
        )
        .strip()
    )

    if subprocess.check_output(["git", "status", "--porcelain"], text=True).strip():
        print("❌ Git tree is dirty. Commit or stash changes first.")
        sys.exit(1)

    # -------------------------
    # VERSION BUMP
    # -------------------------
    print("▶ Updating version.py")
    version_file = ROOT / "src" / "version.py"
    version_file.write_text(f'VERSION = "{VERSION}"\n')

    run(["git", "add", "src/version.py"])

    diff_exit = subprocess.run(
        ["git", "diff", "--cached", "--quiet"]
    ).returncode

    if diff_exit == 0:
        print(f"ℹ️ version.py already at {VERSION}")
    else:
        run(["git", "commit", "-m", f"Bump version to {VERSION}"])

    # -------------------------
    # BUILDING
    # -------------------------
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("▶ Packing Source...")
    artifact_dir = BUILD_DIR / "artifact"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    run(
        [
            "rsync",
            "-a",
            "--exclude=__pycache__",
            "--exclude=*.pyc",
            "--exclude=*.AppImage",
            "src/",
            str(artifact_dir / "src/"),
        ]
    )

    run(["rsync", "-a", "data/", str(artifact_dir / "data/")])

    artifact_tar = BUILD_DIR / "artifact.tar.gz"
    run(
        [
            "tar",
            "-czf",
            str(artifact_tar),
            "-C",
            str(artifact_dir),
            ".",
        ]
    )

    # -------------------------
    # ARCH
    # -------------------------
    print("▶ Building Arch...")
    arch_dir = BUILD_DIR / "arch"
    arch_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy(ROOT / "packaging/arch/PKGBUILD", arch_dir / "PKGBUILD")
    shutil.copy(artifact_tar, arch_dir / artifact_tar.name)

    pkgbuild = arch_dir / "PKGBUILD"
    pkgbuild.write_text(
        re.sub(
            r"^pkgver=.*",
            f"pkgver={VERSION}",
            pkgbuild.read_text(),
            flags=re.MULTILINE,
        )
    )

    run(["makepkg", "-sf", "--noconfirm"], cwd=arch_dir)

    for pkg in arch_dir.glob("*.pkg.tar.zst"):
        shutil.move(pkg, OUT_DIR / pkg.name)

    # -------------------------
    # DEB
    # -------------------------
    print("▶ Building DEB...")
    deb_dir = BUILD_DIR / "deb"
    shutil.copytree(ROOT / "packaging/deb", deb_dir, dirs_exist_ok=True)
    shutil.copy(artifact_tar, deb_dir / artifact_tar.name)

    run(
        [
            "podman",
            "run",
            "--rm",
            "-v",
            f"{deb_dir}:/build:Z",
            "-v",
            f"{OUT_DIR}:/out:Z",
            "simplytoast-deb",
            "./build.sh",
            VERSION,
        ]
    )

    # -------------------------
    # RPM
    # -------------------------
    print("▶ Building RPM...")
    rpm_dir = BUILD_DIR / "rpm"
    shutil.copytree(ROOT / "packaging/rpm", rpm_dir, dirs_exist_ok=True)
    shutil.copy(artifact_tar, rpm_dir / artifact_tar.name)

    run(
        [
            "podman",
            "run",
            "--rm",
            "-v",
            f"{rpm_dir}:/build:Z",
            "-v",
            f"{OUT_DIR}:/out:Z",
            "simplytoast-rpm",
            "./build.sh",
            VERSION,
        ]
    )

    # -------------------------
    # APPIMAGE
    # -------------------------
    print("▶ Building AppImage...")
    appimage_dir = BUILD_DIR / "appimage"
    shutil.copytree(
        ROOT / "packaging/appimage", appimage_dir, dirs_exist_ok=True
    )
    shutil.copy(artifact_tar, appimage_dir / artifact_tar.name)

    run(
        [
            "podman",
            "run",
            "--rm",
            "-v",
            f"{appimage_dir}:/build:Z",
            "-v",
            f"{OUT_DIR}:/out:Z",
            "simplytoast-appimage",
            "./build.sh",
            VERSION,
        ]
    )

    # -------------------------
    # FINAL PUSH
    # -------------------------
    print("▶ Tagging and Pushing...")
    run(["git", "tag", TAG])
    TAG_CREATED = True

    run(["git", "push", "origin", CURRENT_BRANCH])
    run(["git", "push", "origin", TAG])

    print("▶ Creating GitHub release...")
    run(
        [
            "gh",
            "release",
            "create",
            TAG,
            *[str(p) for p in OUT_DIR.iterdir()],
            "--title",
            f"{APP_NAME} {VERSION}",
            "--notes",
            f"Release {VERSION}",
        ]
    )

    print(f"✅ Release {VERSION} completed successfully. Artifacts are in {OUT_DIR}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        cleanup_on_failure(1)
        raise
