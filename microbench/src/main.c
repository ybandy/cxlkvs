#include <stdio.h>
#include <fcntl.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <stdint.h>
#include <time.h>
#include <pthread.h>
#include <sys/mman.h>
#include <numaif.h>
#include "liburing.h"
#include "abt.h"
#include "chain.h"


struct my_param
{
    char filename[512];
    off_t file_size;
    uint64_t chain_size;
    size_t access_size;
    int count;
    int num_threads;
    int num_xstreams;
    int num_chases;
    int memory_time;
    int io_time_pre;
    int io_time_post;
    int prefetch;
    int io_mode;
    struct item_t *chain;
    long *op_latencies;
    int *num_peeks;
};


static inline long get_nsec()
{
	struct timespec ts;
	clock_gettime(CLOCK_MONOTONIC, &ts);
	return (ts.tv_sec * 1000000000L) + ts.tv_nsec;
}

static inline void report_time(long start, int count)
{
    double diff = (get_nsec() - start) * 1e-9;
	printf("elapsed time = %f sec, throughput %.1f kops/sec\n", diff, count * 1e-3 / diff);
}

static inline uint64_t init_pointer(uint64_t chain_size)
{
    return (((uint64_t)rand() << 31) | rand()) % chain_size;
}

static inline uint64_t chase_pointers(int num_chases, int memory_time, int prefetch,
                                      uint64_t chain_size, struct item_t *chain)
{
    uint64_t p = init_pointer(chain_size);
    for(int i = 0; i < num_chases; i++)
    {
        for(int j = 0; j < memory_time; j++)
        {
            asm volatile("pause" : : : "memory");
        }

        if(prefetch)
        {
            __builtin_prefetch(chain + p);
            ABT_thread_yield();
        }

        p = load(chain[p]);
    }
    return p;
}

static inline void timed_spin_loop(int time_nsec)
{
    if(time_nsec > 0)
    {
        const long end = get_nsec() + time_nsec;
        while(get_nsec() < end)
        {
            asm volatile("pause" : : : "memory");
        }
    }
}


static void run_each_thread(void *param)
{
    struct my_param *t_param = (struct my_param *)param;
    char *filename = t_param->filename;
    const off_t file_size = t_param->file_size;
    const uint64_t chain_size = t_param->chain_size;
    const size_t access_size = t_param->access_size;
    const int count = t_param->count;
    const int num_chases = t_param->num_chases;
    const int memory_time = t_param->memory_time;
    const int io_time_pre = t_param->io_time_pre;
    const int io_time_post = t_param->io_time_post;
    const int prefetch = t_param->prefetch;
    const int io_mode = t_param->io_mode;
    struct item_t *chain = t_param->chain;
    long *op_latencies = t_param->op_latencies;
    int *num_peeks = t_param->num_peeks;

    struct io_uring ring;
    struct io_uring_sqe *sqe;
    struct io_uring_cqe *cqe;
    const int qd = 1;

    int fd = 0;
    void *buf = NULL;
    if(io_mode > 0)
    {
        if(io_uring_queue_init(qd, &ring, IORING_SETUP_IOPOLL) < 0)
        {
            fprintf(stderr, "failed to initialize io_uring\n");
            exit(1);
        }

        if(io_mode == 1)
        {
            fd = open(filename, O_RDONLY | O_DIRECT);
        }
        else
        {
            fd = open(filename, O_WRONLY | O_DIRECT);
        }
        if(fd < 0)
        {
            fprintf(stderr, "failed to open file: %s\n", filename);
            exit(1);
        }

        if(posix_memalign(&buf, access_size, access_size))
        {
            fprintf(stderr, "failed to allocate memory\n");
            exit(1);
        }
        for(int i = 0; i < access_size / sizeof(int); i++)
        {
            ((int *)buf)[i] = i;
        }
    }

    *num_peeks = 0;
    for(int i = 0; i < count; i++)
    {
        long op_start = get_nsec();

        int fluctuation = (num_chases > 0) ? (rand() % 3) - 1 : 0;
        uint64_t p = chase_pointers(num_chases + fluctuation, memory_time, prefetch,
                                    chain_size, chain);
        if(io_mode > 0)
        {
            timed_spin_loop(io_time_pre);

            off_t addr = (p % (file_size / access_size)) * access_size;
            sqe = io_uring_get_sqe(&ring);
            if(io_mode == 1)
            {
                io_uring_prep_read(sqe, fd, buf, access_size, addr);
            }
            else
            {
                io_uring_prep_write(sqe, fd, buf, access_size, addr);
            }

            if(io_uring_submit(&ring) < 0)
            {
                fprintf(stderr, "failed to submit to io_uring\n");
                exit(1);
            }

            ABT_thread_yield();

            while(io_uring_peek_cqe(&ring, &cqe) == -EAGAIN)
            {
                (*num_peeks)++;
                ABT_thread_yield();
            }
            (*num_peeks)++;

            if(io_mode == 1)
            {
                if(cqe->res != access_size)
                {
                    fprintf(stderr, "couldn't read %ld bytes: %d bytes read\n", access_size, cqe->res);
                    exit(1);
                }
            }
            else
            {
                if(cqe->res < 0)
                {
                    fprintf(stderr, "couldn't write %ld bytes\n", access_size);
                    exit(1);
                }
            }
            io_uring_cqe_seen(&ring, cqe);
        }

        timed_spin_loop(io_time_post);

        long op_end = get_nsec();
        op_latencies[i] = op_end - op_start;
    }

    close(fd);
    free(buf);
    io_uring_queue_exit(&ring);
}

