#!/usr/bin/env sh

cd /home/spinitalia/alma3d

sudo rm -rf /opt/spinitalia/alma3d

# Pulisco la directory
rm -f *~
rm -f alma3d/*~
rm -f *.pyc
rm -f alma3d/*.pyc

# Rendo eseguibile il server CAN
chmod 755 alma3d_canopenshell
chmod 644 config.ini

if [ ! -e /opt/spinitalia/service ]
then
    mkdir /opt/spinitalia/service
fi

# Compilo il software
python -c "import alma3d_service"
cp alma3d_service.pyc /opt/spinitalia/service
cp config.ini /opt/spinitalia/service
cp alma3d_canopenshell /opt/spinitalia/service/

cd /home/spinitalia/alma3d/alma3d
if [ ! -e /opt/spinitalia/service/alma3d ]
then
    mkdir /opt/spinitalia/service/alma3d
fi

python -c "import __init__"
python -c "import Alarm"
python -c "import Canopen"
python -c "import ControlFactory"
python -c "import ControlProtocol"
python -c "import DiscoveryProtocol"
python -c "import Kinematic"
python -c "import PositionFactory"
python -c "import PositionProtocol"
python -c "import Tripod"
cp __init__.pyc /opt/spinitalia/service/alma3d/
cp Alarm.pyc /opt/spinitalia/service/alma3d/
cp Canopen.pyc /opt/spinitalia/service/alma3d/
cp ControlFactory.pyc /opt/spinitalia/service/alma3d/
cp ControlProtocol.pyc /opt/spinitalia/service/alma3d/
cp DiscoveryProtocol.pyc /opt/spinitalia/service/alma3d/
cp Kinematic.pyc /opt/spinitalia/service/alma3d/
cp kinematic_cy.so /opt/spinitalia/service/alma3d/
cp PositionFactory.pyc /opt/spinitalia/service/alma3d/
cp PositionProtocol.pyc /opt/spinitalia/service/alma3d/
cp Tripod.pyc /opt/spinitalia/service/alma3d/
