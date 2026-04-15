FROM odoo:19.0

COPY odoo/requirements.txt /tmp/requirements.txt
RUN if [ -s /tmp/requirements.txt ]; then \
    pip install --no-cache-dir --break-system-packages -r /tmp/requirements.txt; \
    fi