static void run_threads(struct my_param *param)
{
    const int num_xstreams = param->num_xstreams;

    if(ABT_init(0, NULL) != ABT_SUCCESS)
    {
        fprintf(stderr, "Argobots: failed to init\n");
        exit(1);
    }

    ABT_xstream *xstreams = (ABT_xstream *)malloc(num_xstreams * sizeof(ABT_xstream));

    ABT_xstream_self(&xstreams[0]);
    for(int i = 1; i < num_xstreams; i++)
    {
        ABT_xstream_create(ABT_SCHED_NULL, &xstreams[i]);
    }

    const int num_threads = param->num_threads;
    ABT_thread *tid = (ABT_thread *)malloc(num_threads * sizeof(ABT_thread));
    struct my_param *t_params = (struct my_param *)malloc(num_threads * sizeof(struct my_param));
    uint64_t count = param->count;
    uint64_t curr_pos = 0;
    int total = 0;
    for(int i = 0; i < num_threads; i++)
    {
        memcpy(&t_params[i], param, sizeof(struct my_param));
        uint64_t next_pos = count * (i + 1) / num_threads;
        t_params[i].count = (int)(next_pos - curr_pos);
        total += t_params[i].count;
        t_params[i].op_latencies = &(param->op_latencies[curr_pos]);
        t_params[i].num_peeks = &(param->num_peeks[i]);
        curr_pos = next_pos;
    }
    printf("total %d ops\n", total);

    const long start = get_nsec();
    for(int i = 0; i < num_threads; i++)
    {
        ABT_thread_create_on_xstream(xstreams[i % num_xstreams],
                                     run_each_thread,
                                     (void *)(&t_params[i]),
                                     ABT_THREAD_ATTR_NULL,
                                     &tid[i]);
    }
    ABT_thread_join_many(num_threads, tid);
    report_time(start, count);

    ABT_thread_free_many(num_threads, tid);
    for(int i = 0; i < num_xstreams; i++)
    {
        ABT_xstream_join(xstreams[i]);
        ABT_xstream_free(&xstreams[i]);
    }
    ABT_finalize();

    free(tid);
    free(t_params);
    free(xstreams);
}

static void set_latency(int latency)
{
    static int prev_latency = -1;
    if(prev_latency == latency)
    {
        return;
    }
    else
    {
        prev_latency = latency;
    }

    char cmd[1024];
    snprintf(cmd, sizeof(cmd), "bash %s %d", SET_LATENCY_PATH, latency);
    printf("%s\n", cmd);

    FILE *p;
    char buf[1024];
    int ret = 1;
    if((p = popen(cmd, "r")) != NULL)
    {
        while(fgets(buf, 1024, p) != NULL) printf("%s", buf);
        ret = pclose(p);
    }
    if(ret)
    {
        fprintf(stderr, "failed to execute '%s'\n", cmd);
        exit(1);
    }
    sleep(1);
}

static int compare(const void *a, const void *b)
{
    return ( *(long *)a - *(long *)b );
}

static void run_mbench(uint64_t chain_size, struct item_t *chain,
                       char *filename, off_t file_size, size_t access_size,
                       int count, int num_threads, int num_xstreams, int latency,
                       int num_chases, int memory_time, int io_time_pre, int io_time_post,
                       int io_mode, int prefetch, int use_cxl)
{
    if(use_cxl)
    {
        set_latency(latency);
    }

    long *op_latencies = (long *)malloc(count * sizeof(long));
    int *num_peeks = (int *)malloc(num_threads * sizeof(int));

    struct my_param param;
    strcpy(param.filename, filename);
    param.file_size = file_size;
    param.chain_size = chain_size;
    param.access_size = access_size;
    param.count = count;
    param.num_threads = num_threads;
    param.num_xstreams = num_xstreams;
    param.num_chases = num_chases;
    param.memory_time = memory_time;
    param.io_time_pre = io_time_pre;
    param.io_time_post = io_time_post;
    param.prefetch = prefetch;
    param.io_mode = io_mode;
    param.chain = chain;
    param.op_latencies = op_latencies;
    param.num_peeks = num_peeks;

    run_threads(&param);

    qsort(op_latencies, count, sizeof(long), compare);
    printf("op latency = %f, %f, %f, %f, %f, %f usec\n",
           1e-3 * op_latencies[(int)(count * 0.5)],
           1e-3 * op_latencies[(int)(count * 0.9)],
           1e-3 * op_latencies[(int)(count * 0.99)],
           1e-3 * op_latencies[(int)(count * 0.999)],
           1e-3 * op_latencies[(int)(count * 0.9999)],
           1e-3 * op_latencies[(int)(count * 0.99999)]);
    long sum = 0;
    for(int i = 0; i < count; i++) sum += op_latencies[i];
    printf("average op latency = %f usec\n", 1e-3 * (double)sum / (double)count);
    free(op_latencies);

    sum = 0;
    for(int i = 0; i < num_threads; i++) sum += num_peeks[i];
    printf("average num peeks per IO = %.1f\n", (double)sum / (double)count);
    free(num_peeks);
}

