FROM python:latest

WORKDIR /usr/src/app

COPY . .

EXPOSE 8000

RUN pip install -r requirements.txt

RUN python djangotest/manage.py migrate

ENTRYPOINT [ "python", "djangotest/manage.py", "runserver" ]

CMD [ "0.0.0.0:8000" ]
