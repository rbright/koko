from __future__ import annotations

from pathlib import Path
from typing import Final

DEFAULT_REPO_ID: Final[str] = "hexgrad/Kokoro-82M"
DEFAULT_VOICE: Final[str] = "af_heart"
DEFAULT_SAMPLE_RATE: Final[int] = 24_000
MAX_PHONEME_CHARS: Final[int] = 510

DEFAULT_LOCAL_MODEL_DIR: Final[Path] = Path("~/.local/share/koko/kokoro-82m")
LOCAL_CONFIG_FILE: Final[str] = "config.json"
LOCAL_MODEL_FILE: Final[str] = "kokoro-v1_0.pth"
LOCAL_VOICES_DIR: Final[str] = "voices"

SUPPORTED_LANG_CODES: Final[set[str]] = {"a", "b", "e", "f", "h", "i", "j", "p", "z"}
LANG_ALIASES: Final[dict[str, str]] = {
    "en-us": "a",
    "en-gb": "b",
    "es": "e",
    "fr-fr": "f",
    "hi": "h",
    "it": "i",
    "ja": "j",
    "pt-br": "p",
    "zh": "z",
}

# Fallback voice list from https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md
FALLBACK_VOICES: Final[tuple[str, ...]] = (
    "af_heart",
    "af_alloy",
    "af_aoede",
    "af_bella",
    "af_jessica",
    "af_kore",
    "af_nicole",
    "af_nova",
    "af_river",
    "af_sarah",
    "af_sky",
    "am_adam",
    "am_echo",
    "am_eric",
    "am_fenrir",
    "am_liam",
    "am_michael",
    "am_onyx",
    "am_puck",
    "am_santa",
    "bf_alice",
    "bf_emma",
    "bf_isabella",
    "bf_lily",
    "bm_daniel",
    "bm_fable",
    "bm_george",
    "bm_lewis",
    "jf_alpha",
    "jf_gongitsune",
    "jf_nezumi",
    "jf_tebukuro",
    "jm_kumo",
    "zf_xiaobei",
    "zf_xiaoni",
    "zf_xiaoxiao",
    "zf_xiaoyi",
    "zm_yunjian",
    "zm_yunxi",
    "zm_yunxia",
    "zm_yunyang",
    "ef_dora",
    "em_alex",
    "em_santa",
    "ff_siwis",
    "hf_alpha",
    "hf_beta",
    "hm_omega",
    "hm_psi",
    "if_sara",
    "im_nicola",
    "pf_dora",
    "pm_alex",
    "pm_santa",
)