int main(int argc, char *argv[])
{
    char *filename = NULL;
    char *param_file = NULL;
    uint64_t chain_size = 0;
    size_t access_size = 0;
    int count = 0;
    int num_threads = 0;
    int num_xstreams = 0;
    int latency = 0;
    int num_chases = 0;
    int memory_time = 0;
    int io_time_pre = 0;
    int io_time_post = 0;
    int io_mode = 0;
    int prefetch = 0;
    int use_cxl = 0;

    if(argc == 14)
    {
        filename = argv[1];
        chain_size = (uint64_t)atol(argv[2]);
        access_size = (size_t)atoi(argv[3]);
        count = atoi(argv[4]);
        num_threads = atoi(argv[5]);
        num_xstreams = atoi(argv[6]);
        latency = atoi(argv[7]);
        num_chases = atoi(argv[8]);
        memory_time = atoi(argv[9]);
        io_time_pre = atoi(argv[10]);
        io_time_post = atoi(argv[11]);
        io_mode = atoi(argv[12]);
        prefetch = atoi(argv[13]);
        if(latency > 0)
        {
            use_cxl = 1;
        }
    }
    else if(argc == 6)
    {
        filename = argv[1];
        chain_size = (uint64_t)atol(argv[2]);
        access_size = (size_t)atoi(argv[3]);
        use_cxl = atoi(argv[4]);
        param_file = argv[5];
    }
    else
    {
        printf("%s filename chain_size access_size count num_threads num_xstreams latency num_chases memory_time io_time_pre io_time_post io_mode prefetch\n", argv[0]);
        printf("    OR\n");
        printf("%s filename chain_size access_size use_cxl param_file\n", argv[0]);
        printf("\n");
        printf("    io_mode 0: no IO\n");
        printf("    io_mode 1: read IO\n");
        printf("    io_mode 2: write IO\n");
        return 0;
    }

    srand(time(NULL));

    uint64_t nodemask = 1 << 0;

    if(use_cxl)
    {
        nodemask = (1 << 2) | (1 << 3);
        set_latency(0);
    }
    struct item_t *chain = create_pointer_chain(chain_size, nodemask);
    
    int fd = open(argv[1], O_RDONLY | O_DIRECT);
    if(fd < 0)
    {
        fprintf(stderr, "failed to open file: %s\n", filename);
        exit(1);
    }
    const off_t file_size = lseek(fd, 0, SEEK_END);
    printf("file size: %ld\n", file_size);
    close(fd);

    if(param_file == NULL)
    {
        run_mbench(chain_size, chain,
                   filename, file_size, access_size,
                   count, num_threads, num_xstreams, latency,
                   num_chases, memory_time, io_time_pre, io_time_post,
                   io_mode, prefetch, use_cxl);
    }
    else
    {
        FILE *fp;
        if((fp = fopen(param_file, "rt")) == NULL)
        {
            fprintf(stderr, "failed to open file: %s\n", param_file);
            exit(1);
        }
        char buf[1024];
        while(fgets(buf, 1024, fp) != NULL)
        {
            if(sscanf(buf, "%d %d %d %d %d %d %d %d %d %d",
                      &count, &num_threads, &num_xstreams, &latency,
                      &num_chases, &memory_time, &io_time_pre, &io_time_post,
                      &io_mode, &prefetch) == 10)
            {
                printf("param %d %d %d %d %d %d %d %d %d %d\n",
                       count, num_threads, num_xstreams, latency,
                       num_chases, memory_time, io_time_pre, io_time_post,
                       io_mode, prefetch);
                run_mbench(chain_size, chain,
                           filename, file_size, access_size,
                           count, num_threads, num_xstreams, latency,
                           num_chases, memory_time, io_time_pre, io_time_post,
                           io_mode, prefetch, use_cxl);
            }
        }
        fclose(fp);
    }

    if(use_cxl)
    {
        set_latency(0); // munmap can be slow with long latency
    }
    munmap(chain, chain_size * sizeof(struct item_t));
    return 0;
}
