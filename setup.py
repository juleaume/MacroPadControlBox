from distutils.core import setup

setup(
    name="padbox",
    version="0.1.0",
    packages=["padbox"],
    package_dir={"": "src"},
    url="",
    license="",
    author="juleaume",
    author_email="",
    description="",
    install_requires=["pyserial==3.5"],
    entry_points={"console_scripts": ["padbox = padbox.__main__:main"]},
)
