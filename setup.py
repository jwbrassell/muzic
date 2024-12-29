"""Setup script for initializing the TapForNerd Radio application."""
import os
import sys
import subprocess
import platform
import time
from pathlib import Path
import venv
import shutil

def run_with_sudo(cmd, shell=False):
    """Run a command with sudo if needed."""
    if isinstance(cmd, str):
        cmd_list = cmd.split()
    else:
        cmd_list = cmd

    if platform.system().lower() != "windows":
        if not cmd_list[0].startswith('sudo'):
            cmd_list = ['sudo', '-S'] + cmd_list
    
    try:
        return subprocess.run(cmd_list, check=True, shell=shell)
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        raise

def install_xcode_tools():
    """Install Xcode Command Line Tools on macOS."""
    try:
        # Check if already installed
        subprocess.run(['xcode-select', '-p'], check=True, capture_output=True)
        print("✓ Xcode Command Line Tools already installed")
        return True
    except subprocess.CalledProcessError:
        print("Installing Xcode Command Line Tools...")
        try:
            subprocess.run(['xcode-select', '--install'], check=True)
            # Wait for installation to complete
            while True:
                try:
                    subprocess.run(['xcode-select', '-p'], check=True, capture_output=True)
                    print("✓ Xcode Command Line Tools installed")
                    return True
                except subprocess.CalledProcessError:
                    time.sleep(10)
                    print("Waiting for Xcode Command Line Tools installation...")
        except subprocess.CalledProcessError as e:
            print(f"Failed to install Xcode Command Line Tools: {e}")
            return False

