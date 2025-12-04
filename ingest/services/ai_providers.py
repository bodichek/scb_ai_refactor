"""
AI Provider abstraction - supports OpenAI and Claude (Anthropic).
Allows switching between AI providers for PDF parsing.
"""

import base64
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from django.conf import settings

logger = logging.getLogger(__name__)


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    def parse_document(self, images: List[bytes], prompt: str) -> Dict[str, Any]:
        """Parse document images with AI and return structured data."""
        pass


class OpenAIProvider(AIProvider):
    """OpenAI provider for document parsing."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        from openai import OpenAI

        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")
        self.client = OpenAI(api_key=self.api_key)

    def parse_document(self, images: List[bytes], prompt: str) -> Dict[str, Any]:
        """Parse document using OpenAI Vision API."""
        content = [{"type": "input_text", "text": prompt}]

        # Encode images to base64
        for img in images:
            b64 = base64.b64encode(img).decode("utf-8")
            content.append({
                "type": "input_image",
                "image_url": f"data:image/png;base64,{b64}"
            })

        try:
            logger.info(f"Calling OpenAI API with model: {self.model}")
            resp = self.client.responses.create(
                model=self.model,
                input=[{"role": "user", "content": content}],
                max_output_tokens=2000,
                temperature=0
            )

            raw_text = self._extract_text(resp)
            cleaned_text = self._clean_json(raw_text)
            parsed = json.loads(cleaned_text)

            logger.info("OpenAI parsing successful")
            return parsed

        except Exception as e:
            logger.error(f"OpenAI API error: {e}", exc_info=True)
            raise

    def _extract_text(self, resp) -> str:
        """Extract text from OpenAI response."""
        try:
            out = resp.output
            if out and len(out) > 0:
                c = out[0].content[0]
                if hasattr(c.text, "value"):
                    return c.text.value
                if isinstance(c.text, str):
                    return c.text
                if isinstance(c, str):
                    return c
        except Exception:
            logger.error("Primary extraction failed", exc_info=True)

        if hasattr(resp, "output_text"):
            return resp.output_text

        return ""

    def _clean_json(self, text: str) -> str:
        """Clean JSON from markdown code blocks."""
        if not text:
            return ""

        # Remove markdown code blocks
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].strip().startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines)

        # Extract JSON object
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return text[start:end + 1].strip()

        return text.strip()


class ClaudeProvider(AIProvider):
    """Anthropic Claude provider for document parsing."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        import anthropic

        self.api_key = api_key or getattr(settings, "ANTHROPIC_API_KEY", None)
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is not configured in settings")

        self.model = model or getattr(settings, "ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
        self.client = anthropic.Anthropic(api_key=self.api_key)

    def parse_document(self, images: List[bytes], prompt: str) -> Dict[str, Any]:
        """Parse document using Claude Vision API."""
        content = [{"type": "text", "text": prompt}]

        # Add images to content
        for img in images:
            b64 = base64.b64encode(img).decode("utf-8")
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": b64
                }
            })

        try:
            logger.info(f"Calling Claude API with model: {self.model}")
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                temperature=0,
                messages=[{"role": "user", "content": content}]
            )

            raw_text = response.content[0].text
            cleaned_text = self._clean_json(raw_text)
            parsed = json.loads(cleaned_text)

            logger.info("Claude parsing successful")
            return parsed

        except Exception as e:
            logger.error(f"Claude API error: {e}", exc_info=True)
            raise

    def _clean_json(self, text: str) -> str:
        """Clean JSON from markdown code blocks."""
        if not text:
            return ""

        # Remove markdown code blocks
        if "```json" in text or "```" in text:
            lines = text.splitlines()
            in_block = False
            json_lines = []

            for line in lines:
                if line.strip().startswith("```"):
                    in_block = not in_block
                    continue
                if in_block or (not in_block and "{" in line):
                    json_lines.append(line)

            text = "\n".join(json_lines)

        # Extract JSON object
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return text[start:end + 1].strip()

        return text.strip()


def get_ai_provider(provider_name: str = "openai") -> AIProvider:
    """
    Factory function to get AI provider instance.

    Args:
        provider_name: "openai" or "claude"

    Returns:
        AIProvider instance
    """
    provider_name = provider_name.lower()

    if provider_name == "openai":
        return OpenAIProvider()
    elif provider_name == "claude":
        return ClaudeProvider()
    else:
        raise ValueError(f"Unknown AI provider: {provider_name}. Use 'openai' or 'claude'")
