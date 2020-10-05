# /usr/bin/env python3

import os
from yaml import safe_load
from time import sleep
from argparse import ArgumentParser

from loguru import logger as log
from prometheus_client import REGISTRY

from synology_exporter.utils import get_config
from synology_exporter.utils import CollectMany
from synology_exporter.utils import format_logger
from synology_exporter.utils import create_dump_path
from synology_exporter.utils import get_synology_client
from synology_exporter.utils import start_prometheus_server
from synology_exporter.metric_builder import SynoMetricBuilder
from synology_exporter.data_collector import DataInfoCollect
from synology_exporter.data_collector import DataStatCollect
from synology_exporter.data_collector import DataStorageCollect
from synology_exporter.data_collector import DataShareCollect


# Default vars
EXPORTER_PORT = 9150
DUMP_PATH = "/tmp/synology_exporter.cache"
DATA_COLLECTORS = {
    "info": {
        "collector": DataInfoCollect,
        "interval": 60
    },
    "stat": {
        "collector": DataStatCollect,
        "interval": 45
    },
    "storage": {
        "collector": DataStorageCollect,
        "interval": 60
    },
    "share": {
        "collector": DataShareCollect,
        "interval": 120
    },
}


def arg_parser():
    parser = ArgumentParser()
    parser.add_argument(
        "-c",
        "--config",
        required=True,
        help="Config file with Synology credentials info"
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=EXPORTER_PORT,
        help=f"Port for the webserver scraped by Prometheus [Default: {EXPORTER_PORT}]"
    )
    for metric_type, data in DATA_COLLECTORS.items():
        parser.add_argument(
            f"--{metric_type}-refresh-interval",
            type=int,
            default=data["interval"],
            help=f"Refresh interval in seconds for {metric_type} collect [Default: {data['interval']}]"
        )
    for metric_type in DATA_COLLECTORS.keys():
        parser.add_argument(
            f"--disable-{metric_type}-metric",
            action="store_true",
            help=f"Disable {metric_type} collect"
        )
    parser.add_argument(
        "--log-path",
        help=f"Exporter log path"
    )
    parser.add_argument(
        "--dump-path",
        default=DUMP_PATH,
        help=f"Path for the dumps [Default: {DUMP_PATH}]"
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Debug Mode"
    )
    return parser.parse_args()


def main():
    error_msg = "Collector could not run"
    collector_pid = os.getpid()
    pid_file = "/var/run/synology-exporter.pid"
    # Get args
    args = arg_parser()
    # Init logger
    format_logger(
        log_path=args.log_path,
        debug=args.debug
    )
    # Check pid
    if os.path.isfile(pid_file):
        log.error(f"[main] {error_msg}: Existing pid file is present")
        exit(1)
    # Update data collectors dict
    for metric_type, data in DATA_COLLECTORS.items():
        enabled = False if getattr(args, f"disable_{metric_type}_metric") else True
        data.update({
            "interval": getattr(args, f"{metric_type}_refresh_interval"),
            "enabled": enabled
        })
    # Tool starting message
    msg = [f"{k.capitalize()}:{v['interval']}s" for k, v in DATA_COLLECTORS.items() if v["enabled"]]
    log.info(f"[main] Exporter starting [Refresh -> {'|'.join(msg)}]")
    # Get synology credentials from config file
    auths = get_config(args.config)
    # Get nas to collect
    synos = auths.keys()
    # Generate dump file template path
    create_dump_path(args.dump_path)
    # Init prometheus http server
    start_prometheus_server(args.port)
    # Start data collect with interval
    dump_files = {}
    for syno in synos:
        client = get_synology_client(name=syno, auth=auths[syno])
        dump_files[syno] = {}
        for metric_type, data in DATA_COLLECTORS.items():
            if not data["enabled"]:
                continue
            dump_file = os.path.join(
                args.dump_path,
                f"{syno}.{metric_type}.dump"
            )
            data_collect = data["collector"](
                name=syno,
                client=client,
                dump_file=dump_file,
                refresh_interval=data["interval"]
            )
            dump_files[syno][metric_type] = dump_file
            data_collect.start()
    # Wait dump files creation
    log.debug("[main] Wait for first dump file creation ..")
    sleep(2 * len(synos))
    # Get metric status
    metric_status = {k: v["enabled"] for k, v in DATA_COLLECTORS.items()}
    # Start prometheus collector
    builders = []
    for syno in synos: 
        builder = SynoMetricBuilder(
            name=syno,
            metric_status=metric_status,
            dump_files=dump_files[syno]
        )
        builders.append(builder)
    REGISTRY.register(CollectMany(builders))

    while True:
        sleep(30)

