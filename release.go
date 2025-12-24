package main

import (
	"bytes"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
)

const (
	AppName   = "SimplyToast"
	TagPrefix = "v"
)

var (
	tagCreated bool
	tag        string
	buildDir   string
	outDir     string
	rootDir    string
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

func cleanup() {
	if !tagCreated {
		return
	}

	fmt.Println("⚠️ Cleaning up after failure...")

	_ = os.RemoveAll(buildDir)
	_ = os.RemoveAll(outDir)

	exec.Command("git", "reset", "--hard", "HEAD").Run()

	if tag != "" {
		exec.Command("git", "tag", "-d", tag).Run()
	}

	fmt.Println("🧹 Environment restored.")
}

func main() {
	defer func() {
		if r := recover(); r != nil {
			cleanup()
			panic(r)
		}
	}()

	if len(os.Args) < 2 {
		log.Fatal("❌ Usage: release <version>")
	}

	version := os.Args[1]
	versionRe := regexp.MustCompile(`^[0-9]+(\.[0-9]+)+$`)
	if !versionRe.MatchString(version) {
		log.Fatal("❌ Invalid version format")
	}

	tag = TagPrefix + version

	var err error
	rootDir, err = os.Getwd()
	if err != nil {
		log.Fatal(err)
	}

	buildDir = filepath.Join(rootDir, "build")
	outDir = filepath.Join(rootDir, "out")

	// Git cleanliness check
	status := exec.Command("git", "status", "--porcelain")
	out, _ := status.Output()
	if len(bytes.TrimSpace(out)) != 0 {
		log.Fatal("❌ Git tree is dirty")
	}

	// Version bump
	fmt.Println("▶ Updating version.py")
	versionFile := filepath.Join(rootDir, "src", "version.py")
	if err := os.WriteFile(versionFile, []byte(fmt.Sprintf(`VERSION = "%s"`+"\n", version)), 0644); err != nil {
		log.Fatal(err)
	}

	run("git", "add", "src/version.py")

	diff := exec.Command("git", "diff", "--cached", "--quiet")
	if err := diff.Run(); err != nil {
		run("git", "commit", "-m", fmt.Sprintf("Bump version to %s", version))
	}

	// Prepare dirs
	run("mkdir", "-p", buildDir, outDir)

	artifactDir := filepath.Join(buildDir, "artifact")
	run("mkdir", "-p", artifactDir)

	fmt.Println("▶ Packing Source...")
	run("rsync", "-a", "--exclude=__pycache__", "--exclude=*.pyc", "--exclude=*.AppImage", "src/", filepath.Join(artifactDir, "src"))
	run("rsync", "-a", "data/", filepath.Join(artifactDir, "data"))
	run("tar", "-czf", filepath.Join(buildDir, "artifact.tar.gz"), "-C", artifactDir, ".")

	// ARCH
	fmt.Println("▶ Building Arch...")
	archDir := filepath.Join(buildDir, "arch")
	run("mkdir", "-p", archDir)
	run("cp", "packaging/arch/PKGBUILD", archDir)
	run("cp", filepath.Join(buildDir, "artifact.tar.gz"), archDir)

	run("sed", "-i", fmt.Sprintf("s/^pkgver=.*/pkgver=%s/", version), filepath.Join(archDir, "PKGBUILD"))
	runInDir(archDir, "makepkg", "-sf", "--noconfirm")
	run("mv", filepath.Join(archDir, "*.pkg.tar.zst"), outDir)

	// DEB / RPM / AppImage
	type containerBuild struct {
		name string
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
		run("cp", "-r", filepath.Join("packaging", b.name)+"/.", dir)
		run("cp", filepath.Join(buildDir, "artifact.tar.gz"), dir)
		run("podman", "run", "--rm",
			"-v", fmt.Sprintf("%s:/build:Z", dir),
			"-v", fmt.Sprintf("%s:/out:Z", outDir),
			b.image, "./build.sh", version,
		)
	}

	// Tag + push
	fmt.Println("▶ Tagging and pushing...")
	run("git", "tag", tag)
	tagCreated = true
	run("git", "push", "origin", "HEAD")
	run("git", "push", "origin", tag)

	// GitHub release
	fmt.Println("▶ Creating GitHub release...")
	run("gh", "release", "create", tag, filepath.Join(outDir, "*"),
		"--title", fmt.Sprintf("%s %s", AppName, version),
		"--notes", fmt.Sprintf("Release %s", version),
	)

	fmt.Printf("✅ Release %s completed successfully\n", version)
}
