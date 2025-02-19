"""Test for camera traits."""

import datetime
from typing import Any, Awaitable, Callable, Dict

import aiohttp
import pytest

from google_nest_sdm import google_nest_api
from google_nest_sdm.camera_traits import EventImageType, StreamingProtocol
from google_nest_sdm.device import Device
from google_nest_sdm.event import EventMessage

from .conftest import DeviceHandler, NewHandler, NewImageHandler, Recorder


def test_camera_image_traits(fake_device: Callable[[Dict[str, Any]], Device]) -> None:
    raw = {
        "name": "my/device/name",
        "traits": {
            "sdm.devices.traits.CameraImage": {
                "maxImageResolution": {
                    "width": 500,
                    "height": 300,
                }
            },
        },
    }
    device = fake_device(raw)
    assert "sdm.devices.traits.CameraImage" in device.traits
    trait = device.traits["sdm.devices.traits.CameraImage"]
    assert trait.max_image_resolution.width == 500
    assert trait.max_image_resolution.height == 300


def test_camera_live_stream_traits(
    fake_device: Callable[[Dict[str, Any]], Device]
) -> None:
    raw = {
        "name": "my/device/name",
        "traits": {
            "sdm.devices.traits.CameraLiveStream": {
                "maxVideoResolution": {
                    "width": 500,
                    "height": 300,
                },
                "videoCodecs": ["H264"],
                "audioCodecs": ["AAC"],
            },
        },
    }
    device = fake_device(raw)
    assert "sdm.devices.traits.CameraLiveStream" in device.traits
    trait = device.traits["sdm.devices.traits.CameraLiveStream"]
    assert trait.max_video_resolution.width == 500
    assert trait.max_video_resolution.height == 300
    assert trait.video_codecs == ["H264"]
    assert trait.audio_codecs == ["AAC"]
    # Default value
    assert trait.supported_protocols == [StreamingProtocol.RTSP]


def test_camera_live_stream_webrtc_protocol(
    fake_device: Callable[[Dict[str, Any]], Device]
) -> None:
    raw = {
        "name": "my/device/name",
        "traits": {
            "sdm.devices.traits.CameraLiveStream": {
                "supportedProtocols": ["WEB_RTC"],
            },
        },
    }
    device = fake_device(raw)
    assert "sdm.devices.traits.CameraLiveStream" in device.traits
    trait = device.traits["sdm.devices.traits.CameraLiveStream"]
    assert trait.supported_protocols == [StreamingProtocol.WEB_RTC]


def test_camera_live_stream_multiple_protocols(
    fake_device: Callable[[Dict[str, Any]], Device]
) -> None:
    raw = {
        "name": "my/device/name",
        "traits": {
            "sdm.devices.traits.CameraLiveStream": {
                "supportedProtocols": ["WEB_RTC", "RTSP"],
            },
        },
    }
    device = fake_device(raw)
    assert "sdm.devices.traits.CameraLiveStream" in device.traits
    trait = device.traits["sdm.devices.traits.CameraLiveStream"]
    assert trait.supported_protocols == [
        StreamingProtocol.WEB_RTC,
        StreamingProtocol.RTSP,
    ]


def test_camera_live_stream_unknown_protocols(
    fake_device: Callable[[Dict[str, Any]], Device]
) -> None:
    raw = {
        "name": "my/device/name",
        "traits": {
            "sdm.devices.traits.CameraLiveStream": {
                "supportedProtocols": ["WEB_RTC", "XXX"],
            },
        },
    }
    device = fake_device(raw)
    assert "sdm.devices.traits.CameraLiveStream" in device.traits
    trait = device.traits["sdm.devices.traits.CameraLiveStream"]
    assert trait.supported_protocols == [StreamingProtocol.WEB_RTC]


@pytest.mark.parametrize(
    "trait",
    [
        "sdm.devices.traits.CameraMotion",
        "sdm.devices.traits.CameraPerson",
        "sdm.devices.traits.CameraSound",
        "sdm.devices.traits.CameraClipPreview",
        "sdm.devices.traits.CameraEventImage",
    ],
)
def test_image_event_traits(
    trait: str, fake_device: Callable[[Dict[str, Any]], Device]
) -> None:
    raw = {
        "name": "my/device/name",
        "traits": {
            trait: {},
        },
    }
    device = fake_device(raw)
    assert trait in device.traits


