"""AI 图片生成业务逻辑：风格模板、提示词优化、记录数限制。

三种风格各有独立的英文提示词模板，LLM 负责根据用户主题和比例
填充模板中的占位符（[TOPIC]、[ASPECT_RATIO] 等），保证最终提示词
不含未处理的方括号变量。
"""

from __future__ import annotations

import logging
import re
import uuid

from langchain_core.language_models.chat_models import BaseChatModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.image_project import ImageProject
from app.schemas.image_project import StyleTemplate
from app.storage.base import Storage

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 风格模板：标识符 → 完整英文提示词骨架
# 占位符由 LLM 在 optimize_prompt() 中根据用户输入填充
# ---------------------------------------------------------------------------
STYLE_TEMPLATES: dict[StyleTemplate, str] = {
    "minimal_doodle": """\
Minimalist hand-drawn doodle style educational infographic, [ASPECT_RATIO], explaining [TOPIC].

=== TITLE STYLE ===
"[MAIN_TITLE]" in bold, casual handwritten marker font, enclosed in a hand-drawn speech bubble, banner, or cloud shape
Font color: [TITLE_COLOR] (e.g., black, dark blue)
Texture: Ink texture on paper

=== SCENE & LAYOUT ===
Composition: [LAYOUT_TYPE] (e.g., four-quadrant balanced grid / vertical flow chart with hand-drawn arrows / side-by-side comparison columns / dense information sheet with text boxes / step-by-step staircase flow, based on the logic of the MAIN CONTENT below)
Background: Clean white paper, subtle dot grid, or faint notebook lines, high brightness, flat lighting (no shadows)

=== MAIN CONTENT ===

[STEP_1] Visual: [DESCRIPTION_OF_VISUAL_ELEMENT_1] Action: Simple 2D line art sketch, stick figures or cute simplified icons Label: "[LABEL_TEXT_1]" in neat handwritten print

[STEP_2] Visual: [DESCRIPTION_OF_VISUAL_ELEMENT_2] Action: [ACTION_OR_STATE] Label: "[LABEL_TEXT_2]" Connection: [ARROW_STYLE] (e.g., dashed line / curvy doodle arrow / thick marker stroke) pointing from previous step

[STEP_3] [Continue as needed for subsequent steps]

=== VISUAL STYLE ===
Material: Ink pen outlines (variable line weight), felt-tip marker or watercolor highlighter fills.
Render: 2D flat illustration, scanned sketchbook aesthetic, clean vector look.
Colors: White background dominates, with soft pastel accents (mint green, pale yellow, soft pink, baby blue) and bold black outlines for contrast.

=== DECORATIVE ELEMENTS ===
Small doodles (sparkles, stars, lightbulbs, exclamation marks), squiggly lines, dots, washi tape textures, paper clips to fill negative space playfully.

=== MOOD ===
Friendly, organized, clear, cute, accessible, "smart-casual" learning vibe.

Quality: High-quality 2D vector art, clean lines, legible text, visually balanced layout.""",

    "chiikawa_science": """\
Chiikawa (ちいかわ) official manga style educational illustration, [ASPECT_RATIO], explaining [TOPIC].

=== TITLE ===
"[MAIN_TITLE]" in soft pink (#FFB7C5) rounded font
[SUBTITLE_IF_NEEDED]

=== SCENE & LAYOUT ===
Layout: [LAYOUT_TYPE] (e.g., problem-solution bridge crossing a gap / circular lifecycle flow / structured comparison table with checks and crosses / "do vs don't" split panel / input-process-output equation / vertical feature list / fishbone cause-effect diagram / narrowing funnel chart / iceberg surface-vs-hidden diagram / winding roadmap journey / layered technology stack, based on the logic of the MAIN CONTENT below)

Background: Soft gradient cream (#FFF8E7) to [THEME_COLOR], minimal [DECORATIVE_ELEMENTS]

=== MAIN CONTENT ===
Use different official Chiikawa Characters such as Chiikawa / Hachiware / Usagi

[CONTENT_SECTION_1]

Character: [CHARACTER_NAME]

- [CHARACTER_ACTION_AND_EXPRESSION]
- [PROPS_OR_ITEMS]

Visual: [KEY_VISUAL_ELEMENT]

Label: "[LABEL_TEXT]"

[DIALOGUE_OR_ANNOTATION]

[CONTENT_SECTION_2]

[Similar structure as above]

[CONTENT_SECTION_N]

[Continue as needed]

=== KEY CONCEPTS ===
[NUMBER] floating info boxes with cute borders:

Box 1: "[CONCEPT_1]"
Box 2: "[CONCEPT_2]"
Box N: "[CONCEPT_N]"

=== CHIIKAWA STYLE ===
Official Chiikawa aesthetic: round bodies, large sparkly eyes, pink blush, tiny limbs, super deformed proportions, gentle line art.

=== MOOD ===
[EMOTIONAL_TONE], [EDUCATIONAL_GOAL], cute but informative.

Quality: High-quality Chiikawa illustration, clear visual hierarchy, [PURPOSE].""",

    "shinchan_education": """\
Crayon Shin-chan (Yoshito Usui) animation style educational illustration, [ASPECT_RATIO], explaining [TOPIC].

=== TITLE ===
"[MAIN_TITLE]" in playful hand-drawn marker font, bright colors
[SUBTITLE_IF_NEEDED]

=== SCENE & LAYOUT ===
Layout: [LAYOUT_TYPE] (e.g., problem-solution bridge crossing a gap / circular lifecycle flow / structured comparison table with checks and crosses / "do vs don't" split panel / input-process-output equation / vertical feature list / fishbone cause-effect diagram / narrowing funnel chart / iceberg surface-vs-hidden diagram / winding roadmap journey / layered technology stack, based on the logic of the MAIN CONTENT below)

Background: Simple pastel colored shapes, wobbly hand-drawn scenery, minimal details.

=== MAIN CONTENT ===
Use different Crayon Shin-chan characters such as Nohara Shinnosuke (Shin-chan), Nohara Himawari, and Shiro the dog.

[CONTENT_SECTION_1]

Character: [CHARACTER_NAME]

[CHARACTER_ACTION_AND_EXPRESSION]

[PROPS_OR_ITEMS]

Visual: [KEY_VISUAL_ELEMENT]

Label: "[LABEL_TEXT]"

[DIALOGUE_OR_ANNOTATION]

[CONTENT_SECTION_2]

[Similar structure as above]

[CONTENT_SECTION_N]

[Continue as needed]

=== KEY CONCEPTS ===
[NUMBER] floating info boxes with rough crayon texture borders:

Box 1: "[CONCEPT_1]"
Box 2: "[CONCEPT_2]"
Box N: "[CONCEPT_N]"

=== SHIN-CHAN STYLE ===
Crayon Shin-chan-inspired aesthetic: distinct wiggly uneven outlines, flat coloring without complex shading, deformed character proportions, potato-shaped heads, simple geometric backgrounds, and thick expressive eyebrows.

=== MOOD ===
[EMOTIONAL_TONE], [EDUCATIONAL_GOAL], humorous, relaxed and cheeky.

Quality: High-quality humorous educational illustration, funny atmosphere, clear visual hierarchy, [PURPOSE].""",
}

