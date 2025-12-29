package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

func main() {
	if len(os.Args) < 2 || os.Args[1] != "scan" {
		fmt.Fprintln(os.Stderr, "usage: simplytoast-processes scan")
		os.Exit(1)
	}

	rows := scanProcesses()

	enc := json.NewEncoder(os.Stdout)
	enc.SetEscapeHTML(false)
	_ = enc.Encode(rows)
}

// scanProcesses returns:
// [pid:int, name:str, procTime:float, mem:float, cmd:str]
func scanProcesses() [][]any {
	entries, err := os.ReadDir("/proc")
	if err != nil {
		return nil
	}

	totalMemKB := readTotalMemoryKB()

	out := make([][]any, 0, 256)

	for _, e := range entries {
		if !e.IsDir() {
			continue
		}

		pid, err := strconv.Atoi(e.Name())
		if err != nil {
			continue
		}

		cmdlineBytes, err := os.ReadFile(filepath.Join("/proc", e.Name(), "cmdline"))
		if err != nil || len(cmdlineBytes) == 0 {
			continue
		}

		cmd := strings.ReplaceAll(string(cmdlineBytes), "\x00", " ")
		fields := strings.Fields(cmd)
		if len(fields) == 0 {
			continue
		}

		// Skip kernel threads
		if strings.HasPrefix(cmd, "[") && strings.HasSuffix(cmd, "]") {
			continue
		}

		exe := filepath.Base(fields[0])

		procTime := readProcessTime(e.Name())
		mem := readProcessMemPercent(e.Name(), totalMemKB)

		out = append(out, []any{
			pid,
			exe,
			procTime, // utime + stime (jiffies)
			mem,
			cmd,
		})
	}

	return out
}

// ---------------- helpers ----------------

// /proc/meminfo → MemTotal (kB)
func readTotalMemoryKB() float64 {
	data, err := os.ReadFile("/proc/meminfo")
	if err != nil {
		return 0
	}

	for _, line := range strings.Split(string(data), "\n") {
		if strings.HasPrefix(line, "MemTotal:") {
			fields := strings.Fields(line)
			if len(fields) >= 2 {
				if v, err := strconv.ParseFloat(fields[1], 64); err == nil {
					return v
				}
			}
		}
	}
	return 0
}

// utime + stime (in jiffies)
func readProcessTime(pid string) float64 {
	stat, err := os.ReadFile(filepath.Join("/proc", pid, "stat"))
	if err != nil {
		return 0
	}

	fields := strings.Fields(string(stat))
	if len(fields) < 15 {
		return 0
	}

	utime, _ := strconv.ParseFloat(fields[13], 64)
	stime, _ := strconv.ParseFloat(fields[14], 64)

	return utime + stime
}

// VmRSS / MemTotal
func readProcessMemPercent(pid string, totalMemKB float64) float64 {
	status, err := os.ReadFile(filepath.Join("/proc", pid, "status"))
	if err != nil {
		return 0
	}

	for _, line := range strings.Split(string(status), "\n") {
		if strings.HasPrefix(line, "VmRSS:") {
			fields := strings.Fields(line)
			if len(fields) >= 2 {
				if rss, err := strconv.ParseFloat(fields[1], 64); err == nil && totalMemKB > 0 {
					return (rss / totalMemKB) * 100.0
				}
			}
		}
	}
	return 0
}
