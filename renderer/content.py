from rich.console import Group, RenderableType
from rich.table import Table
from rich.text import Text

from components.enemy import EnemyType
from components.item import ItemType
from game import Game
from renderer import glyphs


PanelMode = str


def side_content(game: Game, panel_mode: PanelMode) -> RenderableType:
    if panel_mode == "inventory":
        return "\n".join(
            [
                "인벤토리",
                "",
                *game.inventory.display_lines(),
                "",
                "1-9: 선택 아이템 사용",
                "사용해야 스탯이 바뀝니다.",
            ]
        )
    if panel_mode == "leaderboard":
        return leaderboard_content(game)
    if panel_mode == "help":
        return help_text()
    if panel_mode == "debug":
        return debug_text(game)
    return stats_content(game)


def leaderboard_content(game: Game) -> RenderableType:
    if not game.leaderboard.entries:
        return Text("리더보드\n\n아직 기록이 없습니다.", style="bold")

    title = Text("리더보드\n", style="bold #7cc7ff")
    table = Table.grid(padding=(0, 1))
    table.add_column(justify="right", no_wrap=True)
    table.add_column(no_wrap=True)
    table.add_column(justify="right", no_wrap=True)
    table.add_column(justify="right", no_wrap=True)
    table.add_column(justify="right", no_wrap=True)
    table.add_column(justify="right", no_wrap=True)
    table.add_row(
        Text("#", style="bold #7f8ea3"),
        Text("이름", style="bold #7f8ea3"),
        Text("점수", style="bold #7f8ea3"),
        Text("층", style="bold #7f8ea3"),
        Text("되감기", style="bold #7f8ea3"),
        Text("시간", style="bold #7f8ea3"),
    )

    for rank, entry in enumerate(game.leaderboard.entries, start=1):
        style = rank_style(rank)
        table.add_row(
            Text(str(rank), style=style),
            Text(entry.name, style=style),
            Text(f"{entry.score:,}", style=style),
            Text(str(entry.floors_cleared), style=style),
            Text(str(entry.undo_used), style=style),
            Text(format_seconds(entry.time_seconds), style=style),
        )

    hint = Text("\nq/Esc 종료  i 인벤토리", style="#7f8ea3")
    return Group(title, table, hint)


def help_text() -> str:
    return "\n".join(
        [
            "조작법",
            "",
            "WASD/방향키  이동",
            "z            주변 공격",
            "u            되감기",
            "i            인벤토리",
            "l            리더보드",
            "Ctrl+D       A* 디버그 경로",
            "q/Esc        종료",
            "",
            "범례",
            "어두운 빈칸  방 바닥",
            "어두운 길    통로",
            "어두운 벽    벽",
            f"{glyphs.STAIRS_DOWN} 다음 층 계단",
            f"{glyphs.ATK_ITEM} 공격  {glyphs.DEF_ITEM} 방어",
            f"{glyphs.HEAL_ITEM} 회복  {glyphs.RANGE_ITEM} 범위",
        ]
    )


def stats_content(game: Game) -> Group:
    status = "승리" if game.victory else "게임 오버" if game.game_over else "진행 중"
    stats = Table.grid(padding=(0, 1))
    stats.add_column(width=8, no_wrap=True)
    stats.add_column(no_wrap=True)
    title = Text("던전 크롤러\n", style="bold")
    stats.add_row("", "", "")
    add_stat_row(stats, "상태", status)
    add_stat_row(stats, "현재 층", game.floor)
    add_stat_row(stats, "난이도", difficulty_label(game))
    add_stat_row(stats, "방 개수", len(game.dungeon_map.rooms))
    add_stat_row(stats, "클리어", game.floors_cleared)
    add_stat_row(stats, "턴", game.turn_count)
    stats.add_row("", "", "")
    add_stat_row(stats, "목표", f"{glyphs.STAIRS_DOWN} 계단 도착")
    add_stat_row(stats, "방향", game.goal_direction)
    add_stat_row(stats, "거리", game.goal_distance)
    stats.add_row("", "", "")
    add_bar_row(stats, "HP", game.player.hp, game.player.max_hp, "bold red")
    add_bar_row(stats, "XP", game.player.xp % glyphs.XP_GOAL, glyphs.XP_GOAL, "bold cyan", f"{game.player.xp}/{glyphs.XP_GOAL}")
    add_stat_row(stats, "공격력", game.player.atk, "bold #ff9d00")
    add_stat_row(stats, "방어력", game.player.def_, "bold #66ff7a")
    add_stat_row(stats, "범위", game.player.shockwave_radius, "bold #c77dff")
    add_stat_row(stats, "충격파", game.shockwave_cooldown, "bold #ffd166")
    add_bar_row(
        stats,
        "되감기",
        game.undo_stack.remaining(),
        game.undo_stack.max_size,
        "bold green",
    )
    stats.add_row("", "", "")
    add_stat_row(stats, "남은 적", len(game.enemy_manager.get_all()))
    add_stat_row(stats, "구성", enemy_summary(game))
    add_stat_row(stats, "점수", f"{game.score:,}")

    legend = Text(f"\n어두운 바닥  어두운 길  어두운 벽  {glyphs.STAIRS_DOWN} 계단\n? 도움말", style="#7f8ea3")
    renderables: list[RenderableType] = [end_banner(game), title, stats]
    renderables.extend(effect_texts(game))
    renderables.append(legend)
    return Group(*renderables)


