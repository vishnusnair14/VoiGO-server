#!/bin/sh


# Run migrations
/app/env/bin/python manage.py migrate

# Start the Huey consumer
/app/env/bin/python manage.py run_huey &

# Start Django server
/app/env/bin/python manage.py runserver 0.0.0.0:80


# Keep the script running
wait
