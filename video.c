#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <linux/videodev2.h>
#include <sys/mman.h>
#include <string.h>
#include <time.h>

#define VIDEO_DEVICE "/dev/video0"
#define WIDTH 640
#define HEIGHT 480

struct buffer {
    void *start;
    size_t length;
};

// Callback function type for sending frames
typedef void (*frame_callback)(unsigned char *data, size_t length);

int start_video_capture(int duration, int fps, frame_callback callback) {
    int fd = open(VIDEO_DEVICE, O_RDWR);
    if (fd == -1) {
        perror("Cannot open video device");
        return -1;
    }
    printf("Video device opened\n");

    // Set format
    struct v4l2_format fmt = {0};
    fmt.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    fmt.fmt.pix.width = WIDTH;
    fmt.fmt.pix.height = HEIGHT;
    fmt.fmt.pix.pixelformat = V4L2_PIX_FMT_MJPEG;
    fmt.fmt.pix.field = V4L2_FIELD_ANY;
    if (ioctl(fd, VIDIOC_S_FMT, &fmt) == -1) {
        perror("Setting format failed");
        close(fd);
        return -1;
    }
    printf("Format set: %dx%d, MJPEG\n", WIDTH, HEIGHT);

    // Request buffer
    struct v4l2_requestbuffers req = {0};
    req.count = 1;
    req.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    req.memory = V4L2_MEMORY_MMAP;
    if (ioctl(fd, VIDIOC_REQBUFS, &req) == -1) {
        perror("Requesting buffer failed");
        close(fd);
        return -1;
    }
    printf("Buffer requested\n");

    // Map buffer
    struct buffer buf = {0};
    struct v4l2_buffer vbuf = {0};
    vbuf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    vbuf.memory = V4L2_MEMORY_MMAP;
    vbuf.index = 0;
    if (ioctl(fd, VIDIOC_QUERYBUF, &vbuf) == -1) {
        perror("Querying buffer failed");
        close(fd);
        return -1;
    }
    buf.length = vbuf.length;
    buf.start = mmap(NULL, vbuf.length, PROT_READ | PROT_WRITE, MAP_SHARED, fd, vbuf.m.offset);
    if (buf.start == MAP_FAILED) {
        perror("MMAP failed");
        close(fd);
        return -1;
    }
    printf("Buffer mapped: %zu bytes\n", buf.length);

    // Start streaming
    enum v4l2_buf_type type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    if (ioctl(fd, VIDIOC_STREAMON, &type) == -1) {
        perror("Stream on failed");
        munmap(buf.start, buf.length);
        close(fd);
        return -1;
    }
    printf("Streaming started\n");

    time_t start_time = time(NULL);
    int frame_count = 0;
    int frame_interval_us = 1000000 / fps; // Microseconds per frame

    // Capture frames and send via callback
    while (time(NULL) - start_time < duration) {
        vbuf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
        vbuf.memory = V4L2_MEMORY_MMAP;
        if (ioctl(fd, VIDIOC_QBUF, &vbuf) == -1) {
            perror("Queue buffer failed");
            break;
        }
        if (ioctl(fd, VIDIOC_DQBUF, &vbuf) == -1) {
            perror("Dequeue buffer failed");
            break;
        }
        if (vbuf.bytesused > 0) {
            if (callback != NULL) {
                callback((unsigned char *)buf.start, vbuf.bytesused);
                frame_count++;
                printf("Captured frame %d (%zu bytes)\n", frame_count, vbuf.bytesused);
            } else {
                printf("Warning: Callback is NULL\n");
            }
        } else {
            printf("Warning: Empty frame captured\n");
        }
        usleep(frame_interval_us); // Sleep to enforce FPS
    }

    // Stop streaming
    if (ioctl(fd, VIDIOC_STREAMOFF, &type) == -1) {
        perror("Stream off failed");
    }
    printf("Streaming stopped\n");

    // Cleanup
    munmap(buf.start, buf.length);
    close(fd);
    printf("Total frames captured: %d\n", frame_count);
    return 0;
}