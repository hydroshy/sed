# Environment Setup Tutorial

This guide will help you set up your development environment.

## Step 1: Install Conda Miniforge

1. Download Miniforge from the [official site](https://conda-forge.org/download/).
2. Run the installer in your terminal:
    ```bash
    bash Miniforge3-$(uname)-$(uname -m).sh
    ```

## Step 2: Create a Conda Environment

1. Create a new environment named `sedenv` with Python 3.11:
    ```bash
    conda create --name sedenv python=3.11 -y
    ```

## Step 3: Install System Dependencies

For Ubuntu/Debian systems, install the required packages:
```bash
sudo apt install -y libcamera-dev ffmpeg libcap-dev
sudo apt install qt5-qmake qtbase5-dev
```

```bash
sudo apt install -y libkms++-dev libfmt-dev libdrm-dev
pip install rpi-kms
```
```bash
sudo apt install -y libxcb-xinerama0 libxcb-xfixes0 libxcb-shape0 libxcb-randr0 libxcb-image0 libxcb-keysyms1 libxcb-icccm4 libxcb-render-util0
```
Your environment is now ready!