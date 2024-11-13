FROM python:3.12.3-slim

RUN apt-get update && apt-get install -y virtualenv

WORKDIR /workdir

RUN virtualenv env

COPY requirements.txt /workdir

RUN /workdir/env/bin/pip install -r requirements.txt

COPY . /workdir

EXPOSE 8000

RUN /workdir/env/bin/python manage.py migrate

COPY entrypoint.sh /workdir/entrypoint.sh
RUN chmod +x /workdir/entrypoint.sh

CMD ["/workdir/entrypoint.sh"]

# CMD ["/workdir/env/bin/python", "manage.py", "runserver", "0.0.0.0:8000"]

