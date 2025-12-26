#define _GNU_SOURCE
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>
#include <libgen.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <limits.h>

static int mkdir_p(const char *path, mode_t mode) {
    char *tmp = strdup(path);
    if (!tmp) return -1;

    for (char *p = tmp + 1; *p; p++) {
        if (*p == '/') {
            *p = '\0';
            mkdir(tmp, mode);
            *p = '/';
        }
    }

    int rc = mkdir(tmp, mode);
    if (rc < 0 && errno == EEXIST)
        rc = 0;

    free(tmp);
    return rc;
}

#include <unistd.h>

int atomic_write(const char *path, const char *data, size_t len) {
    int fd = -1;
    char *path_copy1 = NULL;
    char *path_copy2 = NULL;
    char tmp_path[PATH_MAX];

    path_copy1 = strdup(path);
    path_copy2 = strdup(path);
    if (!path_copy1 || !path_copy2)
        goto fail;

    char *dir = dirname(path_copy1);
    char *base = basename(path_copy2);

    if (mkdir_p(dir, 0755) < 0)
        goto fail;

    snprintf(tmp_path, sizeof(tmp_path), "%s/.%s.tmpXXXXXX", dir, base);

    fd = mkstemp(tmp_path);
    if (fd < 0)
        goto fail;

    if (write(fd, data, len) != (ssize_t)len)
        goto fail;

    if (fsync(fd) < 0)
        goto fail;

    if (close(fd) < 0)
        goto fail;
    fd = -1;

    if (rename(tmp_path, path) < 0)
        goto fail;

    return 0;

fail:
    if (fd >= 0)
        close(fd);
    if (tmp_path[0])
        unlink(tmp_path);
    free(path_copy1);
    free(path_copy2);
    return -1;
}
