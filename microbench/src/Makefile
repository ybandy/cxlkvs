CC = gcc

CFLAGS = -Wall -O3 -D_GNU_SOURCE
CFLAGS += -I../liburing/src/include/
CFLAGS += -I../argobots/src/include/
CFLAGS += -DSET_LATENCY_PATH=\"$(HOME)/set_latency.sh\"

LDLIBS = -lpthread -luring -labt -lnuma
LDLIBS += -L../liburing/src/
LDLIBS += -L../argobots/src/.libs/

.PHONY: all clean

all: main

main: main.o chain.o

clean:
	$(RM) main *.o
