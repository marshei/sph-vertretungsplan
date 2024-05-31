FROM registry.fedoraproject.org/fedora-minimal:40 AS install-resource-provider
USER root

RUN mkdir -p /app/config

COPY requirements.txt /app/requirements.txt
COPY python/ /app/

RUN find /app -not -path "/app/venv/*" | grep -E "(/__pycache__$|\.pyc$|\.pyo$)" | xargs rm -rf

# ---------------------------------------------
# Build the final image
# ---------------------------------------------
FROM registry.fedoraproject.org/fedora-minimal:40
USER root

RUN microdnf -y upgrade && \
    microdnf install -y python3.12 python3.12-pip && \
    microdnf reinstall -y tzdata && \
    microdnf clean all && \
    rm -fr /var/cache/dnf && \
    rm -f /var/log/*

COPY --from=install-resource-provider /app /app
WORKDIR /app

RUN pip3 --no-cache-dir install --upgrade pip && \
    pip3 --no-cache-dir install -r /app/requirements.txt && \
    rm -fr /root/.cache

VOLUME [ "/app/config" ]

ENV TZ=Europe/Berlin

ENTRYPOINT [ "python3", "/app/sph_vertretung.py", "--config-file", "/app/config/sph.yml" ]

LABEL description="Schulportal Hessen - Vertretungsplan"
