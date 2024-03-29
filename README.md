![image](https://user-images.githubusercontent.com/33141569/188013840-39407b8f-c7c2-4427-9311-009126cbecb1.png)
# Kesara
Kesara is a multipurpose Discord bot primarily featuring Last.fm, quotes and music cataloguing functionality for personal usage, written in Python. It is designed to be self-hosted on a device such as a Raspberry Pi. 

## Usage
The default prefix for Kesara is ';' but you can easily alter it for your own server using inbuilt commands. 

## Prerequisites
- Python >= 3.9
- PostgreSQL
- `discord.py`
- `pygicord`
- `tekore`
- `asyncpg`

## Credits
- [joinemn's Miso Bot](https://github.com/joinemm/miso-bot) was a valuable reference for getting Kesara to work with the Last.fm API, primarily for retrieving playcounts, code was modified to work with PostgreSQL as well as slash commands rather than conventional ones
- [esmBot's wiki entry for PostgreSQL setup](https://esmbot.github.io/esmBot/postgresql/) was especially useful to understand how to initialize PostgreSQL databases

And finally, a big thank you to everyone involved in writing the libraries used for Kesara!
