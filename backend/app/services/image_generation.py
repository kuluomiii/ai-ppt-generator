"""AI 图片生成业务逻辑：风格模板、提示词优化、记录数限制。

三种风格各有独立的中文提示词模板，LLM 负责根据用户主题和比例
填充模板中的占位符（[TOPIC]、[ASPECT_RATIO] 等），保证最终提示词
不含未处理的方括号变量。用户输入的中文主题必须原样进入最终提示词，
图片中的所有文字要求使用简体中文。
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
# 风格模板：标识符 → 完整中文提示词骨架
# 占位符由 LLM 在 optimize_prompt() 中根据用户输入填充
# 要求：用户中文主题必须原样进入最终提示词；图片中所有文字使用简体中文
# ---------------------------------------------------------------------------
STYLE_TEMPLATES: dict[StyleTemplate, str] = {
    "minimal_doodle": """\
简约手绘涂鸦风格的教育信息图，[ASPECT_RATIO] 比例，讲解主题：[TOPIC]。

=== 标题样式 ===
"[MAIN_TITLE]" 使用粗体、随性的手写马克笔字体，包裹在手绘对话气泡、横幅或云朵形状中
字体颜色：[TITLE_COLOR]（例如：黑色、深蓝色）
质感：纸面墨水笔触

=== 场景与布局 ===
构图：[LAYOUT_TYPE]（例如：四象限均衡网格 / 带手绘箭头的纵向流程图 / 左右对比分栏 / 带文本框的密集信息页 / 阶梯式分步流程，依据下方主要内容的逻辑选择）
背景：干净的白纸、淡淡的点阵网格或浅浅的笔记本横线，高亮度、平光（无阴影）

=== 主要内容 ===

[STEP_1] 画面：[DESCRIPTION_OF_VISUAL_ELEMENT_1] 动作：简单的 2D 线条速写、火柴人或可爱的简化图标 标注："[LABEL_TEXT_1]" 使用工整的手写印刷体

[STEP_2] 画面：[DESCRIPTION_OF_VISUAL_ELEMENT_2] 动作：[ACTION_OR_STATE] 标注："[LABEL_TEXT_2]" 连接：[ARROW_STYLE]（例如：虚线 / 弯曲的涂鸦箭头 / 粗马克笔笔触）从上一步指向此处

[STEP_3] [按后续步骤需要继续]

=== 视觉风格 ===
材质：墨水笔轮廓线（线条粗细有变化），马克笔或水彩荧光笔填充。
渲染：2D 平面插画，扫描速写本质感，干净的矢量外观。
色彩：白色背景为主，搭配柔和的粉彩点缀（薄荷绿、淡黄、浅粉、婴儿蓝），黑色粗轮廓线形成对比。

=== 装饰元素 ===
小涂鸦（闪光、星星、灯泡、感叹号）、波浪线、圆点、和纸胶带纹理、回形针，活泼地填充留白区域。

=== 氛围 ===
友好、有条理、清晰、可爱、平易近人，"聪明休闲"的学习氛围。

=== 文字要求 ===
图片中出现的所有文字（标题、标注、对话框、信息框）必须使用简体中文，文字清晰可读、无错别字。

质量：高品质 2D 矢量画风，线条干净，文字清晰可读，布局视觉均衡。""",

    "chiikawa_science": """\
吉伊卡哇（ちいかわ）官方漫画风格的教育插画，[ASPECT_RATIO] 比例，讲解主题：[TOPIC]。

=== 标题 ===
"[MAIN_TITLE]" 使用柔和粉色（#FFB7C5）圆体字
[SUBTITLE_IF_NEEDED]

=== 场景与布局 ===
布局：[LAYOUT_TYPE]（例如：跨越鸿沟的问题-解决方案桥梁 / 环形生命周期流程 / 带对勾和叉号的对比表格 / "该做 vs 不该做"分屏 / 输入-处理-输出等式 / 纵向特性清单 / 鱼骨因果图 / 收窄漏斗图 / 冰山表层与隐藏部分对比图 / 蜿蜒的路线图旅程 / 分层技术栈，依据下方主要内容的逻辑选择）

背景：奶油色（#FFF8E7）到 [THEME_COLOR] 的柔和渐变，少量 [DECORATIVE_ELEMENTS] 装饰

=== 主要内容 ===
使用不同的吉伊卡哇官方角色，如吉伊卡哇 / 小八猫（哈奇瓦雷）/ 乌萨奇（兔子）

[CONTENT_SECTION_1]

角色：[CHARACTER_NAME]

- [CHARACTER_ACTION_AND_EXPRESSION]
- [PROPS_OR_ITEMS]

画面：[KEY_VISUAL_ELEMENT]

标注："[LABEL_TEXT]"

[DIALOGUE_OR_ANNOTATION]

[CONTENT_SECTION_2]

[结构同上]

[CONTENT_SECTION_N]

[按需继续]

=== 关键概念 ===
[NUMBER] 个带可爱边框的漂浮信息框：

信息框 1："[CONCEPT_1]"
信息框 2："[CONCEPT_2]"
信息框 N："[CONCEPT_N]"

