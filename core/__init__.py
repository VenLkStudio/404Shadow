import platform
import os
import subprocess
import core.configs
import threading
from pythonping import ping
import time
import socket
import json
from collections import defaultdict

class ProcessThread(threading.Thread):
    def __init__(self, cmd, cwd=None, shell=False):
        super().__init__()
        self.cmd = cmd
        self.cwd = cwd
        self.shell = shell
        self.process = None
        self._stop_event = threading.Event()

    def run(self):
        self.process = subprocess.Popen(self.cmd, cwd=self.cwd, shell=self.shell)
        while not self._stop_event.is_set() and self.process.poll() is None:
            time.sleep(0.1)

    def stop(self):
        self._stop_event.set()
        if self.process and self.process.poll() is None:
            self.process.terminate()

def start(config=None):
    if config is None:
        try:
            with open('settings.json', 'r') as f:
                settings = json.load(f)
                if settings.get('best_configurations'):
                    best_config = settings['best_configurations'][0]
                    config = best_config['config']
                    line_num = best_config['line_number']
                    print(f"Using best configuration from settings.json (line {line_num}): {config}")
                else:
                    print("No configurations found in settings.json")
                    return
        except FileNotFoundError:
            print("settings.json not found. Please run ping_sites() first to generate configurations.")
            return
        except json.JSONDecodeError:
            print("Error reading settings.json. File may be corrupted.")
            return
        except Exception as e:
            print(f"Error loading settings: {e}")
            return

    if platform.system() == 'Windows':
        bin_path = os.path.join(os.getcwd(), 'bin')
        try:
            t = ProcessThread(cmd=['ciadpiwin', f'{config}', '--ipset=./lists/ipset.txt', '--hosts=./lists/hosts.txt'], cwd=bin_path, shell=True)
            t.start()
        except FileNotFoundError:
            print(f"Error: ByeDPI executable not found in {bin_path}")
        except Exception as e:
            print(f"Error running ByeDPI: {str(e)}")
    elif platform.system() == 'Linux':
        bin_path = os.path.join(os.getcwd(), 'bin')
        chmod = subprocess.Popen(['chmod a+x ciadpil'], cwd=bin_path, shell=True)
        chmod.wait()
        try:
            t = ProcessThread(cmd=['./ciadpil', f'{config}', '--ipset=./lists/ipset.txt', '--hosts=./lists/hosts.txt'], cwd=bin_path, shell=True)
            t.start()
        except FileNotFoundError:
            print(f"Error: ByeDPI executable not found in {bin_path}")
        except Exception as e:
            print(f"Error running ByeDPI: {str(e)}")
    else:
        print('Error: Your OS is not supported')

def createConfig():
    f = open('../bin/')

def start_test(id):
    print(core.configs.get_config(id))

def ping_sites(stop_event=None):
    bin_path = os.path.join(os.getcwd(), 'bin')
    config_results = defaultdict(int)
    config_lines = {}
    
    if platform.system() == 'Windows':
        with open('bin/proxy_cmds.txt', 'r') as proxy_file:
            for line_num, cmd in enumerate(proxy_file, 1):
                if stop_event and stop_event.is_set():
                    print("Testing stopped by user")
                    return
                    
                cmd = cmd.strip()
                if not cmd:
                    continue
                
                print(f"\nTesting configuration (line {line_num}): {cmd}")
                successful_pings = 0
                config_lines[cmd] = line_num
                    
                t = ProcessThread(cmd=['ciadpiwin', f'{cmd}', '--ipset=./lists/ipset.txt', '--hosts=./lists/hosts.txt'], 
                                cwd=bin_path, shell=True)
                t.start()
                
                try:
                    with open('bin/test_sites.txt', 'r') as sites_file:
                        for site in sites_file:
                            if stop_event and stop_event.is_set():
                                t.stop()
                                print("Testing stopped by user")
                                return
                                
                            site = site.strip()
                            if not site:
                                continue
                                
                            print(f"Testing {site}")
                            try:
                                ip = socket.gethostbyname(site)
                                ping(ip, verbose=False)
                                successful_pings += 1
                            except Exception as e:
                                print(f'Ping error for {site}: {e}')
                finally:
                    t.stop()
                
                config_results[cmd] = successful_pings
                print(f"Configuration (line {line_num}): {successful_pings} successful pings")
                
                # If we found a configuration with 25 successful pings, save it and exit
                if successful_pings >= 25:
                    settings = {
                        "best_configurations": [{
                            "config": cmd,
                            "successful_pings": successful_pings,
                            "line_number": line_num
                        }],
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    try:
                        with open('settings.json', 'w') as f:
                            json.dump(settings, f, indent=4)
                        print("\nFound configuration with 25 successful pings! Results saved to settings.json")
                    except Exception as e:
                        print(f"Error saving to settings.json: {e}")
                    return
                
    elif platform.system() == 'Linux':
        with open('bin/proxy_cmds.txt', 'r') as proxy_file:
            for line_num, cmd in enumerate(proxy_file, 1):
                if stop_event and stop_event.is_set():
                    print("Testing stopped by user")
                    return
                    
                cmd = cmd.strip()
                if not cmd:
                    continue
                
                print(f"\nTesting configuration (line {line_num}): {cmd}")
                successful_pings = 0
                config_lines[cmd] = line_num
                    
                t = ProcessThread(cmd=['./ciadpil', f'{cmd}', '--ipset=./lists/ipset.txt', '--hosts=./lists/hosts.txt'], cwd=bin_path, shell=True)
                t.start()
                
                try:
                    with open('bin/test_sites.txt', 'r') as sites_file:
                        for site in sites_file:
                            if stop_event and stop_event.is_set():
                                t.stop()
                                print("Testing stopped by user")
                                return
                                
                            site = site.strip()
                            if not site:
                                continue
                                
                            print(f"Testing {site}")
                            try:
                                ping(site, verbose=True)
                                successful_pings += 1
                            except Exception as e:
                                print(f"Ping error for {site}: {e}")
                finally:
                    t.stop()
                
                config_results[cmd] = successful_pings
                print(f"Configuration (line {line_num}): {successful_pings} successful pings")
                
                # If we found a configuration with 25 successful pings, save it and exit
                if successful_pings >= 25:
                    settings = {
                        "best_configurations": [{
                            "config": cmd,
                            "successful_pings": successful_pings,
                            "line_number": line_num
                        }],
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    try:
                        with open('settings.json', 'w') as f:
                            json.dump(settings, f, indent=4)
                        print("\nFound configuration with 25 successful pings! Results saved to settings.json")
                    except Exception as e:
                        print(f"Error saving to settings.json: {e}")
                    return
    else:
        print('Error: Your OS is not supported')
        return

    # If no configuration reached 25 pings, save the best one
    sorted_configs = sorted(config_results.items(), key=lambda x: x[1], reverse=True)
    if sorted_configs:
        best_config = sorted_configs[0]
        settings = {
            "best_configurations": [{
                "config": best_config[0],
                "successful_pings": best_config[1],
                "line_number": config_lines[best_config[0]]
            }],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        try:
            with open('settings.json', 'w') as f:
                json.dump(settings, f, indent=4)
            print("\nResults saved to settings.json")
        except Exception as e:
            print(f"Error saving to settings.json: {e}")