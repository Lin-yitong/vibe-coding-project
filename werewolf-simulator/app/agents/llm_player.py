import json
import re
from typing import Any

import httpx

from app.agents.prompt_builder import PromptBuilder
from app.agents.random_agent import RandomAgent
from app.core.config import settings
from app.engine.rule_checker import RuleChecker
from app.models.action import AgentAction, WitchAction
from app.models.game import GameState
from app.models.player import Player


class LLMPlayer(RandomAgent):
    """OpenAI-compatible LLM player with RandomAgent fallback."""

    def __init__(
        self,
        rng=None,
        rule_checker: RuleChecker | None = None,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        super().__init__(rng=rng, rule_checker=rule_checker)
        self.prompt_builder = prompt_builder or PromptBuilder()

    def choose_wolf_target(self, game: GameState, wolves: list[Player]) -> AgentAction:
        actor = wolves[0] if wolves else None
        if not actor:
            return super().choose_wolf_target(game, wolves)
        prompt = self.prompt_builder.build_action_prompt(
            game=game,
            player=actor,
            task="As the wolves, choose one alive non-wolf target to kill tonight.",
            legal_targets=self.rule_checker.legal_wolf_targets(game),
        )
        data = self._chat_json(game, prompt)
        if data is None:
            return super().choose_wolf_target(game, wolves)
        return AgentAction(
            action=str(data.get("action", "kill")),
            actor_id=actor.player_id,
            target=self._normalize_target(data.get("target")),
            reason=str(data.get("reason", "")),
        )

    def choose_seer_target(self, game: GameState, seer: Player) -> AgentAction:
        legal_targets = [pid for pid in self.rule_checker.legal_seer_targets(game) if pid != seer.player_id]
        prompt = self.prompt_builder.build_action_prompt(
            game=game,
            player=seer,
            task="As the seer, choose one alive player to check tonight.",
            legal_targets=legal_targets,
        )
        data = self._chat_json(game, prompt)
        if data is None:
            return super().choose_seer_target(game, seer)
        return AgentAction(
            action=str(data.get("action", "check")),
            actor_id=seer.player_id,
            target=self._normalize_target(data.get("target")),
            reason=str(data.get("reason", "")),
        )

    def choose_witch_action(self, game: GameState, witch: Player) -> WitchAction:
        prompt = self.prompt_builder.build_witch_prompt(
            game=game,
            witch=witch,
            legal_poison_targets=[pid for pid in self.rule_checker.legal_poison_targets(game) if pid != witch.player_id],
        )
        data = self._chat_json(game, prompt)
        if data is None:
            return super().choose_witch_action(game, witch)
        return WitchAction(
            save=bool(data.get("save", False)),
            poison_target=self._normalize_target(data.get("poison_target")),
            reason=str(data.get("reason", "")),
        )

    def generate_speech(self, game: GameState, player: Player) -> str:
        prompt = self.prompt_builder.build_speech_prompt(game, player)
        data = self._chat_json(game, prompt)
        if data is None:
            return super().generate_speech(game, player)
        speech = data.get("speech") or data.get("message") or data.get("text")
        if not isinstance(speech, str) or not speech.strip():
            game.debug_logs.append(f"LLM speech fallback for {player.player_id}: empty speech.")
            return super().generate_speech(game, player)
        return speech.strip()[:300]

    def vote(self, game: GameState, player: Player) -> AgentAction:
        legal_targets = [pid for pid in self.rule_checker.legal_vote_targets(game) if pid != player.player_id]
        prompt = self.prompt_builder.build_action_prompt(
            game=game,
            player=player,
            task="Vote for one alive player to exile today.",
            legal_targets=legal_targets,
        )
        data = self._chat_json(game, prompt)
        if data is None:
            return super().vote(game, player)
        return AgentAction(
            action=str(data.get("action", "vote")),
            actor_id=player.player_id,
            target=self._normalize_target(data.get("target")),
            reason=str(data.get("reason", "")),
        )

    def _chat_json(self, game: GameState, prompt: str) -> dict[str, Any] | None:
        if not settings.llm_enabled:
            return None
        if not settings.llm_api_key:
            game.debug_logs.append("LLM fallback: missing llm_api_key.")
            return None

        url = f"{settings.llm_base_url.rstrip('/')}/chat/completions"
        headers = {"Authorization": f"Bearer {settings.llm_api_key}", "Content-Type": "application/json"}
        payload = {
            "model": settings.llm_model,
            "messages": [
                {"role": "system", "content": self.prompt_builder.system_prompt()},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "response_format": {"type": "json_object"},
        }

        try:
            with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return self._parse_json(content)
        except Exception as exc:
            game.debug_logs.append(f"LLM call failed; using fallback. error={type(exc).__name__}: {exc}")
            return None

    def _parse_json(self, content: str) -> dict[str, Any]:
        text = content.strip()
        fence = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
        if fence:
            text = fence.group(1).strip()
        return json.loads(text)

    def _normalize_target(self, target: Any) -> str | None:
        if target is None:
            return None
        if isinstance(target, int):
            return f"player_{target}"
        text = str(target).strip()
        if not text or text.lower() == "null":
            return None
        if text.startswith("player_"):
            return text
        if text.isdigit():
            return f"player_{text}"
        match = re.search(r"(\d+)", text)
        if match:
            return f"player_{match.group(1)}"
        return text
