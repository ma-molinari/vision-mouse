from setuptools import find_packages, setup


# Compatibility shim for older pip/setuptools versions bundled with Xcode Python.
setup(
    name="vision-mouse",
    version="0.1.0",
    description="Local hand-tracking mouse control pipeline for macOS.",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    package_data={"vision_mouse": ["resources/models/*.task"]},
    install_requires=[
        "mediapipe>=0.10.0",
        "opencv-python>=4.10.0",
        "pynput>=1.7.0",
    ],
    python_requires=">=3.9",
)
