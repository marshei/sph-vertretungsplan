FROM fedora:39 AS install-resource-provider
USER root

RUN mkdir -p /app/config

COPY requirements.txt /app/requirements.txt
COPY python/ /app/

RUN find /app -not -path "/app/venv/*" | grep -E "(/__pycache__$|\.pyc$|\.pyo$)" | xargs rm -rf

# ---------------------------------------------
# Build the final image
# ---------------------------------------------
FROM fedora:39
USER root

RUN dnf -y upgrade && \
    dnf install -y python3.12 python3.12-pip && \
    dnf reinstall -y tzdata && \
    dnf clean all

COPY --from=install-resource-provider /app /app
WORKDIR /app

RUN pip3 --no-cache-dir install --upgrade pip && \
    pip3 --no-cache-dir install -r /app/requirements.txt

VOLUME [ "/app/config" ]

ENV TZ=Europe/Berlin

ENTRYPOINT [ "python3", "/app/sph_vertretung.py", "--config-file", "/app/config/sph.yml" ]

LABEL description="Schulportal Hessen - Vertretungsplan"
