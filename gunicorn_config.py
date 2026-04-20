import multiprocessing

# Worker class for Flask-SocketIO with gevent
worker_class = 'gevent'
workers = multiprocessing.cpu_count() * 2 + 1

# WebSocket support
worker_connections = 1000

# Timeout settings
timeout = 120
keepalive = 2

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Process naming
proc_name = 'fameko'

# Bind address (Render sets this via PORT)
bind = '0.0.0.0:10000'
