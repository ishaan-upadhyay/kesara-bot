from pygicord import Paginator
from discord import Embed
from copy import deepcopy

custom_emojis = {
    "\U000023EA": "REPLACE (first page",
    "\U00002B05": "REPLACE (previous page)",
    "\U000023F9": "REPLACE (stop session)",
    "\U000027A1": "REPLACE (next page)",
    "\U000023E9": "REPLACE (last page)",
    "\U0001F522": "REPLACE (input numbers)",
    "\U0001F512": "REPLACE (lock unlock)"
}

def pages_from_list(base_embed: Embed, contents: list, max_lines=20):
    pages=[]

    for idx, content in enumerate(contents, start=1):
        if len(base_embed.description) + len(content) <= 2000 and (idx-1) % max_lines != 0:
            base_embed.description += f'\n{content}'
        else:
            pages.append(base_embed)
            base_embed = deepcopy(base_embed)
            base_embed.description = content
    
    return pages

async def send_pages(ctx, base_embed, contents, max_lines=20):
    pages = pages_from_list(base_embed, contents, max_lines)
    paginator = Paginator(pages=pages, emojis=custom_emojis)
    await paginator.start(ctx)