#!/bin/bash

apt-get update -y
apt-get install -y default-jdk

TOMCAT_VERSION=9.0.96
TOMCAT_DIR=/opt/tomcat
TOMCAT_SERVICE=/etc/systemd/system/tomcat.service

wget  https://dlcdn.apache.org/tomcat/tomcat-9/v${TOMCAT_VERSION}/bin/apache-tomcat-${TOMCAT_VERSION}.tar.gz
mkdir -p $TOMCAT_DIR
tar xzf apache-tomcat-${TOMCAT_VERSION}.tar.gz -C $TOMCAT_DIR --strip-components=1
groupadd tomcat
useradd -s /bin/false -g tomcat -d /opt/tomcat tomcat
chown -R tomcat: /opt/tomcat
rm -f apache-tomcat-${TOMCAT_VERSION}.tar.gz

chmod +x $TOMCAT_DIR/bin/*.sh

TOMCAT_SERVER_FILE="/opt/tomcat/conf/server.xml"
sudo sed -i 's/port="8080"/port="80"/' $TOMCAT_SERVER_FILE

${TOMCAT_DIR}/bin/catalina.sh start
