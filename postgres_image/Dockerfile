FROM postgres:16

RUN apt-get update \
    && apt-get install -y --no-install-recommends pgbackrest \
    && rm -rf /var/lib/apt/lists/*

COPY postgres_image/scripts/pgbackrest-archive.sh /usr/local/bin/pgbackrest-archive.sh

RUN chmod +x /usr/local/bin/pgbackrest-archive.sh
