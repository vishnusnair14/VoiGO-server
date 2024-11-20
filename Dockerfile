# FROM python:3.12.3-slim
#
# RUN apt-get update && apt-get install -y virtualenv
#
# WORKDIR /app
#
# RUN virtualenv env
#
# COPY requirements.txt /app
#
# RUN /app/env/bin/pip install -r requirements.txt
#
# COPY . /app
#
# EXPOSE 80
#
# RUN /app/env/bin/python manage.py migrate
#
# COPY entrypoint.sh /app/entrypoint.sh
# RUN chmod +x /app/entrypoint.sh
#
# CMD ["/app/entrypoint.sh"]
#
# # CMD ["/app/env/bin/python", "manage.py", "runserver", "0.0.0.0:8000"]
#



# Use an official Python runtime as a base image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1


# Set the working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Django project files
COPY . /app/

# Expose the port on which the app runs
EXPOSE 8000

# Command to run the application
CMD ["gunicorn", "VoiGO.wsgi:application", "--bind", "0.0.0.0:8000"]
CMD ["/app/env/bin/python", "manage.py", "runserver", "0.0.0.0:8000"]