async def test_camera_live_stream_rtsp(
    app: aiohttp.web.Application,
    recorder: Recorder,
    device_handler: DeviceHandler,
    api_client: Callable[[], Awaitable[google_nest_api.GoogleNestAPI]],
) -> None:
    device_id = device_handler.add_device(
        traits={
            "sdm.devices.traits.CameraLiveStream": {
                "maxVideoResolution": {
                    "width": 500,
                    "height": 300,
                },
                "videoCodecs": ["H264"],
                "audioCodecs": ["AAC"],
            },
        }
    )

    post_handler = NewHandler(
        recorder,
        [
            {
                "results": {
                    "streamUrls": {
                        "rtspUrl": "rtsps://someurl.com/CjY5Y3VKaTfMF?auth=g.0.token"
                    },
                    "streamExtensionToken": "CjY5Y3VKaTfMF",
                    "streamToken": "g.0.token",
                    "expiresAt": "2018-01-04T18:30:00.000Z",
                },
            },
            {
                "results": {
                    "streamExtensionToken": "dGNUlTU2CjY5Y3VKaTZwR3o4Y1...",
                    "streamToken": "g.1.newStreamingToken",
                    "expiresAt": "2019-01-04T18:30:00.000Z",
                }
            },
            {
                "results": {
                    "streamExtensionToken": "last-token...",
                    "streamToken": "g.2.newStreamingToken",
                    "expiresAt": "2020-01-04T18:30:00.000Z",
                }
            },
            {},
        ],
    )
    app.router.add_post(f"/{device_id}:executeCommand", post_handler)

    api = await api_client()
    devices = await api.async_get_devices()
    assert len(devices) == 1
    device = devices[0]
    assert device.name == device_id
    trait = device.traits["sdm.devices.traits.CameraLiveStream"]
    stream = await trait.generate_rtsp_stream()
    assert recorder.request == {
        "command": "sdm.devices.commands.CameraLiveStream.GenerateRtspStream",
        "params": {},
    }
    assert stream.stream_token == "g.0.token"
    assert stream.expires_at == datetime.datetime(
        2018, 1, 4, 18, 30, tzinfo=datetime.timezone.utc
    )
    assert stream.rtsp_stream_url == "rtsps://someurl.com/CjY5Y3VKaTfMF?auth=g.0.token"

    stream = await stream.extend_rtsp_stream()
    assert recorder.request == {
        "command": "sdm.devices.commands.CameraLiveStream.ExtendRtspStream",
        "params": {
            "streamExtensionToken": "CjY5Y3VKaTfMF",
        },
    }
    assert stream.stream_token == "g.1.newStreamingToken"
    assert stream.expires_at == datetime.datetime(
        2019, 1, 4, 18, 30, tzinfo=datetime.timezone.utc
    )
    assert (
        stream.rtsp_stream_url
        == "rtsps://someurl.com/CjY5Y3VKaTfMF?auth=g.1.newStreamingToken"
    )

    stream = await stream.extend_rtsp_stream()
    assert recorder.request == {
        "command": "sdm.devices.commands.CameraLiveStream.ExtendRtspStream",
        "params": {
            "streamExtensionToken": "dGNUlTU2CjY5Y3VKaTZwR3o4Y1...",
        },
    }
    assert stream.stream_token == "g.2.newStreamingToken"
    assert stream.expires_at == datetime.datetime(
        2020, 1, 4, 18, 30, tzinfo=datetime.timezone.utc
    )
    assert (
        stream.rtsp_stream_url
        == "rtsps://someurl.com/CjY5Y3VKaTfMF?auth=g.2.newStreamingToken"
    )

    await stream.stop_rtsp_stream()
    assert recorder.request == {
        "command": "sdm.devices.commands.CameraLiveStream.StopRtspStream",
        "params": {
            "streamExtensionToken": "last-token...",
        },
    }

    assert device.get_diagnostics() == {
        "data": {
            "name": "**REDACTED**",
            "parentRelations": [],
            "traits": {
                "sdm.devices.traits.CameraLiveStream": {
                    "maxVideoResolution": {
                        "width": 500,
                        "height": 300,
                    },
                    "videoCodecs": ["H264"],
                    "audioCodecs": ["AAC"],
                }
            },
            "type": "sdm.devices.types.device-type1",
        },
        "command": {
            "sdm.devices.commands.CameraLiveStream.ExtendRtspStream": 2,
            "sdm.devices.commands.CameraLiveStream.GenerateRtspStream": 1,
            "sdm.devices.commands.CameraLiveStream.StopRtspStream": 1,
        },
    }


