FROM python:3.8-slim
MAINTAINER L.Koné (loko-loko@github.com)

ENV PYTHONUNBUFFERED 1
WORKDIR /exporter

# Create temporary path
RUN mkdir -p /tmp/.pkg

# Copy package + files
ADD synology_exporter /tmp/.pkg/synology_exporter
ADD setup.py /tmp/.pkg/

# Install package
RUN pip install -q /tmp/.pkg \
    && rm -fr /tmp/.pkg

ADD docker-entrypoint.sh /

# Run entrypoint
ENTRYPOINT ["/docker-entrypoint.sh"]

