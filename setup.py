import os


# this should be run with sudo
# installs necessary apts and pip packages
def install_pack(package_name):
    os.system(f"sudo apt-get install -y {package_name}")
def install_pip_package(package_name):
    try:
        os.system(f"pip3 install {package_name}")
    except Exception as e:
        os.system(f'sudo apt-get install -y python3-{package_name}')

def install_display_drivers(url):
    os.system(f"git clone")

def main():
    necessary_packages = [
        "iw",
        "wireless-tools",
        "python3-pip",
        "python3-pil",
        "python3-rpi.gpio",
        "python3-gpiozero",
        "aircrack-ng",
        "mdk4",
        "git"
    ]
    nessesary_pip_packages = [
        "Pillow",
        "gpiozero",
        "scapy"
    ]
    git_repo_drivers = [
        'https://github.com/waveshare/e-Paper.git'
    ]
    
    for package in necessary_packages:
        install_pack(package)

    for pip_package in nessesary_pip_packages:
        install_pip_package(pip_package)

    for git_repo in git_repo_drivers:
        install_display_drivers(git_repo)

if __name__ == "__main__":
    main()