async def test_camera_live_stream_web_rtc(
    app: aiohttp.web.Application,
    recorder: Recorder,
    device_handler: DeviceHandler,
    api_client: Callable[[], Awaitable[google_nest_api.GoogleNestAPI]],
) -> None:
    device_id = device_handler.add_device(
        traits={
            "sdm.devices.traits.CameraLiveStream": {
                "supportedProtocols": ["WEB_RTC"],
            },
        }
    )

    post_handler = NewHandler(
        recorder,
        [
            {
                "results": {
                    "answerSdp": "some-answer",
                    "expiresAt": "2018-01-04T18:30:00.000Z",
                    "mediaSessionId": "JxdTxkkatHk4kVnXlKzQICbfVR...",
                },
            },
            {
                "results": {
                    "expiresAt": "2019-01-04T18:30:00.000Z",
                    "mediaSessionId": "JxdTxkkatHk4kVnXlKzQICbfVR...",
                }
            },
            {
                "results": {
                    "expiresAt": "2020-01-04T18:30:00.000Z",
                    "mediaSessionId": "JxdTxkkatHk4kVnXlKzQICbfVR...",
                }
            },
            {},
        ],
    )
    app.router.add_post(f"/{device_id}:executeCommand", post_handler)

    api = await api_client()
    devices = await api.async_get_devices()
    assert len(devices) == 1
    device = devices[0]
    assert device.name == device_id
    trait = device.traits["sdm.devices.traits.CameraLiveStream"]
    assert trait.supported_protocols == [StreamingProtocol.WEB_RTC]
    stream = await trait.generate_web_rtc_stream("a=recvonly")
    assert recorder.request == {
        "command": "sdm.devices.commands.CameraLiveStream.GenerateWebRtcStream",
        "params": {
            "offerSdp": "a=recvonly",
        },
    }
    assert stream.answer_sdp == "some-answer"
    assert stream.expires_at == datetime.datetime(
        2018, 1, 4, 18, 30, tzinfo=datetime.timezone.utc
    )
    assert stream.media_session_id == "JxdTxkkatHk4kVnXlKzQICbfVR..."

    stream = await stream.extend_stream()
    expected_request = {
        "command": "sdm.devices.commands.CameraLiveStream.ExtendWebRtcStream",
        "params": {
            "mediaSessionId": "JxdTxkkatHk4kVnXlKzQICbfVR...",
        },
    }
    assert expected_request == recorder.request
    assert "some-answer" == stream.answer_sdp
    assert (
        datetime.datetime(2019, 1, 4, 18, 30, tzinfo=datetime.timezone.utc)
        == stream.expires_at
    )
    assert "JxdTxkkatHk4kVnXlKzQICbfVR..." == stream.media_session_id

    stream = await stream.extend_stream()
    assert recorder.request == {
        "command": "sdm.devices.commands.CameraLiveStream.ExtendWebRtcStream",
        "params": {
            "mediaSessionId": "JxdTxkkatHk4kVnXlKzQICbfVR...",
        },
    }
    assert stream.answer_sdp == "some-answer"
    assert stream.expires_at == datetime.datetime(
        2020, 1, 4, 18, 30, tzinfo=datetime.timezone.utc
    )
    assert "JxdTxkkatHk4kVnXlKzQICbfVR..." == stream.media_session_id

    await stream.stop_stream()
    assert recorder.request == {
        "command": "sdm.devices.commands.CameraLiveStream.StopWebRtcStream",
        "params": {
            "mediaSessionId": "JxdTxkkatHk4kVnXlKzQICbfVR...",
        },
    }


async def test_camera_event_image(
    app: aiohttp.web.Application,
    recorder: Recorder,
    device_handler: DeviceHandler,
    api_client: Callable[[], Awaitable[google_nest_api.GoogleNestAPI]],
) -> None:
    device_id = device_handler.add_device(
        traits={"sdm.devices.traits.CameraEventImage": {}}
    )

    post_handler = NewHandler(
        recorder,
        [
            {
                "results": {
                    "url": "https://domain/sdm_event/dGNUlTU2CjY5Y3VKaTZwR3o4Y",
                    "token": "g.0.eventToken",
                },
            }
        ],
    )
    app.router.add_post(f"/{device_id}:executeCommand", post_handler)

    api = await api_client()
    devices = await api.async_get_devices()
    assert len(devices) == 1
    device = devices[0]
    assert device.name == device_id
    trait = device.traits["sdm.devices.traits.CameraEventImage"]
    image = await trait.generate_image("some-eventId")
    assert recorder.request == {
        "command": "sdm.devices.commands.CameraEventImage.GenerateImage",
        "params": {"eventId": "some-eventId"},
    }
    assert image.url == "https://domain/sdm_event/dGNUlTU2CjY5Y3VKaTZwR3o4Y"
    assert image.token == "g.0.eventToken"
    assert image.event_image_type == EventImageType.IMAGE


