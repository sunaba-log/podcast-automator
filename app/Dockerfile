# Base image used for preparing dependencies and for the final image
FROM public.ecr.aws/lambda/python:3.12-x86_64 as baseimage
COPY --from=public.ecr.aws/datadog/lambda-extension:latest /opt/. /opt/
RUN pip install --no-cache-dir --upgrade pip poetry
RUN dnf update -y \
    && dnf install -y make tzdata \
    && dnf clean all \
        && rm -rf /var/cache/yum
WORKDIR ${LAMBDA_TASK_ROOT}


# Prepare dependencies in separate builder to allow efficient docker caching
FROM baseimage as builder
RUN pip install --no-cache-dir --upgrade pip poetry
ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=1
ENV POETRY_VIRTUALENVS_CREATE=1
ENV POETRY_CACHE_DIR=/tmp/docker_builder/poetry_cache
COPY mcp_server/pyproject.toml mcp_server/poetry.lock mcp_server/Makefile ./
RUN poetry run pip install datadog-lambda
RUN --mount=type=cache,target=$POETRY_CACHE_DIR make install-prod POETRY_INSTALL_FLAG=--no-root


# Finally, build the application docker image using the base image and dependencies from the previous steps
FROM baseimage
ENV VIRTUAL_ENV=${LAMBDA_TASK_ROOT}/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}
COPY mcp_server ./
RUN chmod -R a+rX ${LAMBDA_TASK_ROOT}
RUN make install-prod
ENV PYTHONPATH=${VIRTUAL_ENV}/lib/python3.12/site-packages
ENV DD_LAMBDA_HANDLER="src.lambda_handler.lambda_handler"
CMD [ "datadog_lambda.handler.handler" ]
