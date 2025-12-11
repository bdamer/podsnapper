#!/usr/bin/python3

import os
import urllib.request
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
import requests
import sys

# Settings
HOME_DIR=os.path.expanduser('~')
# File holding feed subscriptions
FEEDS_FILE=HOME_DIR + "/.podsnapper/feeds.txt"
# File holding downloaded files
INV_FILE=HOME_DIR + "/.podsnapper/inventory.txt"
# Directory for temporary files
TMP_DIR=HOME_DIR + "/.podsnapper/tmp/"
# File to store podcasts in
POD_DIR=HOME_DIR + "/Podcasts/"
# Headers to send when making requests
HEADERS = {"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36"}

DRY_RUN=False
if len(sys.argv) > 1:
	if sys.argv[1] == "--dry-run" or sys.argv[1] == '-dr':
		DRY_RUN=True

# Begin podsnapper
class Item:
	def __init__(self):
		self.id = ""
		self.title = ""
		self.url = ""
		self.feed_id = ""
	def __str__(self):
		return "Item[" + self.id + "] - " + self.title + " [" + self.url + "]"

class Feed:
	def __init__(self, id, url, naming):
		self.id = id
		self.url = url
		self.naming = naming

def init():
	if not os.path.isdir(TMP_DIR):
		os.mkdir(TMP_DIR)
	if not os.path.isdir(POD_DIR):
		os.mkdir(POD_DIR)

def load_inventory():
	print(f'Loading inventory: {INV_FILE}')
	res = set()
	if os.path.isfile(INV_FILE):
		file = open(INV_FILE, 'r')
		lines = file.readlines()
		for line in lines:
			res.add(line.strip())
	return res

def load_feeds():
	print(f'Loading feeds: {FEEDS_FILE}')
	res = {}
	if os.path.isfile(FEEDS_FILE):
		file = open(FEEDS_FILE, 'r')
		lines = file.readlines()
		for line in lines:
			line = line.strip()
			if line.startswith("#"):
				continue
			tok = line.split()
			if len(tok) == 3:
				res[tok[0]] = Feed(tok[0], tok[1], tok[2])
			else:
				print(f'Invalid feed: {line}')
	return res

def download_rss(feed_id, url):
	print(f'Downloading: {url}')
	r = requests.get(url,headers=HEADERS)
	with open(TMP_DIR + feed_id + ".rss", 'wb') as fh:
	    fh.write(r.content)

def parse_rss(feed_id, items):
	print("Parsing: " + feed_id)
	try:
		tree = ET.parse(TMP_DIR + feed_id + ".rss")
		root = tree.getroot()
		if not root.tag == "rss":
			print("Unexpected RSS format")
			return
		# Loop over channels
		for channel in root:
			parse_items(feed_id, channel, items)
	except Exception:
		print(f'Failed to parse feed: {feed_id}')

def parse_items(feed_id, channel, items):
	for i in channel:
		if not i.tag == "item":
			continue
		item = Item()
		item.feed_id = feed_id
		for attr in i:
			if attr.tag == "title" or attr.tag == "itunes:title":
				item.title = attr.text
			elif attr.tag == "guid":
				item.id = attr.text
			elif attr.tag == "enclosure":
				item.url = attr.attrib["url"]
		items.append(item)

def strip_url(url):
	return url.split('?')[0]

def download_items(items, feeds):
	# Open inventory file for writing
	inv = open(INV_FILE, 'a')
	for item in items:
		# Compute filename based on feed settings
		filename = ""
		if feeds[item.feed_id].naming == 'title':
			filename = item.title.replace("/", "%2f") + ".mp3"
		else:
			url = urlparse(item.url)
			filename = os.path.basename(url.path)
		target_dir = POD_DIR + item.feed_id
		if not os.path.isdir(target_dir):
			os.mkdir(target_dir)
		target = target_dir + "/" + filename
		if os.path.isfile(target) or DRY_RUN:
			print(f'Target file already exists, skipping: {filename}')
		else:
			print(f'Downloading item {item.title} [{item.url}] to {target}')
			r = requests.get(item.url,headers=HEADERS)
			with open(target, 'wb') as fh:
			    fh.write(r.content)
		# Update inventory with stripped URL
		inv.write(f'{item.feed_id}|{item.id}\n')

def update():

	inv = load_inventory()

	# Refresh all subscriptions
	feeds = load_feeds()
	items = []
	for f in feeds:
		try:
			download_rss(f, feeds[f].url)
			parse_rss(f, items)
		except ConnectionError:
			print(f"Connection error while updating feed {f}")
		except Exception:
			print(f"Generic error while updating feed {f}")

	# Remove items that we have already downloaded
	items[:] = [item for item in items if (not f'{item.feed_id}|{item.id}' in inv)]

	print("Found " + str(len(items)) + " items")
	download_items(items, feeds)
	print("All done")

# Begin podsnapper
init()
update()