=== 吉伊卡哇风格 ===
官方吉伊卡哇美学：圆润的身体、大而闪亮的眼睛、粉色腮红、小小的四肢、Q版比例、温柔的线条画风。

=== 氛围 ===
[EMOTIONAL_TONE]，[EDUCATIONAL_GOAL]，可爱但有信息量。

=== 文字要求 ===
图片中出现的所有文字（标题、标注、对话框、信息框）必须使用简体中文，文字清晰可读、无错别字。

质量：高品质吉伊卡哇插画，清晰的视觉层次，[PURPOSE]。""",

    "shinchan_education": """\
蜡笔小新（臼井仪人）动画风格的教育插画，[ASPECT_RATIO] 比例，讲解主题：[TOPIC]。

=== 标题 ===
"[MAIN_TITLE]" 使用俏皮的手绘马克笔字体，色彩明快
[SUBTITLE_IF_NEEDED]

=== 场景与布局 ===
布局：[LAYOUT_TYPE]（例如：跨越鸿沟的问题-解决方案桥梁 / 环形生命周期流程 / 带对勾和叉号的对比表格 / "该做 vs 不该做"分屏 / 输入-处理-输出等式 / 纵向特性清单 / 鱼骨因果图 / 收窄漏斗图 / 冰山表层与隐藏部分对比图 / 蜿蜒的路线图旅程 / 分层技术栈，依据下方主要内容的逻辑选择）

背景：简单的粉彩色块、摇晃的手绘场景、极简细节。

=== 主要内容 ===
使用不同的蜡笔小新角色，如野原新之助（小新）、野原向日葵（小葵）和小白狗。

[CONTENT_SECTION_1]

角色：[CHARACTER_NAME]

[CHARACTER_ACTION_AND_EXPRESSION]

[PROPS_OR_ITEMS]

画面：[KEY_VISUAL_ELEMENT]

标注："[LABEL_TEXT]"

[DIALOGUE_OR_ANNOTATION]

[CONTENT_SECTION_2]

[结构同上]

[CONTENT_SECTION_N]

[按需继续]

=== 关键概念 ===
[NUMBER] 个带粗糙蜡笔质感边框的漂浮信息框：

信息框 1："[CONCEPT_1]"
信息框 2："[CONCEPT_2]"
信息框 N："[CONCEPT_N]"

=== 蜡笔小新风格 ===
蜡笔小新动画美学：明显歪扭不均匀的轮廓线、无复杂阴影的平涂上色、变形的人物比例、土豆形状的头部、简单的几何背景、粗而有表现力的眉毛。

=== 氛围 ===
[EMOTIONAL_TONE]，[EDUCATIONAL_GOAL]，幽默、轻松、调皮。

=== 文字要求 ===
图片中出现的所有文字（标题、标注、对话框、信息框）必须使用简体中文，文字清晰可读、无错别字。

质量：高品质幽默教育插画，搞笑氛围，清晰的视觉层次，[PURPOSE]。""",
}

MAX_RECORDS_PER_USER = 10

# 用于检测未处理占位符的正则：匹配 [UPPERCASE_WORDS] 形式
_PLACEHOLDER_RE = re.compile(r"\[[A-Z][A-Z_]+\]")


def build_style_prompt(style: StyleTemplate, raw_prompt: str, aspect_ratio: str) -> str:
    """将风格模板与用户原始需求拼接为 LLM user prompt。

    模板本身作为参考结构附在 prompt 末尾，让 LLM 理解输出格式；
    同时明确要求 LLM 将所有占位符替换为具体内容、保留用户的中文主题。
    """
    template = STYLE_TEMPLATES[style]
    return (
        f"请为下面的主题生成一份完整的中文图片生成提示词。\n"
        f"主题（用户的原始需求）：{raw_prompt}\n"
        f"宽高比：{aspect_ratio}\n\n"
        f"以下方模板作为结构参考。"
        f"你必须把每一个 [占位符] 替换为与主题相关的具体内容，"
        f"用户的中文主题必须原样保留在最终提示词中（不要翻译成英文）。"
        f"最终提示词中不得留下任何方括号占位符。"
        f"最终提示词必须是一段连贯的中文文本，"
        f"并且明确要求：图片中的所有文字使用简体中文，文字清晰、无错别字。\n\n"
        f"--- 模板开始 ---\n{template}\n--- 模板结束 ---"
    )


async def optimize_prompt(
    *,
    chat: BaseChatModel,
    style: StyleTemplate,
    raw_prompt: str,
    aspect_ratio: str = "1:1",
) -> str:
    """调用 LLM 将用户原始需求 + 风格模板优化为适合 Seedream 的中文提示词。

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
        "你是一位专业的 AI 图片提示词工程师。"
        "给定一个风格模板和用户主题，产出一份完整的中文图片生成提示词。"
        "把所有 [占位符] 替换为与主题相关的具体内容，"
        "用户的中文主题必须原样出现在最终提示词中。"
        "最终提示词必须包含文字要求：图片中的所有文字使用简体中文，文字清晰、无错别字。"
        "只输出最终提示词本身——不要解释、不要 markdown 代码块。"
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
