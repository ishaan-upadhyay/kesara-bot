from pygicord import Paginator
import discord
from discord import Embed, ui
from copy import deepcopy
from typing import Optional, List

custom_emojis = {
    "\U000023EA": "REPLACE (first page",
    "\U00002B05": "REPLACE (previous page)",
    "\U000023F9": "REPLACE (stop session)",
    "\U000027A1": "REPLACE (next page)",
    "\U000023E9": "REPLACE (last page)",
    "\U0001F522": "REPLACE (input numbers)",
    "\U0001F512": "REPLACE (lock unlock)",
}

class Paginator(ui.View):
    def __init__(self, user_id: int, pages: List[Embed], timeout: Optional[float], current_page: int, max_pages: int, embed: Embed, **kwargs):
        super().__init__(user_id=user_id, timeout=timeout)
        self.pages = pages
        self.current_page = current_page
        self.max_pages = max_pages
        self.embed = embed
        self._add_buttons()
        self._enable_buttons()

    def _add_buttons(self) -> None:
        """
        Add all the necessary buttons to the current view
        """
        first_btn = ui.Button(style = discord.ButtonStyle.primary, label="first", emoji="<:right_double_arrow:882752531124584518>")
        async def first_page(self, interaction: discord.Interaction, button: ui.Button):
            self.current_page = 1
            await self._swap_page(interaction)
        first_btn.callback = first_page

        next_btn = ui.Button(style = discord.ButtonStyle.primary, label="next", emoji="<:right_arrow:882751138548551700>")
        async def next_page(self, interaction: discord.Interaction, button: ui.Button):
            self.current_page = self.current_page + 1 if self.current_page + 1 < self.max_pages else self.max_pages
            await self._swap_page(interaction)
        next_btn.callback = next_page

        prev_btn = ui.Button(style = discord.ButtonStyle.primary, label="prev", emoji="<:left_arrow:882751271457685504>")
        async def previous_page(self, interaction: discord.Interaction, button: ui.Button):
            self.current_page = self.current_page - 1 if self.current_page - 1 > 0 else 0
            await self._swap_page(interaction)
        prev_btn.callback = previous_page

        last_btn = ui.Button(style = discord.ButtonStyle.primary, label="last", emoji="<:right_double_arrow:882752531124584518>")
        async def last_page(self, interaction: discord.Interaction, button: ui.Button):
            self.current_page = self.max_pages
            await self._swap_page(interaction)
        last_btn.callback = last_page

        self.add_item(first_btn).add_item(next_btn).add_item(prev_btn).add_item(last_btn)

    def _enable_buttons(self) -> None:
        """
        Enables the correct buttons on current page with respect to max_pages
        """
        if self.current_page == 1:
            for c in self.children:
                if c.label == "previous":
                    c.disabled=True
                    break
        elif self.current_page == self.max_pages:
            for c in self.children:
                if c.label == "next":
                    c.disabled=True
                    break

        """
        Swaps out the current embed being displayed
        """

def pages_from_list(base_embed: Embed, contents: list, max_lines=20):
    pages = []

    for idx, content in enumerate(contents, start=1):
        if len(base_embed.description) + len(content) <= 2000 and idx % max_lines != 0:
            base_embed.description += f"\n{content}"
        else:
            pages.append(base_embed)
            base_embed = deepcopy(base_embed)
            base_embed.description = content

    if base_embed is not None and base_embed.description != "":
        pages.append(base_embed)

    return pages


async def send_pages(ctx, base_embed, contents, max_lines=20):
    pages = pages_from_list(base_embed, contents, max_lines)
    paginator = Paginator(pages=pages, emojis=custom_emojis)
    await paginator.start(ctx)
