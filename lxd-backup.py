#!/usr/bin/env python3

import sys
import subprocess
from pylxd import Client
import os
from dotenv import load_dotenv
from pathlib import Path


# Set env variable to suppress warnings (see: https://github.com/lxc/pylxd/pull/361)
os.environ["PYLXD_WARNINGS"] = "none"

# load restic environment
envPath = Path(os.path.join(sys.path[0], 'resticenv.sh'))
load_dotenv(dotenv_path=envPath)

# Get all the containers from LXD
client = Client()
containers = client.containers.all()

# Lists of created snapshots and mounts
# This is to keep track - in case a step fails and mounting / snapshotting needs to be reverted.
successfulSnapshots = set()

# Did anyerror occur?
error = 0

##
## Procedure function definitions
##

# Create LXD snapshots on the ZFS volumes - one for each LXD container. The snapshots is always called "resticsnap" to be able to distinct it from regular snapshots
def createSnapshots():
    print("Creating snapshots ...")

    for container in containers:       
        # Adding snapshot for restic backup
        print("    ... creating snapshot of", container.name)
        container.snapshots.create('resticsnap', stateful=False, wait=True)
        successfulSnapshots.add(container)

# Remove all the LXD snapshots that were successfully created
def removeSnapshots():
    print("Removing snapshots ...")

    for container in successfulSnapshots:
        print("Deleting snapshot of container {container}".format(container=container.name))
        container.snapshots.get('resticsnap').delete(wait=True)
    
# Mount all resticsnap snapshots to directories in /mnt/backup/
def mountSnapshots():
    print("Mounting snapshots ...")

    for container in containers:
        # Mount snapshot
        print("    ... mounting filesystem for container", container.name)

        try: storagePool = container.devices['root']['pool']
        except: storagePool = 'default'

        subprocess.run("mkdir -p /mnt/backup/{container} && mount -t zfs {pool}/containers/{container}@snapshot-resticsnap /mnt/backup/{container}".format(container=container.name, pool=storagePool), shell=True, capture_output=True, check=True)

# Remove all the snapshots mounts that were successfully created
def unmountSnapshots():
    print("Unmounting snapshots ...")

    for container in containers:
        if os.path.ismount(Path("/mnt/backup/{container}".format(container=container.name))):
            print("Unmounting filesystem for container", container.name)
            subprocess.run("umount /mnt/backup/{container} && rm -r /mnt/backup/{container}".format(container=container.name), shell=True, check=True)

# Run Restic to back up files in mounted ZFS snapshots
def runRestic():
    print("Running restic on /mnt/backup/")
    subprocess.run("restic backup /mnt/backup /root /opt/backup /var/snap/lxd/common/lxd", shell=True, check=True)


# Forget old backups
def forgetOldBackups():
    print("Forgetting old backups ...")
    subprocess.run('''\
        restic forget --prune \
        --keep-last 5 \
        --keep-daily 14 \
        --keep-weekly 4 \
        --keep-monthly 2 \
        ''', shell=True, check=True)

# Check repo integrity
def checkIntegrity():
    print("Checking backup repo integrity ...")
    subprocess.run("restic check", shell=True, check=True)

# Unlock restic repo 
def unlockRestic():
    print("Unlocking Restic repo ...")
    subprocess.run("restic unlock", shell=True, check=True)
    

## 
## Main procedure
try:
    createSnapshots()
    try:
        mountSnapshots()
        try:
            runRestic()
        except Exception as e:
            print("Running Restic failed!", e)
            unlockRestic()
            error = 1
    except Exception as e:
        print("Mounting the snapshots failed!", e)
        error = 1
    finally:
        unmountSnapshots()
except Exception as e:
    print("Creating the snapshots failed!", e)
    error = 1
finally:
    removeSnapshots()

try:
    forgetOldBackups()
except subprocess.CalledProcessError as err:
    print("Forgetting old backups failed:", err.stderr.decode('UTF-8'))
    unlockRestic()
    error = 1

try:
    checkIntegrity()
except subprocess.CalledProcessError as err:
    print("Checking repository integrity failed:", err.stderr.decode('UTF-8'))
    unlockRestic()
    error = 1


### Exit with return code "non-zero" and display a warning message in the log if backup failed.
if error != 0:
    sys.exit("\n\n>>> One or more error occured. BACKUP FAILED! See error messages above. <<< \n\n")



