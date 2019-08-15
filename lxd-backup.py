#!/usr/bin/env python3

import sys
import subprocess
from pylxd import Client
import os
from dotenv import load_dotenv
from pathlib import Path


### Set env variable to suppress warnings (see: https://github.com/lxc/pylxd/pull/361)
os.environ["PYLXD_WARNINGS"] = "none"

## load restic environment
envPath = Path(os.path.join(sys.path[0], 'resticenv.sh'))
load_dotenv(dotenv_path=envPath)

### Get all the containers from LXD
client = Client()
containers = client.containers.all()

### Create snapshots and mount them
for container in containers:
	try:
		storagePool = container.devices['root']['pool']
	except:
		storagePool = 'default'
		# Adding snapshot for restic backup
	print("Creating snapshot of", container.name)
	try:
		container.snapshots.create('resticsnap', stateful=False, wait=True)
	except:
		print("Could not create snapshot for", container.name)
	# Mount snapshot
	print("Mounting filesystem for container", container.name)
	try:
		subprocess.run("mkdir -p /mnt/backup/{container} && mount -t zfs {pool}/containers/{container}@snapshot-resticsnap /mnt/backup/{container}".format(container=container.name, pool=storagePool), shell=True, capture_output=True, check=True)
	except subprocess.CalledProcessError as err:
		print("    mounting {contname} failed: {error}".format(contname=container.name, error=err.stderr.decode('UTF-8')))


### Make Restic backup ...
print("Running restic on /mnt/backup/")
try:
	subprocess.run("restic backup /mnt/backup", shell=True, check=True)
except subprocess.CalledProcessError as err:
	print("Running restic on /mnt/backup/ failed.")


### Ummount all containers and delete their snapshots
for container in containers:
	print("Unmounting filesystem for container", container.name)
	if os.path.ismount(Path("/mnt/backup/{container}".format(container=container.name))):
		try:
			subprocess.run("umount /mnt/backup/{container} && rm -r /mnt/backup/{container}".format(container=container.name), shell=True, check=True)
		except subprocess.CalledProcessError as err:
			print("Unmounting the container and deleting the mount point failed: {error}".format(error=err.stderr.decode('UTF-8')))
		print("Deleting snapshot of container {container}".format(container=container.name))
		try:
			container.snapshots.get('resticsnap').delete(wait=True)
		except:
			print("Could not delete snapshot of container {container}".format(container=container.name))
	else:
		print("Container {container} was not mounted. No need to unmount.".format(container=container.name))


### Forget old backups
print("Forgetting old backups ...")
try:
	subprocess.run('''\
		restic forget \
		--keep-last 5 \
		--keep-daily 14 \
		--keep-weekly 4 \
		--keep-monthly 6 \
		''', shell=True, check=True)
except subprocess.CalledProcessError as err:
	print("restic forget failed.")


### Check repo integrity
print("Checking backup repo integrity ...")
try:
	subprocess.run("restic check", shell=True, check=True)
except subprocess.CalledProcessError as err:
	print("Checking repository integrity failed.")

print("Finished.")