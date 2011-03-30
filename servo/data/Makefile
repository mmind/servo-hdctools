INAS=wario servo_loc

# TODO(tbroch) should probably be added to setup.py if possible
all:
	for name in $(INAS); do \
		python ina219.py $$name; \
	done

install:
	echo "Done by ${PWD}/../../setup.py"

clean:
	for name in $(INAS); do \
		rm $$name.xml; \
	done
