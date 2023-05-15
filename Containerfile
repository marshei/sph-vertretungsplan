ARG UBI9_MINIMAL_IMAGE_VERSION="9.2-484"

FROM ubi9-minimal:${UBI9_MINIMAL_IMAGE_VERSION} AS install-resource-provider
USER root

RUN microdnf install -y findutils && \
    microdnf clean all && \
    mkdir -p /app/config

COPY requirements.txt /app/requirements.txt
COPY python/ /app/

RUN find /app -not -path "/app/venv/*" | grep -E "(/__pycache__$|\.pyc$|\.pyo$)" | xargs rm -rf

# ---------------------------------------------
# Build the final image
# ---------------------------------------------
FROM ubi9-minimal:${UBI9_MINIMAL_IMAGE_VERSION}
USER root

RUN microdnf install -y python3.9 python3.9-pip && \
    microdnf reinstall -y tzdata && \
    microdnf clean all

COPY --from=install-resource-provider /app /app
WORKDIR /app

RUN pip3 --no-cache-dir install --upgrade pip && \
    pip3 --no-cache-dir install -r /app/requirements.txt

VOLUME [ "/app/config" ]

ENV TZ=Europe/Berlin

ENTRYPOINT [ "/usr/libexec/platform-python", "/app/sph_vertretung.py", "--config-file", "/app/config/sph.yml" ]

LABEL description="Schulportal Hessen - Vertretungsplan"