@pytest.mark.parametrize(
    "test_trait,test_event_trait",
    [
        ("sdm.devices.traits.CameraMotion", "sdm.devices.events.CameraMotion.Motion"),
        ("sdm.devices.traits.CameraPerson", "sdm.devices.events.CameraPerson.Person"),
        ("sdm.devices.traits.CameraSound", "sdm.devices.events.CameraSound.Sound"),
        ("sdm.devices.traits.DoorbellChime", "sdm.devices.events.DoorbellChime.Chime"),
    ],
)
async def test_camera_active_event_image(
    test_trait: str,
    test_event_trait: str,
    app: aiohttp.web.Application,
    recorder: Recorder,
    device_handler: DeviceHandler,
    api_client: Callable[[], Awaitable[google_nest_api.GoogleNestAPI]],
    event_message: Callable[[Dict[str, Any]], Awaitable[EventMessage]],
) -> None:
    device_id = device_handler.add_device(
        traits={
            "sdm.devices.traits.CameraEventImage": {},
            test_trait: {},
        }
    )

    post_handler = NewHandler(
        recorder,
        [
            {
                "results": {
                    "url": "image-url",
                    "token": "g.0.eventToken",
                },
            }
        ],
    )
    app.router.add_post(f"/{device_id}:executeCommand", post_handler)

    image_handler = NewImageHandler([b"image-bytes"], token="g.0.eventToken")
    app.router.add_get("/image-url", image_handler)

    api = await api_client()
    devices = await api.async_get_devices()
    assert len(devices) == 1
    device = devices[0]
    assert device.name == device_id

    now = datetime.datetime.now(tz=datetime.timezone.utc)
    await device.async_handle_event(
        await event_message(
            {
                "eventId": "0120ecc7-3b57-4eb4-9941-91609f189fb4",
                "timestamp": now.isoformat(timespec="seconds"),
                "resourceUpdate": {
                    "name": device_id,
                    "events": {
                        test_event_trait: {
                            "eventSessionId": "CjY5Y3VKaTZwR3o4Y19YbTVfMF...",
                            "eventId": "FWWVQVUdGNUlTU2V4MGV2aTNXV...",
                        },
                    },
                },
                "userId": "AVPHwEuBfnPOnTqzVFT4IONX2Qqhu9EJ4ubO-bNnQ-yi",
            }
        )
    )

    event_media = await device.event_media_manager.get_active_event_media()
    assert event_media
    assert event_media.event_session_id == "CjY5Y3VKaTZwR3o4Y19YbTVfMF..."
    assert event_media.media.contents == b"image-bytes"


