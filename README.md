# Steamship Package Template 

This repository contains a starter template showing you how to develop and use a package.

## Quick Start

Deploy and use this package in under a minute!

First, make sure you have the Steamship CLI installed:

```bash
npm install -g steamship && ship login
```

Next, provide a handle for this project in `steamship.json`. Package handles must be globally unique. We recommend `YOURNAME-demo`.

```json
{
  "handle": "yourname-demo",
}
```

Then, deploy your package!

```bash
ship deploy
```

Wait about 30 seconds after deployment finishes for the package to become available.

### Invoke your Package from the CLI

Then, create an instance.

```bash
ship package:instance:create --default_name="Beautiful"
```

That keyword argument above is part of the required configuration.
You can see where it's defined in both the [steamship.json](steamship.json) file and in the [src/api.py](src/api.py) file.

The response will let you know what your **Instance Handle** is.

Finally, invoke a method!

```bash
ship package:instance:invoke --instance="INSTANCE_HANDLE" --method="greet"    
```

### Invoke your Package from Python

It's more likely you'll want to call your package from software you're writing. Let's try from Python.

Create a new instance and invoke it with:

```python
from steamship import Steamship

# TODO: Replace with your package and instance handle below
instance = Steamship.use("PACKAGE_HANDLE", "INSTANCE_HANDLE", config={
    "default_name": "Beautiful"
})

print(instance.invoke("greet"))
```

## Extending on your own

Steamship packages run on a cloud stack designed for Language AI.

You can import files, parse and tag them, query over them, and return custom results. 

Full documentation for developers is available at [https://docs.steamship.com/packages/developing](https://docs.steamship.com/packages/developing).