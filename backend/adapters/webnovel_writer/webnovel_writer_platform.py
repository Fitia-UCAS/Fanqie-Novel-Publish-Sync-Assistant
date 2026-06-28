from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class WebnovelWriterRuntime:
    platform: str
    api_key: str
    base_url: str
    model_name: str
    description: str
    temperature: float
    max_tokens: int
    max_retries: int
    retry_delay: float


class WebnovelWriterPlatform:
    """OpenAI-compatible runtime resolver.

    This mirrors the existing character_material/current_plot platform pattern while using
    model defaults that are friendlier for long-form chapter generation.
    """

    PLATFORMS: dict[str, dict[str, str]] = {
        "deepseek": {
            "api_key_env": "DEEPSEEK_API_KEY",
            "api_key_env_alt": "DEEPSEEK_API",
            "base_url_env": "DEEPSEEK_BASE_URL",
            "model_env": "DEEPSEEK_MODEL_NAME",
            "default_base_url": "https://api.deepseek.com/v1",
            "default_model": "deepseek-chat",
            "description": "DeepSeek / OpenAI 兼容",
        },
        "deepseek_reasoner": {
            "api_key_env": "DEEPSEEK_API_KEY",
            "api_key_env_alt": "DEEPSEEK_API",
            "base_url_env": "DEEPSEEK_BASE_URL",
            "model_env": "DEEPSEEK_REASONER_MODEL_NAME",
            "default_base_url": "https://api.deepseek.com/v1",
            "default_model": "deepseek-reasoner",
            "description": "DeepSeek Reasoner",
        },
        "siliconflow": {
            "api_key_env": "SILICONFLOW_API_KEY",
            "api_key_env_alt": "",
            "base_url_env": "SILICONFLOW_BASE_URL",
            "model_env": "SILICONFLOW_MODEL_NAME",
            "default_base_url": "https://api.siliconflow.cn/v1",
            "default_model": "Qwen/Qwen3-30B-A3B-Instruct-2507",
            "description": "SiliconFlow",
        },
        "openai": {
            "api_key_env": "OPENAI_API_KEY",
            "api_key_env_alt": "",
            "base_url_env": "OPENAI_BASE_URL",
            "model_env": "OPENAI_MODEL_NAME",
            "default_base_url": "https://api.openai.com/v1",
            "default_model": "gpt-4o-mini",
            "description": "OpenAI",
        },
        "moonshot": {
            "api_key_env": "MOONSHOT_API_KEY",
            "api_key_env_alt": "",
            "base_url_env": "MOONSHOT_BASE_URL",
            "model_env": "MOONSHOT_MODEL_NAME",
            "default_base_url": "https://api.moonshot.cn/v1",
            "default_model": "kimi-k2-0905-preview",
            "description": "Kimi / 月之暗面",
        },
        "custom": {
            "api_key_env": "CUSTOM_API_KEY",
            "api_key_env_alt": "",
            "base_url_env": "CUSTOM_BASE_URL",
            "model_env": "CUSTOM_MODEL_NAME",
            "default_base_url": "https://your-openai-compatible-endpoint/v1",
            "default_model": "custom-model",
            "description": "自定义 OpenAI 兼容接口",
        },
    }

    @classmethod
    def list_platforms(cls) -> dict[str, str]:
        return {name: item["description"] for name, item in cls.PLATFORMS.items()}

    @classmethod
    def default_runtime_values(cls, platform: str) -> dict[str, str | float | int]:
        cfg = cls._platform_config(platform)
        return {
            "baseUrl": os.getenv(cfg["base_url_env"], cfg["default_base_url"]),
            "modelName": os.getenv(cfg["model_env"], cfg["default_model"]),
            "temperature": 0.72,
            "maxTokens": 8192,
        }

    @classmethod
    def runtime_from_payload(cls, payload: dict) -> WebnovelWriterRuntime:
        platform = str(payload.get("platform") or os.getenv("LLM_PLATFORM") or "deepseek").strip()
        cfg = cls._platform_config(platform)
        api_key = str(
            payload.get("apiKey")
            or os.getenv(cfg["api_key_env"])
            or (os.getenv(cfg.get("api_key_env_alt", "")) if cfg.get("api_key_env_alt") else "")
            or ""
        ).strip()
        if not api_key:
            configured = []
            for name, item in cls.PLATFORMS.items():
                if os.getenv(item["api_key_env"]) or (item.get("api_key_env_alt") and os.getenv(item["api_key_env_alt"])):
                    configured.append(name)
            if configured:
                raise ValueError(f"平台 {platform} 的 API Key 未配置，可切换到已配置平台：{', '.join(configured)}。")
            env_names = "、".join(
                name for item in cls.PLATFORMS.values() for name in (item["api_key_env"], item.get("api_key_env_alt", "")) if name
            )
            raise ValueError(f"没有找到 API Key，请在页面填写 API Key，或配置环境变量：{env_names}")
        return WebnovelWriterRuntime(
            platform=platform,
            api_key=api_key,
            base_url=str(payload.get("baseUrl") or os.getenv(cfg["base_url_env"], cfg["default_base_url"])).strip(),
            model_name=str(payload.get("modelName") or os.getenv(cfg["model_env"], cfg["default_model"])).strip(),
            description=cfg["description"],
            temperature=_float(payload.get("temperature"), 0.72),
            max_tokens=max(1024, _int(payload.get("maxTokens"), 8192)),
            max_retries=max(1, _int(payload.get("maxRetries"), 3)),
            retry_delay=max(0.0, _float(payload.get("retryDelay"), 2.0)),
        )

    @classmethod
    def _platform_config(cls, platform: str) -> dict[str, str]:
        if platform not in cls.PLATFORMS:
            supported = "、".join(cls.PLATFORMS)
            raise ValueError(f"不支持的平台：{platform}。支持的平台：{supported}")
        return cls.PLATFORMS[platform]


def _int(value: object, default: int) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except Exception:
        return default


def _float(value: object, default: float) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except Exception:
        return default
