FROM python:latest

WORKDIR /usr/src/app

COPY . .

RUN python3 -m pip install -r requirements.txt

ENTRYPOINT [ "python3", "build_tfc.py" ]
