from loguru import logger as log
from prometheus_client.core import GaugeMetricFamily
from prometheus_client.core import CollectorRegistry

from synology_exporter.utils import read_data_from_file


class SynoMetricBuilder():

    def __init__(self, name, metric_status, dump_files):
        self.name = name
        self.metric_status = metric_status
        self._dump_files = dump_files

    def get_collect_status(self, metric_type):
        data = read_data_from_file(dump_file=self._dump_files[metric_type])
        return bool(data.get("collect_status", 0))

    def info_metrics(self):
        data = read_data_from_file(dump_file=self._dump_files["info"])
        for metric, value in data["info"].items():
            if not isinstance(value, (int, float)):
                continue
            gauge = GaugeMetricFamily(
                f"synology_info_{metric}",
                f"Synology Info Metrics",
                labels=["dsm"]
            )
            gauge.add_metric([self.name], value)
            yield gauge

    def stat_metrics(self):
        data = read_data_from_file(dump_file=self._dump_files["stat"])
        for metric, value in data["stats"].items():
            if not isinstance(value, (int, float)):
                continue
            gauge = GaugeMetricFamily(
                f"synology_stats_{metric}",
                f"Synology Stats Metrics",
                labels=["dsm"]
            )
            gauge.add_metric([self.name], value)
            yield gauge

    def volume_metrics(self):
        data = read_data_from_file(dump_file=self._dump_files["storage"])
        for metric, value in data["volumes"][0].items():
            if not isinstance(value, (int, float)):
                continue
            gauge = GaugeMetricFamily(
                f"synology_volume_{metric}",
                f"Synology Volume Metrics",
                labels=["dsm", "id"]
            )
            for volume in data["volumes"]:
                tags = [self.name, volume["id"]]
                gauge.add_metric(tags, volume[metric])
            yield gauge

    def disk_metrics(self):
        data = read_data_from_file(dump_file=self._dump_files["storage"])
        for metric, value in data["disks"][0].items():
            if not isinstance(value, (int, float)):
                continue
            gauge = GaugeMetricFamily(
                f"synology_disk_{metric}",
                f"Synology Disk Metrics",
                labels=["dsm", "id", "name"]
            )
            for disk in data["disks"]:
                tags = [self.name, disk["id"], disk["name"]]
                gauge.add_metric(tags, disk[metric])
            yield gauge

    def share_metrics(self):
        data = read_data_from_file(dump_file=self._dump_files["share"])
        for metric, value in data["shares"][0].items():
            if not isinstance(value, (int, float)):
                continue
            gauge = GaugeMetricFamily(
                f"synology_share_{metric}",
                f"Synology Share Metrics",
                labels=["dsm", "uuid", "name", "path"]
            )
            for share in data["shares"]:
                tags = [self.name, share["uuid"], share["name"], share["path"]]
                gauge.add_metric(tags, share[metric])
            yield gauge

    def build(self):

        if self.metric_status["info"] and self.get_collect_status("info"):
            yield from self.info_metrics()

        if self.metric_status["stat"] and self.get_collect_status("stat"):
            yield from self.stat_metrics()

        if self.metric_status["storage"] and self.get_collect_status("storage"):
            yield from self.volume_metrics()
            yield from self.disk_metrics()

        if self.metric_status["share"] and self.get_collect_status("share"):
            yield from self.share_metrics()