async def test_camera_last_active_event_image(
    app: aiohttp.web.Application,
    recorder: Recorder,
    device_handler: DeviceHandler,
    api_client: Callable[[], Awaitable[google_nest_api.GoogleNestAPI]],
    event_message: Callable[[Dict[str, Any]], Awaitable[EventMessage]],
) -> None:
    device_id = device_handler.add_device(
        traits={
            "sdm.devices.traits.CameraEventImage": {},
            "sdm.devices.traits.CameraMotion": {},
            "sdm.devices.traits.CameraSound": {},
        }
    )

    post_handler = NewHandler(
        recorder,
        [
            {
                "results": {
                    "url": "https://domain/sdm_event/dGNUlTU2CjY5Y3VKaTZwR3o4Y",
                    "token": "g.0.eventToken",
                },
            }
        ],
    )
    app.router.add_post(f"/{device_id}:executeCommand", post_handler)

    api = await api_client()
    devices = await api.async_get_devices()
    assert len(devices) == 1
    device = devices[0]
    assert device.name == device_id

    # Later message arrives first
    t2 = datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(seconds=5)
    await device.async_handle_event(
        await event_message(
            {
                "eventId": "4bf981f90619-1499-4be4-75b3-7cce0210",
                "timestamp": t2.isoformat(timespec="seconds"),
                "resourceUpdate": {
                    "name": device_id,
                    "events": {
                        "sdm.devices.events.CameraSound.Sound": {
                            "eventSessionId": "FMfVTbY91Y4o3RwZTaKV3Y5jC...",
                            "eventId": "VXNTa2VGM4V2UTlUNGdUVQVWWF...",
                        },
                    },
                },
                "userId": "AVPHwEuBfnPOnTqzVFT4IONX2Qqhu9EJ4ubO-bNnQ-yi",
            }
        )
    )
    t1 = datetime.datetime.now(tz=datetime.timezone.utc)
    await device.async_handle_event(
        await event_message(
            {
                "eventId": "0120ecc7-3b57-4eb4-9941-91609f189fb4",
                "timestamp": t1.isoformat(timespec="seconds"),
                "resourceUpdate": {
                    "name": device_id,
                    "events": {
                        "sdm.devices.events.CameraMotion.Motion": {
                            "eventSessionId": "CjY5Y3VKaTZwR3o4Y19YbTVfMF...",
                            "eventId": "FWWVQVUdGNUlTU2V4MGV2aTNXV...",
                        },
                    },
                },
                "userId": "AVPHwEuBfnPOnTqzVFT4IONX2Qqhu9EJ4ubO-bNnQ-yi",
            }
        )
    )

    trait = device.active_event_trait
    assert trait
    assert trait.active_event is not None
    assert trait.last_event is not None
    assert trait.last_event.event_session_id == "FMfVTbY91Y4o3RwZTaKV3Y5jC..."
    assert trait.last_event.event_id == "VXNTa2VGM4V2UTlUNGdUVQVWWF..."


async def test_camera_event_image_bytes(
    app: aiohttp.web.Application,
    recorder: Recorder,
    device_handler: DeviceHandler,
    api_client: Callable[[], Awaitable[google_nest_api.GoogleNestAPI]],
) -> None:
    device_id = device_handler.add_device(
        traits={"sdm.devices.traits.CameraEventImage": {}}
    )

    post_handler = NewHandler(
        recorder,
        [
            {
                "results": {
                    "url": "image-url",
                    "token": "g.0.eventToken",
                },
            }
        ],
    )
    image_handler = NewImageHandler([b"image-bytes"], token="g.0.eventToken")

    app.router.add_post(f"/{device_id}:executeCommand", post_handler)
    app.router.add_get("/image-url", image_handler)

    api = await api_client()
    devices = await api.async_get_devices()
    assert len(devices) == 1
    device = devices[0]
    assert device.name == device_id
    trait = device.traits["sdm.devices.traits.CameraEventImage"]
    event_image = await trait.generate_image("some-eventId")
    image_bytes = await event_image.contents()
    assert image_bytes == b"image-bytes"


async def test_camera_active_clip_preview(
    app: aiohttp.web.Application,
    recorder: Recorder,
    device_handler: DeviceHandler,
    api_client: Callable[[], Awaitable[google_nest_api.GoogleNestAPI]],
    event_message: Callable[[Dict[str, Any]], Awaitable[EventMessage]],
) -> None:
    device_id = device_handler.add_device(
        traits={"sdm.devices.traits.CameraClipPreview": {}}
    )

    api = await api_client()
    devices = await api.async_get_devices()
    assert len(devices) == 1
    device = devices[0]
    assert device.name == device_id

    now = datetime.datetime.now(tz=datetime.timezone.utc)
    await device.async_handle_event(
        await event_message(
            {
                "eventId": "0120ecc7-3b57-4eb4-9941-91609f189fb4",
                "timestamp": now.isoformat(timespec="seconds"),
                "resourceUpdate": {
                    "name": device_id,
                    "events": {
                        "sdm.devices.events.CameraClipPreview.ClipPreview": {
                            "eventSessionId": "CjY5Y3VKaTZwR3o4Y19YbTVfMF...",
                            "previewUrl": "https://previewUrl/...",
                        },
                    },
                },
                "userId": "AVPHwEuBfnPOnTqzVFT4IONX2Qqhu9EJ4ubO-bNnQ-yi",
            }
        )
    )

    trait = device.traits["sdm.devices.traits.CameraClipPreview"]
    assert trait.active_event is not None
    image = await trait.generate_active_event_image()
    assert image.url == "https://previewUrl/..."
    assert image.token is None
    assert image.event_image_type == EventImageType.CLIP_PREVIEW
