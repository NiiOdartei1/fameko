#!/usr/bin/env python3
# start_routing.py - Smart routing service launcher
import os
import sys
import time
import subprocess
import logging
from routing_config import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
LOG = logging.getLogger(__name__)

def check_port_available(port):
    """Check if port is available"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('localhost', port))
            return True
        except OSError:
            return False

def start_service(service_file):
    """Start the specified routing service"""
    if not os.path.exists(service_file):
        LOG.error(f"Service file {service_file} not found!")
        return None
    
    LOG.info(f"Starting {service_file}...")
    LOG.info(config.get_startup_message())
    
    try:
        # Set environment variables
        env = os.environ.copy()
        env.update({
            'ROUTING_MODE': config.mode.value,
            'ROUTING_PORT': str(config.port),
            'ENABLE_SIMPLE_ROUTING': str(config.enable_simple_routing).lower(),
            'ENABLE_WEBSOCKETS': str(config.enable_websockets).lower(),
            'ROUTE_CACHE_TTL': str(config.cache_ttl),
            'ROUTE_CACHE_MAX': str(config.cache_max),
            'LOCATION_RETENTION': str(config.location_retention),
            'COORD_DECIMALS': str(config.coord_decimals)
        })
        
        # Start the service
        process = subprocess.Popen([
            sys.executable, "-u", service_file
        ], env=env, cwd=os.getcwd())
        
        return process
    except Exception as e:
        LOG.error(f"Failed to start {service_file}: {e}")
        return None

def main():
    """Main launcher logic"""
    LOG.info("Routing Service Launcher")
    LOG.info("=" * 50)
    
    # Check if port is available
    if not check_port_available(config.port):
        LOG.warning(f"Port {config.port} is already in use!")
        response = input("Kill existing process and continue? (y/n): ").lower().strip()
        if response == 'y':
            try:
                import psutil
                for proc in psutil.process_iter(['pid', 'name', 'connections']):
                    try:
                        for conn in proc.info['connections'] or []:
                            if conn.laddr.port == config.port:
                                LOG.info(f"Killing process {proc.info['pid']} ({proc.info['name']})")
                                proc.kill()
                                time.sleep(1)
                                break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            except ImportError:
                LOG.error("psutil not installed. Please kill the process manually.")
                return
        else:
            LOG.info("Please free up the port and try again.")
            return
    
    # Determine which service to start
    service_file = config.get_service_file()
    
    # Start the service
    process = start_service(service_file)
    
    if process:
        LOG.info(f"Routing service started successfully on port {config.port}")
        LOG.info(f"Service URL: http://{config.host}:{config.port}")
        LOG.info(f"WebSocket endpoints: ws://{config.host}:{config.port}/ws/driver/{{driver_id}}")
        LOG.info(f"Monitor endpoint: ws://{config.host}:{config.port}/ws/monitor")
        
        try:
            # Wait for the process
            process.wait()
        except KeyboardInterrupt:
            LOG.info("Shutting down routing service...")
            process.terminate()
            process.wait()
            LOG.info("Service stopped.")
    else:
        LOG.error("Failed to start routing service")

if __name__ == "__main__":
    main()
