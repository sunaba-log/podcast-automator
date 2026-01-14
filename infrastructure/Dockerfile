FROM hashicorp/terraform
ARG GCLOUD_VERSION=495.0.0
RUN apk update \
    && apk add --no-cache bash curl git make docker-cli docker-cli-buildx findutils jq python3 py3-crcmod libc6-compat \
    && curl -fsSL https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-${GCLOUD_VERSION}-linux-x86_64.tar.gz \
      | tar -xz -C /opt \
    && /opt/google-cloud-sdk/install.sh --quiet --usage-reporting=false --path-update=false --command-completion=false \
    && ln -s /opt/google-cloud-sdk/bin/gcloud /usr/local/bin/gcloud \
    && ln -s /opt/google-cloud-sdk/bin/gsutil /usr/local/bin/gsutil \
    && ln -s /opt/google-cloud-sdk/bin/docker-credential-gcloud /usr/local/bin/docker-credential-gcloud \
    && rm -rf /var/cache/apk/*