MAX_RECORDS_PER_USER = 10

# 用于检测未处理占位符的正则：匹配 [UPPERCASE_WORDS] 形式
_PLACEHOLDER_RE = re.compile(r"\[[A-Z][A-Z_]+\]")


def build_style_prompt(style: StyleTemplate, raw_prompt: str, aspect_ratio: str) -> str:
    """将风格模板与用户原始需求拼接为 LLM user prompt。

    模板本身作为参考结构附在 prompt 末尾，让 LLM 理解输出格式；
    同时明确要求 LLM 将所有占位符替换为具体内容。
    """
    template = STYLE_TEMPLATES[style]
    return (
        f"Please generate a complete English image-generation prompt for the topic below.\n"
        f"Topic (user's original request): {raw_prompt}\n"
        f"Aspect ratio: {aspect_ratio}\n\n"
        f"Use the following template as the structural guide. "
        f"You MUST replace every [PLACEHOLDER] with concrete, topic-specific content. "
        f"Do NOT leave any square-bracket placeholders in your output. "
        f"The final prompt must be a single coherent English text.\n\n"
        f"--- TEMPLATE START ---\n{template}\n--- TEMPLATE END ---"
    )


async def optimize_prompt(
    *,
    chat: BaseChatModel,
    style: StyleTemplate,
    raw_prompt: str,
    aspect_ratio: str = "1:1",
) -> str:
    """调用 LLM 将用户原始需求 + 风格模板优化为适合 Seedream 的英文提示词。

    Parameters
    ----------
    chat : BaseChatModel
        LangChain chat model instance.
    style : StyleTemplate
        风格标识符，决定使用哪个模板。
    raw_prompt : str
        用户输入的原始中文/英文需求描述。
    aspect_ratio : str
        宽高比，如 "1:1"、"16:9"、"9:16"。
    """
    from langchain_core.messages import HumanMessage, SystemMessage

    system = (
        "You are a professional AI image-prompt engineer. "
        "Given a style template and a user topic, produce a complete English image-generation prompt. "
        "Replace ALL [PLACEHOLDER] tokens with concrete, topic-relevant content. "
        "Output ONLY the final prompt — no explanations, no markdown fences."
    )
    user_msg = build_style_prompt(style, raw_prompt, aspect_ratio)

    response = await chat.ainvoke([
        SystemMessage(content=system),
        HumanMessage(content=user_msg),
    ])
    result = response.content.strip()

    # 安全检查：若 LLM 遗漏了占位符，记录警告并做 best-effort 清理
    leftover = _PLACEHOLDER_RE.findall(result)
    if leftover:
        logger.warning(
            "optimize_prompt: %d unresolved placeholder(s) in output for style=%s: %s",
            len(leftover), style, leftover,
        )
        # 移除残留占位符，避免传给 Seedream
        result = _PLACEHOLDER_RE.sub("", result)
        # 清理多余空行
        result = re.sub(r"\n{3,}", "\n\n", result).strip()

    return result


