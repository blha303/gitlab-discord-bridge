#!/usr/bin/env python3
from discord import Client
from json import load

with open("config.json") as f:
    config = load(f)

client = Client()

client.run(config["token"])
