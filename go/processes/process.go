package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

const USER_HZ = 100.0

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
// [pid:int, name:str, cpu:float, mem:float, cmd:str]
func scanProcesses() [][]any {
	entries, err := os.ReadDir("/proc")
	if err != nil {
		return nil
	}

	totalMemKB := readTotalMemoryKB()
	uptime := readUptimeSeconds()

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

		procTime, startTime := readProcessTimes(e.Name())
		cpu := computeCPU(procTime, startTime, uptime)
		mem := readProcessMemPercent(e.Name(), totalMemKB)

		out = append(out, []any{
			pid,
			exe,
			cpu,
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

// /proc/uptime → seconds
func readUptimeSeconds() float64 {
	data, err := os.ReadFile("/proc/uptime")
	if err != nil {
		return 0
	}
	fields := strings.Fields(string(data))
	if len(fields) > 0 {
		if v, err := strconv.ParseFloat(fields[0], 64); err == nil {
			return v
		}
	}
	return 0
}

// utime + stime, starttime (in jiffies)
func readProcessTimes(pid string) (float64, float64) {
	stat, err := os.ReadFile(filepath.Join("/proc", pid, "stat"))
	if err != nil {
		return 0, 0
	}

	fields := strings.Fields(string(stat))
	if len(fields) < 22 {
		return 0, 0
	}

	utime, _ := strconv.ParseFloat(fields[13], 64)
	stime, _ := strconv.ParseFloat(fields[14], 64)
	starttime, _ := strconv.ParseFloat(fields[21], 64)

	return utime + stime, starttime
}

// Stateless CPU %
func computeCPU(procTime, startTime, uptime float64) float64 {
	if uptime <= 0 || startTime <= 0 {
		return 0
	}

	// process lifetime in seconds
	elapsed := uptime - (startTime / USER_HZ)
	if elapsed <= 0 {
		return 0
	}

	// total CPU time in seconds
	cpuSeconds := procTime / USER_HZ

	return (cpuSeconds / elapsed) * 100.0
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
