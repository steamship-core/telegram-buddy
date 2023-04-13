import json
from typing import Optional
import logging
from steamship import Steamship, Task
from steamship.invocable import InvocationContext, Invocable, InvocableRequest, Invocation, LoggingConfig
from steamship.invocable.lambda_handler import create_safe_handler
from steamship.utils.url import Verb
from pyngrok import ngrok
from http import server
from socketserver import TCPServer

def use_local(client: Steamship, package_class, context: Optional[InvocationContext] = None, config: Optional[dict] = None):
    def add_method(package_class, method, method_name=None):
        setattr(package_class, method_name or method.__name__, method)

    def handle_kwargs(kwargs: Optional[dict] = None):
        if kwargs is not None and "wait_on_tasks" in kwargs:
            if kwargs["wait_on_tasks"] is not None:
                for task in kwargs["wait_on_tasks"]:
                    # It might not be of type Task if the invocation was something we've monkeypatched.
                    if type(task) == Task:
                        task.wait()
            kwargs.pop("wait_on_tasks")
        return kwargs

    def invoke(self, path: str, verb: Verb = Verb.POST, **kwargs):
        # Note: the correct impl would inspect the fn lookup for the fn with the right verb.
        path = path.rstrip("/").lstrip("/")
        fn = getattr(self, path)
        new_kwargs = handle_kwargs(kwargs)
        print(f"Patched invocation of self.invoke('{path}', {kwargs})")
        res = fn(**new_kwargs)
        if hasattr(res, 'dict'):
            return getattr(res, 'dict')()
        # TODO: Handle if they returned a InvocationResponse object
        return res

    def invoke_later(self, path: str, verb: Verb = Verb.POST, **kwargs):
        # Note: the correct impl would inspect the fn lookup for the fn with the right verb.
        path = path.rstrip("/").lstrip("/")
        fn = getattr(self, path)
        new_kwargs = handle_kwargs(kwargs)
        invoke_later_args = new_kwargs.get("arguments", {}) # Specific to invoke_later
        print(f"Patched invocation of self.invoke_later('{path}', {kwargs})")
        return fn(**invoke_later_args)

    add_method(package_class, invoke)
    add_method(package_class, invoke_later)

    if not context:
        context = InvocationContext()

    if not context.workspace_id:
        context.workspace_id = client.config.workspace_id
    if not context.invocable_handle:
        context.invocable_handle = f"{package_class}"
    if not context.invocable_type:
        context.invocable_type = "package"

    obj = package_class(
        client=client,
        context=context,
        config=config
    )

    return obj

def make_handler(invocable: Invocable, client: Steamship, context: InvocationContext):
    handler = create_safe_handler(invocable)

    class LocalHttpHandler(server.SimpleHTTPRequestHandler):
        def _set_response(self):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

        def do_GET(self):
            logging.info("GET request,\nPath: %s\nHeaders:\n%s\n", str(self.path), str(self.headers))
            self._set_response()
            self.wfile.write("GET request for {}".format(self.path).encode('utf-8'))

        def do_POST(self):
            content_length = int(self.headers['Content-Length']) # <--- Gets the size of data
            post_data = self.rfile.read(content_length) # <--- Gets the data itself
            try:
                data_str = post_data.decode('utf8')
                post_json = json.loads(data_str)

                invocation = Invocation(
                    http_verb = "POST",
                    invocation_path = self.path,
                    arguments = post_json
                )
                request = InvocableRequest(
                    client_config = client.config,
                    invocation = invocation,
                    logging_config = LoggingConfig(logging_host=None, logging_port=None),
                    invocation_context = context
                )

                resp = handler(request.dict())
                print(resp)

                logging.info("POST request,\nPath: %s\nHeaders:\n%s\n\nBody:\n%s\n",
                        str(self.path), str(self.headers), post_data.decode('utf-8'))
                self._set_response()
                self.wfile.write("POST request for {}".format(self.path).encode('utf-8'))
            except Exception as e:
                print(e)
                self._set_response()
                self.wfile.write("POST request for {}".format(self.path).encode('utf-8'))

    return LocalHttpHandler

def use_local_with_ngrok(client: Steamship, package_class, config: Optional[dict] = None, port: int = 8080):
    """Configures a local-host compatible instance and wires an HTTP endpoint up to it."""
    # Open a HTTP tunnel on the default port 80
    # <NgrokTunnel: "http://<public_sub>.ngrok.io" -> "http://localhost:80">
    http_tunnel = ngrok.connect(port, bind_tls=True)

    public_url = http_tunnel.public_url
    print(f"🚢 Development Hosting 🚢")
    print(f"URL: {public_url}")
    print(f"Client Auth: Hardcoded")

    context = InvocationContext(
        invocable_url=f"{public_url}/"
    )

    instance = use_local(client, package_class, context=context, config=config)

    httpd = TCPServer(("", port), make_handler(instance, client, context))

    print(f"Running __instance_init__:")
    instance.instance_init()

    print(f"Now serving..")
    httpd.serve_forever()

