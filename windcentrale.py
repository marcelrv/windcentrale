#!/usr/bin/env python
# coding: utf-8

from warrant.aws_srp import AWSSRP
import boto3
import paho.mqtt.client as paho
import json
import time
from urllib.request import urlopen, Request

###############################################################
# Small script to get windcentrale.nl info with production for
# your mill data and post to mqtt for further processing
# 2022 Marcel Verpaalen
# 
###############################################################

# configuration
username = ""
password = ""
mqtt_server = "192.168.3.17"
mqtt_port = 1883

mqtt_topic = "/openhab/winddata"
molen = "WND-BR"  # None will give data for all mills. Alternatively find the code for your mill, e.g. WND-BR
refresh_interval = 30

###############################################################
client_id = "715j3r0trk7o8dqg3md57il7q0"
user_pool_id = "eu-west-1_U7eYBPrBd"
region = "eu-west-1"

authentication_details = json.loads(
    urlopen("https://mijn.windcentrale.nl/api/v0/labels/key?domain=mijn.windcentrale.nl").read().decode("utf-8")
)
print("Logon details:")
print("client_id:    {}".format(authentication_details["client_id"]))
print("region:       {}".format(authentication_details["region"]))
print("user_pool_id: {}".format(authentication_details["user_pool_id"]))


def get_authorization():
    try:
        boto3_client = boto3.client("cognito-idp", region_name=region)
        aws = AWSSRP(
            username=username, password=password, pool_id=user_pool_id, client_id=client_id, client=boto3_client
        )
        tokens = aws.authenticate_user()
        #        print("tokens: ", tokens)
        token_type = tokens["AuthenticationResult"]["TokenType"]
        id_token = tokens["AuthenticationResult"]["IdToken"]
        authorization_header = {"Authorization": token_type + " " + id_token}
        return authorization_header
    except Exception as ex:
        print("invalid_user_credentails", ex)
        return None


url = "https://mijn.windcentrale.nl/api/v0/livedata"
if molen is not None:
    url += "?projects=" + molen

client = paho.Client("windcentrale")
client.connect(mqtt_server, mqtt_port)
authorization = get_authorization()

req = Request("https://mijn.windcentrale.nl/api/v0/sustainable/projects")
req.add_header("Authorization", authorization["Authorization"])
print("Mill data", urlopen(req).read().decode("utf-8"))

while True:
    try:
        if authorization is None:
            authorization = get_authorization()
        req = Request(url)
        req.add_header("Authorization", authorization["Authorization"])
        data = json.loads(urlopen(req).read().decode("utf-8"))
        #        print(data)
        client.publish(mqtt_topic, json.dumps(data, indent=4))
    except Exception as ex:
        print("Error while running", ex)
        authorization = None
    time.sleep(refresh_interval)