def debug_text(game: Game) -> str:
    graph_edges = sum(len(edges) for edges in game.dungeon_map.room_graph.values()) // 2
    return "\n".join(
        [
            "알고리즘 디버그",
            "",
            "맵: 2차원 배열 grid",
            f"방 개수: {len(game.dungeon_map.rooms)}",
            f"그래프 간선 수: {graph_edges}",
            "",
            "되감기: 크기 제한 스택",
            f"스냅샷 수: {len(game.undo_stack)}",
            "",
            "턴: FIFO 큐",
            "순서: 플레이어 -> 적",
            "",
            "적 AI: A*",
            f"디버그 경로 표시: {game.debug_paths}",
            "",
            "적 타입",
            "G: 빨강, 기본형",
            "S: 노랑, 넓은 감지",
            "B: 보라 배경, 높은 체력/공격",
        ]
    )


def message_text(game: Game) -> str:
    if game.game_over:
        if game.victory:
            title = "████ 승리 ████"
            detail = f"최종 점수: {game.score}  클리어 층: {game.floors_cleared}"
        else:
            title = "████ 게임 오버 ████"
            detail = f"최종 점수: {game.score}  생존 턴: {game.turn_count}"
        return "\n".join(
            [
                title,
                detail,
                "l: 리더보드 보기   q/Esc: 종료",
                "",
                *game.messages,
            ]
        )
    return "\n".join(["메시지 로그", "", *game.messages])


def add_stat_row(table: Table, label: str, value: object, value_style: str | None = None) -> None:
    table.add_row(Text(label, style="#c7ced8"), Text(str(value), style=value_style or "#e6e8eb"))


def add_bar_row(
    table: Table,
    label: str,
    current: int,
    maximum: int,
    style: str,
    value: str | None = None,
) -> None:
    display_value = value or f"{current}/{maximum}"
    table.add_row(Text(label, style="#c7ced8"), Text(display_value, style="#e6e8eb"))
    table.add_row(Text(""), bar(current, maximum, style))


def effect_texts(game: Game) -> list[Text]:
    texts: list[Text] = []
    for text in (player_hit_effect_text(game), combat_effect_text(game), item_effect_text(game)):
        if text is not None:
            texts.append(text)
    return texts


def combat_effect_text(game: Game) -> Text | None:
    effect = game.combat_effect
    if effect is None:
        return None
    if effect.category == "shockwave":
        style = "bold black on #ffd166"
    else:
        style = "bold white on #b00020"
    return Text(f"  {effect.title}  {effect.detail}  \n", style=style)


def player_hit_effect_text(game: Game) -> Text | None:
    effect = game.player_hit_effect
    if effect is None:
        return None
    return Text(f"  {effect.title}  {effect.detail}  \n", style="bold white on #d00000")


def item_effect_text(game: Game) -> Text | None:
    effect = game.item_effect
    if effect is None:
        return None
    if effect.category == ItemType.ATK.value:
        style = "bold black on #ff9d00"
    elif effect.category == ItemType.DEF.value:
        style = "bold black on #66ff7a"
    elif effect.category == ItemType.RANGE.value:
        style = "bold white on #7b2cbf"
    else:
        style = "bold black on #6fffe9"
    return Text(f"  {effect.title}  {effect.detail}  \n", style=style)


def end_banner(game: Game) -> Text:
    if not game.game_over:
        return Text("")
    if game.victory:
        return Text("  승리! 던전을 클리어했습니다  \n", style="bold white on green")
    return Text("  게임 오버  \n", style="bold white on red")


def difficulty_label(game: Game) -> str:
    if game.floor <= 1:
        return "보통"
    if game.floor == 2:
        return "위험"
    return "매우 위험"


def enemy_summary(game: Game) -> str:
    counts = game.enemy_manager.type_counts()
    return f"G {counts[EnemyType.GRUNT]} / S {counts[EnemyType.SCOUT]} / B {counts[EnemyType.BRUTE]}"


def rank_style(rank: int) -> str:
    if rank == 1:
        return "bold #ffd166"
    if rank == 2:
        return "bold #cdd6e0"
    if rank == 3:
        return "bold #ff9d6c"
    return "#e6e8eb"


def format_seconds(seconds: int) -> str:
    minutes, remain = divmod(max(0, seconds), 60)
    return f"{minutes}:{remain:02d}"


def bar(current: int, maximum: int, style: str, width: int = 10) -> Text:
    value = Text("")
    if maximum <= 0:
        value.append("░" * width, style="dim")
        return value
    filled = max(0, min(width, round(width * current / maximum)))
    value.append("█" * filled, style=style)
    value.append("░" * (width - filled), style="dim")
    return value
