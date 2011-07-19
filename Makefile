SUBDIRS=src servo/data
all:
	for d in $(SUBDIRS); do \
		make -C $$d; \
	done

install:
	for d in $(SUBDIRS); do \
		make -C $$d install; \
	done

clean:
	for d in $(SUBDIRS); do \
		make -C $$d clean; \
	done
