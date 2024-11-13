#!/bin/sh


# Run migrations
/workdir/env/bin/python manage.py migrate

# Start the Huey consumer
/workdir/env/bin/python manage.py run_huey &

# Start Django server
/workdir/env/bin/python manage.py runserver 0.0.0.0:8000


# Keep the script running
wait
