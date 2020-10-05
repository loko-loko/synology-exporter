import os
import sys
import pickle
import socket

from yaml import safe_load
from loguru import logger as log
from synology_dsm import SynologyDSM
from prometheus_client import Info
from prometheus_client import start_http_server

from synology_exporter import __version__ as exporter_version


def format_logger(log_path=None, debug=False):
    log_level = "DEBUG" if debug else "INFO"
    formatter="{time:YYYY/MM/DD HH:mm:ss}  {level:<7} - {message}"
    log.remove()
    log.add(
        sys.stderr,
        level=log_level,
        format=formatter
    )
    if log_path:
        if not os.path.exists(log_path):
            log.error(f"[logger] No log path found from {log_path}")
            exit(1)
        log_file = os.path.join(log_path, "exporter.log")
        log.add(
            log_file,
            level=log_level,
            format=formatter,
            rotation="5 MB"
        )


def start_prometheus_server(port):
    hostname = socket.gethostname()
    log.debug(f"[prometheus] Start web server: 0.0.0.0:{port} (Host:{hostname})")
    start_http_server(port)
    prometheus_info = Info(
        "synology_exporter",
        "Synology Prometheus exporter"
    )
    prometheus_info.info({
        "version": exporter_version,
        "running_on": hostname
    })
    log.info(f"[prometheus] Web server started: {hostname}:{port}")


class CollectMany:

    def __init__(self, builders):
        self.builders = builders

    def collect(self):
        for builder in self.builders:
            yield from builder.build()


def get_synology_client(name, auth):
    log.debug(f"[synology] Get client for {name}")
    try:
        client = SynologyDSM(
            dsm_ip=auth["address"],
            dsm_port=auth["port"],
            username=auth["username"],
            password=auth["password"]
        )
    except Exception as e:
        log.error(f"[synology] Problem to retrieve client of {name}: {e}")
        exit(1)
    return client


def create_dump_path(dump_path):
    if not os.path.exists(dump_path):
        try:
            log.debug("Create dump directory")
            os.makedirs(dump_path)
        except Exception as e:
            log.error(f"The dump directory cannot be created: {e}")
            exit(1)


def get_config(config_file):
    log.debug(f"[config] Get yaml config file: {config_file}")
    try:
        with open(config_file) as f:
            data = safe_load(f)
        return data["configs"]
    except FileNotFoundError as e:
        log.error(f"[config] File was not found: {e}")
        exit(1)
    except Exception as e:
        log.error(f"[config] File cannot be parsed: {e}")
        exit(1)


def write_data_to_file(dump_file, data):
    log.debug(f"Write dump data to {dump_file} ..")
    with open(dump_file, "wb+") as f:
        pickle.dump((data, ), f, pickle.HIGHEST_PROTOCOL)


def read_data_from_file(dump_file):
    log.debug(f"Read dump data from {dump_file} ..")
    with open(dump_file, "rb") as f:
        data = pickle.load(f)[0]
    return data

