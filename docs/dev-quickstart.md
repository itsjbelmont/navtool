# Development Quickstart

This project uses python for the underlying control utility.

From the `navtool/` root directory: `source .venv/bin/activate`

**NOTES:** 

* _This guide assumes your CWD is the root directory of the navtool repository_
* You must have python3 installed on your system

## Get Started With The Dev Env

_**NOTE:**_ For now the dev version and the stable installs both use the same directory path for the database file. This will likely change soon.

1. Create the `.venv/` virtual env folder: `python3 -m venv .venv`

1. Activate the virtual env: `source .venv/bin/activate`

    * Your shell prompt should now be pre-pended with a `(.venv)` prefix.

    * Validate that python3 now calls into the `.venv/`'s python version: `which python3` -> `<NAVTOOL>/navtool/.venv/bin/python3`

    * Validate that pip now calls into the `.venv/`'s python version: `which pip` -> `<NAVTOOL>/navtool/.venv/bin/pip`

1. Update your virtual python's pip version: `pip install --upgrade pip`

1. Install navtool in development mode (so the tool updates when the source code updates), and include the development dependencies: `pip install -e ".[dev]"`

    * If you dont want to use formatting tools or run unit tests you may be able to just run `pip install -e .` without the development dependencies.

1. Validate that navtool is installed in the `.venv`: `which navtool` -> `<NAVTOOL>/navtool/.venv/bin/navtool`

    * **Important:** If you have already installed system wide via `pipx install .` you may need to run `pipx uninstall navtool` to uninstall so that you running navtool does not clash between installed stable/dev versions. Running `which navtool` should validate that you are using navtool out of the dev environment. If `which navtool` points to something other than `.venv/bin/navtool` then you will need to uninstall via `pipx uninstall navtool`

    * **IMPORTANT:** If `which navtool` points to something other than `<NAVTOOL>/.venv/bin/navtool` it is likely because you have already installed navtool to your system via `pipx install .`. In this situation any calls to `navtool` will NOT find your dev changes. Before starting development run `pipx uninstall navtool` to uninstall the system version and then re-install the system version after finishing development.

1. As long as you installed the `[dev]` dependencies then you can validate behavior by running the unit tests: `pytest`