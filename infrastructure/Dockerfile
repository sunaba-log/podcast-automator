FROM hashicorp/terraform
RUN apk update \
    && apk add --no-cache git make docker-cli docker-cli-buildx aws-cli bash findutils jq \
    && rm -rf /var/cache/apk/*
