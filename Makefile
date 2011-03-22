SUBDIRS=src
all:
	for d in $(SUBDIRS); do \
		make DEBUG=1 -C $$d; \
	done

install:
	for d in $(SUBDIRS); do \
		make -C $$d install; \
	done

clean:
	for d in $(SUBDIRS); do \
		make -C $$d clean; \
	done
