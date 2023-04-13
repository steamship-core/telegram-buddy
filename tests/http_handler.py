"""Attempts to mimic the lambda_handler class to create a handler that can be used with HTTP posts."""

import importlib
import inspect
import json
import logging
import sys
import traceback
import uuid
from http import HTTPStatus
from os import environ
from typing import Callable, Dict, Type

from fluent import asynchandler as fluenthandler
from fluent.handler import FluentRecordFormatter

from steamship import Configuration
from steamship.base import SteamshipError
from steamship.client import Steamship
from steamship.data.workspace import SignedUrl
from steamship.invocable import Invocable, InvocableRequest, InvocableResponse, InvocationContext
from steamship.invocable.lambda_handler import safely_find_invocable_class, encode_exception, internal_handler
from steamship.utils.signed_urls import upload_to_signed_url


def handler(internal_handler, event: Dict, _: Dict = None) -> dict:  # noqa: C901
    logging_config = event.get("loggingConfig")
    logging_host = None
    logging_handler = None
    logging_port = None

    if logging_config is not None:
        # Unlike the Lambda version, we default to no logging config but attempt to wire it up if available.
        logging_host = logging_config.get("loggingHost")
        logging_port = logging_config.get("loggingPort")

        logging.basicConfig(level=logging.INFO)
        logging_handler = None

    use_fluent_logging = logging_config and logging_port and logging_host != "none" and logging_port != "none"

    invocation_context_dict = event.get("invocationContext")
    if invocation_context_dict is None:
        return InvocableResponse.error(
            code=HTTPStatus.INTERNAL_SERVER_ERROR,
            message="Plugin/App handler did not receive an invocation context.",
        ).dict(by_alias=True)

    invocation_context = InvocationContext.parse_obj(invocation_context_dict)

    # At the point in the code, the root log level seems to default to WARNING unless set to INFO, even with
    # the BasicConfig setting to INFO above.
    logging.root.setLevel(logging.INFO)

    # These log statements intentionally go to the logging handler pre-remote attachment, to debug logging configuration issues
    logging.info(f"Logging host: {logging_host} Logging port: {logging_port}")
    logging.info(f"Invocation context: {invocation_context}")

    if use_fluent_logging:
        # Configure remote logging
        custom_format = {
            "level": "%(levelname)s",
            "host": "%(hostname)s",
            "where": "%(module)s.%(filename)s.%(funcName)s:%(lineno)s",
            "type": "%(levelname)s",
            "stack_trace": "%(exc_text)s",
            "component": "package-plugin-lambda",
            "userId": invocation_context.user_id,
            "workspaceId": invocation_context.workspace_id,
            "tenantId": invocation_context.tenant_id,
            "invocableHandle": invocation_context.invocable_handle,
            "invocableVersionHandle": invocation_context.invocable_version_handle,
            "invocableInstanceHandle": invocation_context.invocable_instance_handle,
            "invocableType": invocation_context.invocable_type,
            "invocableOwnerId": invocation_context.invocable_owner_id,
            "path": event.get("invocation", {}).get("invocationPath"),
        }

        logging_handler = fluenthandler.FluentHandler(
            "steamship.deployed_lambda",
            host=logging_host,
            port=logging_port,
            nanosecond_precision=True,
            msgpack_kwargs={"default": encode_exception},
        )

        # Without explicit instruction, the fluent handler defaults to UNSET. We want to make sure it is INFO.
        logging_handler.setLevel(logging.INFO)

        formatter = FluentRecordFormatter(custom_format)
        logging_handler.setFormatter(formatter)
        # The below should make it so calls to logging.info etc are also routed to the remote logger
        logging.root.addHandler(logging_handler)
    else:
        pass

    try:
        # Config will accept `workspace_id` as passed from the Steamship Engine, whereas the `Steamship`
        # class itself is limited to accepting `workspace` (`config.workspace_handle`) since that is the manner
        # of interaction ideal for developers.
        config = Configuration(**event.get("clientConfig", {}))
        client = Steamship(config=config, trust_workspace_config=True)
    except SteamshipError as se:
        logging.exception(se)
        return InvocableResponse.from_obj(se).dict(by_alias=True)
    except Exception as ex:
        logging.exception(ex)
        return InvocableResponse.error(
            code=HTTPStatus.INTERNAL_SERVER_ERROR,
            message="Plugin/App handler was unable to create Steamship client.",
            exception=ex,
        ).dict(by_alias=True)
    logging.info(f"Localstack hostname: {environ.get('LOCALSTACK_HOSTNAME')}.")
    response = internal_handler(event, client, invocation_context)

    result = response.dict(by_alias=True, exclude={"client"})
    # When created with data > 4MB, data is uploaded to a bucket.
    # This is a very ugly way to get the deep size of this object
    data = json.dumps(result.get("data", None)).encode("UTF-8")
    data_size = sys.getsizeof(data)
    logging.info(f"Response data size {data_size}")
    if data_size > 4e6 and invocation_context.invocable_type == "plugin":
        logging.info("Response data size >4MB, must upload to bucket")

        filepath = str(uuid.uuid4())
        signed_url = (
            client.get_workspace()
            .create_signed_url(
                SignedUrl.Request(
                    bucket=SignedUrl.Bucket.PLUGIN_DATA,
                    filepath=filepath,
                    operation=SignedUrl.Operation.WRITE,
                )
            )
            .signed_url
        )

        logging.info(f"Got signed url for writing: {signed_url}")

        upload_to_signed_url(signed_url, data)

        # Now remove raw data and replace with bucket
        del result["data"]
        result["dataBucket"] = SignedUrl.Bucket.PLUGIN_DATA.value
        result["dataFilepath"] = filepath

    if logging_handler is not None:
        logging_handler.close()

    return result



def create_safe_handler(known_invocable_for_testing: Type[Invocable] = None):
    # Get the invocable class
    if known_invocable_for_testing is not None:
        invocable_getter = lambda: known_invocable_for_testing  # noqa: E731
    else:
        invocable_getter = safely_find_invocable_class

    bound_internal_handler = lambda event, client, context: internal_handler(  # noqa: E731
        invocable_getter, event, client, context
    )
    return lambda event, context=None: handler(bound_internal_handler, event, context)

