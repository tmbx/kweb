#
# Misc tools for web interfaces
#

# Prefix for installing lib... so we can use the same makefile for local installation and debian package creation
ifndef DESTDIR
	# default: install in system root
	DESTDIR=
endif

# Are we building a debian package?
ifndef DEBIAN
	DEBIAN=0
endif

PYTHON_MODULES=kweb_lib.py kweb_mp.py kweb_session.py kweb_menu.py kweb_forms.py kweb_getstrings.py

all:
	:

clean:
	rm -f python/*.pyc

install:
	# Install files
	mkdir -p $(DESTDIR)/usr/sbin/
	mkdir -p $(DESTDIR)/usr/share/teambox/kweb/
	install -m 755 -o root -g root scripts/apache2_build_conf.sh $(DESTDIR)/usr/sbin/apache2_build_conf
	install -m 755 -o root -g root scripts/apache2_ports.sh $(DESTDIR)/usr/sbin/apache2_ports
	install -m 755 -o root -g root scripts/lighttpd_change_listened_port.sh $(DESTDIR)/usr/sbin/lighttpd_change_listened_port

	# Install Python modules
	mkdir -p $(DESTDIR)/usr/share/python-support/kweb/
	for i in $(PYTHON_MODULES); do \
	    install -m644 python/$$i $(DESTDIR)/usr/share/python-support/kweb/;\
	done

	# Update python modules if we're not building a debian package
	if [ "$(DEBIAN)" != "1" ]; then update-python-modules kweb; fi

setup_py:
	# Create a setup.py file using setup.py.tmpl file and set the version to the head HG rev.
	cat setup.py.tmpl | sed "s/__VERSION__/`hg head | head -1 | sed 's#changeset: *\([0-9]*\):.*#\1#g'`/g" > setup.py

egg: setup_py
	# Build the egg
	python setup.py bdist_egg

