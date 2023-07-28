# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Security grpc interface."""

import asyncio
import logging
from typing import AsyncGenerator
from typing import AsyncIterator

from floss.pandora.floss import adapter_client
from floss.pandora.floss import floss_enums
from floss.pandora.floss import utils
from floss.pandora.server import bluetooth as bluetooth_module
from google.protobuf import any_pb2
from google.protobuf import empty_pb2
from google.protobuf import wrappers_pb2
import grpc
from pandora import host_pb2
from pandora import security_grpc_aio
from pandora import security_pb2


class SecurityService(security_grpc_aio.SecurityServicer):
    """Service to trigger Bluetooth Host security pairing procedures.

    This class implements the Pandora bluetooth test interfaces,
    where the meta class definition is automatically generated by the protobuf.
    The interface definition can be found in:
    https://cs.android.com/android/platform/superproject/+/main:external
    /pandora/bt-test-interfaces/pandora/security.proto
    """

    def __init__(self, server: grpc.aio.Server, bluetooth: bluetooth_module.Bluetooth):
        self.server = server
        self.bluetooth = bluetooth

    async def OnPairing(self, request: AsyncIterator[security_pb2.PairingEventAnswer],
                        context: grpc.ServicerContext) -> AsyncGenerator[security_pb2.PairingEvent, None]:

        class PairingObserver(adapter_client.BluetoothCallbacks):
            """Observer to observe all pairing events."""

            def __init__(self, loop: asyncio.AbstractEventLoop, task):
                self.loop = loop
                self.task = task

            @utils.glib_callback()
            def on_ssp_request(self, remote_device, class_of_device, variant, passkey):
                address, name = remote_device

                result = (address, name, class_of_device, variant, passkey)
                asyncio.run_coroutine_threadsafe(self.task['pairing_events'].put(result), self.loop)

        async def streaming_answers(self):
            while True:
                pairing_answer = await utils.anext(self.bluetooth.pairing_answers)
                answer = pairing_answer.WhichOneof('answer')
                address = utils.address_from(pairing_answer.event.connection.cookie.value)

                logging.info(f'pairing_answer: {pairing_answer} address: {address}')

                if answer == 'confirm':
                    self.bluetooth.set_pairing_confirmation(address, True)
                elif answer == 'passkey':
                    pass  # TODO: b/289480188 - Supports this method.
                elif answer == 'pin':
                    pass  # TODO: b/289480188 - Supports this method.

        observers = []
        try:
            self.bluetooth.pairing_events = asyncio.Queue()
            observer = PairingObserver(asyncio.get_running_loop(), {'pairing_events': self.bluetooth.pairing_events})
            name = utils.create_observer_name(observer)
            self.bluetooth.adapter_client.register_callback_observer(name, observer)
            observers.append((name, observer))

            self.bluetooth.pairing_answers = request
            streaming_answers_task = asyncio.create_task(streaming_answers(self))
            await streaming_answers_task

            while True:
                address, name, _, variant, passkey = await self.bluetooth.pairing_events.get()

                event = security_pb2.PairingEvent()
                event.connection.CopyFrom(host_pb2.Connection(cookie=any_pb2.Any(value=utils.address_to(address))))

                if variant == floss_enums.SspVariant.PASSKEY_CONFIRMATION:
                    event.numeric_comparison = passkey
                elif variant == floss_enums.SspVariant.PASSKEY_ENTRY:
                    event.passkey_entry_request.CopyFrom(empty_pb2.Empty())
                elif variant == floss_enums.SspVariant.CONSENT:
                    event.just_works.CopyFrom(empty_pb2.Empty())
                elif variant == floss_enums.SspVariant.PASSKEY_NOTIFICATION:
                    event.passkey_entry_notification.CopyFrom(passkey)
                yield event
        finally:
            streaming_answers_task.cancel()
            for name, observer in observers:
                self.bluetooth.adapter_client.unregister_callback_observer(name, observer)

            self.bluetooth.pairing_events = None
            self.bluetooth.pairing_answers = None

    async def Secure(self, request: security_pb2.SecureRequest,
                     context: grpc.ServicerContext) -> security_pb2.SecureResponse:
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)  # type: ignore
        context.set_details('Method not implemented!')  # type: ignore
        raise NotImplementedError('Method not implemented!')

    async def WaitSecurity(self, request: security_pb2.WaitSecurityRequest,
                           context: grpc.ServicerContext) -> security_pb2.WaitSecurityResponse:
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)  # type: ignore
        context.set_details('Method not implemented!')  # type: ignore
        raise NotImplementedError('Method not implemented!')


class SecurityStorageService(security_grpc_aio.SecurityStorageServicer):
    """Service to trigger Bluetooth Host security persistent storage procedures.

    This class implements the Pandora bluetooth test interfaces,
    where the meta class definition is automatically generated by the protobuf.
    The interface definition can be found in:
    https://cs.android.com/android/platform/superproject/+/main:external
    /pandora/bt-test-interfaces/pandora/security.proto
    """

    def __init__(self, server: grpc.aio.Server, bluetooth: bluetooth_module.Bluetooth):
        self.server = server
        self.bluetooth = bluetooth

    async def IsBonded(self, request: security_pb2.IsBondedRequest,
                       context: grpc.ServicerContext) -> wrappers_pb2.BoolValue:
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)  # type: ignore
        context.set_details('Method not implemented!')  # type: ignore
        raise NotImplementedError('Method not implemented!')

    async def DeleteBond(self, request: security_pb2.DeleteBondRequest,
                         context: grpc.ServicerContext) -> empty_pb2.Empty:
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)  # type: ignore
        context.set_details('Method not implemented!')  # type: ignore
        raise NotImplementedError('Method not implemented!')
