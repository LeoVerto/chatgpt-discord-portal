# build stage
FROM python:3.10-alpine AS builder

# install PDM
RUN pip install -U pip setuptools wheel
RUN pip install pdm

# copy files
COPY pyproject.toml pdm.lock README.md LICENSE /project/
COPY portal/ /project/portal

# install dependencies and project into the local packages directory
WORKDIR /project
RUN mkdir __pypackages__ && pdm install --prod --no-lock --no-editable


# run stage
FROM python:3.10-alpine

# retrieve packages from build stage
ENV DATA_DIR=/data
ENV PYTHONPATH=/project/pkgs
COPY --from=builder /project/__pypackages__/3.10/lib /project/pkgs

VOLUME /data

CMD ["python", "-m", "portal"]
