#ifndef __CHAIN_H__
#define __CHAIN_H__


struct item_t
{
    uint64_t val[8];
};


void store(struct item_t *dst, uint64_t val);
uint64_t load(struct item_t src);
struct item_t *create_pointer_chain(uint64_t size, uint64_t nodemask);


#endif
