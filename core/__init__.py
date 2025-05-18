import platform
import os
import subprocess

def start():
    if platform.system() == 'Windows':
        bin_path = os.path.join(os.getcwd(), 'bin')
        try:
            p = subprocess.Popen(['ciadpiwin', '--fake', '-1', '--ttl', '10', '--auto=ssl_err', '--fake', '-1', '--ttl', '5', '--hosts', './lists/list-discord.txt'], cwd=bin_path, shell=True)
            p.wait()
        except FileNotFoundError:
            print(f"Error: ByeDPI executable not found in {bin_path}")
        except Exception as e:
            print(f"Error running ByeDPI: {str(e)}")
    elif platform.system() == 'Linux':
        bin_path = os.path.join(os.getcwd(), 'bin')
        chmod = subprocess.Popen(['chmod', 'ugo+x', 'ciadpil'], cwd=bin_path, shell=True)
        chmod.wait()
        try:
            p = subprocess.Popen(['ciadpil', '--fake', '-1', '--ttl', '10', '--auto=ssl_err', '--fake', '-1', '--ttl', '5', '--hosts', ''], cwd=bin_path, shell=True)
            p.wait()
        except FileNotFoundError:
            print(f"Error: ByeDPI executable not found in {bin_path}")
        except Exception as e:
            print(f"Error running ByeDPI: {str(e)}")
    else:
        print('Error: Your OS is not supported')