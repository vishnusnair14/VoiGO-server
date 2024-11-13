import subprocess

python_path = 'D:\\VoiGo\\VoiGo-Server\\venv\\Scripts\\python.exe'

manage_py_path = 'D:\\VoiGo\\VoiGo-Server\\VoiGO\\manage.py'

# Run the management command to reset WebSocket clients
subprocess.run([python_path, manage_py_path, 'reset_ws_clients'])

# Start the Django server
subprocess.run([python_path, manage_py_path, 'runserver', 'localhost:8000'])