def install_homebrew():
    """Install Homebrew on macOS."""
    try:
        # Check if Homebrew is already installed
        if shutil.which("brew"):
            print("✓ Homebrew already installed")
            return True

        print("Installing Homebrew...")
        
        # Install Xcode Command Line Tools first
        if not install_xcode_tools():
            return False

        # Install Homebrew
        install_cmd = '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
        process = subprocess.Popen(install_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            print(f"Failed to install Homebrew: {stderr.decode()}")
            return False

        # Add Homebrew to PATH
        shell = os.environ.get('SHELL', '/bin/bash')
        if 'zsh' in shell:
            rc_file = os.path.expanduser('~/.zshrc')
        else:
            rc_file = os.path.expanduser('~/.bash_profile')

        brew_path = '/opt/homebrew/bin/brew'
        if os.path.exists(brew_path):
            with open(rc_file, 'a') as f:
                f.write('\n# Add Homebrew to PATH\n')
                f.write('eval "$(/opt/homebrew/bin/brew shellenv)"\n')
            
            # Source the file to update current session
            subprocess.run([shell, '-c', f'source {rc_file}'])
            
        print("✓ Homebrew installed and configured")
        return True
        
    except Exception as e:
        print(f"Error installing Homebrew: {e}")
        return False

def get_package_manager():
    """Determine the system's package manager."""
    system = platform.system().lower()
    if system == "darwin":
        if install_homebrew():
            return "brew"
        return None
    elif system == "linux":
        if shutil.which("apt-get"):
            return "apt-get"
        elif shutil.which("yum"):
            return "yum"
        elif shutil.which("dnf"):
            return "dnf"
    elif system == "windows":
        if shutil.which("choco"):
            return "choco"
        else:
            # Install Chocolatey
            subprocess.run(['powershell', '-Command', 
                'Set-ExecutionPolicy Bypass -Scope Process -Force; ' +
                '[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; ' +
                'iex ((New-Object System.Net.WebClient).DownloadString(\'https://chocolatey.org/install.ps1\'))'])
            return "choco"
    return None

def install_dependencies():
    """Install system dependencies (Redis, FFmpeg)."""
    pkg_mgr = get_package_manager()
    system = platform.system().lower()
    
    if not pkg_mgr:
        print("No supported package manager found.")
        sys.exit(1)
        
    print("Installing system dependencies...")
    
    try:
        if pkg_mgr == "brew":
            # Homebrew doesn't need sudo
            subprocess.run(['brew', 'install', 'redis', 'ffmpeg'])
        elif pkg_mgr == "apt-get":
            run_with_sudo(['apt-get', 'update'])
            run_with_sudo(['apt-get', 'install', '-y', 'redis-server', 'ffmpeg'])
        elif pkg_mgr == "yum" or pkg_mgr == "dnf":
            run_with_sudo([pkg_mgr, 'install', '-y', 'redis', 'ffmpeg'])
        elif pkg_mgr == "choco":
            # Chocolatey needs admin shell, not sudo
            subprocess.run(['choco', 'install', '-y', 'redis-64', 'ffmpeg'])
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        sys.exit(1)

def start_redis():
    """Start Redis server."""
    system = platform.system().lower()
    try:
        if system == "darwin":
            # Homebrew services don't need sudo
            subprocess.run(['brew', 'services', 'start', 'redis'])
        elif system == "linux":
            run_with_sudo(['systemctl', 'start', 'redis'])
        elif system == "windows":
            subprocess.Popen(['redis-server'], 
                           creationflags=subprocess.CREATE_NEW_CONSOLE)
        
        # Wait for Redis to start
        time.sleep(2)
        print("✓ Redis server started")
    except Exception as e:
        print(f"Error starting Redis: {e}")
        sys.exit(1)

def check_python_version():
    """Check if Python version meets requirements."""
    if sys.version_info < (3, 9):
        print("Error: Python 3.9 or higher is required")
        sys.exit(1)

def verify_installation():
    """Verify that all components are installed and running."""
    try:
        # Check FFmpeg first
        subprocess.run(['ffmpeg', '-version'], capture_output=True)
        print("✓ FFmpeg is installed")
        
        # Ensure Redis Python package is installed
        try:
            import redis
        except ImportError:
            print("Installing Redis Python package...")
            pip_path = os.path.join('venv', 'bin', 'pip') if platform.system().lower() != "windows" else os.path.join('venv', 'Scripts', 'pip')
            subprocess.run([pip_path, 'install', 'redis'])
        
        # Check Redis connection
        client = redis.Redis(host='localhost', port=6379, db=0)
        client.ping()
        print("✓ Redis server is running")
        
    except Exception as e:
        print(f"Verification failed: {e}")
        sys.exit(1)

def setup_environment():
    """Set up environment variables."""
    if not os.path.exists('.env'):
        print("Creating .env file from template...")
        with open('.env.example', 'r') as template, open('.env', 'w') as env:
            env.write(template.read())
        print("✓ Created .env file")
    else:
        print("✓ .env file exists")

def create_directories():
    """Create necessary directories."""
    directories = [
        'instance',
        'logs',
        'media/uploads',
        'media/processed',
        'media/archive',
        'reports/temp'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    print("✓ Created required directories")

def initialize_database():
    """Initialize the database."""
    try:
        from app.core.database import Database
        from app.core.config import get_settings
        
        settings = get_settings()
        db = Database(settings.database.path)
        db.initialize_schema('schema.sql')
        print("✓ Initialized database")
    except Exception as e:
        print(f"✗ Failed to initialize database: {e}")
        sys.exit(1)

def setup_virtualenv():
    """Create and activate virtual environment."""
    if not os.path.exists('venv'):
        print("Creating virtual environment...")
        venv.create('venv', with_pip=True)
    
    # Install Python dependencies
    pip_path = os.path.join('venv', 'bin', 'pip') if platform.system().lower() != "windows" else os.path.join('venv', 'Scripts', 'pip')
    subprocess.run([pip_path, 'install', '-r', 'requirements.txt'])
    print("✓ Virtual environment ready")

def start_application():
    """Start the Flask application."""
    try:
        # Set Flask environment variables
        os.environ['FLASK_APP'] = 'app'
        os.environ['FLASK_ENV'] = 'development'
        
        # Get the correct flask path
        flask_path = os.path.join('venv', 'bin', 'flask') if platform.system().lower() != "windows" else os.path.join('venv', 'Scripts', 'flask')
        
        # Start Flask application in a new console
        if platform.system().lower() == "windows":
            subprocess.Popen([flask_path, 'run'], 
                           creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            subprocess.Popen([flask_path, 'run'], 
                           start_new_session=True)
        
        print("✓ Application started at http://localhost:5000")
    except Exception as e:
        print(f"Error starting application: {e}")
        sys.exit(1)

def main():
    """Run the setup process."""
    print("\nTapForNerd Radio Setup\n")
    
    print("Checking Python version...")
    check_python_version()
    
    print("\nSetting up Python environment...")
    setup_virtualenv()
    
    # On macOS, set up Homebrew first
    if platform.system().lower() == "darwin":
        print("\nChecking package manager...")
        if not install_homebrew():
            print("Failed to set up Homebrew. Please install it manually.")
            sys.exit(1)
    
    print("\nInstalling system dependencies...")
    install_dependencies()
    
    print("\nStarting Redis server...")
    start_redis()
    
    print("\nVerifying installation...")
    verify_installation()
    
    print("\nSetting up application...")
    setup_environment()
    create_directories()
    initialize_database()
    
    print("\nStarting application...")
    start_application()
    
    print("\nSetup complete! The application is now running at:")
    print("http://localhost:5000")

if __name__ == '__main__':
    main()
