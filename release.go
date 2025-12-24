package main

import (
	"bytes"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"time"
)

const (
	AppName   = "SimplyToast"
	TagPrefix = "v"
)

var (
	tag        string
	rootDir   string
	buildDir  string
	outDir    string
)

func run(name string, args ...string) {
	cmd := exec.Command(name, args...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		log.Fatalf("❌ command failed: %s %v", name, args)
	}
}

func runInDir(dir, name string, args ...string) {
	cmd := exec.Command(name, args...)
	cmd.Dir = dir
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		log.Fatalf("❌ command failed in %s: %s %v", dir, name, args)
	}
}

func main() {
	if len(os.Args) < 2 {
		log.Fatal("❌ Usage: release <version>")
	}

	version := os.Args[1]
	if !regexp.MustCompile(`^[0-9]+(\.[0-9]+)+$`).MatchString(version) {
		log.Fatal("❌ Invalid version format")
	}

	tag = TagPrefix + version

	exe, err := os.Executable()
	if err != nil {
		log.Fatal(err)
	}
	rootDir = filepath.Dir(exe)

	buildDir = filepath.Join(rootDir, "build")
	outDir = filepath.Join(rootDir, "out")

	// Git clean check
	status := exec.Command("git", "status", "--porcelain")
	out, _ := status.Output()
	if len(bytes.TrimSpace(out)) != 0 {
		log.Fatal("❌ Git tree is dirty")
	}

	// Version bump
	fmt.Println("▶ Updating version.py")
	versionFile := filepath.Join(rootDir, "src", "version.py")
	if err := os.WriteFile(versionFile,
		[]byte(fmt.Sprintf("VERSION = \"%s\"\n", version)),
		0644); err != nil {
		log.Fatal(err)
	}

	run("git", "add", "src/version.py")
	run("git", "commit", "-m", fmt.Sprintf("Bump version to %s", version))

	// Tag + push FIRST (AUR REQUIRES THIS)
	fmt.Println("▶ Tagging and pushing...")
	run("git", "tag", tag)
	run("git", "push", "origin", "HEAD")
	run("git", "push", "origin", tag)

	// Give GitHub time to generate tarball
	fmt.Println("⏳ Waiting for GitHub tarball...")
	time.Sleep(10 * time.Second)

	// Arch build (AUR-compliant)
	fmt.Println("▶ Building Arch...")
	archDir := filepath.Join(buildDir, "arch")
	run("mkdir", "-p", archDir)
	run("cp", filepath.Join(rootDir, "packaging/arch/PKGBUILD"), archDir)

	runInDir(archDir, "makepkg", "-sf", "--noconfirm")

	matches, err := filepath.Glob(filepath.Join(archDir, "*.pkg.tar.zst"))
	if err != nil || len(matches) == 0 {
		log.Fatal("❌ No Arch package produced")
	}
	run("mkdir", "-p", outDir)
	for _, m := range matches {
		run("mv", m, outDir)
	}

	// Other builds (unchanged)
	type containerBuild struct {
		name  string
		image string
	}

	builds := []containerBuild{
		{"deb", "simplytoast-deb"},
		{"rpm", "simplytoast-rpm"},
		{"appimage", "simplytoast-appimage"},
	}

	for _, b := range builds {
		fmt.Printf("▶ Building %s...\n", b.name)
		dir := filepath.Join(buildDir, b.name)
		run("mkdir", "-p", dir)
		run("cp", "-r", filepath.Join(rootDir, "packaging", b.name)+"/.", dir)
		run("podman", "run", "--rm",
			"-v", fmt.Sprintf("%s:/build:Z", dir),
			"-v", fmt.Sprintf("%s:/out:Z", outDir),
			b.image, "./build.sh", version,
		)
	}

	// GitHub release
	fmt.Println("▶ Creating GitHub release...")
	run("gh", "release", "create", tag, filepath.Join(outDir, "*"),
		"--title", fmt.Sprintf("%s %s", AppName, version),
		"--notes", fmt.Sprintf("Release %s", version),
	)

	fmt.Printf("✅ Release %s completed successfully\n", version)
}
