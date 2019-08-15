# lxd-backup.py
A Python script to back up ZFS based LXD containers via Restic

*This script will work with ZFS as storage backend only!*


## What this script does

* It connects to the LXD Daemon and asks for a list of all LXD containers
* It makes a ZFS snapshot for every container (Snapshot of the containers /root/ device)
* The snapshot is mounted to `/mnt/backup/[containername]`
* Restic makes a backup of `/mnt/backup`
* All the mounts are umounted
* Backup snapshots are deleted
* Restic deletes old Backups
* Restic checks backup repository integrity 


## Setup

Download `lxd-backup.py` and make sure you have the following dependencies installed:

* [pylxd](https://pypi.org/project/pylxd/)
* [dotenv](https://pypi.org/project/python-dotenv/)

```
sudo apt install python3-pip
pip3 install pylxd python-dotenv
```

`lxd-backup.py` expects `resticenv.sh` to exist in the same directory. The file contains information about the Restic repository to use and its passphrase. It contains both settings as environment variable definitions and is meant to be sourced either manually (e.g. when using restic mount) or by the `lxd-backup.py` script:

```
#!/bin/bash
export RESTIC_REPOSITORY="sftp:fancyuser.your-storagebox.de:lxd1"
export RESTIC_PASSWORD="mydumbshortinsecurepassphrase"
```

**Also you may want to edit the Python script and adapt the parameters of "restic forget" to your needs.**

That's it. Just run the script and see what happens:

```
chmod u+x lxd-backup.py
./lxd-backup.py
```

---

Feel free to submit a pull request if you made any changes that might help other users! :-) 

