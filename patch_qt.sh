#/bin/bash

# TODO: Qt's installer also patches the paths in several other places - should we also do that?

printf "[Paths]\nPrefix=..\n" > bin/qt.conf

sed -i.bak 's/QT_EDITION = .*/QT_EDITION = OpenSource/' mkspecs/qconfig.pri
sed -i.bak 's/QT_LICHECK = licheck_mac/QT_LICHECK =/' mkspecs/qconfig.pri
rm mkspecs/qconfig.pri.bak
