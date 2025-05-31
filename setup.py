from distutils.core import setup

setup(
    name="padbox",
    version="1.1.0",
    packages=["padbox"],
    package_dir={"": "src"},
    url="",
    license="",
    author="juleaume",
    author_email="",
    description="",
    install_requires=["pyserial==3.5", "pyudev==0.24.3"],
    entry_points={"console_scripts": ["padbox = padbox.__main__:main"]},
)