async def enforce_record_limit(
    session: AsyncSession,
    user_id: uuid.UUID,
    storage: Storage,
) -> None:
    """确保用户记录不超过 MAX_RECORDS_PER_USER 条。

    在创建新记录之前调用。若当前已有 ≥ 10 条，删除最早的若干条
    （含关联存储文件），为新记录腾出位置。

    注意：文件删除是 best-effort，失败仅记 warning；DB 操作在同一事务内，
    失败则整体回滚。已删文件属副作用，下次创建时最终一致。
    """
    stmt = (
        select(ImageProject.id, ImageProject.image_key)
        .where(ImageProject.user_id == user_id)
        .order_by(ImageProject.created_at.asc())
    )
    result = await session.execute(stmt)
    rows = result.all()

    if len(rows) < MAX_RECORDS_PER_USER:
        return

    # +1 为新记录腾出位置
    to_delete_count = len(rows) - MAX_RECORDS_PER_USER + 1
    victims = rows[:to_delete_count]

    # Best-effort 删除存储文件（在 DB 事务外，不影响原子性）
    for _, image_key in victims:
        if image_key:
            try:
                storage.delete(image_key)
            except Exception:
                logger.warning("删除图片文件失败 key=%s", image_key, exc_info=True)

    victim_ids = [v.id for v in victims]
    await session.execute(delete(ImageProject).where(ImageProject.id.in_(victim_ids)))
