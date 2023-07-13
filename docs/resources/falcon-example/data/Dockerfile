FROM python AS build

RUN pip install datasets
RUN mkdir -p tmp/datasets
COPY dataset_script.py tmp/
RUN python tmp/dataset_script.py

FROM scratch AS binaries
COPY --from=build ./tmp/datasets /