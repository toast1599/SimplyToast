#include <signal.h>
#include <stdlib.h>
#include <errno.h>
#include <unistd.h>

int main(int argc, char **argv) {
    if (argc != 2)
        return 1;

    pid_t pid = (pid_t)atoi(argv[1]);
    if (pid <= 0)
        return 1;

    if (kill(pid, SIGTERM) == 0)
        return 0;

    return 1;
}
