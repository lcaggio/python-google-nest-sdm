"""Test for camera traits."""

from typing import Any, Callable, Dict

from google_nest_sdm.device import Device


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
    assert 500 == trait.max_image_resolution.width
    assert 300 == trait.max_image_resolution.height


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
    assert 500 == trait.max_video_resolution.width
    assert 300 == trait.max_video_resolution.height
    assert ["H264"] == trait.video_codecs
    assert ["AAC"] == trait.audio_codecs


def test_camera_event_image_traits(
    fake_device: Callable[[Dict[str, Any]], Device]
) -> None:
    raw = {
        "name": "my/device/name",
        "traits": {
            "sdm.devices.traits.CameraEventImage": {},
        },
    }
    device = fake_device(raw)
    assert "sdm.devices.traits.CameraEventImage" in device.traits


def test_camera_motion_traits(fake_device: Callable[[Dict[str, Any]], Device]) -> None:
    raw = {
        "name": "my/device/name",
        "traits": {
            "sdm.devices.traits.CameraMotion": {},
        },
    }
    device = fake_device(raw)
    assert "sdm.devices.traits.CameraMotion" in device.traits


def test_camera_person_traits(fake_device: Callable[[Dict[str, Any]], Device]) -> None:
    raw = {
        "name": "my/device/name",
        "traits": {
            "sdm.devices.traits.CameraPerson": {},
        },
    }
    device = fake_device(raw)
    assert "sdm.devices.traits.CameraPerson" in device.traits


def test_camera_sound_traits(fake_device: Callable[[Dict[str, Any]], Device]) -> None:
    raw = {
        "name": "my/device/name",
        "traits": {
            "sdm.devices.traits.CameraSound": {},
        },
    }
    device = fake_device(raw)
    assert "sdm.devices.traits.CameraSound" in device.traits
