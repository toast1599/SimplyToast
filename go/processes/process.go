package main

/*
#include <stdlib.h>

typedef struct {
    int pid;
    double cpu;
    double mem;
    char* name;
    char* cmd;
} ProcessRow;
*/
import "C"

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"unsafe"
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

// ------------------------------------------------------------
// FFI EXPORTS
// ------------------------------------------------------------

//export ScanProcesses
func ScanProcesses(count *C.int) *C.ProcessRow {
	rows := scanProcesses()
	n := len(rows)

	*count = C.int(n)
	if n == 0 {
		return nil
	}

	mem := C.malloc(C.size_t(n) * C.size_t(C.sizeof_ProcessRow))
	if mem == nil {
		*count = 0
		return nil
	}

	arr := (*[1 << 30]C.ProcessRow)(mem)

	for i, r := range rows {
		arr[i] = C.ProcessRow{
			pid:  C.int(r[0].(int)),
			name: C.CString(r[1].(string)),
			cpu:  C.double(r[2].(float64)),
			mem:  C.double(r[3].(float64)),
			cmd:  C.CString(r[4].(string)),
		}
	}

	return (*C.ProcessRow)(mem)
}

//export FreeProcesses
func FreeProcesses(rows *C.ProcessRow, count C.int) {
	if rows == nil || count <= 0 {
		return
	}

	arr := (*[1 << 30]C.ProcessRow)(unsafe.Pointer(rows))

	for i := 0; i < int(count); i++ {
		C.free(unsafe.Pointer(arr[i].name))
		C.free(unsafe.Pointer(arr[i].cmd))
	}

	C.free(unsafe.Pointer(rows))
}

// ------------------------------------------------------------
// CORE LOGIC (UNCHANGED)
// ------------------------------------------------------------

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
			procTime,
			mem,
			cmd,
		})
	}

	return out
}

// ------------------------------------------------------------
// HELPERS
// ------------------------------------------------------------

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
