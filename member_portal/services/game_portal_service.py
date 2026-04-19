"""Core gameplay and portal services for TNT-2."""

from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests

from core.config import Config
from core.database import db
from utils.security import PasswordValidator, SecurityManager

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def _load_json_file(file_name: str) -> Dict[str, Any]:
    with (DATA_DIR / file_name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


class GamePortalService:
    DEFAULT_MAP_SETTINGS = {
        "shape": "circle",
        "layers": 3,
        "spacing": 130,
        "sort_by": "power",
        "custom_layout": [],
    }

    @staticmethod
    def bootstrap() -> None:
        GamePortalService._ensure_setting("map_settings", GamePortalService.DEFAULT_MAP_SETTINGS)
        GamePortalService._seed_knowledge_entries()

    @staticmethod
    def _ensure_setting(setting_key: str, default_value: Dict[str, Any]) -> None:
        existing = db.fetchone("SELECT setting_key FROM system_settings WHERE setting_key = ?", (setting_key,))
        if existing:
            return
        db.insert(
            "system_settings",
            {
                "setting_key": setting_key,
                "setting_value": json.dumps(default_value, ensure_ascii=False),
                "updated_at": datetime.now().isoformat(),
            },
        )

    @staticmethod
    def _seed_knowledge_entries() -> None:
        existing = db.fetchone("SELECT COUNT(*) AS count FROM knowledge_entries") or {"count": 0}
        if existing["count"]:
            return

        knowledge = _load_json_file("knowledge_base.json")
        for category, entries in knowledge.items():
            for entry in entries:
                tags = ", ".join(entry.get("tags", []))
                metadata = {
                    "best_use": entry.get("best_use", ""),
                    "tags": entry.get("tags", []),
                }
                db.insert(
                    "knowledge_entries",
                    {
                        "category": category,
                        "entry_name": entry["name"],
                        "tags": tags,
                        "summary": entry["summary"],
                        "metadata_json": json.dumps(metadata, ensure_ascii=False),
                        "source": "seed",
                        "updated_at": datetime.now().isoformat(),
                    },
                )

    @staticmethod
    def get_setting(setting_key: str, default_value: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        row = db.fetchone("SELECT setting_value FROM system_settings WHERE setting_key = ?", (setting_key,))
        if not row:
            return default_value or {}
        try:
            return json.loads(row["setting_value"])
        except json.JSONDecodeError:
            return default_value or {}

    @staticmethod
    def set_setting(setting_key: str, value: Dict[str, Any]) -> bool:
        payload = json.dumps(value, ensure_ascii=False)
        existing = db.fetchone("SELECT setting_key FROM system_settings WHERE setting_key = ?", (setting_key,))
        data = {"setting_value": payload, "updated_at": datetime.now().isoformat()}
        if existing:
            return db.update("system_settings", data, {"setting_key": setting_key})
        return db.insert("system_settings", {"setting_key": setting_key, **data}) is not None

    @staticmethod
    def calculators_data() -> Dict[str, Any]:
        return _load_json_file("calculators.json")

    @staticmethod
    def _slugify_username(seed: str) -> str:
        clean = "".join(ch if ch.isalnum() else "_" for ch in seed.strip().lower())
        clean = clean.strip("_") or "member"
        candidate = clean
        suffix = 1
        while db.fetchone("SELECT id FROM users WHERE username = ?", (candidate,)):
            suffix += 1
            candidate = f"{clean}_{suffix}"
        return candidate

    @staticmethod
    def register_member(payload: Dict[str, Any]) -> Tuple[bool, str, Optional[int]]:
        email = payload.get("email", "").strip().lower()
        password = payload.get("password", "")
        game_name = payload.get("game_name", "").strip()
        state_name = payload.get("state", "").strip()
        specialization = payload.get("specialization", "").strip()
        discord_id = payload.get("discord_id", "").strip()

        if not game_name:
            return False, "اسم اللاعب داخل اللعبة مطلوب", None
        if not email or "@" not in email:
            return False, "البريد الإلكتروني غير صالح", None
        if not state_name:
            return False, "الدولة أو الولاية مطلوبة", None

        try:
            player_power = int(str(payload.get("player_power", "0")).replace(",", "").strip() or "0")
        except ValueError:
            return False, "قوة اللاعب يجب أن تكون رقمًا صحيحًا", None

        valid_password, password_message = PasswordValidator.validate(password)
        if not valid_password:
            return False, password_message, None

        existing = db.fetchone("SELECT id FROM users WHERE email = ?", (email,))
        if existing:
            return False, "البريد الإلكتروني مستخدم مسبقًا", None

        state_row = db.fetchone(
            "SELECT id, state_name, state_number FROM states WHERE lower(state_name) = lower(?) OR lower(state_number) = lower(?)",
            (state_name, state_name),
        )

        user_id = db.insert(
            "users",
            {
                "username": GamePortalService._slugify_username(game_name),
                "email": email,
                "password_hash": SecurityManager.hash_password(password),
                "full_name": game_name,
                "game_name": game_name,
                "state": state_row["state_name"] if state_row else state_name,
                "state_id": state_row["id"] if state_row else None,
                "player_power": player_power,
                "specialization": specialization,
                "discord_id": discord_id,
                "role": "member",
                "alliance_role": "member",
                "is_email_verified": 0,
                "is_admin": 0,
            },
        )
        if not user_id:
            return False, "تعذر إنشاء الحساب", None

        if state_row:
            db.insert(
                "state_members",
                {
                    "user_id": user_id,
                    "state_id": state_row["id"],
                    "role": "member",
                },
            )

        return True, "تم تسجيل العضو الجديد بنجاح", user_id

    @staticmethod
    def authenticate_member(login_id: str, password: str, ip_address: str | None = None) -> Tuple[bool, str, Optional[int]]:
        user = db.fetchone(
            """
            SELECT id, password_hash, is_active, is_banned, role
            FROM users
            WHERE lower(email) = lower(?) OR lower(username) = lower(?)
            """,
            (login_id, login_id),
        )
        if not user:
            db.insert("login_attempts", {"username": login_id, "ip_address": ip_address, "success": 0})
            return False, "بيانات دخول العضو غير صحيحة", None
        if user["role"] not in {"member", "admin", "super_owner", "state_admin"}:
            return False, "هذا الحساب ليس حساب عضو", None
        if not user["is_active"] or user.get("is_banned"):
            return False, "الحساب معطل أو محظور", None
        if not SecurityManager.verify_password(password, user["password_hash"]):
            db.insert("login_attempts", {"username": login_id, "ip_address": ip_address, "success": 0})
            return False, "بيانات دخول العضو غير صحيحة", None

        db.update("users", {"last_login": datetime.now().isoformat()}, {"id": user["id"]})
        db.insert("login_attempts", {"username": login_id, "ip_address": ip_address, "success": 1})
        return True, "تم تسجيل دخول العضو بنجاح", user["id"]

    @staticmethod
    def authenticate_state(login_id: str, password: str) -> Tuple[bool, str, Optional[int]]:
        state = db.fetchone(
            """
            SELECT id, state_name, password_hash, is_active
            FROM states
            WHERE lower(contact_email) = lower(?)
               OR lower(state_name) = lower(?)
               OR lower(state_number) = lower(?)
            """,
            (login_id, login_id, login_id),
        )
        if not state:
            return False, "حساب الولاية غير موجود", None
        if not state["is_active"]:
            return False, "حساب الولاية معطل", None
        if not SecurityManager.verify_password(password, state["password_hash"]):
            return False, "بيانات دخول الولاية غير صحيحة", None
        return True, "تم تسجيل دخول الولاية بنجاح", state["id"]

    @staticmethod
    def create_state_account(payload: Dict[str, Any], admin_user_id: Optional[int]) -> Tuple[bool, str, Optional[int]]:
        state_name = payload.get("state_name", "").strip()
        state_number = payload.get("state_number", "").strip()
        contact_email = payload.get("contact_email", "").strip().lower()
        password = payload.get("password", "")
        if not state_name or not state_number or not password:
            return False, "اسم الولاية ورقمها وكلمة المرور مطلوبة", None
        existing = db.fetchone(
            "SELECT id FROM states WHERE lower(state_name) = lower(?) OR lower(state_number) = lower(?)",
            (state_name, state_number),
        )
        if existing:
            return False, "الولاية موجودة بالفعل", None
        state_id = db.insert(
            "states",
            {
                "state_name": state_name,
                "state_number": state_number,
                "password_hash": SecurityManager.hash_password(password),
                "admin_user_id": admin_user_id,
                "description": payload.get("description", "").strip(),
                "contact_email": contact_email,
                "contact_discord": payload.get("contact_discord", "").strip(),
                "is_active": 1,
            },
        )
        if not state_id:
            return False, "تعذر إنشاء الولاية", None
        if admin_user_id:
            db.insert("state_members", {"user_id": admin_user_id, "state_id": state_id, "role": "admin"})
        return True, "تم إنشاء الولاية بنجاح", state_id

    @staticmethod
    def update_state_account(state_id: int, payload: Dict[str, Any]) -> bool:
        update_data = {
            "state_name": payload.get("state_name", "").strip(),
            "state_number": payload.get("state_number", "").strip(),
            "description": payload.get("description", "").strip(),
            "contact_email": payload.get("contact_email", "").strip().lower(),
            "contact_discord": payload.get("contact_discord", "").strip(),
            "updated_at": datetime.now().isoformat(),
        }
        filtered = {key: value for key, value in update_data.items() if value != ""}
        if payload.get("password"):
            filtered["password_hash"] = SecurityManager.hash_password(payload["password"])
        return bool(filtered) and db.update("states", filtered, {"id": state_id})

    @staticmethod
    def toggle_state(state_id: int, enabled: bool) -> bool:
        return db.update("states", {"is_active": 1 if enabled else 0, "updated_at": datetime.now().isoformat()}, {"id": state_id})

    @staticmethod
    def update_member_account(user_id: int, payload: Dict[str, Any]) -> bool:
        update_data: Dict[str, Any] = {"updated_at": datetime.now().isoformat()}
        if "game_name" in payload:
            update_data["game_name"] = payload["game_name"].strip()
            update_data["full_name"] = payload["game_name"].strip()
        if "state" in payload:
            update_data["state"] = payload["state"].strip()
        if "specialization" in payload:
            update_data["specialization"] = payload["specialization"].strip()
        if "discord_id" in payload:
            update_data["discord_id"] = payload["discord_id"].strip()
        if "player_power" in payload:
            try:
                update_data["player_power"] = int(str(payload["player_power"]).replace(",", "").strip() or "0")
            except ValueError:
                return False
        if "alliance_role" in payload:
            update_data["alliance_role"] = payload["alliance_role"].strip()
        return db.update("users", update_data, {"id": user_id})

    @staticmethod
    def set_member_ban(user_id: int, is_banned: bool) -> bool:
        return db.update("users", {"is_banned": 1 if is_banned else 0, "updated_at": datetime.now().isoformat()}, {"id": user_id})

    @staticmethod
    def set_map_settings(shape: str, layers: int, spacing: int, sort_by: str, custom_layout: Optional[List[Dict[str, Any]]] = None) -> bool:
        payload = {
            "shape": shape if shape in {"circle", "square", "custom"} else "circle",
            "layers": max(1, layers),
            "spacing": max(40, spacing),
            "sort_by": sort_by if sort_by in {"power", "specialization"} else "power",
            "custom_layout": custom_layout or [],
        }
        return GamePortalService.set_setting("map_settings", payload)

    @staticmethod
    def upsert_calculator_modifier(calculator_type: str, target_key: str, resource_key: str, multiplier: float) -> bool:
        existing = db.fetchone(
            "SELECT id FROM calculator_modifiers WHERE calculator_type = ? AND target_key = ? AND resource_key = ?",
            (calculator_type, target_key, resource_key),
        )
        data = {
            "calculator_type": calculator_type,
            "target_key": target_key,
            "resource_key": resource_key,
            "multiplier": multiplier,
            "updated_at": datetime.now().isoformat(),
        }
        if existing:
            return db.update("calculator_modifiers", data, {"id": existing["id"]})
        return db.insert("calculator_modifiers", data) is not None

    @staticmethod
    def _resource_multiplier(calculator_type: str, target_key: str, resource_key: str) -> float:
        row = db.fetchone(
            "SELECT multiplier FROM calculator_modifiers WHERE calculator_type = ? AND target_key = ? AND resource_key = ?",
            (calculator_type, target_key, resource_key),
        )
        return float(row["multiplier"]) if row else 1.0

    @staticmethod
    def _round_resource(value: float) -> int:
        return int(round(value))

    @staticmethod
    def calculate_training(troop_type: str, tier: int, count: int, speed_bonus_percent: float = 0.0) -> Dict[str, Any]:
        data = GamePortalService.calculators_data()["troops"]
        troop = data[troop_type]
        tier_data = troop["tiers"][str(tier)]
        effective_speed = max(0.05, 1 + (speed_bonus_percent / 100.0))
        resources = {
            resource: GamePortalService._round_resource(tier_data[resource] * count * GamePortalService._resource_multiplier("troops", troop_type, resource))
            for resource in ("food", "wood", "coal", "iron")
        }
        total_minutes = (tier_data["time_minutes"] * count) / effective_speed
        return {
            "category": "troops",
            "label": troop["name_ar"],
            "tier": tier,
            "count": count,
            "resources": resources,
            "time_minutes": round(total_minutes, 2),
            "speedups_minutes": math.ceil(total_minutes),
        }

    @staticmethod
    def calculate_upgrade(category: str, target_key: str, current_level: int, target_level: int, speed_bonus_percent: float = 0.0) -> Dict[str, Any]:
        source = GamePortalService.calculators_data()[category]
        entry = source[target_key]
        base = entry["base"]
        growth = float(entry["growth"])
        effective_speed = max(0.05, 1 + (speed_bonus_percent / 100.0))

        if target_level <= current_level:
            raise ValueError("المستوى المستهدف يجب أن يكون أعلى من الحالي")

        totals = {"food": 0, "wood": 0, "coal": 0, "iron": 0}
        total_minutes = 0.0
        breakdown = []

        for level in range(current_level + 1, target_level + 1):
            level_costs = {}
            factor = growth ** max(level - 1, 0)
            for resource in totals:
                value = GamePortalService._round_resource(
                    base[resource] * factor * GamePortalService._resource_multiplier(category, target_key, resource)
                )
                totals[resource] += value
                level_costs[resource] = value
            level_time = round((base["time_minutes"] * factor) / effective_speed, 2)
            total_minutes += level_time
            breakdown.append({"level": level, "resources": level_costs, "time_minutes": level_time})

        return {
            "category": category,
            "label": entry["name_ar"],
            "from_level": current_level,
            "to_level": target_level,
            "resources": totals,
            "time_minutes": round(total_minutes, 2),
            "speedups_minutes": math.ceil(total_minutes),
            "breakdown": breakdown,
        }

    @staticmethod
    def _member_rows_for_map(state_name: Optional[str]) -> List[Dict[str, Any]]:
        query = """
            SELECT id, username, full_name, game_name, state, player_power, specialization
            FROM users
            WHERE role IN ('member', 'admin', 'state_admin')
              AND is_active = 1
              AND is_banned = 0
        """
        params: Tuple[Any, ...] = ()
        if state_name:
            query += " AND lower(state) = lower(?)"
            params = (state_name,)
        return db.fetchall(query + " ORDER BY player_power DESC, username ASC", params)

    @staticmethod
    def _sort_members(members: List[Dict[str, Any]], sort_by: str) -> List[Dict[str, Any]]:
        if sort_by == "specialization":
            return sorted(members, key=lambda item: ((item.get("specialization") or "zzz"), -(item.get("player_power") or 0)))
        return sorted(members, key=lambda item: (-(item.get("player_power") or 0), item.get("username") or ""))

    @staticmethod
    def compute_bear_map(state_name: Optional[str] = None) -> Dict[str, Any]:
        settings = GamePortalService.get_setting("map_settings", GamePortalService.DEFAULT_MAP_SETTINGS)
        members = GamePortalService._sort_members(
            GamePortalService._member_rows_for_map(state_name),
            settings.get("sort_by", "power"),
        )
        shape = settings.get("shape", "circle")
        layers = int(settings.get("layers", 3))
        spacing = int(settings.get("spacing", 130))
        custom_layout = settings.get("custom_layout", [])
        points: List[Dict[str, Any]] = []

        if shape == "custom" and custom_layout:
            for index, member in enumerate(members):
                seed = custom_layout[index % len(custom_layout)]
                points.append(
                    {
                        "member_id": member["id"],
                        "name": member.get("game_name") or member.get("full_name") or member["username"],
                        "power": member.get("player_power") or 0,
                        "specialization": member.get("specialization") or "غير محدد",
                        "slot": seed.get("slot", f"C-{index + 1}"),
                        "x": float(seed.get("x", 0)),
                        "y": float(seed.get("y", 0)),
                    }
                )
        elif shape == "square":
            current_layer = 1
            slot_index = 0
            for member in members:
                side_len = current_layer * 2 + 1
                perimeter = max(8, (side_len - 1) * 4)
                offset = slot_index % perimeter
                if slot_index and offset == 0:
                    current_layer = min(current_layer + 1, layers)
                ring = min(current_layer, layers)
                edge = max(1, perimeter // 4)
                step = (offset % edge) - (edge // 2)
                distance = ring * spacing
                if offset < edge:
                    x, y = step * (spacing / max(edge // 2, 1)), -distance
                elif offset < edge * 2:
                    x, y = distance, step * (spacing / max(edge // 2, 1))
                elif offset < edge * 3:
                    x, y = -step * (spacing / max(edge // 2, 1)), distance
                else:
                    x, y = -distance, -step * (spacing / max(edge // 2, 1))
                points.append(
                    {
                        "member_id": member["id"],
                        "name": member.get("game_name") or member.get("full_name") or member["username"],
                        "power": member.get("player_power") or 0,
                        "specialization": member.get("specialization") or "غير محدد",
                        "slot": f"S-{slot_index + 1}",
                        "x": round(x, 2),
                        "y": round(y, 2),
                    }
                )
                slot_index += 1
        else:
            slot_index = 0
            for layer in range(1, layers + 1):
                radius = layer * spacing
                seats = max(6, layer * 8)
                for seat in range(seats):
                    if slot_index >= len(members):
                        break
                    angle = (2 * math.pi * seat) / seats
                    member = members[slot_index]
                    points.append(
                        {
                            "member_id": member["id"],
                            "name": member.get("game_name") or member.get("full_name") or member["username"],
                            "power": member.get("player_power") or 0,
                            "specialization": member.get("specialization") or "غير محدد",
                            "slot": f"R{layer}-{seat + 1}",
                            "x": round(math.cos(angle) * radius, 2),
                            "y": round(math.sin(angle) * radius, 2),
                        }
                    )
                    slot_index += 1

        state_row = None
        if state_name:
            state_row = db.fetchone("SELECT id FROM states WHERE lower(state_name) = lower(?)", (state_name,))
        if state_row:
            db.execute("DELETE FROM member_positions WHERE state_id = ?", (state_row["id"],))
        for index, point in enumerate(points):
            db.insert(
                "member_positions",
                {
                    "state_id": state_row["id"] if state_row else None,
                    "user_id": point["member_id"],
                    "slot_label": point["slot"],
                    "shape": shape,
                    "pos_x": point["x"],
                    "pos_y": point["y"],
                    "sort_order": index + 1,
                    "assigned_power": point["power"],
                    "updated_at": datetime.now().isoformat(),
                },
            )

        return {
            "shape": shape,
            "layers": layers,
            "spacing": spacing,
            "points": points,
            "state_name": state_name,
        }

    @staticmethod
    def upsert_knowledge_entry(category: str, entry_name: str, tags: Iterable[str], summary: str, best_use: str, source: str = "owner") -> bool:
        tags_csv = ", ".join(tag.strip() for tag in tags if tag.strip())
        metadata = json.dumps({"best_use": best_use, "tags": [tag.strip() for tag in tags if tag.strip()]}, ensure_ascii=False)
        existing = db.fetchone(
            "SELECT id FROM knowledge_entries WHERE category = ? AND entry_name = ?",
            (category, entry_name),
        )
        payload = {
            "category": category,
            "entry_name": entry_name,
            "tags": tags_csv,
            "summary": summary,
            "metadata_json": metadata,
            "source": source,
            "is_active": 1,
            "updated_at": datetime.now().isoformat(),
        }
        if existing:
            return db.update("knowledge_entries", payload, {"id": existing["id"]})
        return db.insert("knowledge_entries", payload) is not None

    @staticmethod
    def search_knowledge(question: str, limit: int = 5) -> List[Dict[str, Any]]:
        tokens = [token.strip().lower() for token in question.replace("،", " ").replace(",", " ").split() if token.strip()]
        rows = db.fetchall(
            "SELECT id, category, entry_name, tags, summary, metadata_json FROM knowledge_entries WHERE is_active = 1"
        )
        scored: List[Tuple[int, Dict[str, Any]]] = []
        for row in rows:
            haystack = " ".join(
                [
                    row.get("category", ""),
                    row.get("entry_name", ""),
                    row.get("tags", ""),
                    row.get("summary", ""),
                    row.get("metadata_json", ""),
                ]
            ).lower()
            score = sum(1 for token in tokens if token in haystack)
            if score:
                scored.append((score, row))
        scored.sort(key=lambda item: (-item[0], item[1]["category"], item[1]["entry_name"]))
        return [row for _, row in scored[:limit]]

    @staticmethod
    def _local_ai_answer(user: Dict[str, Any], question: str, snippets: List[Dict[str, Any]]) -> str:
        profile_name = user.get("game_name") or user.get("username") or "اللاعب"
        profile_bits = [
            f"اللاعب: {profile_name}",
            f"القوة: {user.get('player_power') or 0:,}",
            f"التخصص: {user.get('specialization') or 'غير محدد'}",
            f"الولاية: {user.get('state') or 'غير محددة'}",
        ]

        lines = ["تحليل المساعد الخبير:", " | ".join(profile_bits)]
        if snippets:
            lines.append("أفضل المعلومات المطابقة لسؤالك:")
            for snippet in snippets:
                metadata = {}
                try:
                    metadata = json.loads(snippet.get("metadata_json") or "{}")
                except json.JSONDecodeError:
                    metadata = {}
                lines.append(f"- [{snippet['category']}] {snippet['entry_name']}: {snippet['summary']}")
                if metadata.get("best_use"):
                    lines.append(f"  الاستخدام الأفضل: {metadata['best_use']}")
        else:
            lines.append("لم أجد تطابقًا مباشرًا في قاعدة المعرفة، لذلك سأعطيك توجيهًا عمليًا عامًا.")

        if "دب" in question or "bear" in question.lower():
            lines.append("للدب: رتّب الأقوى أولًا، ثم وزّع الأدوار الهجومية في المواقع المتقدمة، ولا تترك التخصصات الدفاعية تستهلك أفضل أماكن الضرر.")
        if "بحث" in question or "research" in question.lower():
            lines.append("إذا كان هدفك تسريع النمو فابدأ بأبحاث التطوير، وإذا كان هدفك القتال أو التجمعات فادفع أبحاث القتال أولًا.")
        if "بناء" in question or "مبنى" in question or "building" in question.lower():
            lines.append("عند الترقية، حافظ على توازن بين المقر ومركز الأبحاث والثكنة حتى لا تتعطل متطلبات الفتح أو التدريب.")

        return "\n".join(lines)

    @staticmethod
    def _remote_ai_answer(user: Dict[str, Any], question: str, snippets: List[Dict[str, Any]]) -> Optional[str]:
        if not Config.AI_API_KEY:
            return None

        context_payload = {
            "player": {
                "game_name": user.get("game_name") or user.get("username"),
                "power": user.get("player_power") or 0,
                "specialization": user.get("specialization") or "غير محدد",
                "state": user.get("state") or "غير محددة",
                "academy_level": user.get("academy_level") or 0,
            },
            "knowledge_matches": [
                {
                    "category": snippet.get("category"),
                    "entry_name": snippet.get("entry_name"),
                    "summary": snippet.get("summary"),
                    "metadata_json": snippet.get("metadata_json"),
                }
                for snippet in snippets
            ],
        }

        system_prompt = (
            "You are a Whiteout Survival strategy expert for TNT alliance. "
            "Respond in Arabic, be practical, concise, and tailor the answer to the player's profile and supplied knowledge."
        )
        user_prompt = (
            f"Player context: {json.dumps(context_payload, ensure_ascii=False)}\n"
            f"Question: {question}\n"
            "Give an actionable answer with priorities, not generic advice."
        )

        try:
            response = requests.post(
                Config.AI_API_BASE_URL,
                headers={
                    "Authorization": f"Bearer {Config.AI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": Config.AI_MODEL_NAME,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.4,
                },
                timeout=Config.AI_REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            payload = response.json()
            choices = payload.get("choices") or []
            if not choices:
                return None
            message = choices[0].get("message") or {}
            content = message.get("content", "").strip()
            return content or None
        except Exception:
            return None

    @staticmethod
    def ai_answer(user_id: int, question: str) -> Dict[str, Any]:
        user = db.fetchone(
            "SELECT game_name, username, player_power, specialization, state, academy_level, building_levels_json, research_levels_json FROM users WHERE id = ?",
            (user_id,),
        ) or {}
        snippets = GamePortalService.search_knowledge(question)
        answer = GamePortalService._remote_ai_answer(user, question, snippets)
        if not answer:
            answer = GamePortalService._local_ai_answer(user, question, snippets)
        db.insert(
            "ai_chat_logs",
            {
                "user_id": user_id,
                "question": question,
                "answer": answer,
                "context_json": json.dumps({"matches": [item["entry_name"] for item in snippets]}, ensure_ascii=False),
            },
        )
        return {"answer": answer, "matches": snippets}

    @staticmethod
    def owner_dashboard_data() -> Dict[str, Any]:
        states = db.fetchall(
            "SELECT id, state_name, state_number, contact_email, contact_discord, description, is_active, created_at FROM states ORDER BY state_number, state_name"
        )
        members = db.fetchall(
            """
            SELECT id, email, username, game_name, state, player_power, specialization, role, alliance_role, is_banned, created_at
            FROM users
            WHERE role IN ('member', 'admin', 'state_admin')
            ORDER BY player_power DESC, created_at DESC
            """
        )
        knowledge_counts = db.fetchall(
            "SELECT category, COUNT(*) AS count FROM knowledge_entries WHERE is_active = 1 GROUP BY category ORDER BY category"
        )
        modifiers = db.fetchall(
            "SELECT calculator_type, target_key, resource_key, multiplier FROM calculator_modifiers ORDER BY calculator_type, target_key, resource_key"
        )
        return {
            "states": states,
            "members": members,
            "map_settings": GamePortalService.get_setting("map_settings", GamePortalService.DEFAULT_MAP_SETTINGS),
            "knowledge_counts": knowledge_counts,
            "calculator_modifiers": modifiers,
        }

    @staticmethod
    def member_dashboard_data(user_id: int) -> Dict[str, Any]:
        user = db.fetchone(
            """
            SELECT id, username, email, game_name, state, player_power, specialization, discord_id,
                   academy_level, building_levels_json, research_levels_json, alliance_role
            FROM users WHERE id = ?
            """,
            (user_id,),
        ) or {}
        state_name = user.get("state")
        return {
            "profile": user,
            "map_data": GamePortalService.compute_bear_map(state_name),
            "knowledge_highlights": db.fetchall(
                "SELECT category, entry_name, summary FROM knowledge_entries WHERE is_active = 1 ORDER BY category, entry_name LIMIT 8"
            ),
            "calculator_catalog": GamePortalService.calculators_data(),
        }