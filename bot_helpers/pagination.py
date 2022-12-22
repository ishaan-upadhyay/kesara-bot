import discord
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

class Paginator(discord.ui.View):
    def __init__(self, user_id: int, pages: List[discord.Embed], timeout: Optional[float], 
                 max_pages: int=0, current_page: int = 1, **kwargs):
        super().__init__(user_id=user_id, timeout=timeout)
        self.pages = pages
        self.current_page = current_page
        self.max_pages = max_pages if max_pages else len(pages)
        self.message = None
        self._add_buttons()
        self._enable_buttons()

    async def _add_buttons(self) -> None:
        """
        Add all the necessary buttons to the current view
        """
        first_btn = discord.ActivityTypeui.Button(style = discord.ButtonStyle.primary, label="first", emoji="<:left_double_arrow:882752531124584518>")
        async def first_page(self, interaction: discord.Interaction):
            self.current_page = 1
            await self._swap_page(interaction)
        first_btn.callback = first_page

        prev_btn = discord.ui.Button(style = discord.ButtonStyle.primary, label="prev", emoji="<:left_arrow:882751271457685504>")
        async def previous_page(self, interaction: discord.Interaction):
            self.current_page = self.current_page - 1 if self.current_page - 1 > 0 else 0
            await self._swap_page(interaction)
        prev_btn.callback = previous_page
        
        next_btn = discord.ui.Button(style = discord.ButtonStyle.primary, label="next", emoji="<:right_arrow:882751138548551700>")
        async def next_page(self, interaction: discord.Interaction):
            self.current_page = self.current_page + 1 if self.current_page + 1 < self.max_pages else self.max_pages
            await self._swap_page(interaction)
        next_btn.callback = next_page

        last_btn = discord.ui.Button(style = discord.ButtonStyle.primary, label="last", emoji="<:right_double_arrow:882752531124584518>")
        async def last_page(self, interaction: discord.Interaction):
            self.current_page = self.max_pages
            await self._swap_page(interaction)
        last_btn.callback = last_page

        self.add_item(first_btn).add_item(prev_btn).add_item(next_btn).add_item(last_btn)

    async def _enable_buttons(self) -> None:
        """
        Enables the correct buttons on current page with respect to max_pages
        """
        if self.current_page == 1:
            self.children[0].disabled = True
            self.children[1].disabled = True
        elif self.current_page == self.max_pages:
            self.children[2].disabled = True
            self.children[3].disabled = True
        else:
            for c in self.children:
                c.disabled = False

    async def _swap_page(self, interaction: discord.Interaction) -> None:
        """
        Swaps out the current embed being displayed
        """
        self._enable_buttons()
        self.message = interaction.message if hasattr(interaction, "message") else None
        await interaction.response.edit_message(embed=self.pages[self.current_page - 1], view=self)

    async def start(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(embed=self.pages[self.current_page - 1], view=self)

def pages_from_list(base_embed: discord.Embed, contents: List[str], max_lines=20) -> List[discord.Embed]:
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

async def send_pages(interaction: discord.Interaction, base_embed: discord.Embed, contents: List[str], max_lines: int=20):
    pages = pages_from_list(base_embed, contents, max_lines)
    paginator = Paginator(pages=pages)
    await paginator.start(interaction, timeout=300)