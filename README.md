# lxd-backup.py

_Mounts all existing ZFS-based LXD container root filesystems and runs Restic on those mountpoints. This script was created for personal use! Don't expect high quality and submit PRs if you improved something :-)_

---

## What this script does

* It connects to the LXD Daemon and asks for a list of all LXD containers
* It makes a ZFS snapshot for every container (Snapshot of the containers /root/ device)
* The snapshot is mounted to /mnt/backup/[containername]
* Restic makes a backup of /mnt/backup
* All the mounts are umounted
* Backup snapshots are deleted
* Restic deletes old Backups
* Restic checks backup repository integrity


## Requirements / dependencies

Python3 dependencies are listed in `requirements.txt`, but can also be installed system-wide via:

```
apt install \
    python3-pylxd \
    python3-dotenv \
    python3-path
```

**[Restic](https://github.com/restic/restic) needs to be installed on the system** and must be initialized (`restic init`). Furthermore, the following Restic environment file needs to exist in the same directory as the `lxd-backup.py` script:

`resticenv.sh`

```
#!/bin/bash

export RESTIC_REPOSITORY="sftp:<user>.your-storagebox.de:<hostname>"
export RESTIC_PASSWORD="<passphrase>"
```

* `<user>` SFTP user. Here: Hetzner Storage Box User
* `<hostname>`: Hostname of server for storage subdirectory
* `<passphrase>`: Restic backup archive passphrase

The type of storage (here: SFTP) can be modified as needed. Restic supports multiple storage backends: https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html


## Systemd service and timer files

`lxd-backup.timer`

```
[Unit]
Description=Restic backup cronjob

[Timer]
OnCalendar=*-*-* 03:00:00
RandomizedDelaySec=900

[Install]
WantedBy=timers.target
```

* `OnCalendar`: Makes the backup process run every day at 3 am.
* `RandomizeDelaySec`: Make the backup start at random times within the 900 seconds margin to reduce sudden loads on systems with multiple backup script instances.


`lxd-backup.service`

```
[Unit]
Description=Restic backup

[Service]
Type=simple
User=root
CPUQuota=600%
Environment=PYTHONUNBUFFERED=yes
ExecStart=/usr/bin/python3 /opt/backup/lxd-backup.py
```

* `CPUQuota`: Sets CPU quota limit to use for the backup process. 600 % == 6 cores

Put those files into `/etc/systemd/system/` and enable them:

```
systemctl enable --now lxd-backup.timer
systemctl enable lxd-backup.service  
```


## Deleting old backups

The script has a `restic forget --prune` hardcoded into the source. The retention periods are not yet configurable. If you need to change the values, do it in the source (or create a mechanism to make them configurable and submit a PR ;-) ).

