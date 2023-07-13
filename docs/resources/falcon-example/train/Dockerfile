FROM python AS build
RUN pip install datasets \
    trl==0.4.5 \
    einops \
    torch==2.0.1  \
    transformers==4.26.1 \
    --extra-index-url https://download.pytorch.org/whl/cpu

RUN mkdir -p tmp/model
COPY train_script.py tmp
COPY ./alpaca-fr.csv tmp
RUN python tmp/train_script.py

FROM scratch AS binaries
COPY --from=build tmp/model /