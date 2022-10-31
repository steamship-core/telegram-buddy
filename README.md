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
ship package:instance:create --defaultname="Beautiful"
```

That keyword argument above is part of the required configuration.
You can see where it's defined in both the [steamship.json](steamship.json) file and in the [src/api.py](src/api.py) file.

Finally, invoke a method!

### Invoke your Package from Python

Let's try invoking your package from Python.

Just type:

```python
from steamship import Steamship

# TODO: Replace with your package handle below
instance = Steamship.use("yourname-demo", "instance-name", config={
    "defaultname": "Beautiful"
})
                         
print(instance.invoke("greeting"))
```

## Extending on your own

Steamship packages run on a cloud stack designed for Language AI.

You can import files, parse and tag them, query over them, and return custom results. 

Full documentation for developers is available at [https://docs.steamship.com/packages/developing](https://docs.steamship.com/packages/developing).