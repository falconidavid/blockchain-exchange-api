import json
import logging
from typing import Dict, List

from blockchain_exchange.websocket import BlockchainWebsocket
from blockchain_exchange.channels import ChannelFactory, Channel


class ChannelManager:
    def __init__(self):
        self._ws = BlockchainWebsocket()
        self._channels_factory = ChannelFactory()

        self._channels = {channel_name: dict() for channel_name in self._channels_factory.channels}
        self._ws.set_ws_message_handler(
            handler=self._handle_messages
        )

    @property
    def available_channel_names(self) -> List[str]:
        return list(self._channels_factory.channels.keys())

    def _encode_channel(self, name, channel_params: Dict) -> str:
        encoding = f"{name}"
        for key in sorted(channel_params.keys()):
            encoding = f"{encoding}-{channel_params[key]}"
        return encoding

    def get_channel(self, name, **kwargs) -> Channel:
        channel_id = self._encode_channel(name, kwargs)
        if channel_id in self._channels[name]:
            channel = self._channels[name][channel_id]
        else:
            channel = self._channels_factory.create_channel(
                name=name,
                ws=self._ws,
                **kwargs
            )

            if name == "prices":
                for existing_channel in self._channels[name].values():
                    if existing_channel.symbol == channel.symbol:
                        logging.error("Can subscribe for a single granularity per channel. "
                                      f"Already subscribed to {existing_channel}")
                        return None

            self._channels[name][channel_id] = channel

        return channel

    def get_all_channels(self) -> List[Channel]:
        all_channels = []
        for channel_type, channels in self._channels.items():
            all_channels += [channel for channel in channels.values()]
        return all_channels

    def _handle_messages(self, message: str):
        """A simple logic for handling message received from blockchain websocket"""
        msg: Dict = json.loads(message)

        event_type = msg.pop("event")

        channel_name = msg.pop("channel")
        channel_params = {}
        for key in ["symbol", "granularity"]:
            if key in msg and channel_name != "trading":
                channel_params[key] = msg.pop(key)

        channel = self.get_channel(channel_name, **channel_params)

        channel.on_event(event_type, msg)