#!/bin/bash

apt-get update -y
apt-get install -y default-jdk unzip curl

curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install

TOMCAT_VERSION=9.0.96
TOMCAT_DIR=/opt/tomcat
TOMCAT_SERVICE=/etc/systemd/system/tomcat.service

wget  https://dlcdn.apache.org/tomcat/tomcat-9/v${TOMCAT_VERSION}/bin/apache-tomcat-${TOMCAT_VERSION}.tar.gz
mkdir -p $TOMCAT_DIR
tar xzf apache-tomcat-${TOMCAT_VERSION}.tar.gz -C $TOMCAT_DIR --strip-components=1
rm -f apache-tomcat-${TOMCAT_VERSION}.tar.gz

chmod +x $TOMCAT_DIR/bin/*.sh

TOMCAT_SERVER_FILE="/opt/tomcat/conf/server.xml"
sudo sed -i 's/port="8080"/port="80"/' $TOMCAT_SERVER_FILE

chown -R ubuntu:ubuntu ${TOMCAT_DIR}

${TOMCAT_DIR}/bin/catalina.sh start

# install codedeploy agent
sudo apt install ruby-full
cd /home/ubuntu
wget https://aws-codedeploy-ap-southeast-1.s3.ap-southeast-1.amazonaws.com/latest/install
chmod +x ./install
sudo ./install auto
systemctl start codedeploy-agent
systemctl enable codedeploy-agent
