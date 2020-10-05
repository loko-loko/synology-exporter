import time
from os import rename
from threading import Thread

from loguru import logger as log

from synology_exporter.utils import write_data_to_file


class DataCollect(Thread):

    def __init__(self, name, client, dump_file, refresh_interval):
        Thread.__init__(self)
        self.name = name
        self._client = client
        self._dump_file = dump_file
        self._refresh_interval = refresh_interval
        self._blank_data = {"collect_status": 0}

    def collect(self, metric_type, api, functions):
        log.debug(f"[collect][{metric_type}] Starting data gather thread from {self.name}")
        # Init dump file
        write_data_to_file(dump_file=self._dump_file, data=self._blank_data)
        # Start data collect with interval
        while True:
            # Init data
            data = self._blank_data
            start_time = time.time()
            try:
                api.update()
                data.update({k: f() for k, f in functions.items()})
            except Exception as e:
                log.error(f"[collect][{metric_type}] Error getting data from {self.name}: {e}")
            else:
                collect_duration = time.time() - start_time
                log.info(f"[collect][{metric_type}] Done getting data from {self.name} [time:{round(collect_duration, 2)}s]")
                # Update data with new value if collect OK
                data.update({
                    "collect_status": 1,
                    "collect_duration": collect_duration
                })
            # Write new dump
            new_dump_file = f"{self._dump_file}.new"
            write_data_to_file(dump_file=new_dump_file, data=data)
            rename(new_dump_file, self._dump_file)
            log.debug(f"[collect][{metric_type}] Done dumping data from {self.name} to {self._dump_file}")
            # Waiting for the next collect
            time.sleep(self._refresh_interval)


class DataInfoCollect(DataCollect):

    def get_synology_info(self):
        data = {
            "model": self._client.information.model,
            "ram_mb": self._client.information.ram,
            "serial": self._client.information.serial,
            "temperature": self._client.information.temperature,
            "temperature_warning": self._client.information.temperature_warn,
            "uptime": self._client.information.uptime,
            "version": self._client.information.version_string,
        }
        return data

    def run(self):
        self.collect(
            metric_type="info",
            api=self._client.information,
            functions={
                "info": self.get_synology_info
            }
        )


class DataStatCollect(DataCollect):

    def get_synology_use(self):
        data = {
            "cpu_load": self._client.utilisation.cpu_total_load,
            "mem_use": self._client.utilisation.memory_real_usage,
            "net_up": self._client.utilisation.network_up(),
            "net_down": self._client.utilisation.network_down(),
        }
        return data

    def run(self):
        self.collect(
            metric_type="stat",
            api=self._client.utilisation,
            functions={
                "stats": self.get_synology_use
            }
        )


class DataStorageCollect(DataCollect):

    @staticmethod
    def get_status(status):
        return {"normal": 1}.get(status, 0)

    def get_synology_volumes(self):
        volumes = []
        for volume_id in self._client.storage.volumes_ids:
            volumes.append({
                "id": volume_id,
                "status": self.get_status(self._client.storage.volume_status(volume_id)),
                "used_prc": self._client.storage.volume_percentage_used(volume_id),
            })
        return volumes

    def get_synology_disks(self):
        disks = []
        for disk_id in self._client.storage.disks_ids:
            disks.append({
                "id": disk_id,
                "name": self._client.storage.disk_name(disk_id),
                "status": self.get_status(self._client.storage.disk_status(disk_id)),
                "temperature": self._client.storage.disk_temp(disk_id)
            })
        return disks

    def run(self):
        self.collect(
            metric_type="storage",
            api=self._client.storage,
            functions={
                "volumes": self.get_synology_volumes,
                "disks": self.get_synology_disks
            }
        )


class DataShareCollect(DataCollect):

    def get_synology_shares(self):
        shares = []
        for share_uuid in self._client.share.shares_uuids:
            shares.append({
                "uuid": share_uuid,
                "name": self._client.share.share_name(share_uuid),
                "path": self._client.share.share_path(share_uuid),
                "used": self._client.share.share_size(share_uuid),
                "recycle_bin": self._client.share.share_recycle_bin(share_uuid)
            })
        return shares

    def run(self):
        self.collect(
            metric_type="share",
            api=self._client.share,
            functions={
                "shares": self.get_synology_shares
            }
        )

