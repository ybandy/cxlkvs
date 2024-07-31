#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <sys/mman.h>
#include <numaif.h>
#include "chain.h"


inline void store(struct item_t *dst, uint64_t val)
{
    dst->val[0] = val & 0xff00000000000000;
    dst->val[1] = val & 0x00ff000000000000;
    dst->val[2] = val & 0x0000ff0000000000;
    dst->val[3] = val & 0x000000ff00000000;
    dst->val[4] = val & 0x00000000ff000000;
    dst->val[5] = val & 0x0000000000ff0000;
    dst->val[6] = val & 0x000000000000ff00;
    dst->val[7] = val & 0x00000000000000ff;
}

inline uint64_t load(struct item_t src)
{
    return src.val[0] | src.val[1] | src.val[2] | src.val[3] | src.val[4] | src.val[5] | src.val[6] | src.val[7];
}


struct item_t *create_pointer_chain(uint64_t size, uint64_t nodemask)
{
    // allocate temporary indices to create a pointer chain
    uint64_t *idx = (uint64_t *)malloc((size - 1) * sizeof(uint64_t));
    if(idx == NULL)
    {
        fprintf(stderr, "could not allocate memory to idx\n");
        exit(1);
    }

    printf("generating indices...\n");
    for(uint64_t i = 0; i < size - 1; i++)
    {
        idx[i] = (i + 1);
    }

    for(uint64_t i = size - 2; i > 0; i--)
    {
        uint64_t r = rand();
        if(i > (uint64_t)RAND_MAX + 1)
        {
            r += rand() * ((uint64_t)RAND_MAX + 1);
        }
        uint64_t j = r % i;
        uint64_t tmp = idx[j];
        idx[j] = idx[i];
        idx[i] = tmp;
    }

    // create a pointer chain using the temporary indices
    const size_t length = size * sizeof(struct item_t);
    struct item_t *chain = mmap(NULL, length, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_NORESERVE, -1, 0);
    if(mbind(chain, length, MPOL_INTERLEAVE, &nodemask, sizeof(nodemask) * 8, 0))
    {
        fprintf(stderr, "can't mbind\n");
        exit(1);
    }

    printf("creating pointer chain...\n");
    store(&chain[0], idx[0]);
    for(uint64_t i = 1; i < size - 1; i++)
    {
        store(&chain[idx[i-1]], idx[i]);
    }
    store(&chain[idx[size-2]], 0);

    free(idx);

#if 0
    // check if the pointer chain (1) forms a loop and (2) exhausts all the elements
    printf("verifying pointer chain...\n");
    uint64_t count = 0;
    uint8_t *used = (uint8_t *)calloc(size, sizeof(uint8_t));
    uint64_t p = 0; // start position
    do
    {
        used[p] = 1;
        uint64_t next = get(chain[p]);
        //printf("%lu -> %lu (offset %ld)\n", p, next, (int64_t)next - (int64_t)p);
        p = next;
        count++;
    }
    while(p != 0 && count < size); // until it returns to the start position

    for(uint64_t i = 0; i < size; i++)
    {
        if(used[i] == 0)
        {
            fprintf(stderr, "pointer chain does not go through %lu\n", i);
            exit(1);
        }
    }
    if(count != size)
    {
        fprintf(stderr, "pointer chain has shortcuts or duplicates\n");
        exit(1);
    }
#endif

    return chain;
}
